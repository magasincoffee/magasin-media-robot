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

- TXT, DOCX, EPUB and text-based PDF ingestion through adapters.
- Canonical book/chapter/paragraph/segment manifest.
- Vietnamese-first text normalization with deterministic rules.
- Pronunciation lexicon for names, abbreviations, numbers and special terms.
- Narration plan with voice, style, speed, pause and pronunciation directives.
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
- application-level voice presets.

This work is retained as provider evidence and must not be reimplemented from scratch.

## Target architecture

```text
SOURCE BOOK
   |
   v
Book Ingest
   |
   v
Canonical Book Manifest
   |
   v
Text Normalization + Segmentation
   |
   v
Narration Director + Pronunciation Lexicon
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

**Architecture generation:** SAYDI-AUDIOBOOK-V1  
**Current phase:** architecture reset from video-first product to audiobook-first product.  
**SaydiVoice discovery:** retained and considered the verified provider foundation.  
**Audiobook production implementation:** not yet implemented.

## Authoritative task queue

- **SAYDI-001 — Audiobook architecture + single Source of Truth:** DONE when this architecture change is merged to `main`.
- **SAYDI-002 — Production SaydiVoice provider adapter:** NEXT.
- **SAYDI-003 — Book ingest + canonical manifest.**
- **SAYDI-004 — Text normalization + stable segmentation.**
- **SAYDI-005 — Narration director + pronunciation lexicon + sample approval.**
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
3. validate/adjust chapter structure and pronunciation;
4. approve a narrator sample;
5. synthesize a complete long-form book with interruption/resume;
6. detect and isolate material QA problems;
7. repair only affected segments;
8. assemble and master chapters;
9. export a validated M4B and/or chapter MP3 package;
10. produce a sanitized diagnostic bundle when recovery is not automatic.
