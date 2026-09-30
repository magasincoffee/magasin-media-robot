# SAYDI Audiobook Roadmap

The authoritative task state is `00_PROJECT/SOURCE_OF_TRUTH.md`. This roadmap defines phase intent and acceptance gates.

## SAYDI-001 — Architecture + single Source of Truth

Status: architecture package prepared for merge.

Deliverables:

- audiobook-first product vision;
- single project Source of Truth;
- domain architecture;
- versioned data-contract direction;
- task queue;
- updated QA/development rules;
- explicit preservation of existing SaydiVoice discovery.

Exit gate: all active project documentation agrees that SAYDI Audiobook is the current product and `SAYDI-002` is the only NEXT task.

## SAYDI-002 — Production SaydiVoice provider adapter

Convert field-verified discovery behavior into a stable production interface.

Deliverables:

- request/result models;
- authenticated preflight;
- voice/style application and verification;
- one-attempt side-effect guard;
- controlled download to local storage;
- error taxonomy;
- reconciliation state;
- privacy-safe diagnostics;
- offline tests before live acceptance.

Exit gate: one explicitly authorized production acceptance segment generates and downloads through the new adapter, with metadata/hash validation and no duplicate generation.

## SAYDI-003 — Book ingest + canonical manifest

Deliverables:

- book project creation;
- TXT adapter;
- DOCX adapter;
- EPUB adapter;
- text-PDF adapter;
- source hashing/provenance;
- chapter/block model;
- manifest schema and fixtures.

Exit gate: supported fixtures import deterministically and reproduce the same structural manifest.

## SAYDI-004 — Text normalization + stable segmentation

Deliverables:

- Vietnamese Unicode/punctuation rules;
- spoken numbers/dates/units/abbreviations;
- original vs spoken-text preservation;
- stable segment IDs;
- content hashes;
- invalidation rules;
- regression corpus.

Exit gate: identical input/config generates identical segments and targeted source edits invalidate only affected downstream work.

## SAYDI-005 — Narration director + pronunciation lexicon + sample approval

Deliverables:

- narrator profile;
- semantic style presets;
- pronunciation dictionary;
- pause policy;
- narration fingerprint;
- sample-plan generation;
- approval persistence/invalidation.

Exit gate: full synthesis cannot start without an approval matching the active narration fingerprint.

## SAYDI-006 — Segment synthesis orchestration + resume/idempotency

Deliverables:

- SQLite state store;
- durable job graph;
- operation IDs;
- concurrency policy;
- checkpoint/resume;
- safe retry classes;
- provider reconciliation;
- progress events.

Exit gate: kill/restart during a multi-segment run resumes without duplicating accepted segments.

## SAYDI-007 — Audio processing + chapter assembly + mastering

Deliverables:

- raw audio validation;
- technical normalization;
- pause insertion;
- chapter concatenation;
- configurable mastering profile;
- immutable raw artifacts;
- processed artifact hashes.

Exit gate: deterministic chapter builds validate with FFprobe and can be rebuilt without provider calls.

## SAYDI-008 — Alignment/acoustic QA + isolated repair

Deliverables:

- exact segment coverage checks;
- ASR/alignment verification adapter;
- mismatch scoring;
- silence/clipping/zero-audio checks;
- review queue;
- regenerate-selected-segment workflow;
- book QA report.

Exit gate: seeded missing/duplicate/corrupt/mismatched cases are detected and repaired without rebuilding unaffected chapters.

## SAYDI-009 — Export engine

Deliverables:

- M4B;
- chapter MP3;
- chapter metadata;
- book metadata;
- optional cover embedding;
- export manifest;
- final validation.

Exit gate: exported artifacts open/parse successfully and chapter order/metadata match the canonical manifest.

## SAYDI-010 — Windows desktop control center

Deliverables:

- import/review/configure/sample/approve/create/pause/resume/review/repair/export workflow;
- progress and actionable errors;
- diagnostics access without exposing technical complexity.

Exit gate: normal production does not require terminal commands.

## SAYDI-011 — Installer + end-to-end production acceptance

Deliverables:

- supported clean-machine setup;
- prerequisite validation;
- one-time SaydiVoice login flow;
- upgrade-safe local data handling;
- long-form acceptance book;
- privacy/security review;
- rollback/recovery notes.

Exit gate: a clean supported Windows machine completes the professional acceptance scenario defined in `ARCHITECTURE.md`.
