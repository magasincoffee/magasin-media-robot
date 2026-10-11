"""Read-only review triage for legacy V5 editorial drift.

Works from the existing V5 manifest alone; former V4 spoken text is NOT the
original manuscript. Issues are hypotheses requiring a SHA-matched source
lineage audit and independent review. Never performs correction or TTS.
"""
from __future__ import annotations

import argparse
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import json
import re
import unicodedata
from pathlib import Path

SCHEMA = "saydi-v5-editorial-review-triage-v1"
WORDS = re.compile(r"[^\W_]+", re.UNICODE)
MAX_REVIEW = 25


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tokens(text: str) -> list[str]:
    return WORDS.findall(unicodedata.normalize("NFC", text).casefold())


def without_accents(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").replace("đ", "d")


def diff_types(old: str, current: str) -> set[str]:
    """Conservative lexical categories, not proof of a transcription error."""
    a, b = tokens(old), tokens(current)
    if a == b:
        return set()
    findings: set[str] = set()
    if len(a) == len(b) and sorted(a) == sorted(b):
        return {"POSSIBLE_WORD_REORDER"}
    for opcode, a0, a1, b0, b1 in SequenceMatcher(
        None, a, b, autojunk=False
    ).get_opcodes():
        if opcode == "equal":
            continue
        aa, bb = a[a0:a1], b[b0:b1]
        if opcode == "delete":
            findings.add("POSSIBLE_MISSING_WORDS")
        elif opcode == "insert":
            findings.add("POSSIBLE_ADDED_WORDS")
        elif len(aa) == len(bb) and all(
            without_accents(x) == without_accents(y) for x, y in zip(aa, bb)
        ):
            findings.add("POSSIBLE_VIETNAMESE_DIACRITIC_DRIFT")
        else:
            findings.add("POSSIBLE_WORD_REPLACEMENT")
    return findings


def triage(manifest: dict, manifest_sha256: str,
           legacy_audit: dict | None = None, max_review: int = MAX_REVIEW,
           review_offset: int = 0) -> dict:
    if not isinstance(manifest_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", manifest_sha256):
        raise ValueError("INVALID_MANIFEST_SHA")
    if type(max_review) is not int or not 1 <= max_review <= MAX_REVIEW:
        raise ValueError("INVALID_REVIEW_LIMIT")
    if type(review_offset) is not int or review_offset < 0:
        raise ValueError("INVALID_REVIEW_OFFSET")
    segments = manifest.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("INVALID_SEGMENTS")
    counts: Counter[str] = Counter()
    issues: list[dict] = []
    for idx, segment in enumerate(segments):
        if not isinstance(segment, dict) or type(segment.get("index")) is not int or segment["index"] != idx:
            raise ValueError("INVALID_SEGMENT_ORDER")
        canonical = segment.get("canonical_text")
        spoken = segment.get("spoken_text") or canonical
        if not isinstance(canonical, str) or not canonical.strip() or not isinstance(spoken, str):
            raise ValueError("INVALID_CANONICAL_TEXT")
        flags: set[str] = set()
        # Prior generation is only a *candidate* to review against source,
        # never a canonical truth or an authorization to restore old wording.
        prior = segment.get("origin_spoken_text_v4")
        if isinstance(prior, str) and prior.strip():
            flags.update(diff_types(prior, canonical))
        editorial = segment.get("editorial_text")
        if isinstance(editorial, str) and editorial.strip():
            flags.update("EDITORIAL_" + code for code in diff_types(editorial, canonical))
        flags.update("SPOKEN_" + code for code in diff_types(canonical, spoken))
        if idx and segment.get("parent_line") == segments[idx-1].get("parent_line"):
            previous = segments[idx-1].get("canonical_text", "")
            if isinstance(previous, str) and previous.rstrip().endswith((",", ";", ":")):
                flags.add("POSSIBLE_CLAUSE_CUT")
        if flags:
            counts.update(flags)
            issues.append({
                "index": idx,
                "parent_line": segment.get("parent_line") if type(segment.get("parent_line")) is int else None,
                "codes": sorted(flags),
                "canonical_sha256": sha(canonical.encode("utf-8")),
                "original_source_verified": False,
                "review_required": True,
            })
    legacy_state = "NOT_PROVIDED"
    legacy_number = None
    if legacy_audit is not None:
        if not isinstance(legacy_audit, dict) or (
            legacy_audit.get("source_sha256") != manifest.get("source_sha256")
            or legacy_audit.get("reference_sha256") != manifest.get("reference_sha256")
            or legacy_audit.get("segments") != len(segments)
        ):
            raise ValueError("STALE_LEGACY_AUDIT")
        legacy_number = legacy_audit.get("legacy_paraphrase_suspects")
        if type(legacy_number) is not int or legacy_number < 0:
            raise ValueError("INVALID_LEGACY_SUSPECT_COUNT")
        legacy_state = "BOUND_AGGREGATE_ONLY"
    return {
        "schema": SCHEMA,
        "manifest_sha256": manifest_sha256,
        "chapter": manifest.get("chapter_number"),
        "segment_count": len(segments),
        "potentially_affected_segments": len(issues),
        "counts_by_code": dict(sorted(counts.items())),
        "legacy_audit_status": legacy_state,
        "legacy_paraphrase_suspect_count": legacy_number,
        "legacy_count_does_not_identify_segments": True,
        "review_offset": review_offset,
        "review_items_shown": len(issues[review_offset:review_offset+max_review]),
        "review_queue": issues[review_offset:review_offset+max_review],
        "review_items_not_shown": max(0, len(issues)-(review_offset+max_review)),
        "status": "REVIEW",
        "source_semantic_approval": False,
        "audio_pronunciation_verified": False,
        "production_modified": False,
        "auto_repair": False,
        "owner_final": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="V5 editorial candidate triage (offline, read-only)")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--legacy-audit", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--review-offset", type=int, default=0)
    p.add_argument("--enable-experimental-triage", action="store_true")
    args = p.parse_args()
    if not args.enable_experimental_triage:
        print("V5_EDITORIAL_TRIAGE_DISABLED_DEFAULT")
        return 0
    raw = args.manifest.read_bytes()
    old = (json.loads(args.legacy_audit.read_text(encoding="utf-8-sig"))
           if args.legacy_audit else None)
    result = triage(json.loads(raw.decode("utf-8-sig")), sha(raw), old,
                    review_offset=args.review_offset)
    if any(x.casefold() in {"chunks", "owner_approved_natural_v5", "stitch_cleaned"}
           for x in args.output.parts):
        raise ValueError("REFUSE_PRODUCTION_REPORT")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"status": result["status"], "review_segments": len(result["review_queue"]),
                      "potentially_affected_segments": result["potentially_affected_segments"],
                      "owner_final": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
