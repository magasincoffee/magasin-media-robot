# Next Step

## Immediate next step — authenticated Saydi live session through GitHub Actions

Anonymous Saydi testing is no longer useful as the primary path. The latest controlled diagnostics established a repeatable session-bootstrap block before generation:

- `/api/session/start` returns 403 with `Verification failed. Please retry.`;
- `/api/samples` returns 401 with `Invalid or missing credentials.`;
- the anonymous voice catalog exposes only `Tự động`;
- V0.4.3 correctly stops at `PREFLIGHT_BLOCKED` before Generate.

The next bounded step is therefore to reuse one authenticated persistent browser profile on a Windows self-hosted GitHub Actions runner.

## Operator sequence

1. Configure the target Windows laptop as a self-hosted runner for `magasincoffee/magasin-media-robot`.
2. Start the runner interactively with `run.cmd` under the Windows account that will own the browser profile.
3. Check out PR #9 / branch `feat/saydi-github-live-profile` on that machine.
4. Run `01_DISCOVERY\saydivoice\SETUP_LIVE_PROFILE.bat` once.
5. Chromium opens. Log in to SaydiVoice manually; complete Google/OTP/CAPTCHA yourself if requested.
6. Return to the terminal and press Enter only after the TTS page is back and the login control is gone.
7. Setup must report `PASS`.
8. In GitHub, run **Actions → SaydiVoice Live Session Check → Run workflow**.
9. Do not upload or commit the browser profile.

## Live-session acceptance gate

The first workflow is deliberately non-destructive and must pass before any GitHub Action is allowed to click Generate:

- `TTS_READY`;
- `AUTHENTICATED_OR_HIDDEN`;
- D1/D2 observation completes;
- no provider login/session failure is surfaced;
- no Generate/download occurs;
- only latest privacy-safe evidence/report/log is uploaded.

## After the session gate passes

1. Synchronize/enable the controlled D3 V0.4.x lifecycle implementation in the repository.
2. Run exactly one authorized D3 generation on the same persistent authenticated profile.
3. Require a real success signal before proceeding.
4. Implement D4 result/download metadata capture only after D3 passes.

The operator should not need to download a new diagnostic ZIP for every iteration once the self-hosted GitHub Actions path is active.
