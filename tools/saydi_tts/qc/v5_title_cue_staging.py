"""Opt-in REVIEW-only title cue on existing SAYDI V5 E-staging audio.

Never edits source/WAV/checkpoints or uses models. The added original
soft chime plays BEFORE a heading, never over narration. A/B exports use
the exact same E-stage WAV and gap references, differing only by the cue.
"""
from __future__ import annotations
import argparse
import array
import hashlib
import json
import math
import re
import subprocess
import wave
from pathlib import Path

SCHEMA = "saydi-v5-heading-cue-ab-staging-v1"
LINE = re.compile(r"^file '([^'\n\r]+)'$")
VOICE = re.compile(r"^(\d{6})\.wav$")
GAP = re.compile(r"^gap_(\d{1,5})\.wav$")
FORBIDDEN = {"owner_approved_natural_v5", "chunks", "stitch_cleaned", "qc_batches"}
SR = 48000
CUE_MS = 510
BEFORE_TITLE_GAP_MS = 230
MAX_CUE_PEAK = 0.075   # -22.5 dBFS maximum; normally gentler
MAX_CUE_RMS = 0.032    # -29.9 dBFS maximum


def sha_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def soft_bell_pcm() -> tuple[bytes, dict]:
    """Small, original rounded bell-like tone, no copyrighted sound assets."""
    samples = array.array("h")
    frames = round(SR * CUE_MS / 1000)
    for i in range(frames):
        t = i / SR
        # Gentle onset and exponential disappearance; no abrupt edge.
        attack = min(1.0, t / 0.042)
        tail = min(1.0, (CUE_MS / 1000 - t) / 0.075)
        env = max(0.0, min(attack, tail)) * math.exp(-t / 0.23)
        # Warm consonant dyad rather than a sharp click or music bed.
        tone = (0.078 * math.sin(2 * math.pi * 523.25 * t) +
                0.022 * math.sin(2 * math.pi * 659.25 * t))
        value = min(0.98, max(-0.98, env * tone))
        samples.append(int(round(value * 32767)))
    p = max(abs(x) for x in samples) / 32768
    rms = math.sqrt(sum(float(x) * x for x in samples) / len(samples)) / 32768
    if p > MAX_CUE_PEAK or rms > MAX_CUE_RMS:
        raise ValueError("CUE_EXCEEDS_SOFT_LEVEL_LIMIT")
    return samples.tobytes(), {
        "duration_ms": CUE_MS, "peak_linear": round(p, 6),
        "rms_linear": round(rms, 6), "lead_silence_ms": BEFORE_TITLE_GAP_MS,
        "waveform": "original-soft-rounded-dyad",
    }


def write_wave_new(path: Path, pcm: bytes) -> None:
    with path.open("xb") as handle:
        with wave.open(handle, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm)


