# SaydiVoice Discovery

This workstream learns the real behavior of SaydiVoice Studio before production browser automation is frozen.

Target: `https://voice.saydi.ai/vi/studio/tts/`

## V0.1 status

V0.1 implements a **non-destructive discovery runner**. It opens a visible Playwright Chromium window with a persistent local browser profile, classifies the current page/login state, captures a local screenshot, writes a sanitized interactive-control inventory, and exports a structured discovery report.

It intentionally does **not** generate or download audio yet. Those actions belong to later discovery stages after the surface map is verified.

## Windows setup

1. Install Python 3.11+ if it is not already available.
2. Run `SETUP_DISCOVERY.bat` once.
3. Run `RUN_DISCOVERY.bat`.

`SETUP_DISCOVERY.bat` creates a local `.venv`, installs pinned dependencies, installs Playwright Chromium, installs the discovery package, and runs unit tests before declaring setup complete.

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
    dom_inventory.json   sanitized visible interactive controls
```

Runtime artifacts are local and must not be committed.

## V0.1 privacy boundary

The runner does not intentionally persist:

- passwords or input values;
- raw cookies;
- localStorage/sessionStorage;
- authorization headers;
- raw HTML;
- URL query strings/fragments;
- obvious bearer/JWT/email values in structured evidence/log messages.

Screenshots can naturally contain whatever is visible on the user's own screen, so they remain local-only.

## Page states / exit codes

- `TTS_READY` / exit `0`: TTS editor surface recognized and evidence captured.
- `LOGIN_REQUIRED` / exit `10`: a manual login appears required.
- `ACCESS_BLOCKED` / exit `20`: CAPTCHA/access challenge detected.
- `UNKNOWN` / exit `30`: page captured but V0.1 does not yet recognize it.
- `BROWSER_ERROR` / exit `40`: browser/navigation/discovery failure.

A login-required state is expected during first use. The runner never enters credentials automatically.

## Discovery roadmap

- D0: runner foundation — **V0.1**.
- D1: surface/control map.
- D2: voice/settings catalog.
- D3: generation lifecycle.
- D4: download behavior.
- D5: limits/error states.
- D6: freeze sanitized discovery artifacts for the production Voice Engine.
