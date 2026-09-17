# Next Step

## Immediate next step — Run packaged SaydiVoice Discovery V0.2 on Windows

D1/V0.2 is implemented and packaged. The project now requires one real provider-side run before D1 can be merged.

### Operator sequence

1. Download `MAGASIN_SAYDIVOICE_DISCOVERY_V0.2.zip`.
2. Extract it to a new folder. Do not delete `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\browser_profile`; the existing local profile is intentionally reused.
3. Double-click `CAI_DAT_VA_CHAY.bat`.
4. Wait for the bundled self-tests to pass and for Chromium to open SaydiVoice.
5. **Do not click `Tạo giọng nói` and do not download audio yet.** V0.2 is read-only discovery.
6. Let the runner finish. The runtime folder will open automatically.
7. Return the newest six files from the same run ID:
   - `reports\discovery_report_*.json`
   - `runs\<run-id>\dom_inventory.json`
   - `runs\<run-id>\saydi_map.json`
   - `runs\<run-id>\selectors.json`
   - `screenshots\saydivoice_<run-id>.png`
   - `logs\discovery_<run-id>.jsonl`
8. Do **not** upload `browser_profile`.

### Acceptance gate

D1 can be merged when the real V0.2 artifacts show:

- `TTS_READY` / `CAPTURED`;
- script/editor text absent from `dom_inventory.json`, `saydi_map.json`, and `selectors.json`;
- `saydi_map.json` and `selectors.json` generated successfully;
- Generate, Settings, History, voice selector, language selector, pause selector, format tabs, editor toolbar, and other observed controls map sensibly;
- sliders/settings that still lack stable DOM semantics are explicitly unresolved instead of guessed;
- no new blocking bug.

If the first V0.2 run passes but session reuse remains ambiguous, run `CHAY_LAI_DISCOVERY.bat` once and return the second report/log.

## After D1 — D2 Voice/Settings Catalog

After the live gate passes, merge D1/V0.2 and begin non-destructive D2 discovery of actual voice/settings options: voice catalog, language, speed, stability/expression, pause behavior, output format, and related current UI controls. Add schemas and tests before any automatic Generate/download flow.

## Still out of scope

Do not yet automate Generate, audio download, text-limit stress tests, or the production Voice Engine. Those belong to D3/D4 and later phases.
