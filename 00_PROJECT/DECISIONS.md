# Architecture Decisions

## ADR-001 — FFmpeg is the primary render engine

Status: Accepted

Video editing/rendering automation will be implemented with FFmpeg/FFprobe rather than depending on CapCut, Premiere, or another GUI editor. This makes the pipeline scriptable, testable, deterministic, and independent of GUI layout changes.

## ADR-002 — SaydiVoice is a browser integration

Status: Accepted

Initial TTS will use SaydiVoice Studio at `https://voice.saydi.ai/vi/studio/tts/` through Playwright. It is treated as an external web dependency behind a provider adapter.

## ADR-003 — Discovery precedes production SaydiVoice automation

Status: Accepted

The project will first build a repeatable SaydiVoice Discovery Runner to map actual controls, settings, session behavior, generation/download states, and errors. Production selectors will not be guessed.

## ADR-004 — Persistent browser profiles stay local

Status: Accepted

Authentication/session data stays in the user's local runtime directory and is never stored in the repository.

## ADR-005 — Deterministic V1 before semantic AI editing

Status: Accepted

The first production edit pipeline will be template/rule-based. AI visual semantic scene selection is postponed until the deterministic pipeline is stable.

## ADR-006 — Repository files are durable project memory

Status: Superseded by ADR-011

`CURRENT_STATUS.md`, `NEXT_STEP.md`, `CHANGELOG.md`, `BUG_LOG.md`, `TEST_LOG.md`, and this decision record are the canonical handoff mechanism across chat/context boundaries.

## ADR-007 — Daily user interaction is Desktop-first

Status: Accepted

Technical dependencies may run underneath, but normal operation should be exposed through a simple Windows Control Center.

## ADR-008 — Live Saydi GitHub Actions use a trusted Windows self-hosted runner

Status: Accepted

Real-provider SaydiVoice checks that require authentication/session continuity run through GitHub Actions on the user's trusted Windows machine as a self-hosted runner. GitHub orchestrates the job, but the Playwright persistent browser profile remains in `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\browser_profile` on that machine.

Rationale:

- preserves ADR-004 and the no-secrets-in-Git rule;
- avoids uploading cookies, browser profile archives, OAuth state, or authentication artifacts;
- reuses the same machine/network/browser context after anonymous `/api/session/start` verification failures;
- removes the repeated operator ZIP download/upload loop while keeping live tests reproducible from GitHub Actions;
- allows live evidence artifacts to exclude the profile entirely.

The self-hosted runner should initially be started interactively under the same Windows account that owns the browser profile. Controlled Generate remains separately gated and is not implied by merely having an authenticated profile.

## ADR-009 — Voice mood/style is an application-level preset over verified provider controls

Status: Accepted

SaydiVoice field discovery exposed voice selection, a Biểu cảm ↔ Ổn định axis, speed, pause controls, and audio format. No separate discrete Happy/Sad/Angry mood selector was observed. MAGASIN therefore models delivery style as named application presets that deterministically compose only those verified controls.

Rationale:

- avoids inventing a provider capability that was not observed;
- gives downstream media jobs a stable semantic interface such as `tiktok_energetic` or `story_warm`;
- keeps provider-specific slider ratios and UI behavior behind the Saydi adapter;
- allows presets to be unit-tested and roundtrip-tested without consuming generation quota.

Preset values are implementation policy and may be tuned later from listening tests without changing the provider contract.

## ADR-010 — Live Generate is a separately authorized one-shot side effect

Status: Accepted

Production/discovery automation must treat Generate as an explicit side effect. A normal preflight or control-setting workflow does not imply permission to Generate. When a live Generate is authorized, the default execution contract is exactly one click with no automatic retry.

Rationale:

- prevents accidental quota consumption;
- prevents duplicate history/audio results when terminal signals are ambiguous;
- separates retry policy from provider UI mechanics;
- makes operator authorization auditable in workflow design.

A later production adapter may expose retryability metadata, but a second Generate attempt still requires an explicit caller policy rather than an implicit browser retry.


## ADR-011 — One Source of Truth governs the active SAYDI track

Status: Accepted

`00_PROJECT/SOURCE_OF_TRUTH.md` is the single authority for product identity, architecture generation, current state and the one NEXT task.

Rationale:

- avoids conflicting state across historical README/status/roadmap files;
- makes continuation deterministic across sessions;
- preserves supporting documentation without giving every file equal authority.

Supporting files remain required evidence, but they do not override the Source of Truth.

