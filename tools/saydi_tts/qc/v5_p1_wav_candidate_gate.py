"""Read-only candidate WAV QC for existing SAYDI V5 bounded repair worklists.

Uses original/candidate/neighbor WAV *bytes* only. No TTS, ASR, audio mutation,
network, production controller, or final-approval operation. All metrics are
technical screening signals; they cannot certify Vietnamese tones or emotion.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import struct
import wave
from pathlib import Path

SCHEMA = "saydi-v5-p1-wav-candidate-gate-1"
HEX = re.compile(r"[a-f0-9]{64}\Z")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def valid_sha(value: object) -> bool:
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def _samples(data: bytes) -> tuple[dict, list[int]]:
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            fmt = {"channels": w.getnchannels(), "sample_width": w.getsampwidth(),
                   "sample_rate": w.getframerate(), "frames": w.getnframes(),
                   "comptype": w.getcomptype()}
            if (fmt["comptype"] != "NONE" or fmt["channels"] != 1
                    or fmt["sample_width"] != 2
                    or fmt["sample_rate"] not in {16000, 22050, 24000, 44100, 48000}
                    or fmt["frames"] < 1 or fmt["frames"] > 48000 * 120):
                raise ValueError("UNSUPPORTED_OR_UNSAFE_WAV_FORMAT")
            frames = w.readframes(fmt["frames"])
    except (wave.Error, EOFError, struct.error) as exc:
        raise ValueError("UNDECODABLE_WAV") from exc
    if len(frames) != fmt["frames"] * 2:
        raise ValueError("TRUNCATED_WAV_PAYLOAD")
    samples = [item[0] for item in struct.iter_unpack("<h", frames)]
    return fmt, samples


def _metrics(fmt: dict, samples: list[int]) -> dict:
    count = len(samples)
    rms = math.sqrt(sum(float(v) * float(v) for v in samples) / count) / 32768
    peak = max(abs(v) for v in samples) / 32768
    near_clipped = sum(abs(v) >= 32760 for v in samples) / count
    return {"duration_ms": round(count * 1000 / fmt["sample_rate"], 2),
            "rms_dbfs": round(20 * math.log10(max(rms, 1e-9)), 2),
            "peak_dbfs": round(20 * math.log10(max(peak, 1e-9)), 2),
            "near_clipped_fraction": round(near_clipped, 6)}


def inspect(original: bytes, candidate: bytes, receipt: dict,
            left: bytes | None = None, right: bytes | None = None) -> dict:
    if not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA:
        raise ValueError("WRONG_CANDIDATE_RECEIPT")
    idx = receipt.get("segment")
    attempts = receipt.get("attempts_used")
    if type(idx) is not int or idx < 0 or type(attempts) is not int or attempts not in {0, 1}:
        raise ValueError("INVALID_SEGMENT_OR_ATTEMPT_BUDGET")
    for name in ("manifest_sha256", "source_sha256", "voice_reference_sha256",
                 "tts_text_fingerprint", "original_wav_sha256", "candidate_wav_sha256"):
        if not valid_sha(receipt.get(name)):
            raise ValueError("REQUIRED_SHA_MISSING_OR_MALFORMED")
    if receipt["original_wav_sha256"] != digest(original):
        raise ValueError("STALE_ORIGINAL_WAV_SHA")
    if receipt["candidate_wav_sha256"] != digest(candidate):
        raise ValueError("STALE_CANDIDATE_WAV_SHA")
    if digest(candidate) == digest(original):
        raise ValueError("CANDIDATE_IDENTICAL_TO_BASELINE")

    formats, waveforms, metrics = [], [], []
    for raw in (original, candidate):
        fmt, frames = _samples(raw)
        formats.append(fmt)
        waveforms.append(frames)
        metrics.append(_metrics(fmt, frames))
    if {k: formats[0][k] for k in ("channels", "sample_width", "sample_rate")} != {
            k: formats[1][k] for k in ("channels", "sample_width", "sample_rate")}:
        raise ValueError("WAV_CODEC_MISMATCH")
    candidate_fmt = formats[1]
    candidate_frames = waveforms[1]
    flags = []
    if metrics[1]["duration_ms"] < 150:
        flags.append("CANDIDATE_TOO_SHORT")
    ratio = metrics[1]["duration_ms"] / max(metrics[0]["duration_ms"], 1)
    if ratio < 0.67 or ratio > 1.5:
        flags.append("DURATION_CHANGE_REVIEW")
    if metrics[1]["rms_dbfs"] < -48:
        flags.append("NEAR_SILENT_CANDIDATE")
    if metrics[1]["near_clipped_fraction"] > 0.001:
        flags.append("POSSIBLE_CLIPPING")
    if abs(metrics[1]["rms_dbfs"] - metrics[0]["rms_dbfs"]) > 8:
        flags.append("GAIN_CHANGE_REVIEW")
    if left is None or right is None:
        flags.append("NEIGHBOR_WAV_EVIDENCE_INCOMPLETE")

    checks = []
    for side, data, index in (("left", left, 0), ("right", right, -1)):
        key = f"{side}_wav_sha256"
        if data is None:
            if receipt.get(key) is not None:
                raise ValueError("CLAIMED_NEIGHBOR_WITHOUT_BYTES")
            continue
        if not valid_sha(receipt.get(key)) or receipt[key] != digest(data):
            raise ValueError("NEIGHBOR_SHA_MISMATCH")
        neighbor_fmt, neighbor_samples = _samples(data)
        if any(neighbor_fmt[k] != candidate_fmt[k] for k in (
                "channels", "sample_width", "sample_rate")):
            raise ValueError("NEIGHBOR_CODEC_MISMATCH")
        boundary_jump = (abs(neighbor_samples[-1] - candidate_frames[0])
                         if side == "left"
                         else abs(candidate_frames[-1] - neighbor_samples[0])) / 32768
        if boundary_jump > 0.40:
            flags.append(f"{side.upper()}_BOUNDARY_PCM_JUMP_REVIEW")
        checks.append({"side": side, "sha256": digest(data),
                       "boundary_pcm_jump": round(boundary_jump, 6),
                       "note": "SCREEN_ONLY_NOT_AUDIBLE_SEAM_ACCEPTANCE"})

    return {"schema": SCHEMA, "segment": idx,
            "manifest_sha256": receipt["manifest_sha256"],
            "source_sha256": receipt["source_sha256"],
            "voice_reference_sha256": receipt["voice_reference_sha256"],
            "tts_text_fingerprint": receipt["tts_text_fingerprint"],
            "original_wav_sha256": digest(original),
            "candidate_wav_sha256": digest(candidate),
            "attempts_used": attempts, "attempts_remaining": 2-attempts,
            "sample_rate": candidate_fmt["sample_rate"],
            "original_metrics": metrics[0], "candidate_metrics": metrics[1],
            "neighbor_checks": checks, "flags": sorted(set(flags)),
            "status": "REVIEW_NO_PROMOTION", "audio_pronunciation_verified": False,
            "emotion_verified": False, "source_fidelity_verified": False,
            "worker_started": False, "audio_written": False,
            "approved_to_dispatch": False, "approved_to_promote": False,
            "owner_final": False}


def main() -> int:
    p = argparse.ArgumentParser(description="SAYDI V5 offline candidate WAV technical gate")
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--left", type=Path)
    p.add_argument("--right", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--enable-wav-candidate-inspection", action="store_true")
    args = p.parse_args()
    if not args.enable_wav_candidate_inspection:
        print("SAYDI_WAV_GATE_DISABLED_DEFAULT")
        return 0
    report = inspect(args.original.read_bytes(), args.candidate.read_bytes(),
                     json.loads(args.receipt.read_text(encoding="utf-8-sig")),
                     args.left.read_bytes() if args.left else None,
                     args.right.read_bytes() if args.right else None)
    if any(part.casefold() in {"chunks", "stitch_cleaned", "owner_approved_natural_v5"}
           for part in args.output.parts):
        raise ValueError("OUTPUT_IS_PRODUCTION_LOCATION")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"state": report["status"], "flags": report["flags"],
                      "worker_started": False, "owner_final": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
