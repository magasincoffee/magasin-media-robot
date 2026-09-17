# Session Log

Chronological handoff record across implementation sessions. Each session must append one concise entry before stopping.

## 2026-09-17 — Session 004 — Artifact review + D1 Surface Map

### Goal

Review the first real SaydiVoice artifact set and turn the observed real UI into a safer D1 Surface Map implementation.

### Work completed

- Reviewed uploaded `discovery_report`, DOM inventory, screenshot, and JSONL log from run `20260917_011521_dcb358a9`.
- Confirmed `TTS_READY` / `CAPTURED`, no runtime error, and 37 interactive elements in the V0.1 inventory.
- Confirmed the observed page is anonymous-ready: login controls are visible while the TTS editor is still usable.
- Identified visible controls for language, voice mode, script editor, add speaker, import script, subtitle-to-voice, Generate, Settings/History, pause, WAV/MP3/FLAC/OGG, and assistant chat.
- Found privacy defect `BUG-20260917-006`: V0.1 persisted contenteditable script text in structured DOM evidence.
- Fixed contenteditable text capture in D1/V0.2 and added regression coverage.
- Fixed semantic locator bug `BUG-20260917-007` so login explanatory copy is not misclassified as History.
- Implemented D1 semantic surface mapping and ranked locator candidates.
- Added per-run `saydi_map.json` and `selectors.json` outputs.
- D1/V0.2 code is on branch `feat/saydivoice-d1-surface-map`.
- Windows Actions run `35172844321`: PASS; compile and unit-test steps successful; D1 suite 23 tests.

### Current gate

D1 code is not merged yet. It requires a real V0.2 rerun on the target Windows laptop to confirm the contenteditable privacy fix, inspect the new surface outputs, resolve any provider-specific sliders/settings, and confirm persistent-profile reuse on a second run.

### Next step

Package D1/V0.2 for the operator, run it on the target laptop, review `discovery_report`, `dom_inventory`, `saydi_map`, `selectors`, screenshot, and log, then merge D1 if the live gate passes and continue to D2 Voice/Settings Catalog.

## 2026-09-17 — Session 003 — First real Windows/SaydiVoice field run

### Goal

Verify SaydiVoice Discovery Runner V0.1 on the target Windows laptop against the real SaydiVoice page.

### Evidence observed

- Playwright Chromium installed successfully.
- Bundled tests completed: `16 passed in 0.29s`.
- Discovery run ID: `20260917_011521_dcb358a9`.
- Real page classified as `TTS_READY`.
- Run status: `CAPTURED`.
- Process status: `0`.

### Result

First real Windows/SaydiVoice execution: PASS at setup, browser navigation, classification, and capture level.

### Next step

Review the real artifacts and verify session reuse before D1.

## 2026-09-17 — Session 002 — SaydiVoice Discovery Runner V0.1

### Goal

Implement and self-test the D0 SaydiVoice Discovery Runner foundation.

### Result

- V0.1 implemented and merged through PR #1.
- 16 local tests PASS.
- PR Windows CI PASS.
- Post-merge Windows CI PASS.

## 2026-09-17 — Session 001 — Repository foundation

### Goal

Create durable project memory before writing SaydiVoice Discovery code.

### Result

Repository/document scaffold: PASS.
