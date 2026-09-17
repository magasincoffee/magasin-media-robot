# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery. D0–D2 are complete and field-verified. PR #7 merged D2/V0.3.2 to `main`. D3 Generation Lifecycle V0.4.0 is implemented, CI/package verified on PR #8, and now requires one explicitly authorized real generation on the target Windows laptop.**

## Completed

- D0 / Discovery Runner V0.1: complete and merged.
- D1 / Surface Map V0.2: complete, field-verified, merged.
- D2 / Voice & Settings Catalog V0.3.2: complete, field-verified, merged through PR #7 as `ec7ee7c0b18e488a3bc43361e8e38ca4e88ce54b`.
- Final D2 real run: `20260917_151143_da1bfcc6`.
- D2 final evidence:
  - 32 language options captured;
  - exactly one automatic voice card captured as `Tự động — Hệ thống tự chọn giọng`;
  - voice/language/pause surfaces restored after observation;
  - stability `2.8`, expression `Ổn định`, speed `1.00×`;
  - WAV/MP3/FLAC/OGG captured with MP3 selected;
  - pause values `0.45s`, `0.25s`, `0.3s`, `0.6s` captured without changing them;
  - uploaded structured evidence contains no visible editor phrase;
  - no D2 Generate/download action.
- `BUG-20260917-008` is VERIFIED.
- D3 / V0.4.0 implemented on branch `feat/saydivoice-d3-generation-lifecycle`, PR #8:
  - Generate is gated by explicit `--allow-generate`;
  - D3 runs exactly one fixed short sample in a disposable same-session tab;
  - no audio download is clicked;
  - lifecycle observation records Generate disabled/busy state, audio/result controls, quota text, and new alerts/toasts;
  - alerts already present before Generate are treated as baseline;
  - editor content is never persisted; only fixed-sample length/SHA-256 are stored;
  - writes `generation_lifecycle.json`, `d3_before_generate.png`, and `d3_after_generate.png`;
  - Windows CI run `35199227801`: PASS;
  - packaged V0.4.0 compile: PASS;
  - packaged V0.4.0 pytest: **46 tests PASS**;
  - operator ZIP excludes `.venv`, `browser_profile`, cookie/token/secret files.

## Current live gate

Run V0.4.0 once using `CAI_DAT_VA_CHAY_D3.bat` and explicitly confirm Y. This intentionally may consume **one SaydiVoice generation/quota unit**.

Return from the same run ID:
- `runs\<run-id>\generation_lifecycle.json`
- `runs\<run-id>\d3_before_generate.png`
- `runs\<run-id>\d3_after_generate.png`
- `reports\discovery_report_<run-id>.json`
- `logs\discovery_<run-id>.jsonl`

Acceptance: lifecycle trace accurately identifies processing plus success/error/timeout evidence; no download occurs; D1/D2 privacy remains intact.

## Not yet implemented

- D3 real-provider field verification and merge.
- D4 audio download discovery.
- D5 controlled limits/error characterization.
- D6 frozen discovery contracts.
- Production Voice Engine.
- Media Analyzer, Scene Planner, Subtitle Engine, Render Engine, Desktop UI, diagnostics/resume runtime, installer, full regression.

## Repository visibility risk

GitHub metadata still reports the repository as public. Never commit passwords, cookies, browser profiles, auth tokens, private media, or raw runtime/session artifacts.

## Current active objective

Perform one controlled D3 generation field run; review lifecycle evidence; fix/test if needed; merge PR #8 when accepted; then begin D4 audio-download lifecycle.
