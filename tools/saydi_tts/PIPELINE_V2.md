# SAYDI TTS Pipeline

## Default voice
- Engine: VieNeu v3 Turbo / ONNX
- Voice: SAYDI Nam Mien Nam
- Worker: DESKTOP-H4A16IL-SAYDI-TTS

## Text segmentation
For audiobook jobs, do not split at arbitrary character positions.

1. Preserve chapter and paragraph structure when cleaning PDF/Docs text.
2. Prefer chunk boundaries at paragraph endings.
3. Secondary boundary: complete sentence ending in ., ?, !, …
4. Target chunk size: 1,300–1,700 characters.
5. Maximum preferred chunk size: ~1,900 characters.
6. Never split inside a sentence unless unavoidable.
7. Normalize page numbers, extraction artifacts, duplicated whitespace and broken line wraps before enqueueing.

This reduces prosody resets and the number of joins.

## Smooth audio join
Worker patch: tools/saydi_tts/PATCH_SMOOTH_JOIN_V2.ps1

For each rendered WAV:
- trim excessive leading/trailing near-silence,
- preserve a small natural speech edge,
- add short fade-in/fade-out to prevent clicks,
- insert an 80 ms controlled join gap,
- concatenate to one WAV,
- apply final loudness normalization,
- encode MP3 at 48 kHz mono / 128 kbps.

Do not use raw FFmpeg concat of untrimmed VieNeu chunk WAVs for final audiobook output.

## Long-book execution
Create one queue job per chapter rather than one job for the whole book.
Each chapter has independent chunk checkpoints and an MP3 output.
After all chapters complete, optionally merge chapter files into a final audiobook container while keeping chapter boundaries.
