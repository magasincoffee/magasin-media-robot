# SAYDI Audiobook Architecture

## 1. System context

SAYDI is a local-first audiobook production system. The core owns book structure, text fidelity, intelligence policy, job state, audio assembly and QA. LLM and TTS providers are replaceable adapters; cloud services are optional rather than required dependencies.

```text
                       +----------------------+
SOURCE BOOK ---------->|  Desktop Control UI  |
                       +----------+-----------+
                                  |
                                  v
                       +----------------------+
                       |   Project / Job API   |
                       +----------+-----------+
                                  |
          +-----------------------+-----------------------+
          |                       |                       |
          v                       v                       v
 +----------------+      +------------------+    +------------------+
 | Book/Text Core |      | Narration Engine |    | State / Events   |
 +-------+--------+      +---------+--------+    +---------+--------+
         |                         |                       |
         +------------+------------+-----------------------+
                      |
                      v
             +-------------------+
             | Segment Orchestr. |
             +---------+---------+
                       |
                       v
             +-------------------+
             | Intelligence Layer|
             +---------+---------+
                       |
          rules + local LLM + optional cloud
                       |
                       v
             +-------------------+
             | Voice Provider API|
             +---------+---------+
                       |
          +------------+-------------+
          |                          |
          v                          v
      Local TTS                SaydiVoice Adapter
      required V1              verified optional
                               Chrome/Playwright
             |
             v
        raw segment audio
             |
             v
       +-----------------+
       | Audio Engine    |
       | FFmpeg/FFprobe  |
       +--------+--------+
                |
                v
       +-----------------+
       | QA / Alignment  |
       +--------+--------+
                |
       repair --+-- pass
                |
                v
       +-----------------+
       | Export Engine   |
       +-----------------+
        M4B / chapter MP3
```

## 2. Domain model

### Book

A logical production project with immutable source identity and user-editable production metadata.

### Chapter

Ordered structural unit. A chapter has a stable `chapter_id`, title, ordinal and ordered blocks.

### Block

Paragraph, heading, list item, quote, dialogue block or other semantically meaningful source unit.

### Segment

Smallest independently synthesizable and regeneratable spoken unit.

Required segment properties include:

- stable `segment_id`;
- `chapter_id`;
- source span / source hash;
- normalized spoken text;
- narration directives;
- pronunciation overrides;
- generation status;
- audio artifact reference;
- QA status.

### Narration profile

Provider-neutral semantic delivery configuration such as narrator voice, speed, expressiveness, pause policy and pronunciation lexicon. Provider adapters map this profile to provider-specific controls.

### Export profile

Container/codec/metadata/loudness configuration for a target delivery format. Platform-specific values must be configuration, not hard-coded domain assumptions.

## 3. Major modules

### 01_DISCOVERY/saydivoice

Existing field-discovery and provider-evidence tooling. It remains isolated from production domain logic.

### 02_BOOK_INGEST

Responsibilities:

- detect supported source type;
- copy source into immutable local project storage;
- extract structural text;
- create the first canonical manifest;
- preserve provenance and source hashes;
- reject unsupported/encrypted/unreadable inputs with actionable errors.

Adapters:

- TXT;
- DOCX;
- EPUB;
- text PDF;
- optional OCR adapter later.

### 03_TEXT_ENGINE

Responsibilities:

- deterministic Unicode/whitespace cleanup;
- Vietnamese punctuation normalization;
- spoken rendering of numbers, dates, units and abbreviations;
- preserve original text separately from normalized spoken text;
- stable segmentation;
- change detection by hash;
- user-approved pronunciation substitutions.

Rule: normalization may change how text is spoken but must not silently change meaning.

### 04_NARRATION_ENGINE

Responsibilities:

- narrator selection;
- application-level style preset;
- pause policy;
- pronunciation lexicon;
- optional dialogue/speaker metadata;
- sample plan generation;
- chapter/segment narration plan.

The narration engine outputs provider-neutral directives only.

### 05_VOICE_ENGINE

Production interface:

```text
VoiceRequest
  segment_id
  text
  narrator_key
  style_key
  pronunciation_overrides
  output_format
  operation_id

VoiceResult
  status
  provider
  provider_voice
  local_audio_path
  duration
  byte_count
  sha256
  provider_reference
  error_class
  retryable
```

Initial adapter: SaydiVoice through installed Chrome + Playwright + persistent local authenticated profile.

The adapter must enforce one side-effect attempt per `operation_id` unless orchestration explicitly starts a new safe attempt.

### 06_AUDIO_ENGINE

Responsibilities:

- decode/validate generated audio;
- trim only policy-approved leading/trailing silence;
- normalize technical format;
- optional de-click/de-noise only when measurable and non-destructive;
- chapter concatenation;
- inter-segment and inter-chapter pause insertion;
- loudness/mastering according to export profile;
- FFmpeg/FFprobe validation.

