# Current Status

Last updated: 2026-09-18

## Overall state

**Phase 0 — SaydiVoice Discovery is functionally complete for the authenticated Windows path. The production Voice Engine is implemented on `feat/saydi-production-provider`, and Saydi now has a local supervisor status/heartbeat layer so operator-visible state no longer depends on the ChatGPT conversation remaining open. The remaining production gate is still one read-only authenticated backend preflight on `MAGASIN-PC`; no additional live generation is required for ordinary implementation work.**

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

## Supervisor status + heartbeat

- PR #20 was merged into the active production-provider branch.
- Local state is written to `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydi\supervisor_state.json`.
- Local dashboard is rendered to `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydi\saydi_status.html`.
- Status vocabulary is frozen as `IDLE`, `RUNNING`, `WAIT_USER`, `RETRYING`, `FAILED`, and `DONE`.
- Active provider jobs emit a 30-second heartbeat; the dashboard marks an active heartbeat stale after 90 seconds.
- Provider progress now publishes step-level state for request validation, preflight, settings, Generate, Download, completion, and user-required states.
- Retryable provider failures remain `WAIT_USER` because Generate is never retried automatically; `RETRYING` is reserved for an explicit outer-supervisor retry.
- Status storage excludes request text, cookies, auth tokens, provider bodies, and generated audio.
- A self-hosted status-only smoke workflow can create a desktop `SAYDI CONTROL` shortcut without contacting Saydi.
- The production read-only live-preflight workflow now publishes its own state into the same dashboard.

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
- Operator state: local JSON + self-refreshing HTML dashboard with heartbeat.

## Phase 1 implementation progress

- Voice preset/control work is merged into `main` via PR #16.
- Production `02_VOICE_ENGINE` package is implemented on `feat/saydi-production-provider` with:
  - provider-neutral request/result models;
  - normalized failure dispositions (`fix_input`, `re_auth`, `retry`, `do_not_retry`);
  - explicit Generate/Download authorization gates;
  - no automatic Generate retry;
  - `SaydiPlaywrightBackend` using installed Chrome and the local authenticated profile;
  - local download metadata (`path`, byte count, SHA-256);
  - five frozen application-level style presets;
  - supervisor state, heartbeat, and local dashboard.
- Latest hosted Voice Engine CI run `35304115327`: PASS, **22 tests**.
- Hosted CI verified it has no authenticated Saydi profile, so ordinary unit CI cannot perform live provider side effects.
- Production backend read-only live preflight remains the final smoke gate. It now reports `RUNNING` / `WAIT_USER` / `FAILED` / `DONE` into the local supervisor dashboard and still contains no Generate or Download authorization.

## Not yet completed

- Confirm one read-only production-backend preflight on `MAGASIN-PC`.
- Remove or disable the temporary branch-only live-preflight workflow after that gate.
- Merge the production Voice Engine PR after the smoke gate and PR CI pass.
- Final production Generate/Download acceptance test, only with separate explicit authorization.
- Production local audio handoff from provider adapter to media pipeline.
- Downstream media pipeline phases.

## Repository visibility risk

The repository is public. Never commit passwords, cookies, browser profiles, auth tokens, private media, generated private audio, or sensitive runtime/session artifacts.

## Current active objective

Use the local `SAYDI CONTROL` dashboard to observe the next read-only production `SaydiPlaywrightBackend` preflight on `MAGASIN-PC`. Confirm the smoke result, then remove the temporary preflight workflow and merge the provider adapter. Do not Generate or Download during this gate, and do not spend another generation unless a later production acceptance test is explicitly authorized.
