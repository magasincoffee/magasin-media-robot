"""Read-only, opt-in V5 pre-render editorial QC.

Complements the established editorial pipeline and V5 QC01-05. Four
independent deterministic passes + an optional separately produced reviewer
receipt; does not edit source text, invoke LLM/TTS, or authorize FINAL.
Reports contain no manuscript words or filenames from private sources.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path

SCHEMA = "saydi-v5-editorial-multiround-1"
WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
HARD = {"INVALID_INDEX_ORDER", "EMPTY_CANONICAL", "TTS_TEXT_HASH_DRIFT",
        "DUPLICATE_INDEX", "MISSING_SEGMENTS"}


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def words(value: str) -> list[str]:
    return WORD_RE.findall(unicodedata.normalize("NFC", value).casefold())


def issue(pass_id: str, code: str, index: int | None = None,
          severity: str = "REVIEW", **safe_details) -> dict:
    return {"pass": pass_id, "code": code, "index": index,
            "severity": severity, **safe_details}


def inspect(manifest: dict, manifest_sha256: str, reviews: dict | None = None,
            legacy_audit: dict | None = None) -> dict:
    items = manifest.get("segments")
    if not isinstance(items, list) or not items:
        raise ValueError("MISSING_SEGMENTS")
    if not isinstance(manifest_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", manifest_sha256):
        raise ValueError("INVALID_MANIFEST_SHA")
    findings: list[dict] = []
    sequence: list[tuple[int, str, str, int]] = []
    seen: set[int] = set()
    source_verified = 0
    missing_source_provenance = 0
    legacy_opaque_hashes = 0
    for pos, obj in enumerate(items):
        if not isinstance(obj, dict):
            raise ValueError("SEGMENT_NOT_OBJECT")
        try:
            idx = int(obj["index"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("INVALID_SEGMENT_INDEX") from None
        if idx in seen:
            findings.append(issue("STRUCTURE", "DUPLICATE_INDEX", idx, "BLOCK"))
        seen.add(idx)
        if idx != pos:
            findings.append(issue("STRUCTURE", "INVALID_INDEX_ORDER", idx, "BLOCK",
                                  expected_position=pos))
        canonical = obj.get("canonical_text")
        if not isinstance(canonical, str) or not canonical.strip():
            findings.append(issue("STRUCTURE", "EMPTY_CANONICAL", idx, "BLOCK"))
            canonical = ""
        spoken = obj.get("spoken_text")
        if not isinstance(spoken, str) or not spoken.strip():
            spoken = canonical
        parent = obj.get("parent_line", idx)
        try:
            parent = int(parent)
        except (TypeError, ValueError):
            findings.append(issue("STRUCTURE", "INVALID_PARENT_GROUP", idx, "REVIEW"))
            parent = idx
        sequence.append((idx, canonical, spoken, parent))

        # Orthography pass: suspicious Unicode/text-layout artifacts, not
        # speculative "spelling corrections"; authorial language remains intact.
        for label, data in (("canonical", canonical), ("spoken", spoken)):
            if "\ufffd" in data:
                findings.append(issue("ORTHOGRAPHY", "REPLACEMENT_CHARACTER", idx,
                                      field=label))
            if any(ch in data for ch in ("\u200b", "\u200c", "\u200d", "\ufeff")):
                findings.append(issue("ORTHOGRAPHY", "INVISIBLE_FORMAT_CHARACTER", idx,
                                      field=label))
            if data != unicodedata.normalize("NFC", data):
                findings.append(issue("ORTHOGRAPHY", "NOT_NFC", idx, field=label))
            if re.search(r"(?<!\d)[,;:!?](?=[^\W\d_])", data, re.UNICODE):
                findings.append(issue("ORTHOGRAPHY", "PUNCTUATION_SPACING_REVIEW", idx,
                                      field=label))

        # Text lineage. Missing original/source spans cannot be certified.
        original = obj.get("original_text")
        if isinstance(original, str) and original:
            source_verified += 1
            if words(original) != words(canonical):
                findings.append(issue("FIDELITY", "SOURCE_CANONICAL_TOKEN_DIFF", idx))
        elif not obj.get("source_span") and not obj.get("original_span"):
            missing_source_provenance += 1
        if words(canonical) != words(spoken):
            findings.append(issue("FIDELITY", "CANONICAL_SPOKEN_TOKEN_DIFF", idx))
        editorial = obj.get("editorial_text")
        if isinstance(editorial, str) and editorial and words(editorial) != words(spoken):
            findings.append(issue("FIDELITY", "EDITORIAL_SPOKEN_TOKEN_DIFF", idx))
        declared = obj.get("tts_text_sha256")
        if isinstance(declared, str) and re.fullmatch(r"[a-fA-F0-9]{64}", declared):
            # Legacy V5's tts_text_sha256 is a producer-specific fingerprint.
            # Field observation: it is NOT sha256(spoken_text.encode("utf8")).
            # Verify actual bytes only when a producer explicitly declares
            # that encoding contract; never block all legacy chunks falsely.
            if obj.get("tts_text_hash_scheme") == "sha256_utf8_spoken_v1":
                if digest(spoken) != declared.lower():
                    findings.append(issue("FIDELITY", "TTS_TEXT_HASH_DRIFT", idx, "BLOCK"))
            else:
                legacy_opaque_hashes += 1
        else:
            findings.append(issue("FIDELITY", "TTS_TEXT_HASH_UNAVAILABLE", idx))

    if missing_source_provenance:
        findings.append(issue("FIDELITY", "SOURCE_PROVENANCE_UNVERIFIED",
                              None, count=missing_source_provenance))

    # Continuity pass: candidate fragment/overlap markers only. Never move,
    # drop, deduplicate or rewrite an author's repeated phrases automatically.
    for previous, current in zip(sequence, sequence[1:]):
        a, ac, _, pa = previous
        b, bc, _, pb = current
        wa, wb = words(ac), words(bc)
        if ac.strip() and bc.strip() and pa == pb and ac.rstrip()[-1] in ",;:":
            findings.append(issue("CONTINUITY", "CLAUSE_CUT_WITHIN_PARENT", b,
                                  previous_index=a))
        if wa and wb and wa[-1] == wb[0]:
            findings.append(issue("CONTINUITY", "POSSIBLE_BOUNDARY_REPEAT", b,
                                  previous_index=a))
        if wa and wa == wb:
            findings.append(issue("CONTINUITY", "POSSIBLE_DUPLICATE_UNIT", b,
                                  previous_index=a))

    # Bind the existing legacy editorial audit to the exact chapter/source and
    # voice: this is useful inherited evidence, NOT an independent spellcheck.
    legacy_summary = {"status": "NOT_SUPPLIED"}
    if legacy_audit is not None:
        if not isinstance(legacy_audit, dict):
            raise ValueError("INVALID_LEGACY_EDITORIAL_AUDIT")
        same_source = bool(manifest.get("source_sha256")) and (
            legacy_audit.get("source_sha256") == manifest["source_sha256"])
        same_reference = bool(manifest.get("reference_sha256")) and (
            legacy_audit.get("reference_sha256") == manifest["reference_sha256"])
        same_count = legacy_audit.get("segments") == len(items)
        if not (same_source and same_reference and same_count):
            findings.append(issue("LEGACY_AUDIT", "LEGACY_AUDIT_BINDING_MISMATCH",
                                  None, "BLOCK"))
        suspect_count = legacy_audit.get("legacy_paraphrase_suspects")
        if type(suspect_count) is not int or suspect_count < 0:
            raise ValueError("INVALID_LEGACY_PARAPHRASE_COUNT")
        if suspect_count:
            findings.append(issue("LEGACY_AUDIT", "LEGACY_PARAPHRASE_REVIEW",
                                  None, count=suspect_count))
        if legacy_audit.get("word_integrity") != "PASS":
            findings.append(issue("LEGACY_AUDIT", "LEGACY_WORD_INTEGRITY_NOT_PASS"))
        if legacy_audit.get("v5_spoken_text_diff") is not False:
            findings.append(issue("LEGACY_AUDIT", "V5_SPOKEN_TEXT_DIFFERENCE"))
        if legacy_audit.get("canonical_source_utf8") is not True:
            findings.append(issue("LEGACY_AUDIT", "CANONICAL_UTF8_UNVERIFIED"))
        legacy_summary = {
            "status": "BOUND_TO_SOURCE_AND_VOICE" if same_source and same_reference and same_count else "BINDING_FAILED",
            "legacy_paraphrase_suspects": suspect_count,
            "word_integrity": legacy_audit.get("word_integrity"),
            "v5_spoken_text_diff": legacy_audit.get("v5_spoken_text_diff"),
            "canonical_source_utf8": legacy_audit.get("canonical_source_utf8"),
            "independent_proof": False,
        }

    # Separately produced editorial-verification receipts only; independence
    # cannot be inferred from repeating the same algorithm. No fake PASS.
    reviewer_status = "PENDING"
    reviewer_count = 0
    if reviews is not None:
        if not isinstance(reviews, dict) or reviews.get("manifest_sha256") != manifest_sha256:
            raise ValueError("STALE_EDITORIAL_REVIEW_RECEIPT")
        reviewers = reviews.get("validators")
        if not isinstance(reviewers, list):
            raise ValueError("INVALID_EDITORIAL_REVIEW_RECEIPT")
        ids: set[str] = set()
        for reviewer in reviewers:
            if not isinstance(reviewer, dict) or not isinstance(reviewer.get("validator_id"), str):
                raise ValueError("INVALID_REVIEWER")
            rid = reviewer["validator_id"].strip()
            if not rid or rid in ids or reviewer.get("manifest_sha256") != manifest_sha256:
                raise ValueError("REVIEWER_NOT_DISTINCT_OR_STALE")
            ids.add(rid)
            if reviewer.get("status") not in {"PASS", "REVIEW"}:
                raise ValueError("INVALID_REVIEWER_STATUS")
            if reviewer.get("status") == "REVIEW":
                findings.append(issue("INDEPENDENT", "INDEPENDENT_EDITORIAL_REVIEW", None))
        reviewer_count = len(ids)
        if reviewer_count >= 2:
            reviewer_status = "RECEIPTS_PRESENT_NOT_PROOF_OF_SEMANTIC_CORRECTNESS"
        else:
            reviewer_status = "INSUFFICIENT_INDEPENDENT_REVIEWS"
    if reviewer_count < 2:
        findings.append(issue("INDEPENDENT", "INDEPENDENT_REVIEW_PENDING", None))
    counts = Counter((x["pass"], x["code"]) for x in findings)
    blocks = sum(x["severity"] == "BLOCK" for x in findings)
    return {
        "schema": SCHEMA,
        "manifest_sha256": manifest_sha256,
        "chapter": manifest.get("chapter_number"),
        "segment_count": len(items),
        "source_text_verified_segments": source_verified,
        "missing_source_provenance_count": missing_source_provenance,
        "legacy_opaque_tts_hash_count": legacy_opaque_hashes,
        "legacy_editorial_audit": legacy_summary,
        "passes": ["STRUCTURE", "ORTHOGRAPHY", "CONTINUITY", "FIDELITY",
                   "INDEPENDENT"],
        "finding_count": len(findings),
        "blocking_count": blocks,
        "counts": [{"pass": p, "code": c, "count": n}
                   for (p, c), n in sorted(counts.items())],
        "findings": findings,
        "independent_review_status": reviewer_status,
        "status": "BLOCKED" if blocks else "REVIEW",
        "production_changed": False,
        "source_changed": False,
        "auto_repair": False,
        "owner_final": False,
        "warning": "Deterministic screens and external receipts cannot prove spelling, meaning, accent or natural narration. All material findings require source-aware review."
    }


def write_report(path: Path, report: dict) -> None:
    if path.exists():
        raise FileExistsError("REPORT_ALREADY_EXISTS")
    path.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    fd, name = tempfile.mkstemp(prefix=".editorial-", suffix=".pending", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
        if path.exists():
            raise FileExistsError("REPORT_ALREADY_EXISTS")
        # Exclusive creation: do not silently replace another report.
        with open(path, "x", encoding="utf-8") as target:
            target.write(Path(name).read_text(encoding="utf-8"))
    finally:
        Path(name).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Isolated V5 editorial multiround pre-TTS evidence QC")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--independent-reviews", type=Path)
    parser.add_argument("--legacy-editorial-audit", type=Path)
    parser.add_argument("--enable-experimental-editorial-qc", action="store_true")
    args = parser.parse_args()
    if not args.enable_experimental_editorial_qc:
        print("V5_EDITORIAL_QC_DISABLED_DEFAULT")
        return 0
    raw = args.manifest.read_bytes()
    manifest = json.loads(raw.decode("utf-8-sig"))
    reviews = (json.loads(args.independent_reviews.read_text(encoding="utf-8-sig"))
               if args.independent_reviews else None)
    legacy = (json.loads(args.legacy_editorial_audit.read_text(encoding="utf-8-sig"))
              if args.legacy_editorial_audit else None)
    report = inspect(manifest, hashlib.sha256(raw).hexdigest(), reviews, legacy)
    write_report(args.report, report)
    print(json.dumps({"report": str(args.report), "status": report["status"],
                      "segments": report["segment_count"],
                      "findings": report["finding_count"], "owner_final": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
