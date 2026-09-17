# SaydiVoice Discovery

This workstream learns the real behavior of SaydiVoice Studio before production browser automation is frozen.

Target: `https://voice.saydi.ai/vi/studio/tts/`

## Current status — V0.3 / D2

D0 established the browser runner. D1 Surface Map/V0.2 passed its real Windows field gate on run `20260917_110310_7bf1810a` and was merged through PR #2.

V0.3 implements D2 Voice/Settings Catalog. It remains non-destructive: **it does not click Generate and does not download audio**.

V0.3 retains all D1 evidence and additionally:

- opens only whitelisted read-only selector surfaces for voice, language, and pause;
- records newly visible controls/options after each selector opens;
- closes opened selector surfaces with Escape;
- probes the visible settings groups for stability, expression, reading speed, pause, and output format;
- records roles, accessible values/ranges, range values, stable attributes, and bounded structural hints when the provider exposes them;
- writes `voice_catalog.json` and `settings_catalog.json`;
- keeps editor/input privacy suppression in place.

## Windows setup

1. Install Python 3.11+ if not already available.
2. Run `CAI_DAT_VA_CHAY.bat` for the one-click setup/test/run path.
3. Or run `SETUP_DISCOVERY.bat` once, then `CHAY_LAI_DISCOVERY.bat` for later passes.

## Local runtime root

Default:

`%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\`

```text
saydivoice/
  browser_profile/       persistent browser session; local only
  logs/                  JSONL run logs
  screenshots/           local screenshots
  reports/               discovery_report_<run-id>.json
  downloads/             reserved for later download discovery
  runs/<run-id>/
    dom_inventory.json
    saydi_map.json
    selectors.json
    voice_catalog.json
    settings_catalog.json
```

Runtime artifacts are local and must not be committed.

## D2 safe-interaction policy

The D2 catalog code contains an explicit whitelist. Current allowed trigger labels are only:

- voice selector: `Tự động`;
- language selector: `VI`;
- pause selector: `Đang tắt`;
- settings tab: `Cài đặt` (reserved/observational).

`Tạo giọng nói`, `Xoá tất cả`, login, download, clone, and other mutating or production actions are not in the D2 trigger whitelist.

If a current provider label changes, the catalog records `TRIGGER_NOT_FOUND` instead of guessing or clicking an arbitrary control.

## Privacy boundary

Structured discovery evidence does not intentionally persist:

- script/editor values;
- passwords;
- text/email/password input values;
- cookies, localStorage, sessionStorage, authorization headers;
- raw HTML;
- URL query strings/fragments;
- obvious bearer/JWT/email secrets.

Numeric range values that are explicitly identified as setting sliders may be recorded because they are provider settings, not user script content.

Screenshots remain local-only and can naturally show whatever is visible on the user's own screen.

## Discovery roadmap

- D0: runner foundation — complete.
- D1: surface/control map — complete and field-accepted.
- D2: voice/settings catalog — **V0.3 code/CI phase**.
- D3: generation lifecycle.
- D4: download behavior.
- D5: limits/error states.
- D6: freeze sanitized discovery contracts for the production Voice Engine.
