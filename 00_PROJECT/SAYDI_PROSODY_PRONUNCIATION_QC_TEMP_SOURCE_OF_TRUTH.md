# SAYDI Prosody + Pronunciation QC — Temporary Source of Truth

Status: ACTIVE
Owner directive date: 2026-10-04
Authority scope: local VieNeu audiobook quality control only.

## Owner objective

The Owner should be able to request an audiobook style/genre and let SAYDI handle routine narration quality automatically.

The local pipeline must not stop at "the words roughly match the manuscript". It must also detect and reduce:

- unclear or slurred Vietnamese words ("lơ lớ", swallowed syllables, weak consonants/vowels);
- wrong or unstable pronunciation of names, abbreviations, numbers and foreign terms;
- robotic/flat intonation;
- pace that is too fast or too slow for the selected narration profile;
- unnatural pauses or missing pauses;
- low expressive variation inconsistent with the selected audiobook style;
- clipping/technical defects.

The target is materially more natural long-form listening, not a false promise of perfect human equivalence.

## Non-negotiable design rules

1. QC is DEFAULT-ON after synthesis.
2. Never regenerate an entire chapter when only one chunk is defective.
3. Every QC verdict is attached to the exact audio SHA-256 it evaluated.
4. Automatic repair is bounded. Never create an infinite rerender loop.
5. A repair that changes meaning, narrator identity, or materially changes narration style requires Owner review.
6. Private manuscript text/audio remains local and must not be uploaded to GitHub artifacts.
7. ASR similarity alone is insufficient for final acceptance.
8. Preserve source text separately from any TTS-only spoken-form/pronunciation rewrite.
9. If a pronunciation defect remains after the retry budget, escalate the exact word/chunk/timecode instead of hiding it.

## Target pipeline

```text
SOURCE TEXT
   |
   v
spoken normalization + pronunciation lexicon
   |
   v
VieNeu TTS render
   |
   v
ASR / forced-alignment pronunciation QC
   |
   +--> unclear/mispronounced word? --> targeted spoken-form/segmentation repair --> rerender chunk
   |
   v
prosody/style QC
   |
   +--> flat / wrong pace / bad pause pattern? --> bounded narration repair --> rerender chunk
   |
   v
acoustic/join QC
   |
   v
PASS -> chapter assembly/export
```

## Required measurements per chunk

Minimum local measurements:

- ASR text similarity;
- word-level confidence/alignment where available;
- exact suspect/unclear tokens;
- speaking rate (words per minute);
- pause/silence ratio and abnormal pause locations;
- pitch/F0 variation or equivalent intonation metric;
- energy/dynamics variation;
- clipping/technical validity;
- attempt number and exact audio hash.

## Automatic pronunciation repair order

For a suspect Vietnamese word or phrase:

1. keep canonical/original text unchanged;
2. apply an explicit pronunciation lexicon/spoken-form override when a known entry exists;
3. normalize abbreviation/number/name/foreign-term reading;
4. split the chunk near the suspect token to reduce TTS context failure;
5. rerender only that chunk;
6. run ASR + pronunciation QC again;
7. if the bounded retry budget is exhausted, require review or a voice/model fallback.

Do not "fix" pronunciation by silently changing semantic content.

## Automatic prosody/style repair order

For a chunk outside the active narration profile:

1. adjust sentence/chunk boundaries;
2. adjust supported pace/pause controls;
3. add TTS-only punctuation/spoken-form hints when semantically safe;
4. rerender only the affected chunk;
5. rerun pronunciation + prosody + acoustic QC;
6. escalate after the retry budget instead of looping forever.

## Task queue

### SAYDI-QC-001 — Core quality contracts and deterministic repair policy

Status: DONE — merged to main in PR #60; CI PASS

Required:
- provider-neutral quality observation/report contracts;
- pronunciation/prosody/acoustic decision policy;
- bounded auto-repair plan;
- tests proving unclear pronunciation, flat delivery, retry exhaustion and incomplete metrics behavior.

Acceptance:
- code compiles;
- unit tests pass;
- no provider/browser dependency enters the audiobook core.

