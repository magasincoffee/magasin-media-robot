# SAYDI Audiobook — Source of Truth

Last updated: 2026-10-04

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
**Operating model:** local-first Windows audiobook production with replaceable AI/TTS providers and no mandatory paid/cloud dependency.  
**AI policy:** deterministic rules first; local LLM is the default semantic-analysis path; ChatGPT/other cloud LLMs are optional fallbacks only when explicitly enabled by the owner.  
**Voice policy:** provider-neutral Voice Engine; the final V1 must have an all-local TTS path. SaydiVoice remains a field-verified optional provider and is the fastest real provider for early workflow validation.

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
- **AI Analysis Interface** with structured output, schema validation, confidence and review routing.
- **Local LLM default path** for book/segment analysis with model replacement behind an adapter.
- Optional ChatGPT/cloud-LLM fallback that is disabled by default and must never receive manuscript text without explicit operator enablement.
- **Rule Engine + Local LLM + Human Approval** authority model.
- Provider-neutral Voice Engine with both:
  - SaydiVoice production adapter;
  - an all-local TTS provider path before V1 production acceptance.
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

## Windows SAPI narration quality decision

Operator listening verdict on 2026-09-30: **REJECT for production narration quality**.

Observed result: the sample was intelligible and proved the end-to-end local workflow, but sounded strongly robotic and lacked expressive/emotional delivery. Therefore:

- Windows SAPI remains an infrastructure/test provider only;
- it must not be treated as a production audiobook narrator;
- successful SAPI execution proves plumbing, state, conversion and delivery mechanics only;
- production audio approval now requires a higher-quality provider sample, starting with the verified SaydiVoice path;
- any later all-local TTS candidate must be benchmarked separately for Vietnamese naturalness and expressive narration before V1 production acceptance.

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
SAYDI INTELLIGENCE LAYER
   |
   +--> deterministic Rule Engine
   +--> Local LLM (default)
   +--> ChatGPT / cloud LLM (optional fallback, owner-enabled)
   |
   v
Decision Engine + confidence/review routing
   |
   v
Narrative Interpretation + Prosody Director
   |
   v
Voice Casting + Representative Sample Set
   |
   v
TEXT PREVIEW APPROVAL -> AUDIO SAMPLE APPROVAL
   |
   v
Segment Job Orchestrator
   |
   v
Voice Provider API
   |
   +--> Local TTS (required all-local V1 path)
   +--> SaydiVoice (verified optional provider)
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
16. **Local intelligence is default:** semantic analysis must be able to run through a local LLM adapter; cloud AI is optional, disabled by default and never an architectural dependency.
17. **Structured AI only:** LLM outputs that influence production must conform to versioned schemas and be validated before use; free-form prose is not an executable decision.
18. **Book context precedes segment context:** book-level genre/tone/profile analysis is created first; segment analysis then receives book/chapter context rather than reasoning from isolated sentences.
19. **Human approval controls expensive/long-running synthesis:** the operator must approve both text interpretation and representative audio samples before full-book synthesis.
20. **No mandatory paid provider:** V1 production acceptance requires a usable all-local path for analysis and TTS, while external providers remain optional adapters.
21. **Executable evidence before scale:** architecture work is not considered validated until a small vertical slice can be run and inspected end-to-end.

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

## Intelligence, classification, and decision authority

SAYDI must not depend on an LLM for tasks that deterministic code can solve reliably.

The authority stack is:

```text
DETERMINISTIC RULES
        |
        v
AI ANALYSIS INTERFACE
        |
        +--> Local LLM (default)
        +--> optional cloud LLM
        |
        v
SCHEMA VALIDATION
        |
        v
DECISION ENGINE
        |
        +--> AUTO
        +--> AUTO + LOG
        +--> REVIEW
        |
        v
HUMAN APPROVAL for book-wide narration choices
```

Examples that should remain deterministic where practical:

- repeated header/footer/page-number removal;
- exact chapter numbering patterns;
- numbers/units/date normalization with known rules;
- stable IDs/hashes;
- completed-job/idempotency checks.

Examples where semantic AI may help:

- genre/subgenre classification;
- overall tone and target narration style;
- ambiguous sentence-boundary repair;
- dialogue/context interpretation;
- annotation classification when layout/rules are insufficient;
- implied emotion, pace, energy and emphasis;
- representative sample selection.

