# Next Step

## Immediate next step — observe one read-only production backend smoke, then merge Voice Engine

Phase 0 SaydiVoice discovery and the reusable voice/style preset layer are complete. The production `02_VOICE_ENGINE` adapter and the supervisor status/heartbeat layer are implemented and pass hosted CI. The remaining gate before merge is a **read-only** authenticated preflight using the production backend on `MAGASIN-PC`.

## Production adapter already implemented

- Provider-neutral `VoiceRequest` / `VoiceResult` contract.
- Frozen style presets: `tiktok_energetic`, `review_natural`, `story_warm`, `news_stable`, `slow_emotional`.
- Explicit `allow_generate` and `allow_download` gates.
- One-attempt Generate policy; no implicit browser retry.
- Failure classification: `fix_input`, `re_auth`, `retry`, `do_not_retry`.
- Installed-Chrome + local persistent-profile backend.
- Voice, stability/expression, speed, pause-enable and output-format application.
- Bounded generation terminal-state handling.
- Local Download handoff with non-overwriting output path, byte count and SHA-256.
- Local supervisor status file + self-refreshing HTML dashboard.
- Statuses: `IDLE`, `RUNNING`, `WAIT_USER`, `RETRYING`, `FAILED`, `DONE`.
- 30-second active heartbeat with 90-second stale detection.
- GitHub-hosted Windows CI: run `35304115327`, **22 tests PASS**.
- Ordinary CI verifies no authenticated Saydi profile is present and therefore cannot perform live side effects.

## Operator dashboard

The local state is:

```text
%LOCALAPPDATA%\MAGASIN\MediaRobot\saydi\supervisor_state.json
```

The dashboard is:

```text
%LOCALAPPDATA%\MAGASIN\MediaRobot\saydi\saydi_status.html
```

The self-hosted status smoke workflow also creates a desktop `SAYDI CONTROL` shortcut when it runs successfully.

The dashboard intentionally stores no prompt text, cookies, auth tokens, provider response bodies, or generated audio.

## Current live-smoke gate

Run the production backend `preflight()` only:

1. publish `RUNNING` to the supervisor dashboard;
2. open the existing local authenticated Chrome profile;
3. confirm TTS editor and enabled Generate control are present;
4. classify authentication/session;
5. read current voice/format;
6. publish `DONE`, `WAIT_USER`, or `FAILED`;
7. close Chrome.

This workflow contains **no setting mutation, no Generate, and no Download**.

The first historical smoke attempt found a Windows stdout encoding defect. That was fixed by forcing UTF-8/ASCII-safe log output. A later self-hosted attempt ended abnormally before a complete job log was retained. The new supervisor layer is specifically intended to make the next run's progress visible locally rather than leaving the operator to infer whether the robot is still working.

## After the read-only smoke passes

1. Confirm `DONE` in `SAYDI CONTROL`.
2. Remove or disable the temporary branch-only live-preflight workflow from the merge diff.
3. Refresh the production Voice Engine PR.
4. Require offline PR CI PASS.
5. Merge `02_VOICE_ENGINE` to `main`.
6. Only then consider one final end-to-end production Generate + Download acceptance test, under new explicit authorization.
7. Hand the resulting local audio path into the deterministic media pipeline.

No new Generate or Download is authorized by this plan.