Source generation audio remains immutable; processed derivatives are separate artifacts.

### 07_ALIGNMENT_QA

Two independent classes of QA:

**Structural/text coverage QA**

- all canonical segments have exactly one accepted audio artifact;
- no missing/duplicate/out-of-order segments;
- ASR/forced-alignment comparison where available;
- mismatch severity and confidence recorded;
- suspicious segments routed to review/repair.

**Acoustic QA**

- decode succeeds;
- duration plausible;
- clipping/peak checks;
- unexpected long silence;
- zero/near-zero audio;
- channel/sample format consistency;
- chapter-boundary continuity.

QA never silently rewrites source text to make a mismatch disappear.

### 08_EXPORT_ENGINE

Responsibilities:

- M4B assembly;
- chapter-MP3 package;
- chapter markers;
- title/author/narrator metadata;
- optional cover embedding;
- deterministic filenames;
- export manifest;
- final validation.

### 09_ORCHESTRATOR

Owns the durable state machine.

Responsibilities:

- task graph;
- checkpoints;
- dependency ordering;
- safe retry classification;
- cancellation;
- resume;
- progress;
- concurrency limits;
- idempotency;
- event log.

SQLite is the initial state-store target. Filesystem artifacts are referenced by stable IDs/hashes rather than used as the only state database.

### 10_DESKTOP_APP

Business-level actions only:

- Import book
- Review chapters
- Configure narrator/style
- Edit pronunciation dictionary
- Generate sample
- Approve sample
- Create audiobook
- Pause/resume
- Review issues
- Repair selected segments
- Export
- Open diagnostics

### 11_QA

Unit, integration, provider-contract, long-run, resume, corruption, export and privacy tests.

### 12_INSTALLER

Installs/supports runtime dependencies, local folders, application shortcut and prerequisite checks without packaging credentials or browser sessions.

## 4. Stable artifact contracts

Each stage writes versioned artifacts.

```text
book_source
 -> book_manifest.v1.json
 -> narration_plan.v1.json
 -> segment_jobs in SQLite
 -> segment VoiceResult + raw audio
 -> processed_segment metadata
 -> chapter_manifest.v1.json
 -> qa_report.v1.json
 -> export_manifest.v1.json
```

Schemas are versioned. A schema version change requires migration or explicit regeneration.

## 5. Segment identity

Segment identity must be stable across interrupted runs.

Recommended identity inputs:

```text
book_id
chapter stable key
block ordinal
segment ordinal within block
normalized-text hash
normalization schema version
```

Do not use random IDs as the only identity for source-derived segments.

If source text changes, affected segments receive new content hashes and only dependent artifacts are invalidated.

## 6. State and idempotency

Every side-effecting operation has an `operation_id`.

Before live TTS generation:

1. verify job dependency state;
2. verify no accepted audio already exists for the same content hash + narration fingerprint;
3. reserve the operation;
4. perform exactly one provider generation attempt;
5. persist terminal evidence before scheduling another attempt.

A process crash after provider success but before local commit must enter reconciliation, not blindly regenerate.

## 7. Retry model

Failures are classified as:

- `fix_input`
- `re_auth`
- `retry_safe`
- `reconcile_first`
- `do_not_retry`

Network/browser retries must not imply a second Generate click unless provider outcome is known safe.

## 8. Sample approval gate

Full-book synthesis is blocked until an approved sample exists for the active narration fingerprint.

A narration fingerprint includes at least:

- provider;
- voice;
- style preset;
- speed;
- expression/stability controls;
- pause policy;
- pronunciation-lexicon version.

Changing the fingerprint invalidates prior approval.

## 9. Runtime directory model

```text
%LOCALAPPDATA%/SAYDI/Audiobook/
  config/
  browser_profile/
  library/<book_id>/
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

Git contains code, schemas, tests and sanitized documentation only.

## 10. Security and privacy

Never commit or upload by default:

- source manuscripts;
- generated private audio;
- cookies/session storage;
- browser profiles;
- passwords/tokens;
- local database;
- diagnostic bundles containing book text.

Sanitized CI evidence may include structural metadata and synthetic fixtures but not private production text/audio.

## 11. Observability

Every job emits structured events including:

- timestamp;
- book/job/segment IDs;
- stage;
- attempt number;
- operation ID;
- status transition;
- sanitized error class;
- artifact hash where applicable;
- duration metrics.

Logs must support reconstruction of what happened without exposing private manuscript contents.

## 12. Professional acceptance scenario

The reference acceptance test is a multi-chapter book large enough to exercise long-running generation.

The test must demonstrate:

- deterministic ingest;
- stable segmentation;
- sample approval;
- interruption during synthesis;
- resume without duplicating completed segments;
- one intentionally failed segment repaired in isolation;
- successful chapter assembly;
- QA report;
- valid M4B/chapter-MP3 export;
- no secrets/private runtime artifacts in Git.


## 13. Intelligence provider architecture

Semantic reasoning is exposed through a provider-neutral `AnalysisProvider` contract. Local LLM execution is the default target. ChatGPT/cloud models are optional fallback adapters and are disabled unless the operator enables them.

No LLM response is executable until it passes schema validation and policy checks.

Book analysis and segment analysis are separate operations so long books can use hierarchical context rather than one giant prompt.

## 14. Executable vertical slice

Development must preserve an end-to-end runnable path from an early stage.

The initial slice is intentionally narrow:

```text
small text PDF
 -> canonical excerpt/chapter
 -> three text layers
 -> simple structured book analysis
 -> narration profile
 -> representative passage
 -> text preview
 -> real audio sample
 -> approval state
