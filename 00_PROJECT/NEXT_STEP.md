# Next Step

## Immediate next step — Live-verify D2 / SaydiVoice Discovery V0.3

D1/V0.2 is merged. D2/V0.3 code and Windows CI are now complete on branch `feat/saydivoice-d2-voice-settings-catalog`.

### What V0.3 does

- retains all D1 privacy/surface-map behavior;
- opens the voice selector, language selector, and pause selector for observation only;
- captures visible option text/roles/selected state when the provider exposes them;
- closes observed menus without intentionally changing selections;
- probes Stability / Expression / Speed / Pause / Output format surfaces for real current values, ranges, ARIA metadata, and locator hints;
- writes `voice_catalog.json` and `settings_catalog.json`;
- never clicks Generate and never downloads audio;
- falls back gracefully to D1 evidence if a provider-specific D2 probe fails.

### Operator sequence

1. Use the packaged `MAGASIN_SAYDIVOICE_DISCOVERY_V0.3.zip` on the target Windows laptop.
2. Extract to a new folder.
3. Run `CAI_DAT_VA_CHAY.bat` once.
4. Do not click or change anything in the SaydiVoice window while discovery is running.
5. Let the robot open/close observation surfaces and finish by itself.
6. Return the newest eight artifacts from one run ID:
   - `reports\discovery_report_<run-id>.json`
   - `runs\<run-id>\dom_inventory.json`
   - `runs\<run-id>\saydi_map.json`
   - `runs\<run-id>\selectors.json`
   - `runs\<run-id>\voice_catalog.json`
   - `runs\<run-id>\settings_catalog.json`
   - `screenshots\saydivoice_<run-id>.png`
   - `logs\discovery_<run-id>.jsonl`
7. Do not send `browser_profile`.

### D2 acceptance gate

D2 may be merged when:

- run remains `TTS_READY` / `CAPTURED`;
- `voice_catalog.json` and `settings_catalog.json` are generated, or an explicit non-blocking warning accurately explains a provider surface that could not be cataloged;
- voice/language/pause observations do not change a selection;
- stability/expression/speed evidence reflects real DOM/current UI rather than guessed selectors;
- output format remains unchanged;
- no Generate/download action occurs;
- no script/editor content appears in structured outputs;
- no new blocking defect is found.

## After D2 — D3 Generation Lifecycle

Only after D2 field acceptance: characterize the real Generate lifecycle using a minimal controlled text sample, including start/processing/success/error states. Do not begin download automation until D4.
