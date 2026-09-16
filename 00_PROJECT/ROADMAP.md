# Roadmap

## Phase 0 — SaydiVoice Discovery

Goal: understand the real SaydiVoice Studio behavior before production automation is written.

Deliverables:

- persistent Playwright profile flow;
- login/session detection;
- TTS page state map;
- voice catalog discovery;
- settings/control discovery;
- robust locator candidates;
- generation-state detection;
- preview/download behavior;
- error/popup/session-expiry states;
- long-text behavior tests;
- screenshots, structured JSON output, logs, and discovery report.

Exit gate: a repeatable discovery run can produce evidence sufficient to implement the SaydiVoice production adapter without guessing selectors or settings.

## Phase 1 — Voice Engine

Build provider-neutral voice interface + SaydiVoice adapter. Add retries, download validation, chunking strategy, audio normalization, and integration tests.

## Phase 2 — Media Analyzer

Implement FFprobe metadata inspection, source inventory, orientation handling, basic scene detection, and validation.

## Phase 3 — Scene Planner

Implement deterministic template-based planning for short-form vertical videos. Create an explicit timeline/edit decision list.

## Phase 4 — Subtitle Engine

Implement sentence-level caption timing from known script + generated audio. Add optional word-level/local alignment later.

## Phase 5 — Video Composer + Render Engine

Implement 9:16 composition, trims, crop/scale, overlays, logo, captions, voice, background music, ducking, transitions, CTA, render, and artifact validation.

## Phase 6 — Desktop Control Center

Create the simple operator workflow: choose source media, enter content, choose template/voice, create video, preview, open output, resume, and diagnostics.

## Phase 7 — QA / Diagnostics / Resume

Harden state machine, checkpoints, automatic retries, diagnostic bundles, unit/integration/regression tests, and actionable error reporting.

## Phase 8 — Installer

Create one-time Windows setup and Desktop shortcut. Validate on a clean-machine scenario.

## Phase 9 — Smart Selection (optional after stable V1)

Add stronger source-clip scoring/selection and semantic visual understanding only after the deterministic pipeline is production-stable.
