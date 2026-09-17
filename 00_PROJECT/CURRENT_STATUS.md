# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery is functionally complete for the authenticated Windows path. D1–D4 generation/download, voice/style controls, reversible preset application, authenticated preflight, and one real `tiktok_energetic` preset generation are field-verified on `MAGASIN-PC`. The next objective is to freeze these verified contracts into a production SaydiVoice provider adapter; no additional live generation is required for ordinary implementation work.**

## Completed

- D0 / Discovery Runner V0.1 completed and merged.
- D1 / Surface Map V0.2 completed and field-verified.
- D2 / Voice + Settings Catalog field evidence accepted:
  - authenticated voice surface exposes real voices, including `Adam — Giọng hot tiktok`;
  - voice catalog discovery found 60 Vietnamese voices across the authenticated selector;
  - the UI exposes a Biểu cảm ↔ Ổn định axis, speed control, pause section, and WAV/MP3/FLAC/OGG formats;
  - no separate provider control for discrete moods such as Happy/Sad/Angry was observed;
  - script/editor values remain excluded from structured evidence.
- Authenticated live-session path completed:
  - PR #9 added the Windows self-hosted GitHub Actions path;
  - PR #10 switched the persistent profile path to installed Google Chrome rather than bundled Playwright Chromium;
  - live run `35216153839` passed on runner `MAGASIN-PC` with `TTS_READY`, `AUTHENTICATED_OR_HIDDEN`, CI gate PASS, and privacy-safe evidence upload;
  - browser profile remains local under `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\browser_profile` and is never uploaded.
- D3 / Controlled Generation completed and merged via PR #11:
  - authenticated one-shot generation succeeds;
  - `POST /api/tts` returns HTTP 200 with `audio/mpeg`;
  - history write returns HTTP 201;
  - generation lifecycle reaches `SUCCESS_SIGNAL`.
- D4 / Controlled Download Discovery completed and merged via PR #12:
  - authenticated Download succeeds;
  - downloaded MP3 metadata/hash can be captured locally;
  - raw audio is excluded from GitHub artifacts.
- Voice/style control layer field-verified:
  - voice selection can be changed and restored;
  - stability/expression and speed sliders can be set by ratio and verified;
  - MP3/WAV/FLAC/OGG selection can be set and verified;
  - pause enable state can be read/set and restored;
  - D5B3 run `35230995883` completed `Adam → alternate voice → Adam` with `roundtrip_pass=true`, no Generate, and no Download.
- Authenticated production preflight field-verified:
  - D6 run `35233725324` passed all required checks for voice, enabled Generate, editor, two sliders, format, and pause controls;
  - active voice was `Adam — Giọng hot tiktok` and active format was MP3.
- Reusable application-level presets implemented:
  - `tiktok_energetic`;
  - `review_natural`;
  - `story_warm`;
  - `news_stable`;
  - `slow_emotional`.
- Preset application roundtrip verified without generation:
  - workflow run `35237679528` completed successfully.
- Real `tiktok_energetic` generation field-verified:
  - run `35241844708` completed successfully on `MAGASIN-PC`;
  - exactly one Generate click and zero Download clicks;
  - voice `Adam — Giọng hot tiktok`;
  - stability/expression ratio observed `0.2975` (target `0.30`);
  - speed ratio observed `0.6485` (target `0.65`);
  - MP3 selected; pause disabled;
  - `POST /api/tts` returned 200 `audio/mpeg`;
  - `POST /api/library/history` returned 201;
  - terminal state `SUCCESS_SIGNAL`.

## Anonymous-provider limitation

Anonymous diagnostics remain historical characterization only:

- `/api/session/start` returned 403 with `Verification failed. Please retry.`;
- `/api/samples` returned 401 with `Invalid or missing credentials.`;
- anonymous voice catalog exposed only `Tự động`;
- V0.4.3 correctly stopped at `PREFLIGHT_BLOCKED` before Generate.

The production path therefore reuses the authenticated persistent Chrome profile.

## Current acceptance baseline

- Self-hosted runner: `MAGASIN-PC`, Windows x64.
- Browser: installed Google Chrome controlled by Playwright.
- Profile: local persistent Saydi profile; never committed or uploaded.
- Session gate: `TTS_READY` + `AUTHENTICATED_OR_HIDDEN`.
- Generation: one-shot, explicit authorization boundary, no automatic retry.
- Download: explicit separate action; raw audio remains local unless intentionally consumed by the downstream pipeline.
- Voice styling: deterministic application-level preset mapped to verified provider controls.

## Not yet completed

- Merge/freeze the current voice preset/control work into `main`.
- Production `SaydiVoiceProvider` adapter with a stable request/result contract.
- Production local audio handoff from provider adapter to media pipeline.
- Session-expiry/re-auth production error path.
- Downstream media pipeline phases.

## Repository visibility risk

The repository is public. Never commit passwords, cookies, browser profiles, auth tokens, private media, generated private audio, or sensitive runtime/session artifacts.

## Current active objective

Open and validate the preset/control integration PR, then implement the production SaydiVoice provider adapter using the field-verified authenticated Chrome contracts. Do not spend another generation unless a later production acceptance test is explicitly authorized.
