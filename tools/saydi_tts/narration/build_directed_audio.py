from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np
import soundfile as sf


@dataclass(frozen=True)
class SegmentResult:
    index: int
    beat: str
    tempo_factor: float
    pause_before_ms: int
    pause_after_ms: int
    source_sha256: str
    source_duration_sec: float
    directed_duration_sec: float


def _find_ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    for candidate in (
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
    ):
        if candidate.is_file():
            return str(candidate)
    pkg_root = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if pkg_root.exists():
        for candidate in pkg_root.glob("**/ffmpeg.exe"):
            if candidate.is_file():
                return str(candidate)
    raise RuntimeError("FFmpeg not found")


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run(cmd: list[str]) -> None:
    process = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode != 0:
        raise RuntimeError("command failed:\n" + " ".join(cmd) + "\n" + process.stderr[-6000:])


def _trim_edges(audio: np.ndarray, sample_rate: int, *, threshold_db: float = -50.0) -> np.ndarray:
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    threshold = 10 ** (threshold_db / 20.0)
    active = np.flatnonzero(np.abs(audio) > threshold)
    if not active.size:
        return audio.astype(np.float32, copy=False)

    keep_before = int(sample_rate * 0.035)
    keep_after = int(sample_rate * 0.050)
    start = max(0, int(active[0]) - keep_before)
    end = min(len(audio), int(active[-1]) + keep_after + 1)
    return audio[start:end].astype(np.float32, copy=False)


def _fade(audio: np.ndarray, sample_rate: int, ms: int = 10) -> np.ndarray:
    out = audio.astype(np.float32, copy=True)
    n = min(int(sample_rate * ms / 1000.0), len(out) // 4)
    if n > 1:
        out[:n] *= np.linspace(0.0, 1.0, n, dtype=np.float32)
        out[-n:] *= np.linspace(1.0, 0.0, n, dtype=np.float32)
    return out


def _tempo_segment(
    *,
    ffmpeg: str,
    source: Path,
    output: Path,
    tempo_factor: float,
) -> None:
    if not 0.5 <= tempo_factor <= 1.0:
        raise ValueError(f"unsafe atempo factor: {tempo_factor}")
    _run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-af",
            f"atempo={tempo_factor:.6f}",
            "-ar",
            "48000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )


def build_directed_audio(
    *,
    manifest_path: Path,
    chunk_dir: Path,
    output_mp3: Path,
    report_path: Path,
) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    segments = manifest.get("segments") or []
    if not segments:
        raise ValueError("manifest has no segments")

    ffmpeg = _find_ffmpeg()
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    results: list[SegmentResult] = []
    pieces: list[np.ndarray] = []
    sample_rate = 48000
    word_count = 0

    with tempfile.TemporaryDirectory(prefix="saydi-director-") as temp_name:
        temp_dir = Path(temp_name)

        previous_pause_after = 0
        for position, segment in enumerate(segments):
            index = int(segment["index"])
            beat = str(segment["beat"])
            tempo_factor = float(segment["tempo_factor"])
            pause_before = int(segment.get("pause_before_ms", 0))
            pause_after = int(segment.get("pause_after_ms", 0))
            canonical = str(segment["canonical_text"])
            spoken = str(segment["spoken_text"])

            if not canonical.strip() or not spoken.strip():
                raise ValueError(f"segment {index} has empty text")
            word_count += len(canonical.split())

            source = chunk_dir / f"{index:06d}.wav"
            if not source.exists() or source.stat().st_size < 1024:
                raise FileNotFoundError(f"missing rendered chunk: {source}")

            if position == 0:
                gap_ms = pause_before
            else:
                gap_ms = max(previous_pause_after, pause_before)
            if gap_ms:
                pieces.append(np.zeros(int(sample_rate * gap_ms / 1000.0), dtype=np.float32))

            directed = temp_dir / f"{index:06d}_directed.wav"
            _tempo_segment(
                ffmpeg=ffmpeg,
                source=source,
                output=directed,
                tempo_factor=tempo_factor,
            )

            raw_source, source_sr = sf.read(str(source), dtype="float32", always_2d=False)
            if getattr(raw_source, "ndim", 1) > 1:
                raw_source = raw_source.mean(axis=1)
            source_duration = len(raw_source) / float(source_sr)

            audio, sr = sf.read(str(directed), dtype="float32", always_2d=False)
            if sr != sample_rate:
                raise RuntimeError(f"unexpected sample rate {sr} in {directed}")
            audio = _fade(_trim_edges(np.asarray(audio), sample_rate), sample_rate)
            pieces.append(audio)
            directed_duration = len(audio) / sample_rate

            results.append(
                SegmentResult(
                    index=index,
                    beat=beat,
                    tempo_factor=tempo_factor,
                    pause_before_ms=pause_before,
                    pause_after_ms=pause_after,
                    source_sha256=_sha256_file(source),
                    source_duration_sec=round(source_duration, 3),
                    directed_duration_sec=round(directed_duration, 3),
                )
            )
            previous_pause_after = pause_after

        if previous_pause_after:
            pieces.append(np.zeros(int(sample_rate * previous_pause_after / 1000.0), dtype=np.float32))

        merged = np.concatenate(pieces).astype(np.float32)
        peak = float(np.max(np.abs(merged))) if len(merged) else 0.0
        if peak > 0.98:
            merged *= 0.98 / peak

        temp_wav = temp_dir / "golden_story_v2_directed.wav"
        sf.write(str(temp_wav), merged, sample_rate, subtype="PCM_16")

        _run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(temp_wav),
                "-af",
                "loudnorm=I=-18:LRA=11:TP=-2",
                "-ar",
                "48000",
                "-ac",
                "1",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "128k",
                str(output_mp3),
            ]
        )

    duration_sec = len(merged) / sample_rate
    effective_wpm = word_count / max(duration_sec / 60.0, 1e-9)
    target = manifest.get("target") or {}
    duration_ok = (
        float(target.get("duration_seconds_min", 0)) <= duration_sec
        <= float(target.get("duration_seconds_max", math.inf))
    )
    wpm_ok = (
        float(target.get("effective_wpm_min", 0)) <= effective_wpm
        <= float(target.get("effective_wpm_max", math.inf))
    )

    report = {
        "schema_version": "saydi-directed-audio-report-v1",
        "director_version": manifest.get("director_version"),
        "title": manifest.get("title"),
        "profile_key": manifest.get("profile_key"),
        "manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
        "output_path": str(output_mp3),
        "output_sha256": _sha256_file(output_mp3),
        "duration_sec": round(duration_sec, 3),
        "word_count": word_count,
        "effective_wpm": round(effective_wpm, 2),
        "duration_target_pass": duration_ok,
        "wpm_target_pass": wpm_ok,
        "technical_gate": "PASS" if duration_ok and wpm_ok else "REVIEW",
        "segments": [result.__dict__ for result in results],
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--chunk-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    report = build_directed_audio(
        manifest_path=args.manifest,
        chunk_dir=args.chunk_dir,
        output_mp3=args.output,
        report_path=args.report,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
