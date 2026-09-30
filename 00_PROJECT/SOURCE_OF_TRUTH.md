# SAYDI Audiobook — Source of Truth

Last updated: 2026-09-30

## Authority

This file is the single authoritative project state for the SAYDI Audiobook track in this repository.

Precedence:

1. `00_PROJECT/SOURCE_OF_TRUTH.md`
2. architecture and decision records referenced by this file
3. current implementation and tests on `main`
4. historical status/changelog/discovery notes

If another document conflicts with this file, this file wins until it is deliberately updated.

## Product identity

**Product:** SAYDI Audiobook  
**Repository:** `magasincoffee/magasin-media-robot`  
**Operating model:** local-first Windows audiobook production with a replaceable TTS provider layer.  
**Initial TTS provider:** SaydiVoice through the already field-verified authenticated Chrome/Playwright path.

The previous social-video product direction is paused. Existing SaydiVoice discovery work is retained because it is reusable production evidence for the audiobook voice layer.

## Product goal

Turn a legally usable manuscript into a production-ready audiobook with minimal operator work while preserving textual fidelity, resumability, privacy, and auditable QA.

Primary user flow:

```text
Import book
  -> verify chapter structure
  -> choose narrator / style
  -> approve a short voice sample
  -> create audiobook
  -> review QA exceptions
  -> export M4B and/or chapter MP3
```

## In scope for V1

- **PDF-first ingestion** as a primary user path, including:
  - text-based PDF extraction;
  - scanned/image PDF classification;
  - OCR adapter path for scanned pages;
  - page/header/footer/page-number cleanup;
  - structural reconstruction into book/chapter/block form;
  - OCR confidence and suspicious-text review for low-confidence material.
- TXT, DOCX and EPUB ingestion through adapters.
- Canonical book/chapter/paragraph/segment manifest.
- **Three-layer text model**:
  - `original_text` — immutable extracted/source text;
  - `normalized_text` — deterministic cleanup and punctuation/structure normalization;
  - `spoken_text` — speech-oriented rendering used by TTS.
- Vietnamese-first text normalization with deterministic rules.
- **Narrative interpretation** for sentence boundaries, dialogue, narrator text, rhetorical rhythm and ambiguous punctuation.
- **Annotation handling** for footnotes, endnotes, citations, page references, parentheticals, editor/translator notes and sidebars.
- **Prosody direction** for pause, pace, emphasis, energy and semantic emotion.
- Pronunciation lexicon for names, abbreviations, numbers and special terms.
- Narration plan with voice, style, speed, pause, emphasis, emotion and pronunciation directives.
- Segment-addressed TTS generation with checkpoints and resumable execution.
- SaydiVoice production provider adapter.
- Local audio processing with FFmpeg/FFprobe.
- Chapter assembly and book-level mastering.
- Text-to-audio coverage QA and acoustic QA.
- Automatic regeneration only for isolated segments when the failure is proven retry-safe.
- M4B and chapter-MP3 export with metadata and chapter markers.
- Windows desktop operator flow.
- Local runtime state, logs and diagnostics.

## Explicitly out of scope for initial V1

- Video generation/editing.
- Automatic rewriting or summarizing of the author's prose.
- Voice cloning without explicit rights/authorization.
- DRM bypass or acquisition of copyrighted books without permission.
- Fully autonomous publication to third-party stores.
- Heavy generative-AI models unless a measured requirement justifies them.

## Existing verified foundation

The repository already contains field-verified SaydiVoice discovery under `01_DISCOVERY/saydivoice`.

Verified capabilities include:

- authenticated persistent Chrome session on the trusted Windows runner;
- voice discovery and selection;
- stability/expression, speed, pause and format controls;
- one-shot generation;
- download lifecycle;
- privacy-safe evidence handling;
- application-level voice presets;
- observed pause controls for period, comma, semicolon and newline;
- current discovery control layer can read pause timing values and enable/disable pause behavior.

