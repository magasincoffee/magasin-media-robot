# Session Log

Chronological handoff record across implementation sessions. Each session must append one concise entry before stopping.

## 2026-09-17 — Session 007 — D2 V0.3 field review → V0.3.1 corrective build

### Workbox

Started approximately 14:12 ICT under the 28-minute maximum task rule. Stopped before the time limit because a new real-provider operator rerun is now the blocking gate.

### Field evidence reviewed

- Run `20260917_135249_9534c523` completed `TTS_READY` / `ANONYMOUS` / `CAPTURED` with runner `0.3.0` and no runtime error.
- D1 outputs remained valid and structured evidence stayed privacy-safe.
- MP3 selection and WAV/MP3/FLAC/OGG enumeration were captured correctly.
- D2 completeness issue found: voice selector produced only generic `Xoá`; language options were empty; custom slider controls were not semantically exposed; the pause panel remained expanded in the final screenshot.
- Recorded as `BUG-20260917-008`.

### Corrective work completed

- Advanced D2 to runner/package `0.3.1`.
- Added privacy-safe before/after visible-control delta capture for custom menus/surfaces.
- Added generic Clear/Delete/+/- filtering from option semantics.
- Added visible display-value extraction for stability/expression/speed/pause when provider ARIA/range data are missing.
- Added pause-panel structure capture without changing values.
- Added surface-restoration verification: Escape first, then opener toggle when necessary.
- Added per-surface screenshots: voice, language, pause.
- Added explicit closed-after-observation/warnings in catalog output.
- CI now builds a one-click V0.3.1 operator ZIP artifact automatically.

### Verification

- Windows Actions commit `07f43a89297066dbb5641c07dfdac70b0aebae68`: PASS.
- Packaging workflow run `35193609757`: PASS.
- Operator artifact generated successfully.
- Extracted operator ZIP compile: PASS.
- Extracted operator ZIP pytest: **35 tests PASS**.
- Version files: `0.3.1` PASS.

### Next gate

Operator runs `MAGASIN_SAYDIVOICE_DISCOVERY_V0.3.1.zip` once and returns the report/catalog/D1 files plus the three D2 surface screenshots and final screenshot/log. If `BUG-20260917-008` is verified, merge PR #7 and start D3 Generation Lifecycle.

## 2026-09-17 — Session 006 — D2 Voice/Settings Catalog V0.3

### Workbox

Operator requested task execution in bounded workboxes of at most 28 minutes. This workbox started at approximately 13:12 ICT and is stopped as soon as a real-provider operator action becomes the next gate.

### Goal

Complete everything possible for D2 without operator interaction: implementation, privacy safeguards, tests, Windows CI, durable logs, and operator packaging.

### Work completed

- Confirmed D1/V0.2 merged through PR #6 (`79bb057f4adc7ba010645bc63461564fa037e7a8`).
- Created branch `feat/saydivoice-d2-voice-settings-catalog`.
- Added `catalog.py` with non-destructive voice/language/pause observation plus current settings DOM probing.
- Added structured `voice_catalog.json` and `settings_catalog.json` outputs.
- Added stability/expression/speed/pause/output-format evidence model with current value/range/ARIA/locator hints where the provider exposes them.
- Added voice/language/pause option observation that closes opened surfaces and does not intentionally change selections.
- Runner upgraded to V0.3 / report schema 1.2 with optional catalog paths.
- Added graceful D2 fallback: provider-specific catalog failure leaves D1 capture usable.
- Added privacy test proving unrelated script text is not copied into D2 catalogs.
- Added output-format, option deduplication, settings-range, runner-integration, and fallback regression tests.
- Updated `CURRENT_STATUS.md`, `NEXT_STEP.md`, and `TEST_LOG.md`.

### Test result

- Distribution-derived local compile: PASS.
- Distribution-derived local pytest after D2 integration: **38 tests PASS**.
- Windows Actions run `35189216611`: PASS.
- Windows Actions run `35189339655`: PASS after runner integration/fallback tests.

### Next gate

Build/use the V0.3 Windows package and perform one real SaydiVoice run. The operator should not manually change settings or click Generate. Return the V0.3 report, D1 files, `voice_catalog.json`, `settings_catalog.json`, screenshot, and JSONL log for field review.

## 2026-09-17 — Session 005 — Package D1/V0.2 for live Windows verification

### Goal

Finish everything possible without operator interaction and hand off one ZIP for the real V0.2 SaydiVoice field gate.

### Work completed

- Rechecked the real V0.1 report, DOM inventory, screenshot evidence, and JSONL lifecycle.
- Built the V0.2 operator distribution `MAGASIN_SAYDIVOICE_DISCOVERY_V0.2.zip`.
- Added one-click `CAI_DAT_VA_CHAY.bat` and `CHAY_LAI_DISCOVERY.bat` helpers.
- Distribution preserves the existing runtime/browser profile under `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice` rather than bundling session data.
- V0.2 keeps Generate/download actions out of scope and read-only.
- Added D1 outputs `saydi_map.json` and `selectors.json` to the operator handoff contract.
- Replayed a sanitized structural fixture derived from the first real field inventory to check semantic mappings.
- Confirmed the V0.1 leaked script text does not survive V0.2 structured inventory sanitization.
- Updated project status, test log, next step, and Windows helper files on branch `feat/saydivoice-d1-surface-map`.

### Test result

- Compile: PASS.
- Distribution pytest: PASS — 29 tests.
- Version check: PASS (`0.2.0`).
- Field-fixture semantic replay: PASS.
- Real V0.2 provider run: PENDING operator execution on Windows.

### Next step

Operator downloads/extracts the V0.2 ZIP, runs `CAI_DAT_VA_CHAY.bat`, and returns the six newest artifacts from the same run ID. If those pass the live gate, merge D1 and start D2 Voice/Settings Catalog.

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
- Windows Actions run `35172844321`: PASS; D1 suite 23 tests.

### Current gate

D1 code is not merged yet. It requires a real V0.2 rerun on the target Windows laptop.

## 2026-09-17 — Session 003 — First real Windows/SaydiVoice field run

- Playwright Chromium installed successfully.
- Bundled tests completed: `16 passed in 0.29s`.
- Discovery run ID: `20260917_011521_dcb358a9`.
- Real page classified as `TTS_READY` / `CAPTURED`, exit `0`.

## 2026-09-17 — Session 002 — SaydiVoice Discovery Runner V0.1

- V0.1 implemented and merged through PR #1.
- 16 local tests PASS.
- PR and post-merge Windows CI PASS.

## 2026-09-17 — Session 001 — Repository foundation

Repository/document scaffold: PASS.
