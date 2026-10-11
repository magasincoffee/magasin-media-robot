"""Read-only forensic gate for words weakened or lost at a new TTS chunk onset.

Compares raw and post-cleaning PCM *at exact sample alignment*. Separates
head trimming from end trimming and attenuation during the first 12 ms.
It cannot determine phonemes/first-word intelligibility without listening;
it never modifies WAVs, models, manifests, checkpoints, or release state.
"""
from __future__ import annotations
import argparse
import array
import hashlib
import json
import math
import re
import wave
from pathlib import Path

SCHEMA = "saydi-v5-first-word-onset-v1"
SAMPLE_RATE = 48000
SAMPLE_BYTES = 2
FADE_WINDOW_MS = 12
ACTIVE_START_RMS = .003
ATTENUATION_REVIEW_RATIO = .80


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pcm_data(path: Path) -> bytes:
    try:
        with wave.open(str(path), "rb") as w:
            if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1, 2, 48000):
                raise ValueError("WAV_FORMAT_NOT_MONO_48K_PCM16")
            raw = w.readframes(w.getnframes())
    except (OSError, wave.Error, EOFError) as exc:
        raise ValueError("WAV_NOT_READABLE") from exc
    if len(raw) < SAMPLE_BYTES * 1500:
        raise ValueError("WAV_TOO_SHORT_FOR_ONSET_FORENSICS")
    return raw


def align_clean_to_raw(raw: bytes, cleaned: bytes) -> tuple[float, float]:
    """Find an unchanged interior PCM window; no matching means REVIEW/ERROR.

    Zero/silence windows are excluded to avoid accidentally treating a silent
    segment as a reliable sample alignment.
    """
    if len(cleaned) > len(raw):
        raise ValueError("CLEANED_WAV_LONGER_THAN_ORIGINAL")
    for probe_ms in (120, 220, 80, 350):
        start = int(SAMPLE_RATE * probe_ms / 1000) * SAMPLE_BYTES
        end = start + 20 * SAMPLE_RATE * SAMPLE_BYTES // 1000
        if end > len(cleaned):
            continue
        needle = cleaned[start:end]
        arr = array.array("h")
        arr.frombytes(needle)
        if max(abs(s) for s in arr) < 500:
            continue
        pos = raw.find(needle)
        if pos < 0 or pos % SAMPLE_BYTES:
            continue
        # A single exact match is necessary to prove the offset (periodic
        # synth tones or silent samples can otherwise misalign).
        if raw.find(needle, pos + SAMPLE_BYTES) >= 0:
            continue
        lead_bytes = pos - start
        if lead_bytes < 0 or lead_bytes > len(raw) - len(cleaned):
            continue
        head_ms = lead_bytes / (SAMPLE_RATE * SAMPLE_BYTES) * 1000
        tail_ms = (len(raw) - len(cleaned) - lead_bytes) / (SAMPLE_RATE * SAMPLE_BYTES) * 1000
        return round(head_ms, 3), round(tail_ms, 3)
    raise ValueError("UNVERIFIED_PCM_ALIGNMENT")


def head_rms(raw: bytes, ms: int = FADE_WINDOW_MS) -> float:
    frames = int(SAMPLE_RATE * ms / 1000)
    data = array.array("h")
    data.frombytes(raw[:frames * SAMPLE_BYTES])
    if len(data) != frames:
        raise ValueError("WAV_FIRST_WINDOW_INCOMPLETE")
    return math.sqrt(sum(float(x)*x for x in data)/len(data))/32768


def inspect_pair(raw_bytes: bytes, clean_bytes: bytes) -> dict:
    lead, tail = align_clean_to_raw(raw_bytes, clean_bytes)
    raw_rms = head_rms(raw_bytes)
    clean_rms = head_rms(clean_bytes)
    activity = raw_rms >= ACTIVE_START_RMS
    ratio = clean_rms / raw_rms if raw_rms > 0 else None
    fade_overlap = activity and ratio is not None and ratio < ATTENUATION_REVIEW_RATIO
    return {
        "verified_leading_trim_ms": lead,
        "verified_trailing_trim_ms": tail,
        "raw_first12ms_rms": round(raw_rms, 6),
        "clean_first12ms_rms": round(clean_rms, 6),
        "first12ms_energy_ratio": round(ratio, 4) if ratio is not None else None,
        "active_first12ms": activity,
        "onset_attenuation_review": bool(fade_overlap),
        "leading_trim_over50ms": lead > 50,
        "phoneme_or_half_word_loss_proven": False,
    }