### Book Intelligence

Before per-segment narration planning, SAYDI creates a structured `BOOK_PROFILE` from metadata, table of contents, chapter structure and representative passages.

Conceptual output:

```text
genre
subgenre
tone
audience
dialogue_density
technical_density
emotion_range
recommended_narration_profiles[]
confidence
evidence_refs[]
```

The system must not require the entire book to fit into one LLM prompt. It should use hierarchical context and summaries derived from canonical source spans.

### Segment Intelligence

Each segment analysis receives at least:

- active `BOOK_PROFILE`;
- chapter/section context;
- preceding/following context where available;
- current `spoken_text`;
- annotation/speaker metadata.

Conceptual structured output:

```text
segment_type
speaker_role
emotion
emotion_intensity
pace
energy
pause_before_ms
pause_after_ms
emphasis[]
confidence
review_required
```

### Cloud AI privacy boundary

ChatGPT or another cloud model may be used only when explicitly enabled by the operator.

Default production behavior is local. If cloud analysis is enabled, the UI must make the data boundary clear before manuscript text is transmitted.

## Voice casting and approval workflow

SAYDI separates **text correctness** from **voice suitability**.

The workflow is:

```text
BOOK_PROFILE
   |
   v
genre/style classification
   |
   v
candidate narration profiles
   |
   v
representative sample set (normally 3-5 passages)
   |
   v
TEXT PREVIEW GATE
   |
   v
generate real audio samples
   |
   v
AUDIO SAMPLE GATE
   |
   v
APPROVED NARRATION FINGERPRINT
   |
   v
FULL SYNTHESIS
```

Representative passages should cover the book's actual difficulty, not only the first paragraph. Depending on genre they may include:

- ordinary narrator prose;
- difficult names/terms/numbers;
- dialogue or emotional passage for fiction;
- explanatory/list/data passage for business/non-fiction;
- punctuation/annotation edge cases.

The narration fingerprint must include all production-relevant settings, including provider/model, voice, style, speed, expression/prosody policy, pause policy and pronunciation-lexicon version.

Any material fingerprint change invalidates the audio approval and requires a new sample review.

## Executable-first development strategy

The project will be implemented as **runnable vertical slices**, not as a long architecture-only build.

Before scaling to a full book, SAYDI must provide a small operator-visible runner that proves the real workflow.

The first executable slice may use a small synthetic/public-domain text-based PDF and a CLI instead of a desktop UI, but it must produce durable artifacts that the operator can inspect.

Minimum practical slice:

```text
small PDF
 -> extract text
 -> detect at least one chapter/block structure
 -> original/normalized/spoken text
 -> simple BOOK_PROFILE
 -> choose representative passage(s)
 -> produce text preview
 -> build narration fingerprint
 -> generate at least one real audio sample through an available VoiceProvider
 -> record approval/rejection
 -> persist run artifacts/logs
```

The first run is for workflow learning and contract validation, not a claim of production audiobook quality.

Every subsequent task must keep this runner working and expand it rather than building isolated modules that cannot be exercised end-to-end.

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

**Architecture generation:** SAYDI-AUDIOBOOK-V1.3  
**Current phase:** SAYDI-002 executable vertical slice implementation.  
**SaydiVoice discovery:** retained and considered the verified provider foundation.  
**Audiobook production implementation:** STARTED. The first core runner now has provider-neutral contracts, rules analysis, local Ollama adapter boundary, narration fingerprint, representative sample selection, text approval, local prototype voice provider, audio approval state and duplicate-operation guard.

## Authoritative task queue

