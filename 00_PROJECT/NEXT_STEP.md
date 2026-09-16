# Next Step

## Immediate next step — Review real V0.1 artifacts and verify session reuse

The first Windows field run succeeded at the process/classification level:

- bundled tests: `16 passed`;
- run ID: `20260917_011521_dcb358a9`;
- final page state: `TTS_READY`;
- run status: `CAPTURED`;
- process status: `0`.

### Operator sequence

1. In `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\`, collect the files from run `20260917_011521_dcb358a9`:
   - `reports\discovery_report_20260917_011521_dcb358a9.json`
   - `runs\20260917_011521_dcb358a9\dom_inventory.json`
   - `screenshots\saydivoice_20260917_011521_dcb358a9.png`
   - `logs\discovery_20260917_011521_dcb358a9.jsonl`
2. The easiest handoff is to ZIP the whole local `saydivoice` runtime folder and upload it, or upload those four files directly.
3. Run `RUN_DISCOVERY.bat` one more time while the SaydiVoice session is still valid.
4. Confirm the rerun reaches `TTS_READY` / `CAPTURED` without requiring a new login.
5. Return the rerun report/log as well if the session-reuse behavior needs verification.

### D0 field acceptance gate

D0 is fully field-verified when:

- Windows setup succeeds — **observed PASS**;
- real Playwright Chromium opens SaydiVoice — **observed PASS**;
- runner reaches a sensible final classification — **observed `TTS_READY` / `CAPTURED`**;
- report/inventory/screenshot/log exist — report path is observed; full artifact set still needs review;
- artifacts are reviewed for privacy boundaries;
- a second run reuses the persistent browser session while valid.

## After the field gate — D1 Surface Map

Use the real V0.1 artifacts to implement D1:

- enumerate the main TTS editor landmarks and visible interactive controls;
- generate ranked locator candidates using role/label/accessibility name first, stable text/data attributes second, CSS fallback last;
- identify dialogs, tabs, selectors, sliders, cookie/popup surfaces, and login/session states;
- add tests and structured `saydi_map.json` / `selectors.json` outputs;
- record failures/fixes/tests and update project status before advancing to D2.

## Still out of scope until later stages

Do not yet automate voice generation, click Generate, download audio, stress text limits, or implement the production Voice Engine. D3/D4 follow only after the real D1/D2 surface/settings contracts are verified.
