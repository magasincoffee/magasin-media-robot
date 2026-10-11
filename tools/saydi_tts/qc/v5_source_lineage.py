"""Opt-in source-text lineage verification for V5 audiobook editorial manifests.

Runs entirely locally against an explicit UTF-8 manuscript; no ASR, LLM,
TTS, worker, OCR or network. Produces ONLY hashes/indices/counts, never book
text. Lexical equivalence is not independent spelling or listening approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path

WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
HEX_SHA = re.compile(r"[a-f0-9]{64}\Z")
SCHEMA = "saydi-v5-source-lineage-1"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def utf8_sha(text: str) -> str:
    return digest(text.encode("utf-8"))


def token_matches(text: str) -> list[re.Match]:
    return list(WORD_RE.finditer(unicodedata.normalize("NFC", text).casefold()))


def verify_source_hash(manifest: dict, source_bytes: bytes) -> tuple[str, str]:
    expected = manifest.get("source_sha256")
    if not isinstance(expected, str) or not HEX_SHA.fullmatch(expected.lower()):
        raise ValueError("SOURCE_SHA256_UNAVAILABLE")
    try:
        decoded = source_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("SOURCE_NOT_UTF8_TEXT") from exc
    normalized = unicodedata.normalize("NFC", decoded)
    variants = (
        ("RAW_BYTES", digest(source_bytes)),
        ("NFC_UTF8", utf8_sha(normalized)),
        ("NFC_STRIPPED_UTF8", utf8_sha(normalized.strip())),
    )
    for method, actual in variants:
        if expected.lower() == actual:
            return method, normalized
    raise ValueError("SOURCE_SHA256_MISMATCH")


def audit(manifest: dict, source_bytes: bytes, legacy: dict | None = None,
          manifest_sha256: str | None = None) -> dict:
    if manifest_sha256 is None:
        manifest_sha256 = utf8_sha(json.dumps(manifest, ensure_ascii=False,
                                        sort_keys=True, separators=(",", ":")))
        hash_method = "CANONICAL_JSON"
    else:
        if not isinstance(manifest_sha256, str) or not HEX_SHA.fullmatch(manifest_sha256):
            raise ValueError("INVALID_MANIFEST_SHA256")
        hash_method = "RAW_MANIFEST_BYTES"
    method, source = verify_source_hash(manifest, source_bytes)
    segments = manifest.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("MISSING_SEGMENTS")
    source_norm = unicodedata.normalize("NFC", source).casefold()
    smatches = list(WORD_RE.finditer(source_norm))
    sw = [x.group() for x in smatches]
    current: list[str] = []
    lengths: list[int] = []
    findings: list[dict] = []
    for offset, segment in enumerate(segments):
        if not isinstance(segment, dict) or type(segment.get("index")) is not int:
            raise ValueError("INVALID_SEGMENT")
        if segment["index"] != offset:
            raise ValueError("NONCANONICAL_ORDER")
        canonical = segment.get("canonical_text")
        if not isinstance(canonical, str) or not canonical.strip():
            raise ValueError("EMPTY_CANONICAL")
        part = [x.group() for x in token_matches(canonical)]
        current.extend(part)
        lengths.append(len(part))
        spoken = segment.get("spoken_text", canonical)
        if not isinstance(spoken, str):
            raise ValueError("INVALID_SPOKEN_TEXT")
        if [x.group() for x in token_matches(spoken)] != part:
            findings.append({"code": "SPOKEN_CANONICAL_TOKEN_MISMATCH",
                             "index": offset, "status": "REVIEW"})
        editorial = segment.get("editorial_text")
        if isinstance(editorial, str) and [x.group() for x in token_matches(editorial)] != part:
            findings.append({"code": "EDITORIAL_CANONICAL_TOKEN_MISMATCH",
                             "index": offset, "status": "REVIEW"})

    matched = current == sw
    # Punctuation affects spoken pauses and sentence continuity even when
    # every lexical token is present. Only flag differences, never overwrite.
    source_punctuation = re.findall(r"[,.!?;:…]", source)
    rendered_punctuation = re.findall(
        r"[,.!?;:…]", " ".join(s["canonical_text"] for s in segments))
    if source_punctuation != rendered_punctuation:
        findings.append({"code": "PUNCTUATION_ORDER_OR_COUNT_DIFF",
                         "source_mark_count": len(source_punctuation),
                         "canonical_mark_count": len(rendered_punctuation),
                         "status": "REVIEW"})
    first_mismatch = None
    if not matched:
        for pos in range(min(len(sw), len(current))):
            if sw[pos] != current[pos]:
                first_mismatch = pos
                break
        if first_mismatch is None:
            first_mismatch = min(len(sw), len(current))
        findings.append({"code": "CHAPTER_CANONICAL_SOURCE_TOKEN_MISMATCH",
                         "source_token_offset": first_mismatch,
                         "status": "REVIEW"})
    spans: list[dict] = []
    token_start = 0
    # Never assign provenance for any chunk if full chapter token order differs;
    # partial matching can silently misalign after an insertion or deletion.
    if matched:
        for seg, length in zip(segments, lengths):
            idx = seg["index"]
            end = token_start + length
            if length:
                start_char = smatches[token_start].start()
                end_char = smatches[end-1].end()
                span_digest = utf8_sha(source_norm[start_char:end_char])
            else:
                span_digest = utf8_sha("")
                findings.append({"code": "NO_LEXICAL_TOKENS", "index": idx,
                                 "status": "REVIEW"})
            spans.append({
                "index": idx, "source_word_start": token_start,
                "source_word_end_exclusive": end, "word_count": length,
                "source_span_sha256": span_digest,
                "canonical_sha256": utf8_sha(seg["canonical_text"]),
                "previous_index": idx-1 if idx else None,
                "next_index": idx+1 if idx+1<len(segments) else None,
                "verified": bool(length),
            })
            token_start = end
    legacy_status = "NOT_SUPPLIED"
    suspects = None
    if legacy is not None:
        if not isinstance(legacy, dict) or (
            legacy.get("source_sha256") != manifest.get("source_sha256")
            or legacy.get("reference_sha256") != manifest.get("reference_sha256")
            or legacy.get("segments") != len(segments)):
            raise ValueError("STALE_LEGACY_AUDIT")
        suspects = legacy.get("legacy_paraphrase_suspects")
        if type(suspects) is not int or suspects < 0:
            raise ValueError("BAD_LEGACY_AUDIT_COUNT")
        legacy_status = "SHA_BOUND_PREVIOUS_AUDIT_REVIEW_ONLY"
        if suspects:
            findings.append({"code": "LEGACY_PARAPHRASE_SUSPECTS",
                             "count": suspects, "status": "REVIEW"})
    # Source hash+token coverage alone CANNOT prove semantics or absence
    # of authorial punctuation, spelling, accent or performed voice errors.
    return {
        "schema": SCHEMA,
        "chapter": manifest.get("chapter_number"),
        "manifest_sha256": manifest_sha256,
        "manifest_hash_method": hash_method,
        "source_sha256": manifest["source_sha256"],
        "source_hash_method": method,
        "source_token_count": len(sw),
        "canonical_token_count": len(current),
        "lexical_equivalence": "PASS" if matched else "REVIEW",
        "punctuation_equivalence": "PASS" if source_punctuation == rendered_punctuation else "REVIEW",
        "first_mismatch_source_word_offset": first_mismatch,
        "verified_source_span_count": len(spans),
        "source_spans": spans,
        "legacy_status": legacy_status,
        "legacy_paraphrase_suspects": suspects,
        "findings": findings,
        "status": "REVIEW",
        "independent_spelling_verified": False,
        "independent_semantics_verified": False,
        "voice_pronunciation_verified": False,
        "production_modified": False,
        "auto_render": False,
        "owner_final": False,
    }


def save_new_report(path: Path, report: dict) -> None:
    if any(x.casefold() in {"chunks", "stitch_cleaned", "owner_approved_natural_v5"}
           for x in path.parts):
        raise ValueError("NO_REPORT_IN_PRODUCTION")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--source-utf8", required=True, type=Path)
    p.add_argument("--legacy-audit", type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--opt-in-source-lineage", action="store_true")
    args = p.parse_args()
    if not args.opt_in_source_lineage:
        print("SOURCE_LINEAGE_OFF_BY_DEFAULT")
        return 0
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    legacy = (json.loads(args.legacy_audit.read_text(encoding="utf-8-sig"))
              if args.legacy_audit else None)
    report = audit(manifest, args.source_utf8.read_bytes(), legacy,
                   manifest_sha256=digest(manifest_bytes))
    save_new_report(args.out, report)
    print(json.dumps({"schema": SCHEMA, "status": report["status"],
                      "source_spans": report["verified_source_span_count"],
                      "lexical_equivalence": report["lexical_equivalence"],
                      "findings": len(report["findings"]),
                      "owner_final": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