## ADR-012 — Active product pivots from social video to professional audiobook production

Status: Accepted

The active product is **SAYDI Audiobook**. The earlier social-video direction is paused.

Existing SaydiVoice discovery is preserved and reused because it proves the provider behavior needed by the audiobook Voice Engine. Video-specific implementation is not continued unless the Source of Truth explicitly reactivates it.

## ADR-013 — Canonical book manifest separates source text from spoken text

Status: Accepted

Imported/extracted source text is preserved. Normalized spoken text is a derived representation.

Rationale:

- protects textual fidelity;
- makes pronunciation/normalization changes auditable;
- allows reprocessing without losing the original extracted content;
- supports deterministic invalidation and QA.

## ADR-014 — Segment is the smallest independently regeneratable unit

Status: Accepted

Long-form synthesis is segment-addressed. Each segment has stable source linkage, normalized-text hash, narration fingerprint, provider result and QA state.

Rationale:

- a failed sentence/paragraph can be repaired without regenerating hours of audio;
- interruption/resume is practical;
- provider cost/quota and duplicate side effects are controlled;
- book-wide coverage can be proven exactly.

## ADR-015 — TTS providers are replaceable adapters

Status: Accepted

Audiobook domain logic uses a provider-neutral VoiceRequest/VoiceResult contract. SaydiVoice-specific browser selectors and controls remain inside the SaydiVoice adapter.

The system may add other providers later without changing book, narration, audio or export domain contracts.

## ADR-016 — Durable orchestration uses explicit state, hashes and operation IDs

Status: Accepted

Long-running audiobook production uses a durable local state store, initially SQLite, plus immutable/intermediate artifacts.

A file existing on disk is not sufficient completion evidence. Side effects use operation IDs, accepted artifacts use hashes, and ambiguous provider outcomes enter reconciliation before retry.

## ADR-017 — Full-book generation requires sample approval for the active narration fingerprint

Status: Accepted

Before long-form generation, the operator approves a short sample tied to the exact narrator/style configuration.

Changing the narration fingerprint invalidates the prior approval.

Rationale:

- catches wrong voice/style early;
- prevents wasting long-running provider generation;
- gives a clear human quality boundary without requiring manual approval of every segment.

## ADR-018 — QA is a production gate, not an optional post-process

Status: Accepted

An audiobook cannot enter READY/EXPORTED with unresolved structural coverage failures, failed segment jobs, material text/audio mismatch, invalid chapter order, or technical audio validation failures.

QA results are bound to exact artifact hashes so a later artifact change invalidates the relevant acceptance.


## ADR-019 — Local AI is the default intelligence path

Status: Accepted

Semantic analysis uses a provider-neutral interface. Deterministic rules remain authoritative where practical; a local LLM is the default semantic-analysis target. ChatGPT/cloud LLMs are optional and disabled by default.

Rationale:

- keeps manuscript processing local;
- avoids mandatory token/API costs;
- prevents the audiobook domain from depending on a single AI vendor;
- supports offline operation.

## ADR-020 — No mandatory paid/cloud provider for V1

Status: Accepted

Production V1 must have an all-local execution path for analysis and TTS. SaydiVoice and cloud LLMs remain optional adapters.

Provider/model selection may evolve based on measured Vietnamese quality, licensing and target-machine capability, but the core contracts must remain stable.

## ADR-021 — Rule engine, AI analysis, and human approval have separate authority

Status: Accepted

Deterministic transformations use code/rules. LLMs handle semantic ambiguity through structured outputs. Book-wide voice/style decisions require operator approval.

LLM free-form prose is never treated as an executable production decision.

## ADR-022 — Book intelligence precedes segment intelligence

Status: Accepted

SAYDI first creates a structured book-level profile, then analyzes individual segments with book/chapter context.

This reduces isolated-sentence misclassification and avoids requiring the entire book in one model context window.

## ADR-023 — Text preview and audio sample are separate approval gates

Status: Accepted

The operator first approves what SAYDI intends to read, then approves how it sounds.

Full-book synthesis requires an approved narration fingerprint. A material change to voice/model/style/speed/prosody/pause/pronunciation invalidates audio approval.

## ADR-024 — Executable vertical slice before broad implementation

Status: Accepted

SAYDI must become runnable early. The first implementation milestone is a narrow CLI-driven path that reaches a real audible sample and persists approval state.

Later modules extend this runner. They must not be developed only as disconnected components with no end-to-end execution evidence.
