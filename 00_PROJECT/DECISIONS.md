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

Status: Accepted

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

## ADR-011 — Production provider exposes retry metadata but never retries Generate implicitly

Status: Accepted

The production `SaydiVoiceProvider` owns request validation, authenticated preflight, verified control application, exactly one Generate attempt, terminal classification, and optional explicit Download. It may return `retryable=true` to an orchestration layer, but it never converts that metadata into a second Generate attempt by itself.

Download is also explicit through `download_requested`; merely constructing or validating a provider request cannot click Generate or Download.

Rationale:

- preserves ADR-010 at the production boundary;
- allows Business OS / Media Robot orchestration to make retry decisions without duplicating provider mechanics;
- prevents duplicate provider history/audio after ambiguous failures or reboot recovery;
- keeps unit/offline verification free of quota-consuming side effects.