def verify_stage(manifest_bytes: bytes, stage: Path) -> tuple[dict, list[tuple[int, str, str | None]]]:
    manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    if not isinstance(manifest.get("segments"), list):
        raise ValueError("INVALID_MANIFEST_SEGMENTS")
    receipt = json.loads((stage / "REVIEW_RECEIPT.json").read_text(encoding="utf-8"))
    if receipt.get("schema") != "saydi-v5-staging-review-assembly-v1":
        raise ValueError("NOT_THE_APPROVED_E_STAGING_FORMAT")
    if receipt.get("manifest_sha256") != sha_bytes(manifest_bytes):
        raise ValueError("E_STAGE_MANIFEST_SHA_MISMATCH")
    if receipt.get("chapter_final") is not False or receipt.get("production_modified") is not False:
        raise ValueError("E_STAGE_NOT_SAFE_REVIEW")
    mp3 = stage / "CHAPTER_STAGING_NOT_FINAL.REVIEW.mp3"
    if sha_bytes(mp3.read_bytes()) != receipt.get("mp3_sha256"):
        raise ValueError("E_STAGE_AUDIO_HASH_MISMATCH")
    lines = (stage / "review_concat.txt").read_text(encoding="utf-8").splitlines()
    wavdir = (stage / "review_wavs").resolve()
    pairs = []
    i = 0
    while i < len(lines):
        match = LINE.fullmatch(lines[i])
        if not match:
            raise ValueError("INVALID_CONCAT_SYNTAX")
        wav = Path(match.group(1))
        voice = VOICE.fullmatch(wav.name)
        if voice is None or wav.resolve().parent != wavdir or not wav.is_file():
            raise ValueError("UNEXPECTED_VOICE_PATH_OR_ORDER")
        idx = int(voice.group(1))
        if idx >= len(manifest["segments"]) or manifest["segments"][idx].get("index") != idx:
            raise ValueError("NONCANONICAL_VOICE_INDEX")
        pause_path = None
        if i+1 < len(lines):
            next_match = LINE.fullmatch(lines[i+1])
            if next_match is None:
                raise ValueError("INVALID_CONCAT_SYNTAX")
            next_file = Path(next_match.group(1))
            if GAP.fullmatch(next_file.name):
                if next_file.resolve().parent != wavdir or not next_file.is_file():
                    raise ValueError("UNEXPECTED_GAP_PATH")
                pause_path = str(next_file.resolve())
                i += 1
        pairs.append((idx, str(wav.resolve()), pause_path))
        i += 1
    if not pairs or len(set(p[0] for p in pairs)) != len(pairs):
        raise ValueError("DUPLICATE_OR_MISSING_VOICE")
    if any(pairs[j][0] >= pairs[j+1][0] for j in range(len(pairs)-1)):
        raise ValueError("NONMONOTONIC_VOICE_ORDER")
    if len(pairs) != receipt.get("included_voice_wavs"):
        raise ValueError("VOICE_COUNT_DIFFERS_FROM_E_RECEIPT")
    actual_titles = [i for i, _, _ in pairs if manifest["segments"][i].get("heading")]
    if actual_titles != receipt.get("heading_indices"):
        raise ValueError("HEADING_RECEIPT_MISMATCH")
    if not actual_titles:
        raise ValueError("NO_HEADINGS_IN_SOURCE_STAGING")
    return receipt, pairs


def make_playlists(pairs: list[tuple[int, str, str | None]], titles: set[int],
                   selected: set[int], cue: Path, lead: Path) -> tuple[str, str, list[int]]:
    control, enhanced = [], []
    applied = []
    chosen = [p for p in pairs if p[0] in selected]
    if not chosen:
        raise ValueError("EMPTY_PREVIEW_SELECTION")
    for pos, (idx, voice_path, pause) in enumerate(chosen):
        if idx in titles:
            enhanced += [f"file '{cue.resolve().as_posix()}'",
                         f"file '{lead.resolve().as_posix()}'"]
            applied.append(idx)
        original = f"file '{Path(voice_path).as_posix()}'"
        control.append(original)
        enhanced.append(original)
        # Last selected voice never needs a following gap. Otherwise, keep
        # exactly the E-stage pause only when another selected voice follows.
        if pos+1 < len(chosen) and pause is not None:
            gapline = f"file '{Path(pause).as_posix()}'"
            control.append(gapline)
            enhanced.append(gapline)
    if not applied:
        raise ValueError("SELECTED_WINDOW_HAS_NO_HEADING")
    return "\n".join(control)+"\n", "\n".join(enhanced)+"\n", applied


