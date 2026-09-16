# Next Step

## Immediate next step — Field-verify SaydiVoice Discovery Runner V0.1

Run the V0.1 discovery runner on the target Windows laptop against the real SaydiVoice Studio page before expanding automation.

### Operator sequence

1. Obtain the merged/current project files on the laptop.
2. In `01_DISCOVERY\saydivoice`, run `SETUP_DISCOVERY.bat` once.
3. Confirm setup completes its bundled unit tests successfully.
4. Run `RUN_DISCOVERY.bat`.
5. If SaydiVoice requires authentication, log in manually inside the Chromium window opened by the runner. The default run allows up to 180 seconds and stores only the browser session in the local persistent profile.
6. Do not click Generate or download audio during this V0.1 pass.
7. Let the runner finish and inspect the local runtime root:
   `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\`
8. Review/return the newest:
   - `reports\discovery_report_*.json`
   - `runs\<run-id>\dom_inventory.json`
   - `screenshots\saydivoice_<run-id>.png`
   - `logs\discovery_<run-id>.jsonl`

### Field acceptance gate

V0.1/D0 is field-verified only when:

- the Windows setup succeeds;
- Playwright Chromium opens the real SaydiVoice target;
- first-use manual login can populate/reuse the local profile when needed;
- the runner reaches a sensible final classification, preferably `TTS_READY` after login;
- the report, sanitized DOM inventory, screenshot, and JSONL log are created;
- evidence contains no intentionally captured password/input values, raw cookies, storage, authorization headers, or URL query/fragment secrets;
- rerunning the runner does not require login again while the SaydiVoice session remains valid.

## After the field gate — D1 Surface Map

Use the real V0.1 evidence to implement D1:

- enumerate the main TTS editor landmarks and visible interactive controls;
- generate ranked locator candidates using role/label/accessibility name first, stable text/data attributes second, CSS fallback last;
- identify dialogs, tabs, selectors, sliders, cookie/popup surfaces, and login/session states;
- add tests and structured `saydi_map.json` / `selectors.json` outputs;
- record failures/fixes/tests and update project status before advancing to D2.

## Still out of scope until later stages

Do not yet automate voice generation, click Generate, download audio, stress text limits, or implement the production Voice Engine. D3/D4 follow only after the real D1/D2 surface/settings contracts are verified.