```

A CLI is acceptable for this slice. The purpose is to expose real data flow, failure modes and operator decisions before GUI/full-book scaling.

## 15. Cost/availability architecture

Production V1 must not require a paid API.

Required architectural paths:

- local deterministic rules;
- local LLM adapter;
- local TTS adapter;
- local FFmpeg/FFprobe;
- local SQLite/state.

External services such as SaydiVoice or ChatGPT may improve convenience or quality but remain optional adapters.


## 16. Default local production loop and invisible QC

The active local production path is default-on and unattended-capable.

```text
Windows boot
  -> SAYDI Local Worker
  -> durable queue/checkpoint state
  -> VieNeu v3 Turbo / ONNX
  -> approved voice: SAYDI Nam Mien Nam
  -> chunk/segment WAV artifacts
  -> chapter assembly + loudness normalization
  -> invisible QC pass
       -> structural/coverage checks
       -> acoustic checks
       -> join continuity checks
       -> local ASR/alignment verification when available
  -> PASS or REVIEW
  -> repair only affected segment(s)
  -> rebuild dependent chapter
  -> chapter MP3
```

### Default behavior

The operator does not need to request the following for each book:

- worker startup;
- queue polling;
- restart recovery;
- checkpoint resume;
- per-chapter assembly;
- ordinary QA/QC execution;
- QA metadata recording.

These are normal local runtime behavior.

### Invisible traceability

No audible QC marker is allowed in listener audio. Traceability lives in metadata/event records.

Each produced unit must be addressable by:

```text
book_id
chapter_number / chapter_id
segment_or_chunk_id
source span/hash
artifact reference/hash
assembled chapter timecode
QA state
QA findings
```

This allows a later review command to identify and repair an exact bad region without requiring the Owner to manually search the audiobook.

### Repair scope

Repair must be minimal:

```text
finding
 -> exact segment/chunk
 -> regenerate/reprocess affected unit only
 -> rerun unit QC
 -> rebuild chapter only
 -> preserve unaffected accepted audio
```

### Active deployment note

The currently field-validated local production host is `DESKTOP-H4A16IL` with VieNeu v3 Turbo / ONNX and the approved `SAYDI Nam Mien Nam` voice. Boot recovery and chapter synthesis have been validated. Full local ASR/forced-alignment QC remains a required default module but is not yet field-accepted on that worker.


## 17. Narration Preprocess pipeline

A book must not flow directly from PDF extraction into TTS chunks.

Required production path:

```text
SOURCE PDF
 -> extraction/OCR
 -> layout cleanup
 -> structure reconstruction
 -> semantic block classification
 -> original_text
 -> normalized_text
 -> spoken_text
 -> narration plan
 -> heading/title pause plan
 -> sentence/paragraph-aware segmentation
 -> preview/sample approval
 -> TTS
 -> chapter assembly
 -> QC/ASR
```

### Layout cleanup

Remove or classify before speech:

- standalone/repeated page numbers;
- repeated headers and footers;
- broken line-wrap artifacts;
- duplicated whitespace;
- extraction control characters;
- decorative text that has no spoken meaning;
- indexes/navigation residue that the active book policy marks non-spoken.

Never delete meaningful footnotes, citations, annotations or sidebars merely because they are inconvenient. They require an explicit read/skip/defer/review policy.

### Semantic narration blocks

The canonical narration manifest separates headings from body prose. A heading is never treated as just another sentence in a long TTS chunk.

Recommended default timing:

- chapter title: pause before 800–1200 ms, pause after 1200–1800 ms;
- section heading: pause before 500–900 ms, pause after 800–1400 ms;
- paragraph transition: 250–500 ms;
- ordinary sentence boundary: provider/default natural pause.

These are provider-neutral targets. Adapters map them to verified capabilities.

### Expressiveness

Narration emotion and emphasis are semantic metadata. If VieNeu does not expose a reliable direct emotion control, the adapter may only use validated techniques such as:

- independent segment rendering;
- punctuation;
- pause boundaries;
- pace/profile selection supported by the engine;
- approved voice/reference settings.

Do not claim unsupported per-sentence emotion control.