def create_review(manifest_path: Path, stage: Path, output: Path,
                  start: int | None = None, count: int | None = None) -> dict:
    if not output.is_absolute() or any(p.casefold() in FORBIDDEN for p in output.parts):
        raise ValueError("REFUSE_UNSAFE_STAGING_DESTINATION")
    if output.resolve() == stage.resolve() or stage.resolve() in output.resolve().parents:
        raise ValueError("OUTPUT_MUST_NOT_MODIFY_E_STAGE")
    raw_manifest = manifest_path.read_bytes()
    receipt, pairs = verify_stage(raw_manifest, stage)
    if start is None and count is None:
        selected = {i for i, _, _ in pairs}
    else:
        if start is None or count is None or start < 0 or not 1 <= count <= 2000:
            raise ValueError("INVALID_PREVIEW_WINDOW")
        selected = set(range(start, start+count))
    titles = set(receipt["heading_indices"])
    # Validate user selection before creating any files.
    chosen = [i for i, _, _ in pairs if i in selected]
    if not chosen or not any(i in titles for i in chosen):
        raise ValueError("PREVIEW_REQUIRES_HEADING")
    output.mkdir(parents=True, exist_ok=False)
    cue_pcm, stats = soft_bell_pcm()
    cue = output / "title_soft_bell.wav"
    lead = output / "silence_before_title_230ms.wav"
    write_wave_new(cue, cue_pcm)
    write_wave_new(lead, b"\x00\x00" * round(SR * BEFORE_TITLE_GAP_MS / 1000))
    a, f, headings = make_playlists(pairs, titles, selected, cue, lead)
    samples = []
    for key, playlist in (("E_CONTROL", a), ("F_TITLE_CUE", f)):
        listfile = output / f"{key}.concat.txt"
        listfile.write_text(playlist, encoding="utf-8")
        mp3 = output / f"CHAPTER_{key}.REVIEW.mp3"
        subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                        "-f", "concat", "-safe", "0", "-i", str(listfile),
                        "-af", "loudnorm=I=-18:LRA=11:TP=-2",
                        "-ar", "48000", "-ac", "1", "-c:a", "libmp3lame",
                        "-b:a", "128k", str(mp3)], check=True, timeout=240)
        probe = subprocess.run(["ffprobe", "-v", "error",
                                "-show_entries", "format=duration",
                                "-of", "default=noprint_wrappers=1:nokey=1",
                                str(mp3)], check=True, capture_output=True,
                               text=True, timeout=30)
        samples.append({"variant": key, "filename": mp3.name,
                        "duration_seconds": round(float(probe.stdout), 3),
                        "sha256": sha_bytes(mp3.read_bytes())})
    if samples[1]["duration_seconds"] <= samples[0]["duration_seconds"]:
        raise ValueError("TITLE_CUE_NOT_PRESENT_IN_OUTPUT")
    result = {
        "schema": SCHEMA,
        "e_source_sha256": receipt["mp3_sha256"],
        "e_source_manifest_sha256": receipt["manifest_sha256"],
        "chapter": receipt["chapter"],
        "voice_count": len(chosen), "title_indices": headings,
        "cue": stats, "cue_sha256": sha_bytes(cue.read_bytes()),
        "files": samples, "only_difference": "soft-cue-plus-230ms-silence-before-titles",
        "all_voice_wavs_identical_in_control_and_candidate": True,
        "all_existing_gaps_identical_in_control_and_candidate": True,
        "no_sfx_under_speech": True,
        "no_speech_rerendered": True,
        "production_modified": False, "owner_approved": False,
        "chapter_final": False,
        "status": "TITLE_CUE_AB_REVIEW_ONLY",
    }
    with (output / "TITLE_CUE_AB_RECEIPT.json").open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Soft title cue before existing headings; staged A/B only")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--e-stage-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--start-index", type=int)
    parser.add_argument("--count", type=int)
    parser.add_argument("--enable-title-cue-review", action="store_true")
    args = parser.parse_args()
    if not args.enable_title_cue_review:
        print("TITLE_CUE_STAGING_DISABLED_DEFAULT")
        return 0
    r = create_review(args.manifest, args.e_stage_dir, args.out_dir,
                      args.start_index, args.count)
    print(json.dumps({"status": r["status"], "titles": r["title_indices"],
                      "voices": r["voice_count"], "cue": r["cue"],
                      "samples": r["files"], "chapter_final": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