Known provider boundary:

- the current discovery control layer does **not** yet support writing arbitrary per-punctuation pause timing values;
- no separate discrete provider control for emotions such as Happy/Sad/Angry has been observed;
- therefore audiobook emotion/prosody is an application-level semantic model mapped only onto provider controls that are actually verified.

This work is retained as provider evidence and must not be reimplemented from scratch.

## Target architecture

```text
SOURCE BOOK / PDF
   |
   v
PDF Classifier / Book Ingest
   |
   +--> text PDF extraction
   +--> scanned PDF OCR
   |
   v
Canonical Book Manifest
   |
   v
Structure + Annotation Parser
   |
   v
Original -> Normalized -> Spoken Text
   |
   v
Narrative Interpretation
   |
   v
Prosody Director + Pronunciation Lexicon
   |
   v
Segment Job Orchestrator
   |
   +--> Voice Provider Adapter --> SaydiVoice
   |
   v
Audio Processing / Assembly
   |
   v
Alignment + Acoustic QA
   |
   +--> repair queue for isolated segments
   |
   v
Export Engine
   |
   +--> M4B
   +--> chapter MP3
   +--> metadata / QA report
```

## Architectural invariants

1. **Immutable source:** imported source files are never destructively modified.
2. **Canonical manifest:** every spoken unit has a stable ID derived from the normalized book structure.
3. **Segment-addressed generation:** the smallest regeneratable unit is a segment, not a whole chapter or book.
4. **Provider isolation:** SaydiVoice-specific browser logic never leaks into book/text/audio domain logic.
5. **Idempotent orchestration:** rerunning a completed safe step must not duplicate audio or corrupt state.
6. **Explicit side effects:** live TTS generation is a controlled side effect with bounded retry policy.
7. **Local-first privacy:** source books, generated audio, sessions and credentials remain local by default.
8. **Fidelity before style:** no text may be silently omitted, duplicated or rewritten for performance.
9. **QA before export:** an audiobook cannot reach READY until required structural, coverage and acoustic gates pass.
10. **Resume by checkpoint:** interruption must resume from the last verified safe state.
11. **Three text layers are mandatory:** `original_text`, `normalized_text`, and `spoken_text` must be stored separately; spoken improvements never overwrite source fidelity.
12. **Punctuation is interpreted, not blindly trusted:** poor or missing punctuation may be repaired only in derived normalized/spoken layers and must preserve meaning.
13. **Annotations are explicit domain objects:** footnotes/endnotes/citations/editor notes must be classified and governed by a read/skip/defer/review policy; they must never disappear silently.
14. **Emotion is semantic, provider-neutral metadata:** SAYDI may classify delivery emotion/energy, but provider adapters may use only controls the provider actually exposes.
15. **Uncertain interpretation becomes review:** low-confidence OCR, sentence-boundary, annotation or narration decisions must be surfaced instead of silently guessed.

## Professional narration requirements

These requirements are mandatory for a production-quality audiobook and are not optional polish.

### 1. Three text representations

Every source span that can become spoken audio must preserve:

```text
ORIGINAL_TEXT
    |
    v
NORMALIZED_TEXT
    |
    v
SPOKEN_TEXT
```

Example:

```text
original_text:
"3kg, xem chú thích (1)."

normalized_text:
"3 kg, xem chú thích (1)."

spoken_text:
"ba ki-lô-gam. Xem chú thích số một."
```

Rules:

- `original_text` is immutable evidence.
- `normalized_text` may repair Unicode, spacing, punctuation and structural defects.
- `spoken_text` may express numbers, units, abbreviations and speech-specific phrasing.
- normalization/spoken rendering must not summarize, omit, invent or change the semantic meaning of the work.

### 2. Punctuation and sentence reconstruction

SAYDI must not assume source punctuation is correct.

The text engine must be able to:

