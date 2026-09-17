# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery. D1 and D2 are field-verified. D3 is blocked specifically by anonymous Saydi session verification, not by selector/editor automation. A self-hosted GitHub Actions live-session path is being added so the authenticated persistent browser profile can be reused without repeated operator package downloads.**

## Completed

- D0 / Discovery Runner V0.1 completed and merged.
- D1 / Surface Map V0.2 completed and field-verified.
- D2 / Voice + Settings Catalog field evidence is accepted:
  - language catalog captures visible language choices;
  - current voice surface resolves `Tự động — Hệ thống tự chọn giọng` instead of modal navigation tabs;
  - stability `2.8`, expression `Ổn định`, speed `1.00×`, pause `Đang tắt`, MP3 + WAV/MP3/FLAC/OGG remain captured;
  - pause panel is observed non-destructively and restored;
  - script/editor values remain excluded from structured evidence.
- Controlled D3 diagnostics were advanced through operator checkpoint V0.4.3:
  - V0.4.2 network diagnostics showed `/api/session/start` 403, `/api/samples` 401 and `/api/gpu/eta` 401 in the anonymous session;
  - V0.4.3 captured safe provider error details: `/api/session/start` → `Verification failed. Please retry.` and `/api/samples` → `Invalid or missing credentials.`;
  - V0.4.3 stopped at `PREFLIGHT_BLOCKED` with `attempt_count: 0`, so no Generate click and no quota consumption occurred.
- Independent browser testing reproduced the same anonymous limitation: voice catalog only exposed `Tự động`, and anonymous generation failed.
- Branch `feat/saydi-github-live-profile`, PR #9, adds:
  - a one-time interactive local profile bootstrap;
  - a Windows self-hosted GitHub Actions live session workflow;
  - an authenticated-session CI gate;
  - privacy-safe latest evidence upload only;
  - no browser-profile upload to GitHub.

## Current live gate

The next provider test must use an authenticated persistent Saydi profile on the same Windows machine/network context used by the self-hosted runner.

Acceptance for the live session gate:

- page state `TTS_READY`;
- auth state `AUTHENTICATED_OR_HIDDEN`;
- voice/settings observation completes without login/session errors;
- no Generate or Download action occurs in the first live-session workflow;
- `browser_profile` remains local and is never uploaded.

## Repository synchronization note

`main` currently contains the V0.3.2 discovery source. The later V0.4.x D3 diagnostic checkpoints were field-run as operator packages during this session. The GitHub live-session infrastructure is being merged first; once authenticated session reuse is proven, the controlled D3 lifecycle implementation will be synchronized/enabled in the repository as the next bounded change.

## Not yet completed

- Authenticated self-hosted live session verification.
- Repository sync/enablement of controlled D3 generation lifecycle on the authenticated profile.
- D3 successful generation observation.
- D4 audio/result download discovery.
- D5 controlled limits/error characterization.
- D6 frozen discovery contracts.
- Production Voice Engine and downstream media pipeline phases.

## Repository visibility risk

The repository is public. Never commit passwords, cookies, browser profiles, auth tokens, private media, generated private audio, or sensitive runtime/session artifacts.

## Current active objective

Finish PR #9 CI, bootstrap the authenticated local Saydi profile once on the Windows self-hosted runner, pass the non-destructive GitHub Actions live session check, then enable controlled D3 on that same profile.
