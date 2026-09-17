# D2 Voice/Settings Catalog V0.3 — implementation note

Date: 2026-09-17
Branch: `feat/saydivoice-d2-voice-settings-catalog`

## Implemented

- non-destructive observation of voice, language, and pause selectors;
- structured `voice_catalog.json` and `settings_catalog.json` outputs;
- current setting evidence for stability, expression, speed, pause, and output format when exposed by provider DOM/ARIA;
- output-format selected state and options;
- explicit warnings for provider surfaces that cannot be resolved safely;
- graceful fallback to D1 capture if D2 provider probing fails;
- runner/report upgrade to V0.3 / schema 1.2;
- privacy regression coverage preventing unrelated script/editor text from entering D2 catalogs.

## Automated verification

- local distribution-derived pytest: 38 tests PASS;
- Windows Actions run `35189216611`: PASS;
- Windows Actions run `35189339655`: PASS.

## Field gate

V0.3 must run once on the target Windows laptop. No manual setting changes, Generate action, or audio download should occur. Review the report, D1 evidence, voice/settings catalogs, screenshot, and JSONL log before merging D2.
