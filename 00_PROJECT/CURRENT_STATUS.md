# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery. D1 Surface Map/V0.2 is merged to `main`. D2 Voice/Settings Catalog V0.3 completed its first real Windows/SaydiVoice run, exposed provider-specific catalog gaps, and has been revised as V0.3.1 on branch `feat/saydivoice-d2-voice-settings-catalog`. One V0.3.1 field rerun is now required before D2 merge.**

## Completed

- D0 / Discovery Runner V0.1 completed and merged.
- D1 / Surface Map V0.2 completed, field-verified, and merged through PR #6 as `79bb057f4adc7ba010645bc63461564fa037e7a8`.
- Real V0.2 field run `20260917_110310_7bf1810a` confirmed `TTS_READY` / `ANONYMOUS` / `CAPTURED`, 38 interactive elements, correct D1 outputs, and the V0.1 contenteditable privacy leak fixed on the real provider page.
- D2 / V0.3 implementation is on branch `feat/saydivoice-d2-voice-settings-catalog` and PR #7.
- Real D2 V0.3 field run `20260917_135249_9534c523` completed cleanly at the runner level: `0.3.0`, schema `1.2`, `TTS_READY` / `ANONYMOUS` / `CAPTURED`, no runtime exception, 38 captured interactive elements.
- V0.3 correctly preserved D1 outputs and output-format evidence (WAV/MP3/FLAC/OGG with MP3 selected) and did not invoke Generate/download actions.
- V0.3 field review found `BUG-20260917-008`: custom provider surfaces were under-captured. Voice options collapsed to generic `Xoá`, language options were empty, custom slider values were visible but not represented as stable slider nodes, and the pause panel remained expanded in the final screenshot.
- V0.3.1 fixes are implemented on the same branch:
  - privacy-safe before/after visible-control delta for custom selector surfaces;
  - generic Clear/Delete/+/- filtering;
  - visible display-value parsing for stability/expression/speed/pause when ARIA/range values are absent;
  - pause-panel structure capture without changing values;
  - Escape + opener-toggle restoration logic;
  - per-surface screenshots for voice/language/pause;
  - explicit `closed_after_observation` and warnings;
  - runner/version update to `0.3.1`.
- Automated V0.3.1 Windows Actions run `35192735044`: PASS.

## Current live gate

Run the V0.3.1 operator build once on the target Windows laptop. Return these outputs from the same run ID:

- `reports\discovery_report_<run-id>.json`
- `runs\<run-id>\dom_inventory.json`
- `runs\<run-id>\saydi_map.json`
- `runs\<run-id>\selectors.json`
- `runs\<run-id>\voice_catalog.json`
- `runs\<run-id>\settings_catalog.json`
- `runs\<run-id>\d2_voice_surface.png`
- `runs\<run-id>\d2_language_surface.png`
- `runs\<run-id>\d2_pause_surface.png`
- `screenshots\saydivoice_<run-id>.png`
- `logs\discovery_<run-id>.jsonl`

Acceptance requires: no setting selection/value change; no Generate/download; script/editor values absent from structured evidence; meaningful voice/language surface evidence or explicit warnings; visible display values captured; pause panel restored when practical; D1 evidence remains valid.

## Not yet implemented

- D2 V0.3.1 real-provider verification and merge.
- D3 generation lifecycle observation/automation.
- D4 audio download discovery.
- D5 controlled limits/error characterization.
- D6 frozen discovery contracts.
- Production Voice Engine.
- Media Analyzer, Scene Planner, Subtitle Engine, Render Engine, Desktop UI, full diagnostics/resume runtime, and installer.

## Repository visibility risk

GitHub metadata has reported the repository as public. Never commit passwords, cookies, browser profiles, auth tokens, private media, voice catalogs from a private account, or raw local runtime/session artifacts.

## Current active objective

Finish V0.3.1 packaging/CI, perform one real Windows/SaydiVoice rerun, review the eleven outputs above, then either verify `BUG-20260917-008` and merge PR #7 or fix any remaining provider-specific defect before starting D3.
