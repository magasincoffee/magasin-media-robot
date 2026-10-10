"""SAYDI V5 bounded QC worklist: typed observations -> auditable actions.

Does not call VieNeu, Whisper or worker jobs. Stays disconnected from production
until SOT parent gate and owner acceptance allow integration.
"""
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path

ALLOWED_CODES={"OWNER_CONFIRMED_TONE_DRIFT","OWNER_CONFIRMED_WRONG_WORD",
               "OWNER_CONFIRMED_AUDIBLE_CLICK"}
MAX_ATTEMPTS=2
def read(path):
    o=json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(o,dict):raise ValueError("EXPECTED_OBJECT")
    return o
def validate_confirmation(event, report):
    if set(event)-{"index","code","audio_sha256","approved_sample_sha256","resolved"}:
        raise ValueError("UNSUPPORTED_OWNER_CONFIRMATION_FIELDS")
    i=event.get("index")
    if not isinstance(i,int) or i<0 or i>=report["segment_count"]:
        raise ValueError("INVALID_CONFIRMED_INDEX")
    if event.get("code") not in ALLOWED_CODES:
        raise ValueError("UNSUPPORTED_QC_DEFECT")
    if not isinstance(event.get("audio_sha256"),str) or len(event["audio_sha256"])!=64:
        raise ValueError("CONFIRMATION_REQUIRES_SHA256")
    return True

def create_worklist(report, attempts=None, owner_events=None, max_auto=3,
                    max_owner=12):
    if report.get("schema")!="saydi-v5-qc01-05-audit-v1" or report.get("final") is not False:
        raise ValueError("INVALID_QC_SOURCE")
    if not (1<=max_auto<=8 and 1<=max_owner<=50):
        raise ValueError("INVALID_WORK_LIMIT")
    attempts=attempts or {}
    owner_events=owner_events or []
    if not isinstance(attempts,dict) or not isinstance(owner_events,list):
        raise ValueError("INVALID_QC_STATE")
    all_items=report["qc04"]["issues"]
    current={x["index"]:x for x in all_items}
    queued=[]
    resolved=[]
    blocked=[]
    for evt in owner_events:
        validate_confirmation(evt,report)
        idx=evt["index"]
        if idx not in current or current[idx]["checked_audio_sha256"]!=evt["audio_sha256"]:
            raise ValueError("STALE_OR_UNTRACKED_AUDIO_CONFIRMATION")
        count=attempts.get(str(idx),0)
        if type(count) is not int or not 0<=count<=MAX_ATTEMPTS:
            raise ValueError("INVALID_ATTEMPT_LEDGER")
        if evt.get("resolved") is True:
            if not evt.get("approved_sample_sha256") or len(evt["approved_sample_sha256"])!=64:
                raise ValueError("RESOLUTION_REQUIRES_SAMPLE_PROOF")
            resolved.append({"segment":idx,"outcome":"OWNER_SCOPED_SAMPLE_ACCEPTED",
                             "audio_sha256":evt["audio_sha256"],
                             "sample_sha256":evt["approved_sample_sha256"],
                             "whole_chapter_accepted":False})
        elif count>=MAX_ATTEMPTS:
            blocked.append({"segment":idx,"reason":"MAX_2_ATTEMPTS_EXHAUSTED",
                            "next":"HUMAN_REVIEW"})
        else:
            queued.append({"segment":idx,"code":evt["code"],
                           "original_audio_sha256":evt["audio_sha256"],
                           "attempts_used":count,"remaining_attempts":MAX_ATTEMPTS-count,
                           "action":"STAGE_ONE_V5_SEGMENT_CANDIDATE",
                           "auto_run":False,"owner_acceptance_after":True})
    # A false-positive ASR alone is never permission to regenerate speech.
    ambiguous=[{"segment":x["index"],"at_s":x["at_s"],
        "reason":"ASR_SUSPECT_SECOND_SIGNAL_REQUIRED",
        "classes":[z["class"] for z in x["asr_issue_classes"]][:3],
        "special_term":x.get("special_term")}
        for x in all_items if x["index"] not in
        {y["segment"] for y in resolved+blocked+queued}]
    semantic=[{"segment":x["index"],"at_s":x["at_s"],
               "suggestion":x["suggested_delivery"],"action":"EDITORIAL_REVIEW_ONLY"}
              for x in report["qc03"]["semantic_candidates"]]
    # Candidate work only after explicit owner confirmation, never if the
    # available chapter observation is missing/changed since confirmation.
    return {
        "schema":"saydi-v5-bounded-qc-worklist-v1",
        "chapter":report["chapter"],
        "source_review_audio_sha256":report["review_mp3_sha256"],
        "status":"REVIEW_NOT_FINAL",
        "qc01_approved_sample_only":report["qc01"]["owner_approved_scope"]=="SAMPLE_ONLY",
        "qc02_approved_sample_only":report["qc02"]["approved_sample_not_entire_chapter"],
        "qc03_emotion_review_total":report["qc03"]["candidate_total"],
        "qc04_asr_review_total":report["qc04"]["checked_asr_review_count"],
        "qc05_bounded_attempts":MAX_ATTEMPTS,
        "confirmed_actions":queued[:max_auto],
        "confirmed_action_total":len(queued),
        "resolved_sample_events":resolved,
        "blocked_after_retry":blocked,
        "owner_review_queue":(ambiguous+semantic)[:max_owner],
        "owner_review_total":len(ambiguous)+len(semantic),
        "technical_edge_review_count":report["qc02"]["flag_count"],
        "no_autonomous_tts_started":True,
        "no_audio_written":True,
        "no_auto_final":True,
        "privacy":"INDEX_AND_HASH_ONLY_NO_MANUSCRIPT",
        "integration_status":"DRAFT_SOT_GATE_NOT_PRODUCTION"
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--audit",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--attempts")
    p.add_argument("--events")
    p.add_argument("--opt-in",action="store_true")
    args=p.parse_args()
    if not args.opt_in:
        raise SystemExit("BOUNDED_QC_WORKLIST_DISABLED_BY_DEFAULT")
    result=create_worklist(read(args.audit),read(args.attempts) if args.attempts else {},
                           read(args.events).get("events",[]) if args.events else [])
    dest=Path(args.out)
    if dest.exists():raise FileExistsError("REFUSE_OVERWRITE_WORKLIST")
    if any(k.lower() in {"chunks","owner_approved_natural_v5","stitch_cleaned"} for k in dest.parts):
        raise ValueError("WORKLIST_CANNOT_WRITE_PRODUCTION")
    dest.parent.mkdir(parents=True,exist_ok=True)
    temp=dest.with_suffix(".pending")
    if temp.exists():raise FileExistsError("PENDING_WORKLIST_EXISTS")
    temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    os.replace(temp,dest)
    print(json.dumps({"output":str(dest),"state":result["status"],
        "confirmed_repair_actions":result["confirmed_action_total"],
        "owner_review_total":result["owner_review_total"],
        "resolved_sample_events":len(result["resolved_sample_events"]),
        "automatic_tts_started":False},ensure_ascii=True))

if __name__=="__main__":
    main()
