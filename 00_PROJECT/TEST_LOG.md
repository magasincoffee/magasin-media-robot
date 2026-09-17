# Test Log

## 2026-09-17 — D2 V0.3.1 field review + V0.3.2 corrective build

Scope: review the operator's V0.3.1 real-provider artifacts, verify which parts of `BUG-20260917-008` are fixed, isolate the remaining custom-surface gap, and build V0.3.2.

### Real V0.3.1 field evidence

- Run ID inferred consistently from catalog evidence paths: `20260917_142133_bd48aed7`.
- Uploaded structured evidence reviewed: DOM inventory, D1 map/selectors, voice catalog, settings catalog, and three D2 surface screenshots.
- Privacy regression: PASS — the visible editor phrase from the screenshot is absent from all five uploaded structured JSON artifacts.
- Current setting-value capture: PASS.
  - stability: `2.8`;
  - expression: `Ổn định`;
  - speed: `1.00×`;
  - pause state: `Đang tắt`;
  - output: MP3 selected, WAV/MP3/FLAC/OGG present.
- Pause structure: PASS.
  - automatic checkbox present and unchecked;
  - period `0.45s`;
  - comma `0.25s`;
  - semicolon `0.3s`;
  - newline `0.6s`;
  - default button present;
  - catalog reports `closed_after_observation: true`.
- Language catalog: FAIL/PARTIAL — surface screenshot visibly shows English, Tiếng Việt, 中文, 日本語, 한국어, Deutsch, Español, Français, while structured `language.options` remained empty.
- Voice catalog: FAIL/PARTIAL — surface screenshot visibly shows one automatic voice card (`Tự động`, `Hệ thống tự chọn giọng`), while structured catalog incorrectly counted modal navigation tabs (`Khám phá`, `Đã chọn`, `Giọng của tôi`, `Yêu thích`) as four voice options.

### V0.3.2 corrective implementation

- Added `enhanced_catalog.py` with a second privacy-safe visible-leaf delta pass for custom provider surfaces.
- Editable/input/contenteditable nodes are excluded from this pass.
- Added language option extraction for newly visible leaf labels.
- Added voice navigation/generic filtering and recognition of the current automatic voice card.
- Enhanced results override weak base-catalog options only when meaningful data is found.
- Added pure regression tests for visible delta, multilingual labels, automatic voice card parsing, and modal-navigation filtering.
- Added runner integration regression verifying enhanced results replace weak results.
- Runner/package version: `0.3.2`.
- Windows Actions / PR run `35195143308`: PASS.
- Operator artifact: `MAGASIN_SAYDIVOICE_DISCOVERY_V0.3.2`.
- Downloaded/extracted operator ZIP compile: PASS.
- Downloaded/extracted operator ZIP pytest: **40 tests PASS**.
- Real V0.3.2 provider verification: PENDING one final operator rerun.

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
- GitHub Actions push run `35189339655`: PASS after D2 runner integration/fallback coverage.
- PR #7 Windows Actions run `35189814339`: PASS — checkout, Python setup, dependency install, compile, unit tests all successful.

## 2026-09-17 — V0.2 Windows distribution packaging self-test

- Distribution: `MAGASIN_SAYDIVOICE_DISCOVERY_V0.2.zip`.
- Runner version: `0.2.0`.
- Compile: PASS.
- Pytest: PASS — **29 tests**.
- Version import: PASS (`0.2.0`).
- Privacy regression replay: PASS.

## 2026-09-17 — First field artifact review + D1/V0.2 validation

- First real V0.1 artifacts reviewed.
- Functional control capture PASS; V0.1 contenteditable privacy defect found and fixed in V0.2.
- D1 Windows Actions run `35172844321`: PASS.
- D1 suite: 23 tests PASS.

## 2026-09-17 — Real Windows SaydiVoice field run

- Playwright Chromium install: PASS.
- Run `20260917_011521_dcb358a9`: `TTS_READY` / `CAPTURED`, process `0`.

## 2026-09-17 — SaydiVoice Discovery Runner V0.1

- Local compile: PASS.
- Local pytest: PASS — 16 tests.
- PR Windows CI and post-merge CI: PASS.

## 2026-09-17 — Repository initialization checks

- Repository access: PASS (`magasincoffee/magasin-media-robot`).
- Default branch: `main`.
- Documentation/source-of-truth scaffold creation: PASS.