def audit(manifest: dict, raw_dir: Path, cleaned_dir: Path,
          manifest_sha256: str, *, max_segments: int = 2000) -> dict:
    if not isinstance(manifest_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", manifest_sha256):
        raise ValueError("INVALID_MANIFEST_SHA")
    segments = manifest.get("segments") if isinstance(manifest, dict) else None
    if not isinstance(segments, list) or not 1 <= len(segments) <= max_segments:
        raise ValueError("INVALID_MANIFEST_SEGMENTS")
    findings = []
    matched = []
    active = attenuated = trimmed_front = trimmed_back = 0
    for i, seg in enumerate(segments):
        if not isinstance(seg, dict) or type(seg.get("index")) is not int or seg["index"] != i:
            raise ValueError("OUT_OF_ORDER_MANIFEST")
        name = f"{i:06d}.wav"
        result = inspect_pair(pcm_data(raw_dir/name), pcm_data(cleaned_dir/name))
        if result["active_first12ms"]:
            active += 1
        if result["onset_attenuation_review"]:
            attenuated += 1
        if result["leading_trim_over50ms"]:
            trimmed_front += 1
        if result["verified_trailing_trim_ms"] > 50:
            trimmed_back += 1
        if result["onset_attenuation_review"] or result["leading_trim_over50ms"]:
            findings.append({
                "segment": i,
                "leading_trim_ms": result["verified_leading_trim_ms"],
                "trailing_trim_ms": result["verified_trailing_trim_ms"],
                "initial_energy_ratio": result["first12ms_energy_ratio"],
                "fade_overlap_risk": result["onset_attenuation_review"],
                "review_required": True,
            })
        matched.append(result["verified_leading_trim_ms"])
    warnings = []
    if attenuated:
        warnings.append("ACTIVE_INITIAL_SOUND_ATTENUATED_REVIEW")
    if trimmed_front:
        warnings.append("ACTUAL_WAV_HEAD_TRIM_REVIEW")
    if trimmed_back:
        warnings.append("ACTUAL_WAV_TAIL_TRIM_REVIEW")
    return {
        "schema": SCHEMA,
        "chapter": manifest.get("chapter_number"),
        "manifest_sha256": manifest_sha256,
        "segments_scanned": len(segments),
        "exact_pcm_alignment_verified_count": len(matched),
        "verified_wav_heads_trim_over50ms": trimmed_front,
        "verified_wav_tails_trim_over50ms": trimmed_back,
        "raw_initial_12ms_active_segments": active,
        "processed_initial_12ms_attenuated_segments": attenuated,
        "initial_attenuation_threshold_ratio": ATTENUATION_REVIEW_RATIO,
        "review_indices": findings[:100],
        "review_indices_omitted": max(0, len(findings)-100),
        "warnings": warnings,
        "status": "REVIEW_ONLY_NO_VOICE_APPROVAL",
        "word_pronunciation_verified": False,
        "user_reported_word_loss_fixed": False,
        "production_modified": False,
        "automatic_worker_start_allowed": False,
        "automatic_promotion_allowed": False,
        "owner_final": False,
    }


def save_new(output: Path, result: dict) -> None:
    if any(s.casefold() in {"chunks", "stitch_cleaned", "owner_approved_natural_v5"} for s in output.parts):
        raise ValueError("REFUSE_PRODUCTION_OUTPUT")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> int:
    p = argparse.ArgumentParser(description="Offline native-WAV first-word preservation audit")
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--raw-dir", required=True, type=Path)
    p.add_argument("--clean-dir", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--enable-first-word-screen", action="store_true")
    args = p.parse_args()
    if not args.enable_first_word_screen:
        print("FIRST_WORD_QC_OFF_BY_DEFAULT")
        return 0
    raw = args.manifest.read_bytes()
    result = audit(json.loads(raw.decode("utf-8-sig")), args.raw_dir, args.clean_dir, sha(raw))
    save_new(args.output, result)
    print(json.dumps({"status": result["status"],
        "verified_heads_trimmed": result["verified_wav_heads_trim_over50ms"],
        "initial_energy_attenuated": result["processed_initial_12ms_attenuated_segments"],
        "owner_final": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
