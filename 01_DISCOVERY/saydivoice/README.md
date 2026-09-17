# SaydiVoice Discovery

This workstream learns the real behavior of SaydiVoice Studio before production browser automation is frozen.

Target: `https://voice.saydi.ai/vi/studio/tts/`

## Current status — V0.2 / D1

V0.1 established the non-destructive discovery runner and passed its first real Windows field run. The field evidence showed that the TTS editor can be ready while login controls are still visible, so **page readiness and authentication state are now tracked separately**.

V0.2 adds the first D1 surface map. It still does **not** generate or download audio.

V0.2:

- opens a visible Playwright Chromium window with the persistent local profile;
- classifies page state (`TTS_READY`, login required, blocked, unknown);
- classifies auth surface (`ANONYMOUS`, `AUTHENTICATED_OR_HIDDEN`, `UNKNOWN`) without claiming account identity;
- captures a local screenshot;
- writes a sanitized interactive-control inventory;
- suppresses all input/contenteditable editor text from structured evidence;
- generates `saydi_map.json` with semantic control keys;
- generates `selectors.json` with ranked locator candidates;
- exports a structured discovery report and JSONL logs.

## Windows setup

1. Install Python 3.11+ if it is not already available.
2. Run `SETUP_DISCOVERY.bat` once.
3. Run `RUN_DISCOVERY.bat`.

`SETUP_DISCOVERY.bat` creates a local `.venv`, installs pinned dependencies, installs Playwright Chromium, installs the discovery package, and runs unit tests before declaring setup complete.

If the package has already been set up from V0.1 and the project files are replaced by V0.2, run `SETUP_DISCOVERY.bat` again so the editable package/test environment is refreshed before the next discovery pass.

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
    saydi_map.json       D1 semantic surface map
    selectors.json       ranked locator candidates
```

Runtime artifacts are local and must not be committed.

## Privacy boundary

The runner does not intentionally persist:

- passwords or input/editor values;
- raw cookies;
- localStorage/sessionStorage;
- authorization headers;
- raw HTML;
- URL query strings/fragments;
- obvious bearer/JWT/email values in structured evidence/log messages.

Screenshots can naturally contain whatever is visible on the user's own screen, so they remain local-only.

The first real V0.1 artifact exposed one privacy bug: a contenteditable editor `div` was treated as ordinary text and its script text entered the DOM inventory. That exact script is not reproduced in Git. V0.2 fixes the root cause and adds a regression test.

## Page states / exit codes

- `TTS_READY` / exit `0`: TTS editor surface recognized and evidence captured.
- `LOGIN_REQUIRED` / exit `10`: the current page is a login surface rather than a usable TTS editor.
- `ACCESS_BLOCKED` / exit `20`: CAPTCHA/access challenge detected.
- `UNKNOWN` / exit `30`: page captured but not recognized.
- `BROWSER_ERROR` / exit `40`: browser/navigation/discovery failure.

A login button can be visible while the editor is still usable anonymously. That is recorded as `TTS_READY` + `ANONYMOUS`, not `LOGIN_REQUIRED`.

## Locator policy

D1 ranks locator candidates in this order where available:

1. stable provider test IDs;
2. role + accessible name;
3. aria-label / placeholder;
4. narrow CSS fallback;
5. exact visible text fallback.

Selectors are never derived from the user's script/editor text.

## Discovery roadmap

- D0: runner foundation — **V0.1 complete / field-verified for opening and capture**.
- D1: surface/control map — **V0.2 in verification**.
- D2: voice/settings catalog.
- D3: generation lifecycle.
- D4: download behavior.
- D5: limits/error states.
- D6: freeze sanitized discovery artifacts for the production Voice Engine.
