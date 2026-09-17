# Next Step

## Immediate next step — Live-verify D1 / SaydiVoice Discovery V0.2

The first real V0.1 artifact set has been reviewed and D1 Surface Map is implemented on branch `feat/saydivoice-d1-surface-map`.

### What V0.2 changes

- suppresses text from every contenteditable script editor before structured evidence is persisted;
- distinguishes `TTS_READY` from authentication state;
- produces `saydi_map.json` and `selectors.json`;
- maps semantic controls and ranked locator candidates;
- keeps unresolved sliders/settings visible as explicit follow-up items instead of guessing selectors.

### Operator sequence

1. Use the newly packaged D1/V0.2 build on the target Windows laptop.
2. Run setup/update if the package requests it, then run discovery.
3. Do not click Generate or download audio yet.
4. Let the runner complete on the real SaydiVoice TTS page.
5. Return the newest:
   - `reports\discovery_report_*.json`
   - `runs\<run-id>\dom_inventory.json`
   - `runs\<run-id>\saydi_map.json`
   - `runs\<run-id>\selectors.json`
   - `screenshots\saydivoice_<run-id>.png`
   - `logs\discovery_<run-id>.jsonl`
6. Run discovery once more while the same SaydiVoice/browser session remains valid and confirm normal reuse behavior.

### Acceptance gate

D1 can be merged when:

- real V0.2 run reaches `TTS_READY` / `CAPTURED`;
- script/editor text is absent from `dom_inventory.json` and other structured discovery outputs;
- `saydi_map.json` and `selectors.json` are generated;
- Generate, Settings, History, voice selector, language selector, pause selector, format tabs, and other observed controls map correctly;
- unresolved sliders/settings are documented rather than assigned guessed selectors;
- second run confirms persistent-profile reuse behavior where applicable;
- no new blocking bug is found.

## After D1 — D2 Voice/Settings Catalog

Open relevant selectors/settings non-destructively and catalog the real current UI options: voices, languages, speed, stability/expression, pause behavior, output formats, and other exposed settings. Add schemas/tests before any automatic generation or download workflow.

## Still out of scope

Do not yet automate Generate, audio download, text-limit stress tests, or the production Voice Engine. Those belong to D3/D4 and later phases.
