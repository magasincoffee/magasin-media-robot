"""SAYDI V5 QC01-05 opt-in, read-only chapter evidence gate.

No TTS, ASR model, auto-repair, output promotion or Control changes.
Consistent with V5 manifest, concatenation, Whisper QC, and review receipt.
"""
import argparse, array, hashlib, json, math, os, re, unicodedata, wave
from collections import Counter
from pathlib import Path
DIMENSIONS=("QC01_PAUSE","QC02_JOIN","QC03_PROSODY","QC04_PRONUNCIATION","QC05_POST_REPAIR")
def sha(p):
    with Path(p).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def read(p):
    v=json.loads(Path(p).read_text(encoding="utf-8-sig"))
    if not isinstance(v,dict):raise ValueError("JSON_NOT_OBJECT")
    return v
def parse_list(p):
    out=[]
    for line in Path(p).read_text(encoding="utf-8-sig").splitlines():
        m=re.fullmatch(r"file '([^']+)'",line)
        if not m:raise ValueError("UNEXPECTED_CONCAT_LINE")
        f=Path(m.group(1))
        if not f.is_file():raise FileNotFoundError(str(f))
        out.append(f)
    return out
def pcm_edge(p):
    with wave.open(str(p),"rb") as w:
        sr=w.getframerate();count=w.getnframes()
        if w.getsampwidth()!=2 or w.getnchannels()!=1 or sr<8000 or count<sr//10:
            raise ValueError("BAD_PCM_WAV")
        n=min(count,max(1,round(sr*.020)))
        a=array.array("h",w.readframes(n))
        w.setpos(count-n)
        b=array.array("h",w.readframes(n))
    def rms(v):
        return math.sqrt(sum(float(x)*float(x) for x in v)/len(v))/32768
    return {"seconds":count/sr,"rate":sr,"start":a[0]/32768,
            "end":b[-1]/32768,"head_rms":rms(a),"tail_rms":rms(b)}
def norm(t):
    return re.sub(r"\s+"," ",unicodedata.normalize("NFC",str(t)).casefold()).strip()
