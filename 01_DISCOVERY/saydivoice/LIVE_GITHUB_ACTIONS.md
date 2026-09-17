# SaydiVoice Live Test via GitHub Actions

## Design

Live SaydiVoice tests run on a **Windows self-hosted GitHub Actions runner**. The runner reuses the same local Playwright persistent profile on every run:

`%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\browser_profile`

The profile is intentionally **not** stored in GitHub, Actions artifacts, cache, or repository files. This preserves ADR-004 and avoids uploading cookies/session data. GitHub Actions is the orchestrator; the authenticated browser state remains local on the trusted Windows runner.

This architecture is preferred for SaydiVoice because the anonymous flow has already shown verification/session failures, and a fresh GitHub-hosted runner changes machine/network context on each run.

## One-time operator bootstrap

1. Configure the target Windows laptop as a GitHub **self-hosted runner** for `magasincoffee/magasin-media-robot`.
2. Run the runner interactively with `run.cmd` under the same Windows account that will own the browser profile. Do not install it as a Windows service for the initial browser verification path.
3. In a checkout of this repository, open `01_DISCOVERY\saydivoice` and run `SETUP_LIVE_PROFILE.bat`.
4. Chromium opens. Log in to SaydiVoice manually. Complete Google/OTP/CAPTCHA yourself if requested.
5. When the TTS page is back and the login button is gone, return to the terminal and press Enter.
6. Setup must report `PASS`.

No password, cookie, token, browser profile, or authentication dump is committed.

## GitHub Actions live workflow

Workflow: `.github/workflows/saydi-live.yml`

Use **Actions → SaydiVoice Live Session Check → Run workflow**.

The first workflow is intentionally non-destructive: it does not click Generate or Download. It verifies that the self-hosted runner can reuse the authenticated local profile and that the Saydi TTS surface/catalog can be observed from GitHub Actions.

After this session check passes, D3 controlled generation can be enabled in a bounded follow-up change. D4 audio-download characterization remains after D3 passes.

## Evidence

The workflow uploads only the latest run evidence/report/log. It never uploads `browser_profile`.

The live session gate currently requires:

- `TTS_READY`;
- `AUTHENTICATED_OR_HIDDEN`.
