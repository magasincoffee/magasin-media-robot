from __future__ import annotations

import argparse
from pathlib import Path
import wave

import lameenc


def convert_wav_to_mp3(source: Path, target: Path, bit_rate_kbps: int = 128) -> None:
    with wave.open(str(source), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())

    if channels not in (1, 2):
        raise ValueError(f"Unsupported channel count: {channels}")
    if sample_width != 2:
        raise ValueError(f"Expected 16-bit PCM WAV, got sample width {sample_width * 8} bits")

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(bit_rate_kbps)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(channels)
    encoder.set_quality(2)

    mp3 = encoder.encode(frames)
    mp3 += encoder.flush()

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(mp3)

    if target.stat().st_size == 0:
        raise RuntimeError("MP3 output is empty")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("target")
    parser.add_argument("--bit-rate", type=int, default=128)
    args = parser.parse_args()

    source = Path(args.source).resolve()
    target = Path(args.target).resolve()
    convert_wav_to_mp3(source, target, args.bit_rate)
    print(f"MP3_OUTPUT={target}")
    print(f"MP3_BYTES={target.stat().st_size}")


if __name__ == "__main__":
    main()
