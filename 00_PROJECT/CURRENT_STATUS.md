# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery. D1 Surface Map/V0.2 is implemented on branch `feat/saydivoice-d1-surface-map`, code/CI verified, packaged for Windows field verification, and now waits for one real V0.2 run on the target laptop before merge.**

## Completed

- Repository/project architecture and durable continuation records established.
- SaydiVoice Discovery Runner V0.1 merged through PR #1.
- First real Windows V0.1 run succeeded: run `20260917_011521_dcb358a9`, `TTS_READY`, `CAPTURED`, exit code `0`.
- Uploaded field artifacts reviewed: report, screenshot, DOM inventory, and JSONL log.
- First real state confirmed as anonymous-ready: TTS editor usable while login controls remain visible.
- 37 visible interactive elements captured in V0.1.
- Privacy defect `BUG-20260917-006` found: V0.1 persisted contenteditable script text.
- Semantic defect `BUG-20260917-007` found: login explanatory text could be confused with History.
- D1/V0.2 implemented: readiness/auth state split, contenteditable privacy suppression, semantic surface map, ranked locator candidates, `saydi_map.json`, and `selectors.json`.
- D1 branch Windows Actions run `35172844321`: PASS; dependency install, compile, and unit tests PASS.
- Branch D1 suite: 23 tests PASS.
- One-click Windows helpers added: `CAI_DAT_VA_CHAY.bat` and `CHAY_LAI_DISCOVERY.bat`.
- Operator distribution `MAGASIN_SAYDIVOICE_DISCOVERY_V0.2.zip` built and self-tested locally.
- Distribution compile: PASS.
- Distribution pytest: **29 tests PASS**.
- Distribution version import: PASS (`0.2.0`).
- Distribution was regression-checked against a sanitized structural fixture derived from the first real field inventory; expected semantic controls mapped and the prior script text was absent from structured evidence.

## Current live gate

Run `MAGASIN_SAYDIVOICE_DISCOVERY_V0.2.zip` on the target Windows laptop and return the newest six artifacts:

- `reports\discovery_report_*.json`
- `runs\<run-id>\dom_inventory.json`
- `runs\<run-id>\saydi_map.json`
- `runs\<run-id>\selectors.json`
- `screenshots\saydivoice_<run-id>.png`
- `logs\discovery_<run-id>.jsonl`

Acceptance requires `TTS_READY` / `CAPTURED`, no editor/script text in structured evidence, correct D1 outputs, and no new blocking defect. A second run may be requested if session-reuse behavior still needs confirmation.

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

Complete the real V0.2 Windows field gate, then merge D1 and proceed to D2 Voice/Settings Catalog.
