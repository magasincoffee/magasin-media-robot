# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery. D1–D4 are now field-verified on the authenticated Windows self-hosted runner path. The anonymous Saydi flow remains blocked by provider verification/authentication, but the persistent authenticated Chrome profile on `MAGASIN-PC` is stable and reusable through GitHub Actions. The next discovery phase is D5 controlled limits/error characterization, followed by D6 contract freeze.**

## Completed

- D0 / Discovery Runner V0.1 completed and merged.
- D1 / Surface Map V0.2 completed and field-verified.
- D2 / Voice + Settings Catalog field evidence accepted:
  - language catalog captures visible language choices;
  - authenticated voice surface exposes real voices, including `Adam — Giọng hot tiktok`;
  - stability `2.8`, expression `Ổn định`, speed `1.00×`, pause `Đang tắt`, MP3 + WAV/MP3/FLAC/OGG remain captured;
  - pause panel is observed non-destructively and restored;
  - script/editor values remain excluded from structured evidence.
- Authenticated live-session path completed:
  - PR #9 added the Windows self-hosted GitHub Actions path;
  - PR #10 switched the persistent profile path to installed Google Chrome rather than bundled Playwright Chromium;
  - live run `35216153839` passed on runner `MAGASIN-PC` with `TTS_READY`, `AUTHENTICATED_OR_HIDDEN`, CI gate PASS, and privacy-safe evidence upload;
  - browser profile remains local under `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\browser_profile` and is never uploaded.
- D3 / Controlled Generation completed and merged via PR #11:
  - live one-shot run `35219033748` used the authenticated persistent profile;
  - exactly one Generate attempt, no reload retry, no Download click;
  - processing state was observed (`Hủy` appeared while Generate disappeared);
  - `POST /api/tts` returned HTTP 200 with `audio/mpeg`;
  - result control `Tải về` appeared;
  - history write returned HTTP 201;
  - generation lifecycle terminal state was `SUCCESS_SIGNAL` with no provider HTTP error.
- D4 / Controlled Download Discovery completed and merged via PR #12:
  - live one-shot run `35219638775` completed successfully;
  - exactly one generation and one Download action;
  - downloaded file metadata: `.mp3`, 11,853 bytes;
  - SHA-256: `f0dd8145d6d55a70ebb46ab032d7805741f81d64e1ac06b4b9a08008f1928be4`;
  - suggested filename: `saydivoice_Toi-Bach_Adam-—-Giọng-hot-tiktok_20260917-191155.mp3`;
  - audio was hashed/measured locally and deleted before artifact staging;
  - uploaded D4 artifact contains metadata/screenshots only, with no retained audio/binary payload.

## Anonymous-provider limitation

Anonymous diagnostics remain useful only as historical characterization:

- `/api/session/start` returned 403 with `Verification failed. Please retry.`;
- `/api/samples` returned 401 with `Invalid or missing credentials.`;
- anonymous voice catalog exposed only `Tự động`;
- V0.4.3 correctly stopped at `PREFLIGHT_BLOCKED` before Generate.

The production/discovery path should therefore reuse the authenticated persistent Chrome profile rather than depend on anonymous session bootstrap.

## Current acceptance baseline

- Self-hosted runner: `MAGASIN-PC`, Windows x64.
- Browser: installed Google Chrome controlled by Playwright.
- Profile: local persistent Saydi profile; never committed or uploaded.
- D1/D2: read-only discovery accepted.
- D3: authenticated generation success accepted.
- D4: download event/metadata success accepted; raw downloaded audio excluded from GitHub artifacts.

## Not yet completed

- D5 controlled limits/error characterization.
- D6 frozen discovery contracts.
- Production Voice Engine/provider adapter based on the frozen contracts.
- Downstream media pipeline phases.

## Repository visibility risk

The repository is public. Never commit passwords, cookies, browser profiles, auth tokens, private media, generated private audio, or sensitive runtime/session artifacts.

## Current active objective

Design and execute a bounded D5 plan that characterizes provider limits/errors without abusive load or unnecessary quota consumption. Preserve the validated authenticated Chrome/profile path and do not re-open anonymous verification work unless the provider behavior materially changes.
