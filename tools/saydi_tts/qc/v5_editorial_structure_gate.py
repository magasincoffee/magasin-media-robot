"""Deterministic offline V5 narration-structure preflight (metadata only).

Identifies separate headings, page furniture/translator annotations, and
mid-clause fragment breaks *before* TTS. Never silently removes author text,
modifies chunks, authorizes production or claims natural voice approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from v5_source_lineage import verify_source_hash

SCHEMA = "saydi-v5-editorial-structure-audit-v1"
PAGE_ALONE = re.compile(r"^\s*[-–—]?\s*\d{1,4}\s*[-–—]?\s*$")
PAGE_LABEL = re.compile(
    r"^\s*(?:trang|page)\s*[:#\-]?\s*\d{1,4}(?:\s*/\s*\d{1,4})?\s*$",
    flags=re.I,
)
ANNOTATION = re.compile(
    r"^\s*(?:chú thích|chú giải|ghi chú|lời người dịch|người dịch chú thích)\s*[:.\-]",
    flags=re.I,
)
NOTE_REFERENCE = re.compile(r"^\s*(?:\[\d{1,3}\]|\(\d{1,3}\))\s+\S")
STRONG_END = (".", "!", "?", "…")


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def audit(manifest: dict, source_bytes: bytes, manifest_digest: str) -> dict:
    if not isinstance(manifest_digest, str) or not re.fullmatch("[a-f0-9]{64}", manifest_digest):
        raise ValueError("INVALID_MANIFEST_HASH")
    if not isinstance(manifest, dict):
        raise ValueError("INVALID_MANIFEST")
    # Exact SHA-bound source identity, with CRLF-to-LF variant if it matches.
    source_method, source = verify_source_hash(manifest, source_bytes)
    items = manifest.get("segments")
    if not isinstance(items, list) or not 1 <= len(items) <= 2000:
        raise ValueError("BAD_SEGMENT_LIST")
    headings, cuts, mixed, title_rework = [], [], [], []
    for index, segment in enumerate(items):
        if not isinstance(segment, dict) or type(segment.get("index")) is not int or segment["index"] != index:
            raise ValueError("BAD_SEGMENT_ORDER")
        text = segment.get("canonical_text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("EMPTY_TEXT")
        if segment.get("heading"):
            headings.append(index)
            if segment.get("pause_before_ms", 0) == 0 and not segment.get("prosody_role"):
                title_rework.append(index)
        if index + 1 < len(items):
            successor = items[index + 1]
            if (not segment.get("parent_end")
                    and segment.get("parent_line") == successor.get("parent_line")
                    and text.rstrip()[-1] not in STRONG_END):
                cuts.append(index)
        if PAGE_ALONE.fullmatch(text.strip()) or PAGE_LABEL.fullmatch(text.strip()):
            mixed.append({"index": index, "type": "PAGE_LIKE_CHUNK_REVIEW"})
        elif ANNOTATION.match(text.strip()) or NOTE_REFERENCE.match(text.strip()):
            mixed.append({"index": index, "type": "ANNOTATION_LIKE_CHUNK_REVIEW"})
    source_lines = source.splitlines()
    source_candidates = []
    for line_index, line in enumerate(source_lines):
        value = line.strip()
        if not value:
            continue
        if PAGE_LABEL.fullmatch(value):
            typ = "EXPLICIT_PAGE_LABEL_CANDIDATE"
        elif PAGE_ALONE.fullmatch(value):
            typ = "AMBIGUOUS_STANDALONE_NUMBER_CANDIDATE"
        elif ANNOTATION.match(value):
            typ = "ANNOTATION_OR_TRANSLATOR_NOTE_REVIEW"
        elif NOTE_REFERENCE.match(value):
            typ = "FOOTNOTE_REFERENCE_REVIEW"
        else:
            continue
        source_candidates.append({
            "line_index": line_index, "type": typ,
            "do_not_speak_without_review": typ == "EXPLICIT_PAGE_LABEL_CANDIDATE",
            "automatic_deletion_allowed": False,
        })
    return {
        "schema": SCHEMA,
        "chapter": manifest.get("chapter_number"),
        "manifest_sha256": manifest_digest,
        "source_sha256": manifest.get("source_sha256"),
        "source_hash_method": source_method,
        "segments": len(items),
        "headings": len(headings),
        "heading_indices": headings,
        "heading_prosody_review_indices": title_rework,
        "same_parent_weak_split_count": len(cuts),
        "same_parent_weak_split_indices": cuts[:100],
        "same_parent_weak_split_omitted": max(0, len(cuts)-100),
        "source_page_and_annotation_candidates": source_candidates[:100],
        "source_page_and_annotation_omitted": max(0, len(source_candidates)-100),
        "manifest_page_and_annotation_candidates": mixed[:100],
        "manifest_page_and_annotation_omitted": max(0, len(mixed)-100),
        "no_unknown_numbers_deleted": True,
        "all_original_text_preserved": True,
        "new_heading_audio_verified": False,
        "narrative_continuity_verified": False,
        "automatic_text_suppression_allowed": False,
        "automatic_rerender_allowed": False,
        "owner_final": False,
        "status": "REVIEW_EDITORIAL_NOT_FINAL",
        "production_modified": False,
    }


def save_new(output: Path, report: dict) -> None:
    if any(part.casefold() in {"owner_approved_natural_v5", "stitch_cleaned", "chunks"}
           for part in output.parts):
        raise ValueError("REFUSE_PRODUCTION_PATH")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-render source structure and nonspoken furniture audit")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-utf8", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--enable-structure-review", action="store_true")
    args = parser.parse_args()
    if not args.enable_structure_review:
        print("EDITORIAL_STRUCTURE_AUDIT_DISABLED_DEFAULT")
        return 0
    raw = args.manifest.read_bytes()
    m = json.loads(raw.decode("utf-8-sig"))
    report = audit(m, args.source_utf8.read_bytes(), digest(raw))
    save_new(args.output, report)
    print(json.dumps({
        "status": report["status"],
        "headings": report["headings"],
        "weak_splits": report["same_parent_weak_split_count"],
        "furniture_candidates": len(report["source_page_and_annotation_candidates"]),
        "owner_final": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
