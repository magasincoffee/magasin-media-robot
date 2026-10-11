"""Opt-in, REVIEW-only instrumental title cue on protected SAYDI V5 E audio.

Reference intent: a soft, identifiable musical bed during a *heading* rather
than a lone chime. All musical notes are synthesized here (not sampled from
third-party audiobook recordings). Intro before each heading; quiet ducked
pad only under the heading voice, no music under normal narration.

No TTS or manuscript/voice/checkpoint changes. Not an Owner approval.
"""
from __future__ import annotations

import argparse
import array
import hashlib
import json
import math
import subprocess
import wave
from pathlib import Path

from v5_title_cue_staging import verify_stage

SR = 48000
MUSIC_MS = 2000
LEAD_MS = 160
MAX_MUSIC_PEAK = 0.055
MAX_MUSIC_RMS = 0.018
MAX_BED_PEAK = 0.009
FORBIDDEN = {"owner_approved_natural_v5", "chunks", "stitch_cleaned", "qc_batches"}
SCHEMA = "saydi-v5-heading-background-music-staging-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def musical_intro() -> tuple[bytes, dict]:
    """Original three-note warm instrumental motif. No copied audio."""
    notes = ((0.10, 392.00, 0.026), (0.48, 493.88, 0.021),
             (0.88, 587.33, 0.018))
    frames = int(SR * MUSIC_MS / 1000)
    values = array.array("h")
    for i in range(frames):
        t = i / SR
        sound = 0.0
        for start, freq, amplitude in notes:
            if t < start:
                continue
            x = t - start
            env = (1 - math.exp(-x / 0.04)) * math.exp(-x / 0.60)
            sound += amplitude * env * (
                math.sin(2 * math.pi * freq * x) +
                0.22 * math.sin(2 * math.pi * 2 * freq * x))
        pad = (math.sin(2 * math.pi * 196 * t) +
               0.5 * math.sin(2 * math.pi * 293.665 * t) +
               0.25 * math.sin(2 * math.pi * 392 * t)) / 1.75
        sound += 0.008 * min(1.0, t / 0.28) * min(1.0, (2-t) / 0.36) * pad
        sound *= max(0.0, min(1.0, (2-t) / 0.23))
        values.append(int(round(max(-1, min(1, sound)) * 32767)))
    peak = max(abs(x) for x in values) / 32768
    rms = math.sqrt(sum(float(x)*x for x in values) / len(values)) / 32768
    if peak > MAX_MUSIC_PEAK or rms > MAX_MUSIC_RMS:
        raise ValueError("PRELUDE_EXCEEDS_SAFE_LEVEL")
    return values.tobytes(), {
        "duration_ms": MUSIC_MS, "peak": round(peak, 6),
        "rms": round(rms, 6), "design": "original-soft-three-note-pad",
    }


