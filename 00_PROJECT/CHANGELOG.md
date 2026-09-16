# Changelog

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
