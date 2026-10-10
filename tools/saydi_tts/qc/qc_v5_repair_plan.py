"""SAYDI V5 QC05 bounded repair proposal — does not call VieNeu or mutate jobs.

Feed selections to the EXISTING safe repair workflow only after separate
Owner/control and staging-gate approval. Never auto-rerender ASR-only anomalies.
"""
import argparse, hashlib, json, os
from pathlib import Path

def read(path):
    v=json.loads(Path(path).read_text(encoding="utf8"))
    if not isinstance(v,dict):raise ValueError("INVALID_JSON")
    return v
def sha(p):
    with Path(p).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def build(report,manifest,baseline,ledger=None,max_targets=8):
    if not 1<=max_targets<=8:raise ValueError("TOO_MANY_TARGETS")
    if report.get("final_eligible") or report.get("status")!="REVIEW":
        raise ValueError("UNEXPECTED_RELEASE_STATE")
    if int(report["chapter"])!=int(manifest["chapter_number"]):
        raise ValueError("REPORT_CHAPTER_MISMATCH")
    if len(manifest["segments"])!=report["segments_checked"]:
        raise ValueError("REPORT_SEGMENT_COUNT_MISMATCH")
    rows={int(r["index"]):r for r in baseline["rows"]}
    if len(rows)!=len(manifest["segments"]):
        raise ValueError("BASELINE_QC_NOT_COMPLETE")
    attempts=ledger or {}
    if not isinstance(attempts,dict):raise ValueError("BAD_ATTEMPT_LEDGER")
    protected=set(report.get("repair_receipt",{}).get("changed_spoken_segments",[]))
    candidate=report.get("candidate_asr_replacement",{})
    # Owner-chosen R2 must never be clobbered by a generic 'lowest ASR' run.
    if candidate:protected.add(int(candidate["index"]))
    asr=set(int(f["segment"]) for f in report["findings"]
            if f["code"]=="ASR_REVIEW" and f["segment"] is not None)
    prioritized=sorted(asr,key=lambda i:(float(rows[i].get("asr_similarity",0)),i))
    todo=[];blocked=[]
    for i in prioritized:
        used=int(attempts.get(str(i),0))
        if i in protected:
            blocked.append({"segment":i,"reason":"OWNER_APPROVED_CANDIDATE_PRESERVE"})
        elif used>=2:
            blocked.append({"segment":i,"reason":"MAX_TWO_ATTEMPTS"})
        elif len(todo)<max_targets:
            item=manifest["segments"][i]
            if not item.get("tts_text_sha256") or not item.get("reference_fingerprint"):
                blocked.append({"segment":i,"reason":"MISSING_IMMUTABLE_FINGERPRINT"})
                continue
            todo.append({"segment":i,"remaining_attempts":2-used,
                 "canonical_text_sha256":item["tts_text_sha256"],
                 "voice_reference_sha256":item["reference_fingerprint"],
                 "baseline_asr_similarity":rows[i].get("asr_similarity"),
                 "status":"CANDIDATE_ONLY_NEEDS_POST_RENDER_QC"})
    return {"schema":"saydi-v5-qc05-targeted-proposal-v1",
       "chapter":int(report["chapter"]),"source_fingerprint":manifest.get("source_sha256"),
       "reference_fingerprint":manifest.get("reference_sha256"),
       "qc_report_sha256":hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest(),
       "targets":todo,"preserved":blocked,"unallocated_review":max(0,len(asr)-len(todo)-len(blocked)),
       "cpu_threads":1,"min_free_ram_gb":1.5,"max_attempts_per_segment":2,
       "tts_engine":"USE_EXISTING_VIENEU_V5",
       "must_verify_source_hash":True,"run_whisper_only_after_tts_unloaded":True,
       "requires_owner_or_safe_policy_approval":True,"automatic_execution":False,
       "status":"PROPOSAL_ONLY","promotion_allowed":False}
def main():
    p=argparse.ArgumentParser()
    for key in ("qc-report","manifest","baseline-qc","output"):
        p.add_argument("--"+key,type=Path,required=True)
    p.add_argument("--attempt-ledger",type=Path)
    p.add_argument("--max-targets",type=int,default=8)
    p.add_argument("--enable-experimental-plan",action="store_true")
    a=p.parse_args()
    if not a.enable_experimental_plan:
        print("REPAIR_PLAN_DISABLED_DEFAULT");return 0
    data=build(read(a.qc_report),read(a.manifest),read(a.baseline_qc),
               read(a.attempt_ledger) if a.attempt_ledger else None,a.max_targets)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    tmp=a.output.with_suffix(".pending")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    os.replace(tmp,a.output)
    print(json.dumps({"status":data["status"],"targets":len(data["targets"]),
                      "blocked":len(data["preserved"]),"output":str(a.output)}))
    return 0
if __name__=="__main__":raise SystemExit(main())