- detect missing/duplicated/malformed punctuation;
- infer likely sentence boundaries from syntax and semantics;
- split excessively long sentences for natural narration;
- preserve ellipsis, interruption and rhetorical pauses when meaningful;
- assign confidence to repairs;
- route low-confidence changes to review.

Example:

```text
source:
"Anh nhìn cô không nói gì rồi bước đi cô vẫn đứng đó"

spoken interpretation:
"Anh nhìn cô, không nói gì, rồi bước đi. Cô vẫn đứng đó."
```

This change is derived narration text only; the source remains unchanged.

### 3. Annotation / footnote policy

Annotations must be classified into at least:

- `FOOTNOTE`
- `ENDNOTE`
- `CITATION`
- `PAGE_REFERENCE`
- `PARENTHETICAL`
- `EDITOR_NOTE`
- `TRANSLATOR_NOTE`
- `SIDEBAR`

Each annotation receives an explicit policy:

- `READ_INLINE`
- `READ_AT_CHAPTER_END`
- `SKIP_BY_APPROVED_POLICY`
- `SPEECH_NORMALIZE`
- `REQUIRE_REVIEW`

No annotation may be silently deleted merely because it is inconvenient for TTS.

### 4. Narrative interpretation

Before TTS, SAYDI must identify narration context such as:

- narrator prose;
- dialogue;
- quoted material;
- speaker turn where reasonably inferable;
- rhetorical question/exclamation;
- interruption/hesitation;
- reflective/internal passage;
- headings and chapter openings.

V1 does not require automatic multi-voice casting. The interpretation layer must still preserve speaker/context metadata so a single narrator can vary delivery and later versions can add multiple voices without reparsing the book.

### 5. Prosody plan

Each spoken segment may carry provider-neutral directives such as:

```text
emotion
emotion_intensity
pace
energy
pause_before_ms
pause_after_ms
emphasis[]
speaker_role
confidence
```

Initial semantic emotion vocabulary:

- `neutral`
- `warm`
- `joyful`
- `sad`
- `tense`
- `urgent`
- `reflective`
- `mysterious`
- `authoritative`

This is SAYDI metadata, not a claim that SaydiVoice exposes these emotions directly.

The SaydiVoice adapter may translate these semantics into verified controls such as:

- voice selection;
- stability/expression;
- speed;
- pause enable/profile;
- segment boundary pauses.

Unsupported provider controls must never be fabricated.

### 6. Confidence and review gates

Interpretation layers must emit confidence/review state for uncertain cases.

At minimum:

- OCR confidence;
- sentence-boundary confidence;
- annotation-classification confidence;
- narration/prosody confidence where automatic interpretation materially changes delivery.

High-confidence deterministic corrections may proceed automatically.

Low-confidence or materially ambiguous cases enter a **REVIEW queue** so the operator reviews exceptions rather than manually proofreading the entire book.

### 7. PDF-first quality behavior

For PDF input:

```text
PDF
 -> classify text vs scan
 -> extract or OCR
 -> remove repeated page furniture
 -> reconstruct reading order
 -> detect chapters/blocks/annotations
 -> quality review exceptions
 -> canonical book
```

The system must never read recurring page numbers, headers, footers or watermark text merely because PDF extraction returned them.

## Runtime authority

Book/job state is persisted locally. The initial implementation target is SQLite plus immutable/intermediate files under the local runtime root.

Recommended runtime root:

```text
%LOCALAPPDATA%/SAYDI/Audiobook/
  config/
  browser_profile/
  library/
    <book_id>/
      source/
      manifests/
      segments/
      audio/raw/
      audio/processed/
      chapters/
      exports/
      qa/
      logs/
  cache/
  diagnostics/
```

Runtime data never belongs in Git.

## Book job lifecycle

```text
IMPORTED
 -> NORMALIZED
 -> PLANNED
 -> SAMPLE_APPROVED
 -> SYNTHESIZING
 -> ASSEMBLING
 -> QA
 -> READY
 -> EXPORTED
```

Exception states:

- `ACTION_REQUIRED`
- `RETRYABLE_FAILURE`
- `FATAL_FAILURE`
- `CANCELLED`

## Quality gates

A production export requires all applicable gates:

- source structure validated;
- for PDF: text/scan classification completed and OCR/extraction quality exceptions resolved;
- no unresolved repeated header/footer/page-number artifacts in spoken content;
- three-layer text lineage is complete for every spoken segment;
- punctuation/sentence reconstruction review items are resolved;
- annotation policy is explicit for every detected annotation;
- narration/prosody review items above configured uncertainty threshold are resolved;
- every canonical segment accounted for exactly once;
- no unresolved missing/duplicate audio;
- no failed segment jobs;
- duration and silence checks within configured limits;
- clipping/decoding checks pass;
- text-to-audio verification has no unresolved material mismatch;
- chapter ordering and metadata validated;
- export artifact opens successfully with FFprobe or the relevant container validator;
- QA report is persisted with the export.

## Current authoritative status

**Architecture generation:** SAYDI-AUDIOBOOK-V1.1  
**Current phase:** architecture reset from video-first product to audiobook-first product.  
**SaydiVoice discovery:** retained and considered the verified provider foundation.  
**Audiobook production implementation:** not yet implemented.

## Authoritative task queue

- **SAYDI-001 — Audiobook architecture + single Source of Truth:** DONE.
- **SAYDI-002 — Production SaydiVoice provider adapter:** NEXT.
- **SAYDI-003 — PDF-first book ingest + canonical manifest:** classify text/scanned PDF, extract/OCR, reconstruct reading order, remove repeated page furniture, detect chapters/blocks, preserve provenance and expose OCR exceptions.
- **SAYDI-004 — Text interpretation foundation:** implement `original_text -> normalized_text -> spoken_text`, punctuation/sentence reconstruction, number/date/unit/abbreviation speech normalization, annotation parser/policy, stable segmentation and confidence/review outputs.
- **SAYDI-005 — Professional narration director:** implement dialogue/context interpretation, semantic emotion, prosody/pause/emphasis/pace plans, pronunciation lexicon, narration fingerprint and sample approval.
- **SAYDI-006 — Segment synthesis orchestration + resume/idempotency.**
- **SAYDI-007 — Audio processing, chapter assembly and mastering.**
- **SAYDI-008 — Alignment/acoustic QA + isolated repair loop.**
- **SAYDI-009 — M4B/chapter-MP3 export + metadata.**
- **SAYDI-010 — Windows desktop control center.**
- **SAYDI-011 — Clean-machine installer + end-to-end production acceptance.**

Only one task should be treated as NEXT at a time.

## Immediate next task

**SAYDI-002 — Production SaydiVoice provider adapter.**

It must convert the field-verified discovery behavior into a stable provider-neutral request/result contract without changing audiobook domain logic.

## Completion definition for the project

SAYDI Audiobook V1 is production-ready when a clean supported Windows machine can:

1. complete one-time setup and SaydiVoice authentication;
2. import a supported book;
3. validate/adjust chapter structure, OCR exceptions, annotations, punctuation interpretation and pronunciation;
4. approve a narrator sample that demonstrates the active prosody/emotion policy;
5. synthesize a complete long-form book with interruption/resume;
6. detect and isolate material QA problems;
7. repair only affected segments;
8. assemble and master chapters;
9. export a validated M4B and/or chapter MP3 package;
10. produce a sanitized diagnostic bundle when recovery is not automatic.


## Implementation ordering constraint

A full-book production acceptance is forbidden until `SAYDI-003`, `SAYDI-004`, and `SAYDI-005` satisfy their gates.

`SAYDI-002` remains the immediate NEXT task because the provider boundary is required by later stages, but it must stay provider-neutral so punctuation repair, annotation policy, emotion and prosody logic live upstream in the audiobook domain rather than being hard-wired into SaydiVoice browser automation.
