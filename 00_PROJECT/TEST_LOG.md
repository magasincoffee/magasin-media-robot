# Test Log

## 2026-09-17 — D2 V0.3 real-provider review + V0.3.1 corrective build

Scope: review the operator's real SaydiVoice V0.3 artifacts, isolate provider-specific discovery defects, implement V0.3.1 corrective capture, and verify packaging.

### Real V0.3 field run

- Run ID: `20260917_135249_9534c523`.
- Runner: `0.3.0`; schema: `1.2`.
- Page/run: `TTS_READY` / `ANONYMOUS` / `CAPTURED`.
- Runtime exception: none.
- Interactive elements: 38.
- Lifecycle log: clean start → D2 catalog captured → run completed.
- D1 evidence: still valid; script/editor text remained suppressed in structured inventory.
- Output formats: PASS — WAV/MP3/FLAC/OGG observed; MP3 selected.
- D2 semantic completeness: FAIL/PARTIAL.
  - Voice catalog contained only generic `Xoá` instead of meaningful voice options.
  - Language selector opened but options were empty.
  - Stability/expression/speed text values were visible (`2.8`, `Ổn định`, `1.00×`) but generic nearby buttons were associated as controls.
  - Screenshot showed the pause panel remained expanded and exposed rows `0.45s`, `0.25s`, `0.3s`, `0.6s`.
- Defect recorded as `BUG-20260917-008`.

### V0.3.1 corrective implementation

- Added privacy-safe visible-control delta capture around selector opening.
- Added generic control filtering (`Xoá`/Clear, +/- etc.).
- Added display-value parsing from provider-visible label/value text when range/ARIA semantics are unavailable.
- Added pause-panel structure capture without changing values.
- Added Escape + opener-toggle restoration check.
- Added per-surface screenshots for voice/language/pause.
- Added explicit closed-after-observation/warning output.
- Runner/package: `0.3.1`.
- Windows Actions run `35192735044`: PASS.
- Packaging workflow run `35193609757`: PASS.
- GitHub Actions operator artifact produced: `MAGASIN_SAYDIVOICE_DISCOVERY_V0.3.1`.
- Extracted operator ZIP: `MAGASIN_SAYDIVOICE_DISCOVERY_V0.3.1.zip`.
- Extracted ZIP compile: PASS.
- Extracted ZIP pytest: **35 tests PASS**.
- Version check in packaged files: PASS (`0.3.1`).
- Real V0.3.1 provider verification: PENDING one operator rerun.

## 2026-09-17 — D2 Voice/Settings Catalog V0.3 automated verification

Scope: implement and regression-test non-destructive D2 voice/settings observation before real-provider field execution.

- Branch: `feat/saydivoice-d2-voice-settings-catalog`.
- Runner/package version: `0.3.0`.
- Report schema: `1.2`.
- Added `voice_catalog.json` and `settings_catalog.json` outputs.
- Added catalog privacy regression: unrelated script/editor values are not promoted into D2 outputs.
- Added voice option deduplication and selected output-format tests.
- Added stability/speed current-value/range parsing tests from provider-exposed range/ARIA evidence.
- Added runner integration test proving catalog paths are written when D2 succeeds.
- Added graceful-fallback test proving a provider-specific D2 probe failure does not destroy the D1 capture.
- Local distribution-derived compile: PASS.
- Local distribution-derived pytest: **38 tests PASS**.
- Package version import: PASS (`0.3.0`).
- Operator ZIP: `MAGASIN_SAYDIVOICE_DISCOVERY_V0.3.zip`.
- ZIP structure/privacy validation: PASS — 40 packaged files; no `.venv`, `browser_profile`, cookie/token/secret file detected.
- GitHub Actions push run `35189216611`: PASS.
- GitHub Actions push run `35189339655`: PASS after runner integration/fallback coverage.
- PR #7 Windows Actions run `35189814339`: PASS — checkout, Python setup, dependency install, compile, unit tests all successful.

## 2026-09-17 — V0.2 Windows distribution packaging self-test

Scope: final operator ZIP for the D1 live gate.

- Distribution: `MAGASIN_SAYDIVOICE_DISCOVERY_V0.2.zip`.
- Runner version: `0.2.0`.
- `python -m compileall -q src`: PASS.
- `PYTHONPATH=src python -m pytest -q`: PASS — **29 tests**.
- Version import check: PASS (`0.2.0`).
- Real V0.1 field inventory replayed as a sanitized structural fixture with the editor marked contenteditable: expected D1 controls mapped.
- Privacy regression replay: PASS — the prior real script text is absent after V0.2 inventory sanitization.
- Expected selector keys observed in replay include language, voice, script editor, Generate, Settings, History, pause, WAV/MP3/FLAC/OGG, login, toolbar actions, and assistant chat.

## 2026-09-17 — First field artifact review + D1/V0.2 validation

Scope: review uploaded artifacts from real Windows run `20260917_011521_dcb358a9` and validate D1 Surface Map branch.

### Uploaded artifact review

- `discovery_report_20260917_011521_dcb358a9.json`: PASS structurally; runner `0.1.0`, `TTS_READY`, `CAPTURED`, no runtime error.
- `discovery_20260917_011521_dcb358a9.jsonl`: PASS; clean start/completion lifecycle with no exception.
- Screenshot: PASS for visible TTS page; anonymous login controls are visible while TTS editor remains usable.
- `dom_inventory.json`: functional control capture PASS (37 elements), privacy FAIL for V0.1 because a contenteditable script editor persisted its visible text.
- Privacy defect tracked as `BUG-20260917-006`; fixed in V0.2 with browser-probe and serializer suppression plus regression coverage.
- Locator semantic defect `BUG-20260917-007` also fixed so login explanatory copy is not confused with the History tab.

### D1/V0.2 branch verification

- Branch: `feat/saydivoice-d1-surface-map`.
- Version: `0.2.0`.
- D1 writes `saydi_map.json` and `selectors.json` in the per-run directory.
- Windows GitHub Actions run `35172844321`: PASS.
- Environment: `windows-latest`.
- Dependency install: PASS.
- Compile package: PASS.
- Unit-test step: PASS.
- D1 suite: 23 tests, including contenteditable privacy suppression and locator semantic regression coverage.

## 2026-09-17 — Real Windows SaydiVoice field run

- Playwright Chromium download/install: PASS.
- Bundled regression tests: PASS — 16 tests.
- Discovery run ID: `20260917_011521_dcb358a9`.
- Final page classification: `TTS_READY`.
- Final run status: `CAPTURED`.
- Process status: `0`.

## 2026-09-17 — SaydiVoice Discovery Runner V0.1

- Local compile: PASS.
- Local pytest: PASS — 16 tests.
- Package import/version: PASS (`0.1.0`).
- PR GitHub Actions Windows run `35130561175`: PASS.
- Post-merge `main` GitHub Actions run `35130819104`: PASS.

## 2026-09-17 — Repository initialization checks

- Repository access: PASS (`magasincoffee/magasin-media-robot`, admin/push access available).
- Default branch: `main`.
- Documentation/source-of-truth scaffold creation: PASS.
