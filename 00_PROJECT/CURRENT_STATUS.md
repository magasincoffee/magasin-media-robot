# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery. D0–D2 are complete and field-verified. D3 V0.4.0 completed its first real controlled generation attempt and captured a provider reload-page error. V0.4.1 recovery is implemented, Windows CI/package verified, and now needs one operator-authorized real-provider recovery run before D3 can merge.**

## Completed

- D0 / Discovery Runner V0.1: complete and merged.
- D1 / Surface Map V0.2: complete, field-verified, merged.
- D2 / Voice & Settings Catalog V0.3.2: complete, field-verified, merged through PR #7 as `ec7ee7c0b18e488a3bc43361e8e38ca4e88ce54b`.
- `BUG-20260917-008`: VERIFIED.
- D3 branch: `feat/saydivoice-d3-generation-lifecycle`, PR #8.
- First real D3 V0.4.0 run: `20260917_153149_2bb6c109`.
- V0.4.0 real lifecycle evidence:
  - fixed sample length 52; only length/SHA-256 persisted;
  - Generate available at start;
  - after click, Generate disappeared and `Hủy` appeared, showing a real processing phase;
  - provider then returned `Không tải được giọng. Vui lòng tải lại trang.`;
  - terminal state: ERROR;
  - quota 3 → 3;
  - audio elements 5 → 5;
  - no new result/download control;
  - `download_clicked: false`;
  - D1/D2 structured privacy remained intact.
- `BUG-20260917-009` recorded because successful generation is not yet characterized and V0.4.0 missed the `Hủy` processing signal.
- V0.4.1 corrective implementation:
  - detects `Hủy/Cancel` and Generate disappearance as processing;
  - waits best-effort for network-idle before each attempt;
  - adds explicit `--retry-after-reload-error` authorization;
  - permits exactly one reload + retry only when attempt 1 explicitly asks to reload;
  - D3 BAT warns the operator that at most two generation attempts may occur;
  - writes per-attempt traces and screenshots;
  - still never downloads audio and never persists editor text.
- V0.4.1 Windows Actions run `35201169611`: PASS.
- V0.4.1 operator artifact generated.
- Extracted operator ZIP compile: PASS.
- Extracted operator ZIP pytest: **48 tests PASS**.

## Current live gate

Run V0.4.1 once using `CAI_DAT_VA_CHAY_D3.bat` and confirm Y. This may use **up to two SaydiVoice generation attempts**; the second attempt occurs only after the exact reload-page error pattern.

Return from the same run ID:
- `runs\<run-id>\generation_lifecycle.json`
- all `runs\<run-id>\d3_attempt*_before.png`
- all `runs\<run-id>\d3_attempt*_after.png`
- `runs\<run-id>\d3_before_generate.png`
- `runs\<run-id>\d3_after_generate.png`
- `reports\discovery_report_<run-id>.json`
- `logs\discovery_<run-id>.jsonl`

D3 acceptance: processing is correctly recorded; either a success signal is observed after reload recovery, or a repeated provider failure is captured clearly enough to prove a provider/login availability blocker. No download occurs and privacy remains intact.

## Not yet implemented

- D3 V0.4.1 real-provider verification and merge.
- D4 audio download discovery.
- D5 controlled limits/error characterization.
- D6 frozen discovery contracts.
- Production Voice Engine.
- Media Analyzer, Scene Planner, Subtitle Engine, Render Engine, Desktop UI, diagnostics/resume runtime, installer, full regression.

## Repository visibility risk

GitHub metadata still reports the repository as public. Never commit passwords, cookies, browser profiles, auth tokens, private media, or raw runtime/session artifacts.

## Current active objective

Perform one controlled V0.4.1 recovery field run; review the result; then either merge D3 and begin D4 or isolate a provider/login/session blocker before proceeding.
