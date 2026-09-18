# Next Step

## Immediate next step — read-only production backend smoke, then merge Voice Engine

Phase 0 SaydiVoice discovery and the reusable voice/style preset layer are complete. The first production `02_VOICE_ENGINE` adapter is now implemented and passes offline CI. The remaining gate before merge is a **read-only** authenticated preflight using the production backend on `MAGASIN-PC`.

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
- GitHub-hosted Windows CI: run `35243425623`, **15 tests PASS**.
- Ordinary CI verifies no authenticated Saydi profile is present and therefore cannot perform live side effects.

## Current live-smoke gate

Run the production backend `preflight()` only:

1. open the existing local authenticated Chrome profile;
2. confirm TTS editor and enabled Generate control are present;
3. classify authentication/session;
4. read current voice/format;
5. close Chrome.

This workflow contains **no setting mutation, no Generate, and no Download**.

The first smoke attempt found only a Windows stdout encoding defect. That was fixed by forcing UTF-8/ASCII-safe log output. The next self-hosted attempt ended abnormally before a complete job log was retained, so this gate remains pending.

## After the read-only smoke passes

1. Remove or disable the temporary branch-only live-preflight workflow from the merge diff.
2. Open/refresh the production Voice Engine PR.
3. Require offline PR CI PASS.
4. Merge `02_VOICE_ENGINE` to `main`.
5. Only then consider one final end-to-end production Generate + Download acceptance test, under new explicit authorization.
6. Hand the resulting local audio path into the deterministic media pipeline.

No new Generate or Download is authorized by this plan.