### SAYDI-QC-002 — Local worker metric extraction

Status: DONE — field acceptance PASS on DESKTOP-H4A16IL

Required on `C:\SAYDI\worker`:
- preserve current ASR similarity QC; **IMPLEMENTED**
- add word-level confidence/alignment evidence; **IMPLEMENTED via faster-whisper word timestamps**
- calculate speaking rate; **IMPLEMENTED**
- calculate pause/silence ratio; **IMPLEMENTED**
- calculate pitch/intonation variation; **IMPLEMENTED coarse local F0 variation**
- calculate energy/dynamics variation; **IMPLEMENTED**
- emit one structured observation per chunk keyed by audio SHA-256. **IMPLEMENTED**

Acceptance:
- works on DESKTOP-H4A16IL;
- metrics are persisted locally;
- no private audio/text is uploaded.

### SAYDI-QC-002 field evidence

Accepted on 2026-10-04 using Chapter 1 in non-mutating `--observe-only` mode.

Observed evidence:

- chunks observed: 24/24;
- word-confidence metric: 24/24;
- speaking-rate metric: 24/24;
- pause-ratio metric: 24/24;
- pitch-variation metric: 24/24;
- energy-variation metric: 24/24;
- audio SHA-256 traceability: 24/24;
- field gate result: `FIELD GATE CORE METRICS: PASS`;
- observe-only safety confirmed: no WAV deletion and no `repair_chunks` request.

This proves metric extraction and local persistence. It does **not** mean the chapter itself is quality-clean: the same QC pass reported 25 warnings and 1 error, which become input evidence for subsequent pronunciation/prosody repair tasks.

### SAYDI-QC-003 — Vietnamese pronunciation lexicon + spoken-form repair

Status: IMPLEMENTED_IN_PR — CI / merge verification pending

Required:
- versioned pronunciation lexicon; **IMPLEMENTED: vi-pronunciation-v1 + custom lexicon loader**
- safe TTS-only spoken-form layer; **IMPLEMENTED**
- rules for abbreviations, numbers, names and foreign terms; **IMPLEMENTED with conservative explicit-entry policy**
- record exact suspect tokens and applied overrides; **IMPLEMENTED**
- keep canonical source immutable. **IMPLEMENTED + regression tested**

Acceptance:
- known hard words can be corrected without changing source text;
- regression fixtures cover Vietnamese diacritics and common ambiguous forms.

### SAYDI-QC-004 — Targeted automatic rerender loop

Status: PENDING

Required:
- rerender only failed chunks;
- bounded retry budget (default maximum two attempts);
- re-run all QC layers after each repair;
- prevent duplicate/infinite jobs;
- rebuild only dependent chapter artifact after chunk acceptance.

Acceptance:
- one bad chunk does not regenerate accepted chunks;
- retry exhaustion becomes REVIEW with exact location/evidence.

### SAYDI-QC-005 — Prosody/style profiles by audiobook type

Status: PENDING

Required:
- define per-profile pace, pause and intonation envelopes for at least BUSINESS_CLEAR, STORY_NARRATIVE and GENERAL_CLEAR;
- map Owner's simple genre/style request to the profile;
- allow provider-supported controls only; never fabricate unsupported controls.

Acceptance:
- profile-specific QC catches deliberately flat/too-fast/too-slow fixtures;
- changing profile invalidates QC acceptance as required.

### SAYDI-QC-006 — Field acceptance on local VieNeu

Status: PENDING

Required:
- use synthetic/public-domain Vietnamese test passages;
- include intentionally difficult pronunciation and expressive passages;
- demonstrate defect detection, targeted rerender, and final PASS/REVIEW;
- compare before/after samples by Owner listening only at the final acceptance gate.

Acceptance:
- pronunciation defects are localized;
- prosody defects are localized;
- automatic repairs are bounded;
- chapter output remains traceable and listener audio contains no QC markers.

## Current next task

Complete CI/merge verification for `SAYDI-QC-003`. After merge, advance to `SAYDI-QC-004` — targeted automatic rerender loop.

