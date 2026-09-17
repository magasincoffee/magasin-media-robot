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
