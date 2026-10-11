"""SAYDI V5 opt-in, non-production audiobook review assembly.

Uses existing, hash-bound audio only: restores the original initial 12 ms
and retains the rest of the cleaned WAV, adjusts pause semantics, gives
headings bounded level emphasis, and excludes only explicitly selected,
strictly identified page-number voice chunks. Does not use TTS/models,
alter source text, rewrite checkpoints or approve chapter release.
"""
from __future__ import annotations
import argparse
import array
import hashlib
import json
import re
import subprocess
import wave
from pathlib import Path

from v5_first_word_onset_gate import align_clean_to_raw, pcm_data

SCHEMA = "saydi-v5-staging-review-assembly-v1"
PAGE_NUMBER_RE = re.compile(r"[0-9]{1,3}\Z")
FORBIDDEN = {"owner_approved_natural_v5", "chunks", "stitch_cleaned", "qc_batches"}


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def page_artifacts(manifest: dict) -> list[int]:
    items = manifest.get("segments")
    if not isinstance(items, list) or not 1 <= len(items) <= 2000:
        raise ValueError("INVALID_SEGMENTS")
    candidates = []
    for pos, seg in enumerate(items):
        if not isinstance(seg, dict) or type(seg.get("index")) is not int or seg["index"] != pos:
            raise ValueError("OUT_OF_ORDER_SEGMENTS")
        value = seg.get("canonical_text")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("EMPTY_CANONICAL")
        if not PAGE_NUMBER_RE.fullmatch(value.strip()):
            continue
        if seg.get("heading") or not seg.get("parent_end") or pos == 0:
            continue
        if pos != len(items)-1 and not items[pos+1].get("heading"):
            continue
        candidates.append(pos)
    return candidates


def segment_plan(manifest: dict, selected: list[int],
                 excluded: list[int]) -> list[dict]:
    items = manifest["segments"]
    if (not selected or sorted(set(selected)) != selected
            or selected[0] < 0 or selected[-1] >= len(items)):
        raise ValueError("INVALID_SEGMENT_SELECTION")
    candidate_set = set(page_artifacts(manifest))
    skipped = set(excluded)
    if len(skipped) != len(excluded) or not skipped.issubset(candidate_set):
        raise ValueError("UNVERIFIED_PAGE_ARTIFACT_EXCLUSION")
    if any(i not in selected for i in excluded):
        raise ValueError("SKIPPED_SEGMENT_NOT_IN_SELECTED_RANGE")
    active = [i for i in selected if i not in skipped]
    if not active:
        raise ValueError("NO_PLAYABLE_SEGMENTS")
    plan = []
    for order, i in enumerate(active):
        current = items[i]
        next_item = items[active[order+1]] if order+1 < len(active) else None
        if current.get("heading"):
            gap = 1150
        elif next_item is None:
            gap = 0
        elif next_item.get("heading"):
            gap = 950
        elif current.get("parent_line") != next_item.get("parent_line"):
            gap = 675
        else:
            ending = current["canonical_text"].strip()
            if ending.endswith(("?", "!")):
                gap = 460
            elif ending.endswith(("…", "...")):
                gap = 625
            elif ending.endswith((",", ";", ":")):
                gap = 190
            elif ending.endswith("."):
                gap = 365
            else:
                gap = 220
        plan.append({"index": i, "heading": bool(current.get("heading")),
                     "pause_after_ms": gap,
                     "voice_fingerprint_preserved": True})
    return plan


def load_pcm(path: Path) -> bytes:
    return pcm_data(path)


def bounded_heading_gain(pcm: bytes, heading: bool) -> tuple[bytes, float]:
    if not heading:
        return pcm, 1.0
    samples = array.array("h")
    samples.frombytes(pcm)
    highest = max(abs(x) for x in samples)
    gain = min(1.20, 0.96 * 32767 / highest) if highest else 1.0
    # Explicitly avoid lowering loud peaks merely to simulate emphasis.
    gain = max(1.0, gain)
    if gain == 1.0:
        return pcm, 1.0
    louder = array.array("h", (max(-32768, min(32767, int(round(x * gain))))
                         for x in samples))
    return louder.tobytes(), round(gain, 4)


