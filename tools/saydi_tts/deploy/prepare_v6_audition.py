"""Source-only V6 audition preparation, never imports VieNeu or starts a worker.

This is a synthetic/public 5-minute candidate fixture, NOT audio output or an
authenticated SAYDI Owner START. Real rendering requires a separate trusted
SAYDI V6 host lifecycle, runtime grant, resource/mutex checks and safe unload.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

MIN_WORDS = 600
MAX_WORDS = 950
MAX_CHARS = 256
MIN_ESTIMATED_MINUTES = 5.0
MAX_ESTIMATED_MINUTES = 10.0
SPEED_WPM_FOR_PLANNING = 125.0  # estimate only; NO DSP or atempo


def prepare_text(text: str) -> dict:
    if not isinstance(text, str) or "\x00" in text:
        raise ValueError("INVALID_SAMPLE_TEXT")
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        raise ValueError("EMPTY_SAMPLE_TEXT")
    words = len(normalized.split())
    if not MIN_WORDS <= words <= MAX_WORDS:
        raise ValueError("SAMPLE_LENGTH_OUT_OF_RANGE")
    estimated_minutes = round(words / SPEED_WPM_FOR_PLANNING, 2)
    if not MIN_ESTIMATED_MINUTES <= estimated_minutes <= MAX_ESTIMATED_MINUTES:
        raise ValueError("ESTIMATED_LISTENING_LENGTH_OUT_OF_RANGE")

    # Split strictly on sentence boundaries so no first-word clipping at joins.
    # Long source sentences require editorial review, never silent truncation.
    sentences = re.split(r"(?<=[.!?…])\s+", normalized)
    if not sentences or any(len(s) > MAX_CHARS for s in sentences):
        raise ValueError("SENTENCE_TOO_LONG_REVIEW_REQUIRED")
    chunks = []
    for sentence in sentences:
        if not sentence:
            continue
        chunks.append({"index": len(chunks),
                       "text_sha256": sha256(sentence.encode("utf-8")).hexdigest(),
                       "character_count": len(sentence)})
    if not chunks:
        raise ValueError("EMPTY_SEGMENT_SET")
    return {
        "schema": "saydi-v6-audition-source-plan-v1",
        "status": "SOURCE_PLAN_ONLY_NO_AUDIO",
        "source_sha256": sha256(normalized.encode("utf-8")).hexdigest(),
        "word_count": words,
        "estimated_minutes_not_measured": estimated_minutes,
        "natural_speed_only": True,
        "segment_count": len(chunks),
        "segments": chunks,
        "new_audio_generated": False,
        "saydi_owner_start_verified": False,
        "vieneu_loaded": False,
        "h4_changed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline-only public SAYDI V6 audition source plan")
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    data = args.input.read_text(encoding="utf-8")
    print(json.dumps(prepare_text(data), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
