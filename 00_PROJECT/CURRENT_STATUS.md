# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery D0–D6 is complete. Contract v1 is frozen and CI-verified. The next phase is `02_VOICE_ENGINE`: a provider-neutral production voice interface with SaydiVoice behind a Playwright adapter.**

## Completed

- D0 / Discovery Runner completed.
- D1 / Surface Map field-verified.
- D2 / Voice + Settings Catalog field-verified on the authenticated profile.
- Authenticated live-session path verified on `MAGASIN-PC` using installed Google Chrome and the local persistent profile.
- D3 / Controlled Generation field-verified:
  - run `35219033748`;
  - exactly one Generate attempt;
  - processing state observed;
  - `POST /api/tts` returned HTTP 200 `audio/mpeg`;
  - `Tải về` appeared;
  - history write returned HTTP 201;
  - terminal state `SUCCESS_SIGNAL`;
  - no Download click in D3.
- D4 / Controlled Download field-verified:
  - run `35219638775`;
  - one controlled Download after successful generation;
  - MP3 measured/hashed locally and deleted before artifact staging;
  - no raw audio retained in GitHub artifacts.
- D5 / Controlled limits and reversible controls field-verified without unnecessary provider calls:
  - authenticated Vietnamese voice catalog observed at 60 voices;
  - voice roundtrip `Adam — Giọng hot tiktok` → `THEANH28 - Nữ` → Adam passed in run `35230995883`;
  - shared Biểu cảm ↔ Ổn định slider, speed and file format changes were verified reversible;
  - no independent mood/emotion selector was observed;
  - input limit characterized in run `35231771503`: 0 blocked, 1 accepted, 20,000 accepted, target 20,001 clamped to 20,000;
  - D5C emitted `0` `/api/tts` requests.
- D6 / Discovery Contract Freeze completed:
  - contract: `01_DISCOVERY/saydivoice/contracts/saydivoice_contract_v1.json`;
  - narrative freeze: `01_DISCOVERY/saydivoice/D6_CONTRACT_FREEZE.md`;
  - frozen session, locator, controls, input, generation, download, error, retry and privacy contracts;
  - six contract regression tests added;
  - Discovery Tests run `35232777609`: PASS after aligning stale D4 tests with the current download-only implementation.

## Production baseline

- Runner for authenticated browser integration: `MAGASIN-PC`, Windows x64.
- Browser: installed Google Chrome controlled by Playwright.
- Profile: `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\browser_profile`; local only, never committed/uploaded.
- Saydi input contract: 1–20,000 characters per provider request.
- Generate: explicit authorization; one attempt by default; bounded lifecycle observation; no blind retry.
- Download: separate explicit authorization after a success signal; at most one new controlled download.
- Raw generated audio and private editor text stay out of GitHub artifacts.

## Anonymous-provider limitation

Anonymous diagnostics remain historical characterization only:

- `/api/session/start` returned 403 with `Verification failed. Please retry.`;
- `/api/samples` returned 401 with `Invalid or missing credentials.`;
- anonymous voice catalog exposed only `Tự động`.

Production automation must reuse the authenticated persistent Chrome profile rather than depend on anonymous session bootstrap.

## Repository visibility risk

The repository is public. Never commit or upload passwords, cookies, browser profiles, auth tokens, private editor text, private media, raw generated audio, or sensitive runtime/session payloads.

## Current active objective

Start `02_VOICE_ENGINE` with a provider-neutral domain/API layer that consumes the frozen Saydi contract. Keep browser-specific details behind the Saydi adapter and preserve all D6 safety/privacy invariants.