- **SAYDI-001 — Audiobook architecture + single Source of Truth:** DONE.
- **SAYDI-002 — Executable vertical slice + provider/AI contracts:** NEXT.
- **SAYDI-003 — PDF-first book ingest + canonical manifest:** classify text/scanned PDF, extract/OCR, reconstruct reading order, remove repeated page furniture, detect chapters/blocks, preserve provenance and expose OCR exceptions.
- **SAYDI-004 — Text interpretation foundation:** implement `original_text -> normalized_text -> spoken_text`, punctuation/sentence reconstruction, number/date/unit/abbreviation speech normalization, annotation parser/policy, stable segmentation and confidence/review outputs.
- **SAYDI-005 — Professional narration director:** implement hierarchical book/chapter/scene/segment intelligence, contextual semantics, dialogue/speaker-role inference, semantic emotion + intensity, emotional-arc smoothing, prosody/pause/emphasis/pace delivery directives, pronunciation lexicon, narration fingerprint and representative sample approval.
- **SAYDI-006 — Segment synthesis orchestration + resume/idempotency.**
- **SAYDI-007 — Audio processing, chapter assembly and mastering.**
- **SAYDI-008 — Alignment/acoustic QA + isolated repair loop.**
- **SAYDI-009 — M4B/chapter-MP3 export + metadata.**
- **SAYDI-010 — Windows desktop control center.**
- **SAYDI-011 — Clean-machine installer + end-to-end production acceptance.**

Only one task should be treated as NEXT at a time.

## Immediate next task

**SAYDI-002 — Executable vertical slice + provider/AI contracts.**

It must create the first runnable operator-visible path, establish provider-neutral AI/Voice contracts, preserve the field-verified SaydiVoice behavior behind an adapter, and prove a real sample-generation/approval flow before broader implementation.

Required SAYDI-002 evidence:

- runnable CLI/operator runner; **IMPLEMENTED OFFLINE FOUNDATION**
- local offline compile/unit/smoke evidence; **PASS (5 unit tests + prepare/approve smoke in development environment)**
- Windows-local audible sample workflow; **FIELD-RUN PASS — GitHub Actions run 36745274726**
- versioned structured contracts for AI analysis and VoiceProvider;
- deterministic fallback behavior when no LLM is available;
- local-LLM adapter boundary (model may be selected/benchmarked during implementation);
- SaydiVoice production adapter or equivalent real provider path for the first audible sample;
- sample narration fingerprint;
- text-preview and audio-approval state;
- tests for idempotency/privacy/schema validation;
- one bounded real audible sample run after offline gates pass. **PASS — local Windows SAPI WAV produced on trusted runner in run 36745274726**

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

`SAYDI-002` remains the immediate NEXT task because the project must become runnable before the deeper modules are built. It must establish provider-neutral AI/Voice boundaries and a bounded audible sample workflow. Punctuation repair, annotation policy, book intelligence, emotion and prosody remain upstream audiobook-domain logic rather than hard-wired into SaydiVoice browser automation.


## Owner decision 2026-10-09 — SAYDI operations move into one MAGASIN Control Center (future cutover policy)

**Newer Owner directive, authoritative scope:** The Owner will retire all separately operated robot **control interfaces** and manage SAYDI, Supervisor and SAPO through one MAGASIN Control Center on `DESKTOP-H4A16IL` (currently `http://127.0.0.1:8781`). The **SAYDI narration/render/QC engine, source-of-truth, book metadata, audio, queues, checkpoints, profiles and private credentials remain their own separately recoverable backend**, not merged into the Supervisor repository or deleted. The unified UI must expose SAYDI status, book/chapter progress, render/QC/R2 exceptions, RAM budgets, audio playback/Owner listening review and genuine Owner-confirmed START/STOP, without requiring the Owner to launch `C:\SAYDI\control\media_control.py` in a second window. That legacy read-only HTTP source may remain an internal data adapter during migration, but cannot itself authorize a production START/STOP.

**Boot/Owner policy precedence:** This 2026-10-09 directive **supersedes the `default-on after Windows boot` and `worker starts automatically after reboot` parts** of the 2026-10-03 production directive **as the target post-cutover policy**. After the per-robot cutover has been independently verified, SAYDI MUST be **OFF after every Windows reboot** until the Owner explicitly starts SAYDI in the unified Control Center; STOP must prevent Windows Scheduler/watchdog/recovery from reviving SAYDI. While Owner ON, the previously approved routine VieNeu render/automatic QC, checkpoint restart, audio assembly, targeted safe repair and bounded 24/7 progress *remain automatic* without individual clicks. Offline after STOP still permits a lightweight read-only status observer and local UI.

