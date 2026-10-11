"""SAYDI P1: offline, read-only repair readiness contract.

Consumes an existing V5 QC01-05 audit, bounded owner-confirmed worklist,
immutable chapter manifest, and optional P0 source-lineage record.
No calls into the VieNeu worker, scheduler, audio filesystem or network.
A passing contract is NOT permission to execute, promote or publish audio.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "saydi-v5-p1-repair-readiness-v1"
HEX = re.compile(r"[a-f0-9]{64}\Z")


def is_sha(value):
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(manifest: dict, audit: dict, worklist: dict,
            manifest_sha256: str, lineage: dict | None = None) -> dict:
    if not is_sha(manifest_sha256):
        raise ValueError("MANIFEST_SHA_INVALID")
    if worklist.get("schema") != "saydi-v5-bounded-qc-worklist-v1":
        raise ValueError("WRONG_WORKLIST_SCHEMA")
    if audit.get("schema") != "saydi-v5-qc01-05-audit-v1" or audit.get("final") is not False:
        raise ValueError("WRONG_AUDIT_SCHEMA_OR_RELEASE_STATE")
    items = manifest.get("segments")
    if not isinstance(items, list) or not items:
        raise ValueError("MANIFEST_SEGMENTS_MISSING")
    chapter = manifest.get("chapter_number")
    if type(chapter) is not int or worklist.get("chapter") != chapter or audit.get("chapter") != chapter:
        raise ValueError("CHAPTER_MISMATCH")
    source_sha = manifest.get("source_sha256")
    voice_sha = manifest.get("reference_sha256")
    if not is_sha(source_sha) or not is_sha(voice_sha):
        raise ValueError("SOURCE_OR_VOICE_FINGERPRINT_MISSING")
    review_sha = audit.get("review_mp3_sha256")
    if not is_sha(review_sha) or worklist.get("source_review_audio_sha256") != review_sha:
        raise ValueError("STALE_CHAPTER_REVIEW_AUDIO")
    if audit.get("segment_count") != len(items) or worklist.get("status") != "REVIEW_NOT_FINAL":
        raise ValueError("AUDIT_COUNT_OR_WORKLIST_STATE_MISMATCH")
    if (worklist.get("no_autonomous_tts_started") is not True
            or worklist.get("no_auto_final") is not True
            or worklist.get("integration_status") != "DRAFT_SOT_GATE_NOT_PRODUCTION"):
        raise ValueError("UNSAFE_WORKLIST_PRODUCTION_STATE")
    qc04 = audit.get("qc04", {})
    rows = qc04.get("issues") if isinstance(qc04, dict) else None
    if not isinstance(rows, list):
        raise ValueError("AUDIT_QC04_MISSING")
    observed: dict[int, str] = {}
    for row in rows:
        if not isinstance(row, dict) or type(row.get("index")) is not int:
            raise ValueError("QC04_ROW_INVALID")
        idx = row["index"]
        audio = row.get("checked_audio_sha256")
        if not 0 <= idx < len(items) or idx in observed or not is_sha(audio):
            raise ValueError("QC04_AUDIO_PROVENANCE_INVALID")
        observed[idx] = audio
    eligible_lineage = False
    if lineage is not None:
        if (not isinstance(lineage, dict)
                or lineage.get("schema") != "saydi-v5-source-lineage-1"
                or lineage.get("manifest_hash_method") != "RAW_MANIFEST_BYTES"
                or lineage.get("manifest_sha256") != manifest_sha256
                or lineage.get("source_sha256") != source_sha):
            raise ValueError("STALE_P0_SOURCE_LINEAGE")
        spans = lineage.get("source_spans")
        verified_spans = isinstance(spans, list) and len(spans) == len(items)
        total_words = 0
        if verified_spans:
            for i, (span, item) in enumerate(zip(spans, items)):
                canonical = item.get("canonical_text")
                if not isinstance(canonical, str):
                    verified_spans = False
                    break
                words = re.findall(r"[^\W_]+", canonical, re.UNICODE)
                count = len(words)
                if (not isinstance(span, dict)
                        or span.get("index") != i
                        or span.get("verified") is not True
                        or type(span.get("word_count")) is not int
                        or count == 0
                        or span["word_count"] != count
                        or span.get("source_word_start") != total_words
                        or span.get("source_word_end_exclusive") != total_words + count
                        or span.get("canonical_sha256") != checksum(item["canonical_text"].encode("utf-8"))
                        or not is_sha(span.get("source_span_sha256"))):
                    verified_spans = False
                    break
                total_words += count
        eligible_lineage = (
            lineage.get("lexical_equivalence") == "PASS"
            and lineage.get("punctuation_equivalence") == "PASS"
            and lineage.get("verified_source_span_count") == len(items)
            and verified_spans
            and lineage.get("source_token_count") == total_words
            and lineage.get("canonical_token_count") == total_words
            and lineage.get("first_mismatch_source_word_offset") is None
        )
    actions = worklist.get("confirmed_actions")
    if not isinstance(actions, list) or type(worklist.get("confirmed_action_total")) is not int:
        raise ValueError("WORKLIST_ACTIONS_MALFORMED")
    if worklist["confirmed_action_total"] < len(actions) or len(actions) > 8:
        raise ValueError("WORKLIST_BUDGET_INVALID")
    intents = []
    seen: set[int] = set()
    for action in actions:
        idx = action.get("segment") if isinstance(action, dict) else None
        if type(idx) is not int or idx not in observed or idx in seen:
            raise ValueError("ACTION_NOT_IN_AUDIT_OR_DUPLICATE")
        seen.add(idx)
        expected = observed[idx]
        if action.get("original_audio_sha256") != expected:
            raise ValueError("OWNER_EVENT_AUDIO_SHA_MISMATCH")
        if (action.get("action") != "STAGE_ONE_V5_SEGMENT_CANDIDATE"
                or action.get("auto_run") is not False
                or action.get("owner_acceptance_after") is not True):
            raise ValueError("UNSAFE_REPAIR_ACTION")
        if action.get("code") not in {
            "OWNER_CONFIRMED_TONE_DRIFT",
            "OWNER_CONFIRMED_WRONG_WORD",
            "OWNER_CONFIRMED_AUDIBLE_CLICK",
        }:
            raise ValueError("UNSUPPORTED_CONFIRMED_DEFECT_CODE")
        if (type(items[idx].get("index")) is not int
                or items[idx]["index"] != idx):
            raise ValueError("MANIFEST_SEGMENT_INDEX_CHANGED")
        used = action.get("attempts_used")
        remaining = action.get("remaining_attempts")
        if (type(used) is not int or type(remaining) is not int
                or not 0 <= used < 2 or remaining != 2-used):
            raise ValueError("RETRY_BUDGET_VIOLATION")
        item = items[idx]
        text_fingerprint = item.get("tts_text_sha256")
        if not is_sha(text_fingerprint):
            raise ValueError("IMMUTABLE_TTS_FINGERPRINT_MISSING")
        reasons = []
        if not eligible_lineage:
            reasons.append("P0_SOURCE_FIDELITY_NOT_PROVEN")
        # Even when all available hashes match, this read-only contract has
        # never verified WAV bytes on the production host or Owner approval.
        reasons.extend(["HOST_WAV_AND_NEIGHBOR_SHA_NOT_CHECKED",
                        "INDEPENDENT_AUDIO_QC_PENDING",
                        "SOT_PRODUCTION_AUTHORIZATION_PENDING"])
        intents.append({
            "segment": idx,
            "original_audio_sha256": expected,
            "tts_text_fingerprint": text_fingerprint,
            "attempts_remaining": remaining,
            "action": "INSPECT_ONLY_NO_DISPATCH",
            "reasons_not_executable": reasons,
            "approved_to_dispatch": False,
            "approved_to_promote": False,
        })
    return {
        "schema": SCHEMA,
        "chapter": chapter,
        "manifest_sha256": manifest_sha256,
        "source_sha256": source_sha,
        "voice_reference_sha256": voice_sha,
        "original_review_mp3_sha256": review_sha,
        "p0_source_lineage_status": "P0_LINEAGE_RECEIPT_SCREEN_ONLY"
        if eligible_lineage else "PENDING_OR_INCOMPLETE",
        "confirmed_actions_in_worklist": worklist["confirmed_action_total"],
        "actions_exposed_for_inspection": len(intents),
        "intents": intents,
        "state": "REVIEW_ONLY_NO_RUNTIME_PERMISSION",
        "dry_run": True,
        "worker_started": False,
        "audio_written": False,
        "automatic_promotion": False,
        "owner_final": False,
    }


def main():
    p = argparse.ArgumentParser(description="P1 bounded repair dry-run, zero side effects")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--worklist", type=Path, required=True)
    p.add_argument("--lineage", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--enable-p1-dryrun", action="store_true")
    a = p.parse_args()
    if not a.enable_p1_dryrun:
        print("SAYDI_P1_DRYRUN_OFF_BY_DEFAULT")
        return 0
    raw = a.manifest.read_bytes()
    read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
    out = prepare(json.loads(raw.decode("utf-8-sig")), read(a.audit),
                  read(a.worklist), checksum(raw),
                  read(a.lineage) if a.lineage else None)
    if any(x.casefold() in {"chunks", "owner_approved_natural_v5", "stitch_cleaned"}
           for x in a.output.parts):
        raise ValueError("OUTPUT_IS_PRODUCTION_LOCATION")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"state": out["state"],
                      "intents": len(out["intents"]),
                      "worker_started": False, "owner_final": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