def write_pcm(path: Path, data: bytes) -> None:
    with path.open("xb") as dest:
        with wave.open(dest, "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(SR)
            handle.writeframes(data)


def pcm_of(path: Path) -> array.array:
    with wave.open(str(path), "rb") as handle:
        if (handle.getnchannels(), handle.getsampwidth(),
                handle.getframerate()) != (1, 2, SR):
            raise ValueError("UNEXPECTED_TITLE_PCM_FORMAT")
        buff = handle.readframes(handle.getnframes())
    data = array.array("h")
    data.frombytes(buff)
    if not data:
        raise ValueError("EMPTY_TITLE_PCM")
    return data


def quiet_bed_over_heading(original: array.array) -> tuple[bytes, dict]:
    """Duck background 12 dB during voiced frames; never clip voice.

    This modifies only a derived mixed staging WAV. It does not change
    the E-stage WAV, underlying original TTS, or anything after a heading.
    """
    n = len(original)
    mixed = array.array("h")
    max_music = 0.0
    peak_voice = 0
    for i, sample in enumerate(original):
        t = i / SR
        left = (n - i - 1) / SR
        # Short envelope, nothing underneath the next ordinary sentence.
        envelope = min(1.0, t / 0.17, left / 0.38)
        if envelope < 0:
            envelope = 0.0
        chord = (math.sin(2*math.pi*196*t) +
                 .36*math.sin(2*math.pi*293.665*t) +
                 .22*math.sin(2*math.pi*392*t)) / 1.58
        volume = 0.006 * envelope
        if abs(sample) >= 328:  # spoken region: under ~-40dBFS
            volume *= 0.25
        bed = chord * volume
        max_music = max(max_music, abs(bed))
        # Hard headroom cap applies to bed only; preserve the original voice.
        permitted = max(0.0, 0.995 - abs(sample / 32768))
        bed = math.copysign(min(abs(bed), permitted), bed)
        candidate = sample + int(round(bed * 32767))
        mixed.append(max(-32768, min(32767, candidate)))
        peak_voice = max(peak_voice, abs(sample))
    if max_music > MAX_BED_PEAK:
        raise ValueError("HEADING_MUSIC_BED_TOO_LOUD")
    return mixed.tobytes(), {
        "bed_peak": round(max_music, 6),
        "ducked_during_voice": True,
        "original_voice_peak": round(peak_voice / 32768, 5),
    }


def create_ab(manifest_path: Path, e_stage: Path, dest: Path,
              start: int, count: int) -> dict:
    if not dest.is_absolute() or any(p.lower() in FORBIDDEN for p in dest.parts):
        raise ValueError("REFUSE_PRODUCTION_PATH")
    if dest.resolve() == e_stage.resolve() or e_stage.resolve() in dest.resolve().parents:
        raise ValueError("REFUSE_E_STAGE_MUTATION")
    if start < 0 or not 1 <= count <= 2000:
        raise ValueError("INVALID_SELECTION")
    manifest = manifest_path.read_bytes()
    receipt, pairs = verify_stage(manifest, e_stage)
    wanted = set(range(start, start + count))
    chosen = [(idx, voice, gap) for idx, voice, gap in pairs if idx in wanted]
    titles = set(receipt["heading_indices"])
    if not chosen or not any(idx in titles for idx, _, _ in chosen):
        raise ValueError("NO_HEADINGS_SELECTED")
    # No output directory creation until immutable source checks have passed.
    dest.mkdir(parents=True, exist_ok=False)
    cue, stats = musical_intro()
    cue_path = dest/"original_soft_music_intro.wav"
    lead_path = dest/"lead_silence_160ms.wav"
    write_pcm(cue_path, cue)
    write_pcm(lead_path, b"\0\0" * (LEAD_MS * 48))
    (dest/"mixed_heading_wavs").mkdir()
    a, b, seen, bed_stats = [], [], [], []
    for index, (idx, voice, gap) in enumerate(chosen):
        original_file = f"file '{Path(voice).resolve().as_posix()}'"
        a.append(original_file)
        if idx in titles:
            original_pcm = pcm_of(Path(voice))
            mixed, stats_heading = quiet_bed_over_heading(original_pcm)
            new_voice = dest/"mixed_heading_wavs"/f"{idx:06d}.wav"
            write_pcm(new_voice, mixed)
            b += [f"file '{cue_path.resolve().as_posix()}'",
                  f"file '{lead_path.resolve().as_posix()}'",
                  f"file '{new_voice.resolve().as_posix()}'"]
            seen.append(idx)
            bed_stats.append({"index": idx, **stats_heading})
        else:
            b.append(original_file)
        if index + 1 < len(chosen) and gap is not None:
            gapline = f"file '{Path(gap).resolve().as_posix()}'"
            a.append(gapline)
            b.append(gapline)
    files = []
    for name, lines in (("E_NO_BACKGROUND", a), ("G_SOFT_BACKGROUND", b)):
        concat = dest/f"{name}.concat.txt"
        concat.write_text("\n".join(lines)+"\n",encoding="utf-8")
        out = dest/f"CHAPTER_{name}.REVIEW.mp3"
        subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                        "-f", "concat", "-safe", "0", "-i", str(concat),
                        "-af", "loudnorm=I=-18:LRA=11:TP=-2", "-ar", "48000",
                        "-ac", "1", "-c:a", "libmp3lame", "-b:a", "128k", str(out)],
                       check=True, timeout=250)
        p = subprocess.run(["ffprobe", "-v", "error",
                            "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1",
                            str(out)], capture_output=True, text=True,
                           timeout=25, check=True)
        files.append({"version": name, "duration_seconds": round(float(p.stdout), 3),
                      "sha256": sha(out), "filename": out.name})
    if files[1]["duration_seconds"] <= files[0]["duration_seconds"]:
        raise ValueError("MUSICAL_INTRO_MISSING")
    evidence = {"schema": SCHEMA, "chapter": receipt["chapter"],
                "e_audio_sha256": receipt["mp3_sha256"],
                "manifest_sha256": receipt["manifest_sha256"],
                "cue": stats, "cue_sha256": sha(cue_path),
                "music_only_before_and_during_heading": True,
                "preheading_silence_ms": LEAD_MS,
                "heading_indices": seen, "heading_bed": bed_stats,
                "voice_tts_not_rerendered": True,
                "unchanged_e_source": True,
                "files": files,
                "production_modified": False,
                "owner_approved": False,
                "chapter_final": False,
                "status": "STAGING_AB_REVIEW_ONLY"}
    with (dest/"REVIEW_AB_RECEIPT.json").open("x", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)
    return evidence


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--e-stage-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--start-index", type=int, default=0)
    p.add_argument("--count", type=int, required=True)
    p.add_argument("--enable-background-review", action="store_true")
    args = p.parse_args()
    if not args.enable_background_review:
        print("SOFT_BACKGROUND_DISABLED_DEFAULT")
        return 0
    r = create_ab(args.manifest, args.e_stage_dir, args.out_dir,
                  args.start_index, args.count)
    print(json.dumps({"status": r["status"],"titles":r["heading_indices"],
                      "cue":r["cue"],"files":r["files"],"final":False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