**Transition is not complete:** The current Chapter 2 V5 `SAYDI V5 CH02 QC Guardian` Windows task and `RUN_CH02_V5_QC_SAFE.ps1` remain real legacy mechanisms; related V4 watchdog/resume tasks require inventory. A verified Media Control read-only status on 2026-10-09 showed Chapter 2 V5 checkpoint `PAUSED_RESOURCE` / `QC_NEEDS_FREE_RAM`, a minimum **2.3 GiB free RAM** for its safe QC resume, and no running heavy worker. The approved MP3 and 640 existing chunk checkpoints are valuable output: **do not reset, regenerate, double-QC, delete, corrupt or declare FINAL** by attempting a Control Center START before verifying the exact checkpoint/worker ownership and resource safety. **This SOT edit does not apply changes to Windows startup entries**; until a reviewed and tested cutover is actually installed, legacy start behavior still exists and does not count as compliance with new OFF-after-reboot policy.

**Required SAYDI migration gates:** 
1. Capture original installed script hashes, scheduled task action/trigger/state, active PID/mutex, RAM/D:, V5 Chapter 2 checkpoint, current SOT task, and an independently verified Owner Stop/Start / session identity witness.
2. Add a SAYDI-specific local adapter behind Control Center with a durable **Owner generation** / STOP latch and exact named-worker scope. Explicit Owner START accepts a safe queued/chapter job (not a hard-coded blind script); refuse if insufficient RAM, a mutex/another media worker is active, checkpoint is ambiguous or Owner approval/audio reference is missing. Do not fabricate RUNNING before heartbeat.
3. Explicit Owner STOP persists through reboot, prevents scheduled restart, and safely drains a running stage to its existing durable checkpoint. No force killing a VieNeu/FFmpeg/QC child without a separately approved safety policy and actual task evidence. Wrong Origin/CSRF/actor, repeat START/STOP, start with stale status, low RAM, and corrupt checkpoint must all be rejected or idempotent.
4. After project SOT approval, hosted tests and an isolated local dry-run pass, perform **one Owner-approved, hash-pinned backup/stage/apply**; preserve scheduled task definitions for rollback but disable only the conflicting legacy automatic execution triggers. Verify **OFF after reboot** and STOP/START of SAYDI independently of Supervisor/SAPO and Owner-selected 24/7 continuation while ON.
5. Only when the unified Control Center shows the complete live SAYDI operational view and a verified owner lifecycle may separate SAYDI Control **windows/shortcuts** be retired. Never retire its backend/status API, sources, queues or audio merely to achieve one-window UX.

**Authority and status:** The Supervisor project SOT at `magasincoffee/magasin-supervisor/SOURCE_OF_TRUTH.md` holds only the **shared Control Center control-plane/cutover** gates; this SAYDI SOT remains sole authority for SAYDI book/audio task readiness and acceptance. This decision is policy/implementation direction, **NOT proof that SAYDI START/STOP has already been installed**; `SAYDI-002` and downstream book production gates keep their existing statuses. The current Control Center's disabled SAYDI START/STOP buttons are intentional safety gates, not evidence of a functioning actuator. Do not change current service/task settings from this documentation merge alone.

## Owner production directive — default local audiobook QC (2026-10-03)

This directive is authoritative for the active local audiobook production path.

### Default local runtime

The default production narrator path is now:

- local machine: `DESKTOP-H4A16IL`;
- engine: VieNeu v3 Turbo / ONNX;
- approved voice: `SAYDI Nam Mien Nam`;
- durable queue/checkpoints: Supabase-backed TTS book/chapter/chunk state;
- Windows boot recovery: SAYDI worker starts automatically and resumes queued/in-progress work;
- output unit: one mastered MP3 per chapter, with chunk WAVs treated as intermediate artifacts.

The local worker path is **default-on**. The Owner does not need to request VieNeu startup, queue polling, checkpoint resume, chapter assembly, or ordinary QC for every book.

### Invisible QC is mandatory and default-on

Production audio must carry technical traceability that is inaudible to the listener. Do not insert audible beeps, spoken IDs, tones, or other markers into the audiobook.

Every chapter/segment/chunk must remain traceable through stable metadata sufficient to identify:

- book;
- chapter;
- chunk/segment;
- source text span;
- generated artifact;
- chapter timecode after assembly;
- QA status and findings.

After each chapter is assembled, the default local pipeline must automatically run a QC pass before the chapter is considered final.

Minimum QC classes:

1. **Structural/coverage QC** — missing, duplicate, out-of-order or unexpectedly short/long segments.
2. **Acoustic QC** — decode failure, near-zero audio, clipping/peak anomaly, excessive silence, discontinuity at joins, and inconsistent format/loudness.
3. **Text/audio verification** — ASR/forced-alignment comparison when the local verification module is available, with mismatch confidence and exact segment/timecode routing.

QC findings are recorded as metadata only and must not alter listener audio.

### Owner experience rule

The Owner's normal role is to listen for enjoyment/acceptance, not to manually hunt errors.

The system must:

- automatically mark suspicious locations;
- report exact chapter + segment/chunk + timecode;
- regenerate only the affected segment when a repair is safe and approved;
- rebuild only dependent chapter artifacts;
- preserve unaffected accepted audio.

Routine local QC runs automatically. Owner approval is required only when:

- source text interpretation is ambiguous;
- repair would change spoken content/meaning;
- a voice/narration fingerprint changes materially;
- confidence is below the configured automatic-repair threshold.

### Current implementation boundary

Already field-validated on `DESKTOP-H4A16IL`:

- VieNeu v3 Turbo local synthesis;
- `SAYDI Nam Mien Nam` voice;
- automatic queue polling;
- per-chunk checkpoint/resume;
- restart-safe Windows boot recovery;
- FFmpeg chapter assembly;
- book/chapter/chunk progress state;
- invisible QC metadata/event storage.

The full local ASR/forced-alignment verification pass is now part of the **mandatory default architecture** but is not yet field-validated on the active worker. It must be implemented and accepted before claiming fully autonomous semantic audio QA.


## Owner listening verdict — narration preprocessing is mandatory (2026-10-04)

The first full local VieNeu render is now classified as a **DRAFT BASELINE**, not a final audiobook.

Owner listening feedback from Chapter 1 established that technically correct TTS is insufficient. Production acceptance now requires a mandatory **Narration Preprocess** stage before synthesis.

Default pre-TTS behavior must:

1. analyze the complete source book before chunk generation;
2. remove non-spoken PDF artifacts such as page numbers, repeated headers/footers, extraction debris and meaningless layout residue;
3. reconstruct sentences and paragraphs from PDF line wrapping;
4. detect chapters, section headings, subheadings, lists, quotations, dialogue and transitions;
5. preserve source meaning while producing a derived `spoken_text`;
6. assign provider-neutral narration metadata per semantic block;
7. create explicit title/heading delivery with stronger prominence and longer pauses before/after;
8. use paragraph/semantic boundaries for segmentation rather than character-count boundaries alone;
9. preserve low-confidence edits as REVIEW rather than silently guessing.

### Heading delivery policy

Headings are semantic audio landmarks.

Minimum default behavior:

- chapter title is rendered as its own segment;
- section/subsection headings are rendered as separate segments;
- heading pace is slightly slower than body narration where supported;
- heading energy/emphasis is elevated where supported;
- insert a deliberate pause before and after headings;
- do not merge the first body sentence into the heading chunk;
- unsupported emotional/prosody controls must be approximated only through verified provider behavior such as segmentation, punctuation and pause policy; never fabricate provider controls.

### Narration-state classification

Every semantic block should carry a provider-neutral role such as:

```text
CHAPTER_TITLE
SECTION_HEADING
NARRATOR_BODY
DIALOGUE
QUOTE
LIST_ITEM
REFLECTIVE
EXPLANATORY
EMPHATIC
TRANSITION
ANNOTATION
```

and a narration plan such as:

```text
pace
energy
pause_before_ms
pause_after_ms
emphasis
emotion
confidence
review_required
```

### Current-book disposition

The current "Doanh Nghiệp Tự Hành" render remains useful for infrastructure/QC evidence, but must not be labeled FINAL. A production rerender should be based on the new narration-preprocessed manifest, beginning with a Chapter 1 approval sample before replacing the whole book.

## Owner architecture lock — hierarchical semantic narration (2026-10-04)

The Owner has approved the target architecture for determining tone, meaning, emotion and delivery from a supplied book.

This is now a product invariant:

```text
BOOK
 -> BOOK INTELLIGENCE
 -> CHAPTER INTELLIGENCE
 -> SCENE INTELLIGENCE
 -> SEGMENT INTELLIGENCE
 -> EMOTIONAL ARC
 -> DELIVERY DIRECTIVE
 -> TTS
 -> PRONUNCIATION QC
 -> PROSODY/STYLE QC
 -> ACOUSTIC/JOIN QC
 -> PASS / bounded isolated repair / REVIEW
```

Mandatory interpretation behavior:

- analyze the complete canonical book hierarchically rather than treating one excerpt as sufficient book context;
- infer scene semantics and emotional state with context, not keyword matching;
- support emotion intensity and confidence, not only a single binary emotion label;
- distinguish narrator prose, dialogue and speaker/character role where reliably inferable;
- preserve narrator/character continuity across scenes;
- smooth emotional transitions across neighboring segments so delivery does not jump unnaturally;
- translate semantic intent into provider-neutral pace/energy/pause/emphasis/pronunciation directives;
- map only to controls actually supported by the active TTS provider;
- keep canonical source meaning immutable;
- route low-confidence semantic decisions to REVIEW;
- run pronunciation/prosody/acoustic QC after synthesis and repair only affected units with a bounded retry policy.

The durable implementation checklist is:

`00_PROJECT/NARRATION_INTELLIGENCE_CAPABILITY_MATRIX.md`

That matrix may grow whenever the Owner discovers a missing or improvable capability. It records implementation coverage only; authoritative task ordering remains in this Source of Truth.

The Owner's intended end-state is minimal-input operation: supply the legally usable book and optional narrator/style preference; SAYDI handles routine semantic narration planning, generation, QC and safe repair. Owner intervention should normally be limited to initial narration approval and genuine semantic/quality exceptions.

## Owner directive — SAYDI V6 narration quality production upgrade (2026-10-08)

**Decision:** Owner approves **V6 capability upgrade planning**, building on the existing local VieNeu V5 rather than rebuilding the robot. The complete normative implementation and acceptance specification is:

`00_PROJECT/SAYDI_V6_NARRATION_QUALITY_EXECUTION_PLAN.md`

This directive is **requirements approval, not implementation completion**. Do not claim V6 shipped, Chapter 1 FINAL, or full-book production passed without runnable code, QC results, field evidence and Owner listening acceptance.

### Newly locked requirements

1. Preserve the Owner's ~4-minute approved narration reference as the canonical *local* narrator/style anchor. The subjective ~90% Owner assessment is directional listening feedback, **not an automated PASS rate**; the remaining unclear words, Vietnamese tone errors, slurring and joins remain real acceptance concerns.
2. The standard flow is **editorial before render, verification after render, bounded isolated repair**. ChatGPT can supply schema-validated narration directives/biên soạn when Owner enables the cloud boundary; default local Director/robot handles all routine tasks. No manuscript upload or audio/reference file committed to GitHub.
3. Text correctness, source-vs-spoken equivalence, Vietnamese tone and word clarity, emotional/phrase continuity, acoustic joins and narrator-fingerprint consistency are distinct QC dimensions. Whisper alone cannot settle accent/diacritic listening defects. “Mỗi khi hè về” vs “mỗi khi he về” must be diagnosed using original/TTS text and audio evidence before changing text.
4. **Never use `atempo`, time stretching or pitch shifting to simulate human pacing.** Native VieNeu articulation is preserved; semantic punctuation, source-faithful phrasing, reference selection and natural inter-phrase pauses are the allowed initial levers. Changing approved voice/fingerprint requires a new sample acceptance gate.
5. Correct only affected segments with safe retry limit, SHA-matched candidate QC and unchanged-neighbor evidence; no endless renders, no automatic whole-book regeneration, no false `FINAL`.
6. DESKTOP-H4A16IL has approximately 8 GB RAM / 4 logical CPU threads. The active host requires resource preflight, child-process limits, no simultaneous heavy VieNeu+Whisper models, RAM safeguards, checkpoint/resume and watchdog phase accuracy. CPU 100% alone is not proof of hardware damage; thermal limits require real sensor evidence.
7. The Owner receives a **complete chapter MP3** and a small set of representative samples/timecoded true exceptions for listening—not an instruction to hunt defects individually.

### Integration into existing authoritative sequence

