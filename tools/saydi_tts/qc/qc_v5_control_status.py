"""Compact read-only QC01-QC05 operator status from verified local evidence.

A minimal, optional JSON bridge for the existing SAYDI Control/robot.
No new UI, no TTS, no QA rerun, no scheduler hook. Disabled by default.
"""
import argparse, json, os
from pathlib import Path
def read(path):
    v=json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(v,dict):raise ValueError("QC_REPORT_NOT_OBJECT")
    return v
def summarize(five,semantic,pronunciation,plan):
    if len({five["chapter"],semantic["chapter"],pronunciation["chapter"],plan["chapter"]})!=1:
        raise ValueError("MIXED_CHAPTER_ARTIFACTS")
    if five.get("final_eligible") or plan.get("automatic_execution"):
        raise ValueError("UNSAFE_QC_STATE")
    qc=five["qc"]
    return {"schema":"saydi-v5-control-qc-status-v1",
      "chapter":five["chapter"],"qc_version":"V5_EXPERIMENTAL",
      "phase":"QC_REVIEW_PENDING",
      "qc01":{"status":qc["QC01_PAUSE"]["status"],
              "findings":qc["QC01_PAUSE"]["finding_count"]},
      "qc02":{"status":qc["QC02_JOIN"]["status"],
              "findings":qc["QC02_JOIN"]["finding_count"]},
      "qc03":{"status":qc["QC03_PROSODY"]["status"],
              "missing_directives":len(semantic["segments"]),
              "context_groups":semantic["scene_groups_by_parent_line"]},
      "qc04":{"status":qc["QC04_PRONUNCIATION"]["status"],
              "suspected_asr_mismatch_segments":pronunciation["review_segments"],
              "asr_ambiguity_counts":pronunciation["counts_by_kind"]},
      "qc05":{"status":qc["QC05_POST_REPAIR"]["status"],
              "proposed_bounded_repairs":len(plan["targets"]),
              "attempts_per_segment_max":plan["max_attempts_per_segment"],
              "production_promotion_allowed":False},
      "findings_total":five["findings_count"],
      "warning":"These are evidence flags, not confirmed audio faults. Owner 5-minute sample acceptance is not chapter FINAL.",
      "report_path_available":True,"final":False,
      "feature_enabled_in_production":False,"robot_job_unchanged":True}
def main():
    p=argparse.ArgumentParser()
    for key in ("five","semantic","pronunciation","plan","output"):
        p.add_argument("--"+key,type=Path,required=True)
    p.add_argument("--enable-readonly-status",action="store_true")
    args=p.parse_args()
    if not args.enable_readonly_status:
        print("QC_CONTROL_STATUS_DISABLED_DEFAULT");return 0
    data=summarize(read(args.five),read(args.semantic),read(args.pronunciation),read(args.plan))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    tmp=args.output.with_suffix(".pending")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    os.replace(tmp,args.output)
    print(json.dumps({"chapter":data["chapter"],"status":data["phase"],
                      "qc05_plan_count":data["qc05"]["proposed_bounded_repairs"],"output":str(args.output)}))
if __name__=="__main__":raise SystemExit(main())
