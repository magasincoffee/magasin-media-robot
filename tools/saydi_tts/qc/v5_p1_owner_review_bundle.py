"""Build source-safe read-only Owner QC review data for existing Control Center.

Combines SHA-bound QC reports into timecoded exceptions without source text.
Never declares a chapter FINAL or authorizes Control START/STOP/repair actions.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCHEMA = "saydi-v5-p1-owner-review-bundle-1"
HEX = re.compile(r"[a-f0-9]{64}\Z")
ALLOWED_WAV = "saydi-v5-p1-wav-candidate-gate-1"


def _sha(s) -> bool:
    return isinstance(s, str) and HEX.fullmatch(s) is not None


def build(editorial: dict, repair: dict, qc01_05: dict,
          wav_reports: list[dict] | None = None, max_exceptions: int = 25,
          exception_offset: int = 0) -> dict:
    if (type(max_exceptions) is not int or not 1 <= max_exceptions <= 25
            or type(exception_offset) is not int or exception_offset < 0):
        raise ValueError("INVALID_EXCEPTION_PAGE")
    if (editorial.get("schema") != "saydi-v5-editorial-multiround-1"
            or repair.get("schema") != "saydi-v5-p1-repair-readiness-v1"
            or qc01_05.get("schema") != "saydi-v5-qc01-05-audit-v1"):
        raise ValueError("UNKNOWN_REPORT_SCHEMA")
    chapter = editorial.get("chapter")
    if type(chapter) is not int or chapter != repair.get("chapter") or chapter != qc01_05.get("chapter"):
        raise ValueError("CHAPTER_REPORT_MISMATCH")
    manifest_sha = repair.get("manifest_sha256")
    if not _sha(manifest_sha) or editorial.get("manifest_sha256") != manifest_sha:
        raise ValueError("STALE_EDITORIAL_MANIFEST")
    if not _sha(repair.get("source_sha256")) or not _sha(repair.get("voice_reference_sha256")):
        raise ValueError("UNBOUND_SOURCE_OR_VOICE")
    if (editorial.get("owner_final") is not False or qc01_05.get("final") is not False
            or repair.get("owner_final") is not False
            or repair.get("state") != "REVIEW_ONLY_NO_RUNTIME_PERMISSION"
            or repair.get("worker_started") is not False
            or repair.get("automatic_promotion") is not False):
        raise ValueError("UNSAFE_EXTERNAL_REPORT_STATE")
    # Reports from staging might contain words/paths beyond these fields.
    # Explicitly whitelist only indices, codes, counts, and times.
    findings = editorial.get("findings")
    if not isinstance(findings, list):
        raise ValueError("EDITORIAL_FINDINGS_MISSING")
    qc04 = qc01_05.get("qc04")
    if not isinstance(qc04, dict) or not isinstance(qc04.get("issues"), list):
        raise ValueError("QC04_EVIDENCE_MISSING")
    time_by_segment = {}
    for item in qc04["issues"]:
        idx, when = item.get("index"), item.get("at_s")
        if type(idx) is int and idx >= 0 and type(when) in (float, int) and when >= 0:
            time_by_segment[idx] = round(float(when), 2)
    exceptions = []
    for item in findings:
        if not isinstance(item, dict):
            raise ValueError("EDITORIAL_FINDING_MALFORMED")
        code = item.get("code")
        idx = item.get("index")
        if not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9_]{3,70}", code):
            raise ValueError("UNSAFE_FINDING_CODE")
        if idx is not None and (type(idx) is not int or idx < 0):
            raise ValueError("INVALID_FINDING_INDEX")
        exceptions.append({"origin": "EDITORIAL", "code": code, "index": idx,
                           "at_s": time_by_segment.get(idx),
                           "count": item.get("count") if type(item.get("count")) is int else 1})
    for item in qc04["issues"]:
        idx = item.get("index")
        if type(idx) is not int or idx < 0:
            raise ValueError("INVALID_ASR_INDEX")
        if item.get("checked_asr_status") == "REVIEW":
            exceptions.append({"origin": "ASR", "code": "ASR_REVIEW_NOT_CONFIRMED_WRONG_WORD",
                               "index": idx, "at_s": time_by_segment.get(idx), "count": 1})
    wav_reports = wav_reports or []
    if not isinstance(wav_reports, list):
        raise ValueError("INVALID_WAV_REPORTS")
    for report in wav_reports:
        if (not isinstance(report, dict) or report.get("schema") != ALLOWED_WAV
                or report.get("manifest_sha256") != manifest_sha
                or report.get("source_sha256") != repair["source_sha256"]
                or report.get("voice_reference_sha256") != repair["voice_reference_sha256"]
                or report.get("owner_final") is not False
                or report.get("approved_to_promote") is not False
                or report.get("worker_started") is not False):
            raise ValueError("STALE_OR_UNSAFE_WAV_CANDIDATE_REPORT")
        idx = report.get("segment")
        if type(idx) is not int or idx < 0:
            raise ValueError("INVALID_WAV_SEGMENT")
        if not isinstance(report.get("flags"), list):
            raise ValueError("INVALID_WAV_FLAGS")
        for flag in report["flags"]:
            if not isinstance(flag, str) or not re.fullmatch(r"[A-Z0-9_]{3,70}", flag):
                raise ValueError("UNSAFE_WAV_FLAG")
            exceptions.append({"origin": "WAV_CANDIDATE", "code": flag,
                               "index": idx, "at_s": time_by_segment.get(idx), "count": 1})
    # This is a sample for Owner UI. Full exception totals remain visible and
    # additional pages are requested by offset; no silent issue suppression.
    returned = exceptions[exception_offset:exception_offset+max_exceptions]
    return {"schema": SCHEMA, "chapter": chapter,
            "manifest_sha256": manifest_sha,
            "source_sha256": repair["source_sha256"],
            "voice_reference_sha256": repair["voice_reference_sha256"],
            "scope": "READ_ONLY_QC_REVIEW_NOT_OWNER_ACCEPTANCE",
            "p0_source_lineage": repair["p0_source_lineage_status"],
            "editorial_status": editorial.get("status"),
            "independent_editorial_review": editorial.get("independent_review_status"),
            "candidate_count": len(wav_reports),
            "repair_intents": repair.get("actions_exposed_for_inspection"),
            "exception_total": len(exceptions),
            "exception_offset": exception_offset,
            "exceptions_shown": len(returned),
            "exceptions_remaining": max(0,len(exceptions)-(exception_offset+max_exceptions)),
            "exceptions": returned,
            "unverified_gates": ["ORIGINAL_MANUSCRIPT_SEMANTICS",
                "VIETNAMESE_PRONUNCIATION_AND_TONE", "TIMBRE_AND_EMOTION_LISTENING",
                "POSTREPAIR_NEIGHBOR_IMMUTABILITY", "EXACT_HEAD_CI_AND_REBOOT",
                "OWNER_CHAPTER_LISTENING_AND_SOT_AUTHORIZATION"],
            "status": "REVIEW_NOT_FINAL", "dispatch_allowed": False,
            "production_changed": False, "owner_final": False}


def main() -> int:
    p = argparse.ArgumentParser(description="Existing SAYDI owner QC read-only bundle")
    p.add_argument("--editorial", type=Path, required=True)
    p.add_argument("--repair-readiness", type=Path, required=True)
    p.add_argument("--qc01-05", type=Path, required=True)
    p.add_argument("--wav-candidate", type=Path, action="append", default=[])
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--exception-offset", type=int, default=0)
    p.add_argument("--enable-review-bundle", action="store_true")
    args = p.parse_args()
    if not args.enable_review_bundle:
        print("SAYDI_OWNER_REVIEW_BUNDLE_DISABLED_DEFAULT")
        return 0
    read=lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
    result=build(read(args.editorial), read(args.repair_readiness),
                 read(args.qc01_05), [read(x) for x in args.wav_candidate],
                 exception_offset=args.exception_offset)
    if any(x.casefold() in {"chunks", "stitch_cleaned", "owner_approved_natural_v5"}
           for x in args.output.parts):
        raise ValueError("OUTPUT_IS_PRODUCTION_LOCATION")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(json.dumps({"state": result["status"], "exceptions": result["exception_total"],
                      "owner_final": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
