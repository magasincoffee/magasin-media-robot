# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery. D1 Surface Map/V0.2 is merged to `main`. D2 Voice/Settings Catalog V0.3 is implemented, packaged, and automated-test verified on PR #7; the next gate is one real Windows/SaydiVoice V0.3 run by the operator.**

## Completed

- D0 / Discovery Runner V0.1 completed and merged.
- D1 / Surface Map V0.2 completed, field-verified, and merged through PR #6 as `79bb057f4adc7ba010645bc63461564fa037e7a8`.
- Real V0.2 field run `20260917_110310_7bf1810a` confirmed `TTS_READY` / `ANONYMOUS` / `CAPTURED`, 38 interactive elements, correct D1 outputs, and the V0.1 contenteditable privacy leak fixed on the real provider page.
- D2 / V0.3 implementation is on branch `feat/saydivoice-d2-voice-settings-catalog` and PR #7.
- D2 adds `voice_catalog.json` and `settings_catalog.json` to each successful TTS-ready run.
- D2 opens only the voice, language, and pause selectors for observation, captures visible options when exposed, then closes each surface without intentionally selecting an option.
- D2 does not invoke Generate, does not download audio, and does not enter credentials.
- D2 setting probe records stability/expression/speed/pause/output-format labels plus current range/ARIA evidence when the provider exposes it; unresolved custom controls remain explicit rather than guessed.
- Output-format catalog records WAV/MP3/FLAC/OGG and the selected format when available.
- D2 catalog builder excludes unrelated script/editor values and keeps catalog evidence local-only.
- Runner upgraded to `0.3.0`, report schema to `1.2`, and report now includes optional catalog paths.
- Graceful fallback implemented: if the D2 catalog probe fails because the provider UI changed, D1 capture/report still completes instead of failing the entire discovery run.
- Operator package built: `MAGASIN_SAYDIVOICE_DISCOVERY_V0.3.zip`.
- Package ZIP contains 40 files and excludes `.venv`, `browser_profile`, and obvious cookie/token/secret files.

## Verification

- Local distribution-derived compile: PASS.
- Local distribution-derived regression suite: **38 tests PASS**.
- Version import: PASS (`0.3.0`).
- Branch Windows Actions run `35189216611`: PASS.
- Branch Windows Actions run `35189339655`: PASS after D2 runner integration/fallback tests.
- PR #7 Windows Actions run `35189814339`: PASS; checkout, Python setup, dependency install, compile, and unit tests successful.

## Current live gate

Run V0.3 on the target Windows laptop against the real SaydiVoice TTS page. Review:

- `reports\discovery_report_<run-id>.json`
- `runs\<run-id>\dom_inventory.json`
- `runs\<run-id>\saydi_map.json`
- `runs\<run-id>\selectors.json`
- `runs\<run-id>\voice_catalog.json`
- `runs\<run-id>\settings_catalog.json`
- `screenshots\saydivoice_<run-id>.png`
- `logs\discovery_<run-id>.jsonl`

Acceptance requires the D2 outputs to be generated or to report explicit non-blocking warnings, no settings to be changed, no Generate/download action, and no script/editor values in structured evidence.

## Not yet implemented

- D2 real-provider field acceptance and merge.
- D3 generation lifecycle observation/automation.
- D4 audio download discovery.
- D5 controlled limits/error characterization.
- D6 frozen discovery contracts.
- Production Voice Engine.
- Media Analyzer, Scene Planner, Subtitle Engine, Render Engine, Desktop UI, full diagnostics/resume runtime, and installer.

## Repository visibility risk

GitHub metadata has reported the repository as public. Never commit passwords, cookies, browser profiles, auth tokens, private media, voice catalogs from a private account, or raw local runtime/session artifacts.

## Current active objective

Operator runs `MAGASIN_SAYDIVOICE_DISCOVERY_V0.3.zip` once, returns the eight outputs from the same run ID, then field-review/fix/merge D2 before D3 begins.
