# SAYDI Audiobook — Product Vision

## Product goal

Build a professional Windows audiobook production system that converts a legally usable manuscript into a finished audiobook with minimal manual work.

The product is **audiobook-first**. The previous social-video direction is paused.

## Primary UX

The daily workflow should be:

```text
IMPORT BOOK
  -> REVIEW STRUCTURE
  -> CHOOSE NARRATOR / STYLE
  -> APPROVE SAMPLE
  -> CREATE AUDIOBOOK
  -> REVIEW EXCEPTIONS
  -> EXPORT
```

The operator should not need to understand Playwright, FFmpeg, browser profiles, codecs, chunking, SQLite, alignment models, or provider-specific controls.

## Professional quality objectives

- textual fidelity: no silent omission, duplication or rewriting;
- stable chapter and segment identity;
- natural long-form narration controls;
- pronunciation control for proper nouns and difficult terms;
- consistent audio across hours of narration;
- resumable generation after interruption;
- isolated repair instead of full-book regeneration;
- measurable QA before export;
- reproducible project state and diagnostics;
- privacy-safe local storage.

## Core design principles

- **Local-first:** books, working audio, state and diagnostics stay local by default.
- **Provider-neutral:** SaydiVoice is the first TTS adapter, not the product core.
- **Segment-addressed:** every generated spoken unit can be individually tracked and regenerated.
- **Deterministic before intelligent:** canonical parsing, normalization and QA rules precede optional AI enhancements.
- **Human approval at the right boundary:** approve narrator/style with a short sample before expensive full-book generation.
- **Resumable:** long jobs persist checkpoints continuously.
- **Auditable:** every export can be traced to source manifest, narration plan, generated segments and QA evidence.
- **Secure by default:** credentials, sessions, private books and generated audio never enter Git.

## Source-rights boundary

SAYDI processes only content the operator has the right to reproduce or transform, including owned manuscripts, licensed works and public-domain works. The product does not include DRM bypass or unauthorized acquisition workflows.

## Definition of project completion

V1 is complete when a clean supported Windows machine can install SAYDI, complete one-time provider setup, import a book, approve a sample, create a full audiobook with interruption/resume, detect and repair isolated failures, and export validated M4B and/or chapter MP3 artifacts with a QA report.
