"""Read-only plan validator for future SAYDI-009, 010 and 011 work.

A plan receipt cannot authorize export, robot control, Windows installation,
SOT task advancement, or an audiobook FINAL state.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCHEMA = "saydi-future-009-011-inventory-v1"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
TARGETS = ("SAYDI-009", "SAYDI-010", "SAYDI-011")
TASK_GATES = {
    "SAYDI-009": ("source_fidelity", "chapter_qa", "owner_chapter_listening",
                  "chapter_mp3_decode", "chapter_metadata", "m4b_export_decode"),
    "SAYDI-010": ("authenticated_owner_control", "persistent_stop_latch",
                  "off_after_reboot", "worker_mutex_ram", "status_from_heartbeat"),
    "SAYDI-011": ("clean_windows_install", "credentials_local_only",
                  "resume_without_duplicate_render", "reversible_rollback",
                  "end_to_end_accepted"),
}


def _sha(v: object, size: int) -> bool:
    return isinstance(v, str) and (HEX40 if size == 40 else HEX64).fullmatch(v) is not None


def assess(plan: dict, expected_head: str, expected_main_sot: str) -> dict:
    if not _sha(expected_head, 40) or not _sha(expected_main_sot, 40):
        raise ValueError("INVALID_EXPECTED_REFS")
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise ValueError("INVALID_PLAN_SCHEMA")
    if set(plan) != {"schema", "pr_head_sha", "sot_main_sha", "chapters", "targets"}:
        raise ValueError("UNSAFE_OR_MISSING_PLAN_KEYS")
    if plan["pr_head_sha"] != expected_head or plan["sot_main_sha"] != expected_main_sot:
        raise ValueError("STALE_PR_OR_SOT_REF")
    if plan["targets"] != list(TARGETS):
        raise ValueError("AUTHORITY_TASK_ORDER_CHANGED")
    chapters = plan["chapters"]
    if not isinstance(chapters, list) or not chapters or len(chapters) > 1000:
        raise ValueError("INVALID_CHAPTER_INVENTORY")
    findings = []
    seen = set()
    for row in chapters:
        if not isinstance(row, dict) or set(row) != {
            "chapter", "segment_count", "master_mp3_sha256", "qc_report_sha256",
            "duration_ms", "material_review_count"}:
            raise ValueError("INVALID_CHAPTER_ROW")
        n = row["chapter"]
        if type(n) is not int or n < 1 or n in seen:
            raise ValueError("INVALID_OR_DUPLICATE_CHAPTER")
        if seen and n <= max(seen):
            raise ValueError("CHAPTER_ORDER_CHANGED")
        seen.add(n)
        if type(row["segment_count"]) is not int or row["segment_count"] < 1:
            raise ValueError("INVALID_SEGMENT_COUNT")
        if type(row["material_review_count"]) is not int or row["material_review_count"] < 0:
            raise ValueError("INVALID_REVIEW_COUNT")
        if row["master_mp3_sha256"] is not None and not _sha(row["master_mp3_sha256"], 64):
            raise ValueError("INVALID_MASTER_DIGEST")
        if row["qc_report_sha256"] is not None and not _sha(row["qc_report_sha256"], 64):
            raise ValueError("INVALID_QC_DIGEST")
        if row["duration_ms"] is not None and (
                type(row["duration_ms"]) is not int or row["duration_ms"] <= 0):
            raise ValueError("INVALID_DURATION")
        if row["master_mp3_sha256"] is None or row["duration_ms"] is None:
            findings.append({"chapter": n, "reason": "MASTER_OR_DURATION_NOT_YET_PROVEN"})
        if row["qc_report_sha256"] is None:
            findings.append({"chapter": n, "reason": "QC_REPORT_NOT_YET_PROVEN"})
        if row["material_review_count"]:
            findings.append({"chapter": n, "reason": "UNRESOLVED_MATERIAL_REVIEW",
                             "count": row["material_review_count"]})
    return {"schema": SCHEMA, "pr_head_sha": expected_head,
            "sot_main_sha": expected_main_sot,
            "chapters_in_inventory": len(chapters),
            "chapter_findings": findings,
            "planned_targets": [{"task_id": task, "required_field_gates": list(TASK_GATES[task]),
                                 "task_ready": False, "task_done": False} for task in TARGETS],
            "reported_audio_sha_authenticated": False,
            "ffprobe_or_m4b_validation_done": False,
            "owner_acceptance_authenticated": False,
            "control_center_cutover_verified": False,
            "clean_machine_installer_verified": False,
            "status": "PREPARATION_ONLY_NO_SOT_ADVANCE",
            "export_allowed": False, "control_start_allowed": False,
            "installer_deploy_allowed": False, "chapter_final": False,
            "warning": "SHA-looking strings and plan fields cannot prove real audio quality, FFprobe, owner acceptance or host readiness"}


def main() -> int:
    p = argparse.ArgumentParser(description="Offline SAYDI-009/010/011 planning inventory")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--expected-head", required=True)
    p.add_argument("--expected-sot", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--enable-next-task-inventory", action="store_true")
    args = p.parse_args()
    if not args.enable_next_task_inventory:
        print("SAYDI_FUTURE_INVENTORY_DISABLED_DEFAULT")
        return 0
    report = assess(json.loads(args.input.read_text(encoding="utf-8-sig")),
                    args.expected_head, args.expected_sot)
    if any(x.lower() in {"chunks", "owner_approved_natural_v5", "stitch_cleaned"}
           for x in args.output.parts):
        raise ValueError("REFUSE_PRODUCTION_OUTPUT_PATH")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=False, indent=2)
        out.write("\n")
    print(json.dumps({"status": report["status"], "chapters": report["chapters_in_inventory"],
                      "chapter_final": False, "export_allowed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
