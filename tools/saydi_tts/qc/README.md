# SAYDI Local QC

Runs after chapter rendering. Acoustic checks, ASR verification, timecode reporting, and bounded technical repair are local-first and listener-invisible.

## PyAV compatibility

As of 2026-10, faster-whisper 1.2.x passes `metadata_errors` to `av.open()`, while PyAV 19 removed that parameter. The local QC environment must therefore pin `av>=11,<19` until faster-whisper is updated/validated against PyAV 19+.

## QC v2 measurements

Each rendered chunk now records a structured observation keyed to the exact audio SHA-256:

- ASR similarity;
- minimum and mean word confidence from faster-whisper word timestamps;
- suspect/unclear word tokens;
- speaking rate (words/minute);
- pause/silence ratio;
- coarse pitch/F0 variation in semitones;
- energy/dynamics variation;
- clipping ratio;
- duration and attempt number.

These observations are persisted through the existing local QC report path. They are not uploaded as GitHub artifacts.

Important: word confidence and pitch variation are QC signals, not ground truth. Pronunciation repair remains bounded and must not silently change canonical book meaning.

## Safe H4A16IL field gate

Use `INSTALL_QC_V2_FIELD_H4A16IL.ps1` for SAYDI-QC-002 validation.

The field gate:

- backs up the current `C:\SAYDI\qc\run_qc.py`;
- downloads the current `main` QC script;
- runs Chapter 1 in `--observe-only` mode;
- does not delete WAV files;
- does not call `repair_chunks`;
- verifies word confidence, speaking rate, pause ratio, energy variation and audio SHA-256 observations;
- reports pitch/F0 coverage as an additional field signal;
- keeps manuscript/audio/report data local.

This field gate is intended to prove measurement extraction before pronunciation/prosody repair is enabled.


## Editorial-first + post-render QC

Long-form narration now has two mandatory quality stages:

1. **Pre-render Editorial QA** decides semantic chunk boundaries, breathing/pause intent, emphasis intent, and explicit MUST_CHECK pronunciation phrases while preserving canonical source text.
2. **Post-render QC remains authoritative**. ASR/word confidence, pronunciation, prosody, acoustic validity and repair-budget rules still run after VieNeu synthesis.

A successful render is not an acceptance verdict.

For private/local manuscript preparation use:

```powershell
python tools\saydi_tts\narration\prepare_editorial_manifest.py --input <local.txt> --output <local-manifest.json> --must-check "người phụ nữ"
```

Do not commit private manuscript text or generated audio.

Narration assembly also performs click-safe edge preparation:

- 20 ms fade-in;
- 25 ms fade-out;
- exact-zero segment endpoints;
- 12 ms crossfade only when adjacent speech has an intentional zero gap;
- per-segment edge evidence and chapter-level `stitching_gate_pass`.
