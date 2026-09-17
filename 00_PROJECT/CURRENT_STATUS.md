# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery. D1 Surface Map/V0.2 is field-accepted and merged through PR #2. D2 Voice/Settings Catalog V0.3 is implemented, locally self-tested, Windows CI verified, packaged for Windows, and now waits for one real SaydiVoice field run.**

## Completed

- Repository/project architecture and durable continuation records established.
- V0.1 Discovery Runner merged through PR #1.
- First real V0.1 Windows run succeeded: `20260917_011521_dcb358a9`, `TTS_READY`, `CAPTURED`, exit `0`.
- Field privacy defect `BUG-20260917-006` and locator semantic defect `BUG-20260917-007` were found and fixed.
- D1/V0.2 real Windows run `20260917_110310_7bf1810a` passed:
  - runner `0.2.0`;
  - `TTS_READY` / `ANONYMOUS` / `CAPTURED`;
  - 38 interactive elements;
  - contenteditable editor text absent from structured evidence;
  - `saydi_map.json` and `selectors.json` generated;
  - login and History semantics separated correctly.
- D1 PR #2 merged to `main` as `51869ab54dac1e5f0202455cf1f9b40f48dde0b0`.
- D2 branch created: `feat/saydivoice-d2-catalog`.
- D2/V0.3 implementation added:
  - `voice_catalog.json` output;
  - `settings_catalog.json` output;
  - safe trigger whitelist for voice (`Tự động`), language (`VI`), pause (`Đang tắt`), and reserved Settings observation;
  - non-destructive menu-open capture with Escape cleanup;
  - visible settings-context probing for stability, expression, speed, pause, and output format;
  - capture of accessible role/name/value/range evidence and bounded structural hints;
  - editor/input privacy suppression retained;
  - Generate/download/delete/login/clone actions remain outside the trigger whitelist.
- D2 package version: `0.3.0`.
- Local V0.3 distribution verification:
  - compile: PASS;
  - pytest: **37 tests PASS**;
  - version import: PASS (`0.3.0`).
- Windows GitHub Actions latest D2 run `35185941236`: PASS.
- Operator ZIP built: `MAGASIN_SAYDIVOICE_DISCOVERY_V0.3.zip`.

## Current live gate

Run the packaged V0.3 build on the target Windows laptop. The runner itself will open the allowed Voice / Language / Pause selector surfaces, capture evidence, and close them. The operator should **not click `Tạo giọng nói` or download audio**.

Return the newest eight artifacts from the same run ID:

- `reports\discovery_report_*.json`
- `runs\<run-id>\dom_inventory.json`
- `runs\<run-id>\saydi_map.json`
- `runs\<run-id>\selectors.json`
- `runs\<run-id>\voice_catalog.json`
- `runs\<run-id>\settings_catalog.json`
- `screenshots\saydivoice_<run-id>.png`
- `logs\discovery_<run-id>.jsonl`

## D2 acceptance target

D2 may be merged only when the real provider pass confirms:

- `TTS_READY` / `CAPTURED` without a new blocking error;
- voice selector options are captured or a provider-specific reason is clearly documented;
- language and pause surfaces are captured or explicitly reported unavailable;
- stability/expression/speed controls expose enough evidence to define real contracts, or unresolved provider behavior is explicitly documented without guessed selectors;
- script/editor content remains absent from structured outputs;
- no Generate/download action was invoked.

## Not yet implemented

- D3 generation lifecycle automation/observation.
- D4 audio download discovery.
- D5 controlled limits/error characterization.
- D6 frozen discovery contracts.
- Production Voice Engine.
- Media Analyzer, Scene Planner, Subtitle Engine, Render Engine, Desktop UI, full diagnostics/resume runtime, and installer.

## Repository visibility risk

GitHub metadata has reported the repository as public. Never commit passwords, cookies, browser profiles, auth tokens, private media, or raw local runtime/session artifacts.

## Current active objective

Complete one real V0.3/D2 Windows field pass, review the eight artifacts, fix/test any provider-specific issue, then merge D2 and continue automatically into D3 until another operator-side action is required.
