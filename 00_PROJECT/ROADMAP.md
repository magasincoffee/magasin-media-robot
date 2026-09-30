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

## SAYDI-002 — Executable vertical slice + provider/AI contracts

Make SAYDI runnable early so the real operator flow can be observed before full-book scale.

Deliverables:

- minimal production Python package/CLI runner;
- structured `AnalysisProvider` contract;
- structured `VoiceProvider` request/result contract;
- deterministic no-LLM fallback for the first slice;
- local-LLM adapter boundary;
- production SaydiVoice adapter using field-verified behavior;
- narration fingerprint and approval state;
- text-preview gate;
- bounded real audio-sample generation;
- operation-id/idempotency/privacy/schema tests;
- durable run artifact/log layout.

Exit gate: a small synthetic/public-domain input can traverse the runner to a real audible sample, the operator can approve/reject it, and rerunning the same operation does not accidentally duplicate provider side effects.

## SAYDI-003 — PDF-first book ingest + canonical manifest

Deliverables:

- book project creation;
- text-PDF adapter first;
- scan/PDF classifier and OCR path;
- repeated page-furniture cleanup;
- reading-order reconstruction;
- TXT/DOCX/EPUB adapters after the PDF-first gate;
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

## SAYDI-005 — Intelligence + narration director + voice casting/sample approval

Deliverables:

- Rule Engine + local LLM decision path;
- book-level genre/subgenre/tone profile;
- segment-level context/emotion/prosody analysis;
- schema validation + confidence/review routing;
- narrator profile;
- semantic style presets;
- representative 3-5 passage sample selection;
- text-preview approval;
- audio-sample approval;
- pronunciation dictionary;
- pause policy;
- narration fingerprint;
- sample-plan generation;
- approval persistence/invalidation.

Exit gate: full synthesis cannot start without a text-approved interpretation and audio approval matching the active narration fingerprint; local LLM operation is demonstrated and a no-cloud path remains available.

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
