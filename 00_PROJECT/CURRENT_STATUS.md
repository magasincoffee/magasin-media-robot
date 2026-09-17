# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery is field-verified through D5. D6 contract freeze is the active branch gate. The authenticated Windows self-hosted runner path is the production/discovery baseline; anonymous Saydi bootstrap remains unsupported for production.**

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

## Anonymous-provider limitation

Anonymous diagnostics remain historical characterization only:

- `/api/session/start` returned 403 with `Verification failed. Please retry.`;
- `/api/samples` returned 401 with `Invalid or missing credentials.`;
- anonymous voice catalog exposed only `Tự động`.

Production/discovery automation must reuse the authenticated persistent Chrome profile rather than depend on anonymous session bootstrap.

## D6 contract freeze

Branch `d6/contract-freeze-20260917` freezes:

- session/auth requirements;
- locator priority and high-value selectors;
- voice/settings semantics;
- 20,000-character input boundary;
- controlled generation lifecycle and retry policy;
- download lifecycle;
- error classification;
- privacy and artifact boundaries.

Machine-readable contract: `01_DISCOVERY/saydivoice/contracts/saydivoice_contract_v1.json`.

## Repository visibility risk

The repository is public. Never commit or upload passwords, cookies, browser profiles, auth tokens, private editor text, private media, raw generated audio, or sensitive runtime/session payloads.

## Current active objective

Pass D6 contract tests, then build the production SaydiVoice provider adapter against contract v1. Any material Saydi DOM/lifecycle/auth/limit change must increment the contract and trigger only the minimum bounded rediscovery needed for the changed section.
