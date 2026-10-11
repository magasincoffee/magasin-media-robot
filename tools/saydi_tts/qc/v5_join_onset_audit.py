"""SAYDI V5 P0/P1: read-only native-WAV split/onset/trim and pause audit.

Screens structural *risk*, never judges Vietnamese pronunciation or voice.
No models, TTS, original audio changes, or automatic release.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import wave
from collections import Counter
from pathlib import Path

SCHEMA = "saydi-v5-join-onset-risk-v1"
GAP_NAME = re.compile(r"gap_([0-9]{1,5})\.wav\Z")
FILE_ROW = re.compile(r"file '([^']+)'")
REVIEW_TRIM_MS = 50
SEVERE_TRIM_MS = 150
MAX_SEGMENTS = 2000


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def wav_duration_ms(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as w:
            if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getframerate() != 48000:
                raise ValueError("UNEXPECTED_MONO_48KHZ_16BIT_FORMAT")
            if w.getnframes() < 1:
                raise ValueError("EMPTY_WAV")
            return w.getnframes() * 1000.0 / w.getframerate()
    except (OSError, EOFError, wave.Error) as exc:
        raise ValueError("WAV_DECODE_UNAVAILABLE") from exc


def audit(manifest: dict, raw_dir: Path, cleaned_dir: Path,
          concat_data: bytes, manifest_sha256: str) -> dict:
    segments = manifest.get("segments") if isinstance(manifest, dict) else None
    if not isinstance(segments, list) or not 1 <= len(segments) <= MAX_SEGMENTS:
        raise ValueError("INVALID_SEGMENT_LIST")
    if not isinstance(manifest_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", manifest_sha256):
        raise ValueError("INVALID_MANIFEST_SHA")
    lines = concat_data.decode("utf-8-sig").splitlines()
    if len(lines) != 2 * len(segments):
        raise ValueError("INVALID_CONCAT_FILE_COUNT")
    trims = []
    pause_ms = []
    punctuation = Counter()
    split_indices = []
    for idx, seg in enumerate(segments):
        if type(seg.get("index")) is not int or seg["index"] != idx:
            raise ValueError("NONCANONICAL_SEGMENT_INDEX")
        current = FILE_ROW.fullmatch(lines[idx * 2].strip())
        pause = FILE_ROW.fullmatch(lines[idx * 2 + 1].strip())
        if not current or not pause:
            raise ValueError("UNSAFE_CONCAT_SYNTAX")
        name = f"{idx:06d}.wav"
        if Path(current.group(1)).name != name:
            raise ValueError("OUT_OF_ORDER_CONCAT_WAV")
        gap_name = Path(pause.group(1)).name
        match = GAP_NAME.fullmatch(gap_name)
        if not match:
            raise ValueError("UNKNOWN_CONCAT_GAP")
        actual_gap = int(match.group(1))
        if not 50 <= actual_gap <= 2500:
            raise ValueError("OUT_OF_RANGE_GAP")
        pause_ms.append(actual_gap)
        raw_duration = wav_duration_ms(raw_dir / name)
        clean_duration = wav_duration_ms(cleaned_dir / name)
        trim = max(0.0, raw_duration - clean_duration)
        if clean_duration > raw_duration + 0.5:
            raise ValueError("CLEANED_WAV_LONGER_THAN_ORIGINAL")
        if trim > 3000:
            raise ValueError("EXCESSIVE_TRIM_UNTRUSTED")
        if trim > REVIEW_TRIM_MS:
            trims.append({"index": idx, "removed_ms": round(trim, 1),
                          "review": True, "error_confirmed": False})
        text = seg.get("canonical_text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("EMPTY_CANONICAL_SEGMENT")
        trimmed = text.rstrip()
        end = trimmed[-1] if trimmed[-1] in ".,;:!?…" else "OTHER"
        punctuation[end] += 1
        if idx < len(segments)-1 and (
            not seg.get("parent_end")
            and end in {"OTHER", ",", ";", ":"}
        ):
            split_indices.append(idx)
    counts = Counter(pause_ms)
    most_common_gap, most_common_n = counts.most_common(1)[0]
    repetitive = most_common_n / len(segments) >= .75
    severe = [x for x in trims if x["removed_ms"] > SEVERE_TRIM_MS]
    warnings = []
    if trims:
        warnings.append("CHUNK_EDGE_TRIM_REQUIRES_LISTENING")
    if repetitive:
        warnings.append("REPETITIVE_PAUSE_DURATION_REVIEW")
    if split_indices:
        warnings.append("SEMANTIC_CLAUSE_SPLIT_REVIEW")
    return {
        "schema": SCHEMA, "chapter": manifest.get("chapter_number"),
        "manifest_sha256": manifest_sha256, "segments": len(segments),
        "raw_vs_clean_trim_above_50ms_count": len(trims),
        "trim_above_150ms_count": len(severe),
        "trim_review_indices": trims[:100],
        "trim_review_indices_omitted": max(0, len(trims)-100),
        "dominant_pause_ms": most_common_gap,
        "dominant_pause_count": most_common_n,
        "repetitive_pause": repetitive,
        "pause_duration_histogram_ms": dict(sorted(counts.items())),
        "source_punctuation_counts": dict(sorted(punctuation.items())),
        "clauses_without_strong_end_punctuation_indices": split_indices[:100],
        "clauses_omitted": max(0, len(split_indices)-100),
        "warnings": warnings,
        "status": "REVIEW_NOT_FINAL",
        "voice_phonemes_verified": False,
        "technical_edge_risks_are_confirmed_audio_errors": False,
        "allow_automatic_repair": False, "allow_automatic_promotion": False,
        "owner_approved": False, "production_modified": False,
    }


def write_new_report(output: Path, report: dict) -> None:
    if any(part.casefold() in {"chunks", "stitch_cleaned", "owner_approved_natural_v5"}
           for part in output.parts):
        raise ValueError("PRODUCTION_WRITE_REFUSED")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> int:
    p = argparse.ArgumentParser(description="Read-only V5 native WAV onset and joining risk audit")
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--raw-dir", required=True, type=Path)
    p.add_argument("--clean-dir", required=True, type=Path)
    p.add_argument("--concat", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--enable-onset-join-audit", action="store_true")
    args = p.parse_args()
    if not args.enable_onset_join_audit:
        print("ONSET_JOIN_AUDIT_DISABLED_DEFAULT")
        return 0
    raw = args.manifest.read_bytes()
    result = audit(json.loads(raw.decode("utf-8-sig")), args.raw_dir, args.clean_dir,
                   args.concat.read_bytes(), sha(raw))
    write_new_report(args.output, result)
    print(json.dumps({"status": result["status"], "review_trim_count":
        result["raw_vs_clean_trim_above_50ms_count"],
        "repeat_pause": result["repetitive_pause"],
        "owner_approved": False, "production_modified": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