- `SAYDI-004`: structured source-safe editorial/text layering and segment context.
- `SAYDI-005`: Narration Director, approved sample fingerprint and pre-render direction.
- `SAYDI-006`: stable segment-addressed TTS, resource guard, idempotency/restart.
- `SAYDI-007`: native-speed assembly and acoustic joins.
- `SAYDI-008`: layered pronunciation/tone/prosody/acoustic QC plus bounded repair.
- `SAYDI-009/010`: chapter listening package / operator progress and exceptions.

Continue using the existing `SAYDI-ND` and `SAYDI-QC` subtracks; do not create an alternative top-level task queue. **`SAYDI-002` remains the current authoritative NEXT task** until its documented closure gates pass. Work items in the V6 plan are subordinate acceptance work packages only; robots may not skip SOT prerequisites or fabricate DONE.

### Latest local observation (not repo field acceptance)

On 2026-10-08, Chapter 1 V5 was rendered in 347 WAV segments. Initial QC flagged 120 basic REVIEW; a locally generated V5 R2 candidate package reduced basic ASR REVIEW to 115 after selecting 12 improved variants out of 35 targeted attempts. This does **not** establish audible Owner approval; Chapter 1 remains `REVIEW`, and V6 remains unimplemented. Intermediate WAVs, manuscript and listening files stay on the local host.


## Scoped Owner QC pilot — Chapter 2 V5 QC-01 / QC-02 (2026-10-10, proposal only)

**Authority / priority:** This is a read-only and opt-in *quality experiment* on the already produced Chapter 2 REVIEW MP3. It does **not** change the main authoritative NEXT task (**SAYDI-002**), the 2026-10-09 unified Control Center migration and Owner STOP/START policy, the deployed VieNeu engine, voice reference, task protocols, Windows scheduler, checkpoint source, local data models or active Chapter 3 production.

Owner QC priorities: first validate natural contextual pauses (QC-01), then suspected join click/pop events (QC-02) before attempting emotional direction, pronunciation rerender or a fix-verification loop (QC-03–05). Keep existing normal behavior default; no broad fades, atempo, silent text rewriting, or automatic FINAL.

**Baseline evidence** on the host:
- Chapter 2 original REVIEW MP3 duration 3991.700s, SHA-256 `ed17de91ad34570ca2f79695c139fb79f5f0ac33af7faf7604e50095c8a6b831`, 640 source segments, 439 baseline ASR PASS and 201 baseline REVIEW (not accepted as real human listening).
- Existing `pause_after()` already distinguishes comma/sentence/question/paragraph/heading, and `clean_clip()` already uses 12ms edge fades. Direct join reconstruction shows 489 of 640 inserted gaps are 610ms; other gaps are 180/215/670/700/900/1020ms. Don't assume all audible 0.7–0.8s pauses are abnormal.
- Measurements at suspected 00:16:33 / 00:23:34 / 00:36:19 / 00:56:29 / 01:01:12 were gathered from unchanged audio, but do not coincide exactly with reconstructed join points. These are still listening **REVIEW**, not confirmed faults.

**Isolated implementation:** Branch `feat/saydi-v5-ch02-qc01-qc02-audit` provides a *read-only baseline analyzer*, and an opt-in FFmpeg A/B sample generator that varies silence by at most ±80ms on a candidate full-stop boundary, preserving actual spoken WAVs, native voice speed and existing loudnorm. It also produces five unchanged 8s listen excerpts. Original MP3 hash was reverified unchanged; two sample pairs differed by exactly +80ms in total duration. Three scoped offline unit tests passed. No TTS or ASR model was loaded for these tests; current Chapter 3 renderer was not interrupted.

**Owner gate:** Before any production change to `pause_after`, `clean_clip`, `assemble` or QC acceptance, Owner must hear paired clips and adjudicate the five suspected join sounds. Only confirmed issues may receive *segment-level* targeted repair, protected by technical comparison, text-fidelity verification, reversibility, bounded attempts and post-fix listening. QC-03/04/05 remain pending. Full end-to-end regression and Owner FINAL have not passed.

**Report and local-only preview paths:** `tools/saydi_tts/qc/V5_CH02_QC01_QC02_EVIDENCE_20261010.md` and `D:\SAYDI\QC_STAGING\CH02_V5_QC01_QC02_20261010\listening_previews`. Private manuscript, MP3 and WAV remain on the trusted local host; never commit them.

