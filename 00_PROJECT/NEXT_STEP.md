# Next Step

## Immediate next step — Run SaydiVoice Discovery V0.3 / D2 on Windows

D1 is merged and D2 Voice/Settings Catalog V0.3 is implemented, unit-tested, Windows-CI verified, and packaged.

### Operator sequence

1. Download `MAGASIN_SAYDIVOICE_DISCOVERY_V0.3.zip`.
2. Extract it to a new folder.
3. Double-click `CAI_DAT_VA_CHAY.bat`.
4. Wait for bundled self-tests to pass and for Chromium to open SaydiVoice.
5. Do **not** manually click `Tạo giọng nói` and do not download audio.
6. D2 will itself open only whitelisted read-only selector surfaces for Voice, Language, and Pause, observe them, and close them with Escape.
7. Let the runner finish; the local runtime folder opens automatically.
8. Return the newest eight files from the **same run ID**:
   - `reports\discovery_report_*.json`
   - `runs\<run-id>\dom_inventory.json`
   - `runs\<run-id>\saydi_map.json`
   - `runs\<run-id>\selectors.json`
   - `runs\<run-id>\voice_catalog.json`
   - `runs\<run-id>\settings_catalog.json`
   - `screenshots\saydivoice_<run-id>.png`
   - `logs\discovery_<run-id>.jsonl`
9. Do **not** upload `browser_profile`.

## D2 acceptance gate

The implementation session will verify:

- runner `0.3.0` reaches `TTS_READY` / `CAPTURED`;
- voice catalog contains real current provider options, or a precise provider-specific capture limitation is identified;
- language/pause menu evidence is captured without changing the selected value;
- stability/expression/speed setting evidence is sufficient to identify the real interactive mechanism or remains explicitly unresolved rather than guessed;
- editor/script text remains suppressed from structured evidence;
- logs show no Generate/download action;
- no new blocking defect.

If a provider-specific issue is found, record it in `BUG_LOG.md`, fix it, run regression tests/CI, and package a corrected field build before asking the operator to rerun.

## After D2

When the D2 field gate passes:

1. merge D2;
2. begin D3 Generation Lifecycle discovery;
3. design a tightly controlled test that observes `Tạo giọng nói` state transitions using harmless test text and no limit bypassing;
4. add tests/logging/recovery before requesting the next provider-side run.

## Still out of scope for V0.3

No automatic Generate, audio download, stress testing of text limits, provider-limit bypassing, or production Voice Engine behavior.
