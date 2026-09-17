# Changelog

## 2026-09-17 — SaydiVoice Discovery V0.3 / D2 Voice-Settings Catalog

### Added

- Non-destructive D2 catalog module.
- Explicit safe-trigger whitelist for Voice (`Tự động`), Language (`VI`), Pause (`Đang tắt`), with Settings reserved for observation.
- Menu/surface capture that snapshots newly visible controls and closes with Escape.
- Voice catalog output: `voice_catalog.json`.
- Settings catalog output: `settings_catalog.json`.
- Settings-context probing for stability, expression, reading speed, pause, and file format.
- Capture of accessible roles, selection state, range values, and bounded structural hints where exposed.
- D2 report paths and summary fields.
- V0.3 CLI/Windows one-click handoff.
- D2 privacy, safe-trigger, option-diff, dedupe, settings, and runner-orchestration tests.

### Safety

- Generate, download, delete, login, clone, and other mutating/production actions are absent from the D2 trigger whitelist.
- Unknown trigger kinds fail before browser interaction.
- Editor/text input values remain suppressed from structured evidence.

### Verification

- Local compile PASS.
- 37 tests PASS.
- Version import PASS (`0.3.0`).
- Windows Actions run `35185941236`: PASS.
- Operator ZIP built: `MAGASIN_SAYDIVOICE_DISCOVERY_V0.3.zip`.

## 2026-09-17 — SaydiVoice Discovery V0.2 / D1 Surface Map

### Added

- Authentication state separated from page readiness.
- Semantic `saydi_map.json`.
- Ranked `selectors.json` locator candidates.
- D1 Windows operator helpers and packaging.

### Fixed

- Contenteditable script text leak (`BUG-20260917-006`).
- Login explanatory copy vs History semantic collision (`BUG-20260917-007`).

### Field verification

- Real run `20260917_110310_7bf1810a`: PASS.
- `TTS_READY` / `ANONYMOUS` / `CAPTURED`.
- Privacy fix verified live.
- D1 accepted and merged through PR #2 as `51869ab54dac1e5f0202455cf1f9b40f48dde0b0`.

## 2026-09-17 — SaydiVoice Discovery Runner V0.1

### Added

- Python package for non-destructive SaydiVoice discovery.
- Visible Playwright Chromium runner using a persistent local browser profile.
- Safe local runtime under `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice`.
- Page-state classification for `TTS_READY`, `LOGIN_REQUIRED`, `ACCESS_BLOCKED`, and `UNKNOWN`.
- Sanitized interactive DOM inventory.
- Structured JSON discovery reports and JSONL logs.
- URL/query, bearer/JWT, and email redaction safeguards.
- Manual-login observation window.
- Explicit CLI exit codes and Windows setup/run scripts.
- Windows GitHub Actions unit-test workflow.

### Verification

- 16 local tests PASS.
- PR and post-merge Windows CI PASS.
- First real Windows run `20260917_011521_dcb358a9`: functional PASS; artifact review exposed the contenteditable privacy bug later fixed in V0.2.

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