def write_wav_new(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "xb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(pcm)


def safe_out_dir(path: Path, source_dir: Path) -> None:
    if not path.is_absolute():
        raise ValueError("OUTPUT_MUST_BE_ABSOLUTE")
    if any(part.casefold() in FORBIDDEN for part in path.parts):
        raise ValueError("REFUSE_PRODUCTION_PATH")
    if path.resolve() == source_dir.resolve() or source_dir.resolve() in path.resolve().parents:
        raise ValueError("NO_WRITES_UNDER_AUDIO_SOURCE_DIR")


def render(manifest_bytes: bytes, source_dir: Path, output_dir: Path,
           selected: list[int], excluded: list[int],
           ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe") -> dict:
    manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    safe_out_dir(output_dir, source_dir)
    plan = segment_plan(manifest, selected, excluded)
    output_dir.mkdir(parents=True, exist_ok=False)
    wav_dir = output_dir/"review_wavs"
    wav_dir.mkdir(exist_ok=False)
    concat = []
    details = []
    page_candidates = page_artifacts(manifest)
    for item in plan:
        idx = item["index"]
        name = f"{idx:06d}.wav"
        raw = load_pcm(source_dir/"chunks"/name)
        cleaned = load_pcm(source_dir/"stitch_cleaned"/name)
        head_ms, _ = align_clean_to_raw(raw, cleaned)
        if head_ms != 0:
            raise ValueError(f"LEADING_TRIM_BLOCKS_STAGED_REVIEW_{idx}")
        # Preserve the full first 12 ms of native sound from the exact
        # source WAV. All other audio samples stay in the cleaned version.
        changed = raw[:1152] + cleaned[1152:]
        changed, gain = bounded_heading_gain(changed, item["heading"])
        path = wav_dir/name
        write_wav_new(path, changed)
        concat.append("file '"+path.resolve().as_posix()+"'")
        gap = item["pause_after_ms"]
        if gap:
            pause = wav_dir/f"gap_{gap}.wav"
            if not pause.exists():
                write_wav_new(pause, b"\0\0" * (gap*48))
            concat.append("file '"+pause.resolve().as_posix()+"'")
        details.append({"index": idx, "heading": item["heading"],
                        "gain": gain, "gap_after_ms": gap})
    list_file = output_dir/"review_concat.txt"
    list_file.write_text("\n".join(concat)+"\n", encoding="utf-8")
    final = output_dir/"CHAPTER_STAGING_NOT_FINAL.REVIEW.mp3"
    command = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
               "-f", "concat", "-safe", "0", "-i", str(list_file),
               "-af", "loudnorm=I=-18:LRA=11:TP=-2", "-ar", "48000",
               "-ac", "1", "-c:a", "libmp3lame", "-b:a", "128k", str(final)]
    subprocess.run(command, check=True, timeout=300)
    probe = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(final)],
        check=True, capture_output=True, text=True, timeout=30)
    receipt = {
        "schema": SCHEMA, "chapter": manifest.get("chapter_number"),
        "manifest_sha256": sha(manifest_bytes),
        "source_sha256": manifest.get("source_sha256"),
        "selected_segment_count": len(selected),
        "included_voice_wavs": len(details),
        "page_artifact_candidates": page_candidates,
        "excluded_page_artifact_indices": excluded,
        "heading_indices": [x["index"] for x in details if x["heading"]],
        "heading_gains": [{"index": x["index"], "scale": x["gain"]}
                          for x in details if x["heading"]],
        "pcm_first_12_ms_restored": True,
        "no_tts": True, "time_stretched": False,
        "mp3_duration_seconds": round(float(probe.stdout), 3),
        "mp3_sha256": sha(final.read_bytes()),
        "native_word_pronunciation_verified": False,
        "chapter_listening_approved": False,
        "production_modified": False, "chapter_final": False,
        "status": "STAGING_LISTENING_ONLY",
    }
    with (output_dir/"REVIEW_RECEIPT.json").open("x", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--count", type=int)
    parser.add_argument("--skip-page-indices", default="")
    parser.add_argument("--enable-staging-review", action="store_true")
    args = parser.parse_args()
    if not args.enable_staging_review:
        print("STAGED_ASSEMBLER_DISABLED_DEFAULT")
        return 0
    m = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    total = len(m["segments"])
    if args.count is not None and args.count <= 0:
        raise ValueError("BAD_COUNT")
    count = args.count if args.count is not None else total - args.start_index
    selected = list(range(args.start_index, args.start_index+count))
    excluded = ([int(s) for s in args.skip_page_indices.split(",") if s.strip()]
                if args.skip_page_indices else [])
    report = render(args.manifest.read_bytes(), args.source_dir, args.out_dir,
                    selected, excluded)
    print(json.dumps({k: report[k] for k in (
        "status", "included_voice_wavs", "excluded_page_artifact_indices",
        "mp3_duration_seconds", "mp3_sha256", "chapter_final")}))


if __name__ == "__main__":
    raise SystemExit(main())
