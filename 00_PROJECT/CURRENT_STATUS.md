# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery. D1 Surface Map/V0.2 has passed its real Windows/SaydiVoice field gate and is ready to merge. The next implementation phase is D2 — Voice/Settings Catalog.**

## Completed

- Repository/project architecture and durable continuation records established.
- SaydiVoice Discovery Runner V0.1 merged through PR #1.
- First real Windows V0.1 run succeeded: `20260917_011521_dcb358a9`, `TTS_READY`, `CAPTURED`, exit code `0`.
- V0.1 artifacts reviewed and real anonymous-ready behavior documented.
- Field privacy defect `BUG-20260917-006` and locator semantic defect `BUG-20260917-007` found, fixed, and regression-tested.
- D1/V0.2 implemented on branch `feat/saydivoice-d1-surface-map`:
  - page readiness separated from authentication state;
  - contenteditable editor text suppressed;
  - semantic surface map generated as `saydi_map.json`;
  - ranked locator candidates generated as `selectors.json`;
  - Windows helpers and one-click packaging added.
- D1 branch Windows Actions passed; distribution self-test passed.
- Real V0.2 field run `20260917_110310_7bf1810a` reviewed:
  - runner `0.2.0`;
  - `TTS_READY` / `ANONYMOUS` / `CAPTURED`;
  - exit/error state clean;
  - 38 visible interactive elements captured;
  - script editor element index 18 persisted with `contenteditable: true` and no script text;
  - `saydi_map.json` and `selectors.json` generated successfully;
  - login controls and standalone History tab classified correctly;
  - MP3 selected; WAV/MP3/FLAC/OGG format tabs mapped;
  - language, voice selector, generate, settings/history, pause, editor utility controls, and assistant chat mapped.
- Visible stability/expression/speed controls are present on screen but do not expose stable interactive nodes in this D1 capture. D1 intentionally does not invent selectors for them; D2 will inspect these settings live.

## D1 acceptance result

**PASS.** No new blocking defect was found in the uploaded V0.2 report, DOM inventory, surface map, selectors, screenshot, or lifecycle log. The V0.1 privacy leak is verified fixed on the real provider page.

The current field state is anonymous, so authenticated session-reuse behavior is not a D1 blocker. Persistent browser-profile support remains implemented and will be exercised when a later phase requires account authentication.

## Next phase

D2 — Voice/Settings Catalog:

- non-destructively open the current voice selector and settings surfaces;
- catalog available voice/language choices that can be observed safely;
- capture real setting controls and current values/ranges for stability, expression, speed, pause behavior, and output format;
- improve locator evidence for sliders/custom controls without guessing;
- emit structured catalog outputs and tests;
- do not click Generate or download audio yet.

## Not yet implemented

- D2 complete voice/settings catalog.
- D3 generation lifecycle automation/observation.
- D4 audio download discovery.
- D5 controlled limits/error characterization.
- D6 frozen discovery contracts.
- Production Voice Engine.
- Media Analyzer, Scene Planner, Subtitle Engine, Render Engine, Desktop UI, full diagnostics/resume runtime, and installer.

## Repository visibility risk

GitHub metadata has reported the repository as public. Never commit passwords, cookies, browser profiles, auth tokens, private media, or raw local runtime/session artifacts.

## Current active objective

Merge D1/V0.2, create the D2 branch, implement/test D2 Voice/Settings Catalog, and stop only when a new real SaydiVoice interaction is required from the operator.
