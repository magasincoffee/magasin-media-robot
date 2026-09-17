# Changelog

## 2026-09-17 — SaydiVoice authenticated live-session GitHub Actions path

### Added

- Windows self-hosted GitHub Actions workflow for non-destructive Saydi live-session checks.
- One-time `SETUP_LIVE_PROFILE.bat` bootstrap for a persistent local Playwright profile.
- `profile_setup.py` interactive login verifier that keeps credentials out of code/logs.
- `ci_gate.py` acceptance gate requiring `TTS_READY` and `AUTHENTICATED_OR_HIDDEN` before controlled D3 enablement.
- Privacy-safe latest evidence staging/upload that explicitly excludes `browser_profile`.
- Operator documentation for the self-hosted runner/profile workflow.

### Decision

- Real-provider authenticated Saydi checks use a trusted Windows self-hosted runner so the browser profile remains local while GitHub Actions orchestrates execution.
- Fresh GitHub-hosted runners are not used for the authenticated profile because anonymous session verification has already failed and session continuity is required.

### D3 diagnostic findings

- Anonymous `/api/session/start` observed at 403 with `Verification failed. Please retry.`.
- Anonymous `/api/samples` observed at 401 with `Invalid or missing credentials.`.
- V0.4.3 preflight stops at `PREFLIGHT_BLOCKED` with zero generation attempts when that session block is present.
- Repeated operator ZIP download/upload loops are being replaced by the self-hosted Actions path.

## 2026-09-17 — SaydiVoice Discovery Runner V0.1

### Added

- Python package for non-destructive SaydiVoice discovery.
- Visible Playwright Chromium runner using a persistent local browser profile.
- Safe local runtime under `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice` with logs, screenshots, reports, downloads, per-run evidence, and browser profile separated from Git.
- Page-state classification for `TTS_READY`, `LOGIN_REQUIRED`, `ACCESS_BLOCKED`, and `UNKNOWN`.
- Sanitized interactive DOM inventory without input values, raw HTML, cookies, storage, or authorization headers.
- Structured JSON discovery reports and JSONL logs.
- URL/query, bearer/JWT, and email redaction safeguards.
- Manual-login observation window so first-use authentication can populate the persistent local profile without automated credential entry.
- Explicit CLI exit codes and Windows setup/run scripts.
- Windows GitHub Actions unit-test workflow.
- Unit/orchestration regression suite (16 local tests passing; Windows CI passing at run `35130561175`).

### Fixed during self-test

- Prevented editor text from entering discovery inventory.
- Corrected setup so the local package itself is installed.
- Sanitized error logging before persistence.
- Guaranteed Playwright/context cleanup after navigation/probe failures.
- Kept the browser open long enough for manual first-use login and re-probed afterward.

### Verification limitation

The implementation sandbox blocks Chromium navigation by administrator policy, so the first real browser smoke against SaydiVoice must run on the target Windows laptop before D0 is considered field-verified.

## 2026-09-17 — Project initialization

### Added

- Root project README and continuation contract.
- Project vision.
- System architecture.
- Phased roadmap.
- Development/session protocol.
- QA strategy.
- Current status and next-step records.
- SaydiVoice Discovery designated as Phase 0.

### Notes

This initialization established the durable project memory and execution discipline before coding began.
