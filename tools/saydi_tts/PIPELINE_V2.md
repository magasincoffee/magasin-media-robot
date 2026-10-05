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


## Default local QC mode

Default: **ON**.

The Owner does not need to request QC for each audiobook run.

After every chapter is assembled, the local pipeline should automatically:

1. record chapter/chunk traceability metadata;
2. run structural/coverage checks;
3. run acoustic and join-continuity checks;
4. record PASS/REVIEW/FAILED status;
5. when available, run local ASR/alignment against approved spoken text;
6. route only suspicious segments to review/repair.

QC markers are metadata only and must be inaudible.

### Repair behavior

Do not regenerate an entire chapter when one segment fails.

Repair flow:

```text
QC finding
 -> chapter + chunk/segment + timecode
 -> repair/regenerate only affected unit
 -> rerun unit QC
 -> rebuild chapter
 -> keep all unaffected accepted audio
```

### Current deployment status

On `DESKTOP-H4A16IL`:

- default local VieNeu rendering: active;
- boot/restart recovery: active;
- chunk checkpoint/resume: active;
- per-chapter MP3 assembly: active;
- QC metadata/event store: active;
- full local ASR/forced-alignment pass: required by default architecture, implementation/field acceptance pending.

Until ASR acceptance is complete, do not claim semantic speech verification is fully automatic.


## Post-render QC waiter

For unattended long runs, install:

`tools/saydi_tts/qc/INSTALL_WAIT_QC_50.ps1`

Behavior:

```text
render chapter jobs
 -> waiter checks durable book/chapter status every 5 minutes
 -> after chapters 1-5 are COMPLETE
 -> create isolated QC venv
 -> install faster-whisper + acoustic dependencies
 -> Acoustic QC
 -> ASR reverse verification
 -> exact chapter/chunk/timecode report
 -> bounded technical auto-repair only
 -> re-QC repaired chapter
 -> write local report + Supabase QC metadata
 -> disable waiter after success
```

The waiter is restart-safe because it is installed as a Windows Scheduled Task and does not require an open terminal.

ASR mismatch alone is never auto-repaired because the mismatch may come from names, punctuation, source extraction, or ASR uncertainty. Automatic repair is restricted to high-confidence technical failures such as missing/corrupt/near-zero or severe clipping/duration failures.


## Pipeline V3 — narration-preprocessed audiobook

**This supersedes direct PDF-text -> fixed-size chunk rendering for production books.**

Before queue creation:

1. clean PDF extraction artifacts;
2. reconstruct paragraphs and sentences;
3. classify semantic blocks;
4. generate `spoken_text`;
5. generate narration directives;
6. render headings as dedicated segments;
7. segment body text on semantic/paragraph boundaries;
8. run a Chapter 1 preview gate before full-book synthesis.

### Default heading treatment

```text
[PAUSE]
"Chương 3."
[short pause]
"Bước hai: Tuyên bố Vai Ong Chúa của doanh nghiệp."
[longer pause]
<body narration begins>
```

Do not concatenate heading + body into the same long chunk.

### Production status rule

A technically successful render that bypasses Narration Preprocess is `DRAFT`, not `FINAL`.

The current Doanh Nghiệp Tự Hành run is the baseline draft used to validate worker/restart/assembly/QC infrastructure. The next production rerender must use Pipeline V3 and receive Chapter 1 listening approval before full-book replacement.

## Pipeline V4 — Narration Director

**This is the target path for expressive long-form STORY_NARRATIVE output.**

The first Golden Story sample proved that post-render prosody QC alone is insufficient: a technically valid render can still be too fast, under-paused and semantically flat.

Before TTS, Pipeline V4 creates a versioned narration plan:

```text
canonical text
 -> semantic beat classification
 -> sentence/scene segmentation
 -> provider-safe punctuation hint
 -> VieNeu semantic-unit render
 -> beat-specific pitch-preserving tempo
 -> explicit semantic pause insertion
 -> loudness normalization
 -> pronunciation/prosody QC
 -> Owner preview gate
```

Narration Director v1 beats:

- NARRATIVE
- REFLECTIVE_SAD
- TENSION
- DIALOGUE_TENDER
- DIALOGUE_TENSION
- WARM_RELIEF
- SCENE_TRANSITION
- RESOLUTION

### Important provider rule

Do not label structural approximation as a native VieNeu emotion feature.

Until a native emotion/style control is field-verified, emotional delivery is approximated only through:

- semantic segmentation;
- punctuation;
- verified voice/reference selection;
- explicit inter-segment pauses;
- pitch-preserving post-render tempo.

### Production gate

Golden Story V2 is the field gate for this architecture.

Only after Owner accepts its A/B listening result may Narration Director become the default STORY_NARRATIVE path for production books.