def audit(manifest,qc,concat,review=None,owner=None,candidate_qc=None,candidate_wav=None,review_concat=None):
    segments=manifest.get("segments");rows=qc.get("rows")
    if not isinstance(segments,list) or not segments or not isinstance(rows,list):
        raise ValueError("MISSING_ROWS")
    ids=[int(x["index"]) for x in segments]
    if ids!=list(range(len(ids))):raise ValueError("NONCANONICAL_SEGMENT_ORDER")
    mapping={int(x["index"]):x for x in rows}
    if len(mapping)!=len(rows) or set(mapping)!=set(ids):
        raise ValueError("WHISPER_QC_INCOMPLETE")
    # Replace ASR evidence only when exactly one candidate is SHA-pinned.
    candidate_info={}
    if candidate_qc is not None:
        extra=candidate_qc.get("rows",[])
        if not candidate_wav or len(extra)!=1:raise ValueError("CANDIDATE_SCOPE_INVALID")
        c=extra[0];index=int(c["index"])
        if index not in mapping or sha(candidate_wav)!=c.get("audio_sha256"):
            raise ValueError("CANDIDATE_ASR_HASH_MISMATCH")
        if norm(c.get("expected",""))!=norm(segments[index].get("spoken_text","")):
            raise ValueError("CANDIDATE_EXPECTED_TEXT_MISMATCH")
        mapping[index]=c
        candidate_info={"index":index,"asr_status":c.get("status"),
                        "candidate_sha256":sha(candidate_wav)}
    files=parse_list(concat)
    if len(files)!=2*len(ids):raise ValueError("AUDIO_SEGMENT_COVERAGE_MISMATCH")
    flags=[];counts=Counter();total=0.;last=None
    def issue(stage,code,idx,more=None,level="REVIEW"):
        flags.append({"stage":stage,"code":code,"segment":idx,"status":level,
                      "evidence":more or {}})
    for i,item in enumerate(segments):
        audio,gap=files[2*i:2*i+2]
        if audio.name!=f"{i:06d}.wav" or not re.fullmatch(r"gap_\d+\.wav",gap.name):
            raise ValueError("CHUNK_ORDER_MISMATCH")
        a=pcm_edge(audio);g=pcm_edge(gap);gap_ms=int(gap.stem.split("_")[1])
        if abs(g["seconds"]*1000-gap_ms)>4:raise ValueError("GAP_LENGTH_INVALID")
        counts[gap_ms]+=1
        total+=a["seconds"]+g["seconds"]
        if gap_ms>=1400:issue("QC01_PAUSE","LONG_PAUSE",i,{"gap_ms":gap_ms})
        if (item.get("heading") or item.get("parent_end")) and gap_ms<500:
            issue("QC01_PAUSE","STRUCTURAL_PAUSE_SHORT",i,{"gap_ms":gap_ms})
        if abs(a["start"])>.04 or abs(a["end"])>.04:
            issue("QC02_JOIN","NONZERO_WAV_BOUNDARY",i)
        if a["rate"]!=g["rate"]:issue("QC02_JOIN","RATE_MISMATCH",i)
        if last and last["tail_rms"]>.008 and a["head_rms"]>.008:
            db=abs(20*math.log10(a["head_rms"]/last["tail_rms"]))
            if db>12:issue("QC02_JOIN","EDGE_ENERGY_CHANGE",i,{"delta_db":round(db,1)})
        last=a
        row=mapping[i]
        if row.get("status")!="PASS":
            issue("QC04_PRONUNCIATION","ASR_REVIEW",i,{
                "asr_similarity":row.get("asr_similarity"),"reasons":row.get("reasons",[])})
        expected=item.get("spoken_text") or item.get("canonical_text","")
        if norm(row.get("expected",""))!=norm(expected):
            issue("QC04_PRONUNCIATION","QC_EXPECTED_TEXT_DIFFERS",i)
        if re.search(r"(?<!\w)[A-ZĐ]{2,6}(?!\w)",str(item.get("canonical_text",""))):
            issue("QC04_PRONUNCIATION","ABBREVIATION_NEEDS_PRONUNCIATION_CHECK",i)
        if not any(item.get(k) for k in ("narration_role","emotion","prosody_plan","semantic_scene","delivery_directive")):
            issue("QC03_PROSODY","NO_CONTEXTUAL_PROSODY_EVIDENCE",i)
    major=max(counts.values())/len(ids)
    if major>.70:
        issue("QC01_PAUSE","PAUSE_DISTRIBUTION_DOMINATED",None,
              {"dominant_gap_ms":max(counts,key=counts.get),"share":round(major,4)})
    # Owner listening evidence is never inferred from acoustic endpoint metrics.
    if owner is not None:
        if int(owner.get("chapter",-1))!=int(manifest.get("chapter_number",-1)):
            raise ValueError("OWNER_FEEDBACK_WRONG_CHAPTER")
        if owner.get("qc02_issue")=="AUDIBLE_TWO_VOICE_TONES_OWNER_CONFIRMED":
            idx=int(owner.get("qc02_join_before_segment",-1))
            if idx not in ids or int(owner.get("qc02_join_after_segment",-2))!=idx-1:
                raise ValueError("OWNER_JOIN_INDEX_INVALID")
            issue("QC02_JOIN","OWNER_CONFIRMED_TONE_DISCONTINUITY_IN_ORIGINAL",idx,
                  {"source_time_s":owner.get("qc02_source_timestamp_seconds"),
                   "replacement_status":"OWNER_APPROVED_5MIN_SAMPLE_ONLY" if review and review.get("qc02_owner_sample_accepted") else "PENDING_REPAIR"})
    receipt={}
    if review:
        if int(review.get("chapter",-1))!=int(manifest.get("chapter_number",-1)):
            raise ValueError("REVIEW_CHAPTER_MISMATCH")
        for field in ("source_mp3","source_mp3_sha256","output_mp3","output_sha256"):
            if field not in review:raise ValueError("MISSING_REVIEW_FIELD_"+field)
        if sha(review["source_mp3"])!=review["source_mp3_sha256"]:
            raise ValueError("SOURCE_HASH_MISMATCH")
        if sha(review["output_mp3"])!=review["output_sha256"]:
            raise ValueError("REVIEW_HASH_MISMATCH")
        changed=review.get("changed_spoken_segments",[])
        if len(changed)!=len(set(changed)) or any(i not in ids for i in changed):
            raise ValueError("REPAIR_INDEX_INVALID")
        if review_concat:
            revised=parse_list(review_concat)
            if len(revised)!=len(files):
                raise ValueError("REVIEW_AUDIO_COUNT_MISMATCH")
            canonical=lambda p:str(p.resolve()).casefold()
            speech=[i for i in ids if canonical(files[2*i])!=canonical(revised[2*i])]
            silence=[i for i in ids if canonical(files[2*i+1])!=canonical(revised[2*i+1])]
            if speech!=changed or silence!=review.get("changed_silence_after_segments",[]):
                raise ValueError("REVIEW_DIFF_RECEIPT_MISMATCH")
            allowed=review.get("B_rhythm_applied_only_to_window_segments",[])
            if len(allowed)==2 and not all(allowed[0]<=i<=allowed[1] for i in silence):
                raise ValueError("REVIEW_SILENCE_OUTSIDE_APPROVED_WINDOW")
        receipt={"source_hash_ok":True,"output_hash_ok":True,
                 "review_concat_diff_verified":bool(review_concat),
                 "changed_spoken_segments":changed,
                 "owner_sample_approved":bool(review.get("qc02_owner_sample_accepted",False)),
                 "whole_chapter_approved":bool(review.get("whole_chapter_owner_final",False)),
                 "rollback_file":review["source_mp3"]}
        if not receipt["whole_chapter_approved"]:
            issue("QC05_POST_REPAIR","WHOLE_CHAPTER_LISTENING_PENDING",None)
    else:issue("QC05_POST_REPAIR","REPAIR_RECEIPT_NOT_PROVIDED",None)
    stages={}
    for dim in DIMENSIONS:
        sub=[x for x in flags if x["stage"]==dim]
        stages[dim]={"status":"REVIEW" if sub else "MEASURED_NOT_HUMAN_VERIFIED",
                     "finding_count":len(sub),"reason_counts":dict(Counter(x["code"] for x in sub))}
    return {"schema":"saydi-v5-qc01-05-evidence-v1","chapter":manifest.get("chapter_number"),
            "segments_checked":len(ids),"approx_duration_s":round(total,3),
            "gap_distribution_ms":dict(sorted(counts.items())),
            "qc":stages,"findings_count":len(flags),"findings":flags,
            "repair_receipt":receipt,"candidate_asr_replacement":candidate_info,
            "owner_evidence_supplied":owner is not None,"status":"REVIEW",
            "final_eligible":False,"production_changed":False,
            "note":"ASR PASS cannot certify tone/emotion; require Owner listening, verified source and final regression."}
def main():
    p=argparse.ArgumentParser()
    for n in ("manifest","qc","concat","report"):p.add_argument("--"+n,type=Path,required=True)
    p.add_argument("--review",type=Path)
    p.add_argument("--owner-feedback",type=Path)
    p.add_argument("--candidate-qc",type=Path)
    p.add_argument("--candidate-wav",type=Path)
    p.add_argument("--review-concat",type=Path)
    p.add_argument("--enable-experimental-qc",action="store_true")
    a=p.parse_args()
    if not a.enable_experimental_qc:
        print("QC01_TO_QC05_DISABLED_DEFAULT");return 0
    result=audit(read(a.manifest),read(a.qc),a.concat,
                 read(a.review) if a.review else None,
                 read(a.owner_feedback) if a.owner_feedback else None,
                 read(a.candidate_qc) if a.candidate_qc else None,
                 a.candidate_wav,a.review_concat)
    a.report.parent.mkdir(parents=True,exist_ok=True)
    tmp=a.report.with_suffix(".pending")
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    os.replace(tmp,a.report)
    print(json.dumps({"report":str(a.report),"qc":result["qc"],"findings":result["findings_count"],"final_eligible":False}))
    return 0
if __name__=="__main__":raise SystemExit(main())
