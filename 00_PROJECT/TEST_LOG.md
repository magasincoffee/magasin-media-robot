# Test Log

## 2026-09-17 — D3 V0.4.0 real-provider review + V0.4.1 recovery build

### Real V0.4.0 field run

- Run ID: `20260917_153149_2bb6c109`.
- `generation_lifecycle.json`: structurally valid; sample length 52; sample text itself not persisted.
- Download action: PASS — `download_clicked: false`.
- Initial state: Generate available; free quota 3; audio element count 5.
- Processing evidence visible in trace/UI: Generate disappeared and `Hủy` appeared.
- Provider terminal alert: `Không tải được giọng. Vui lòng tải lại trang.`.
- Terminal classification: ERROR.
- Quota: 3 → 3; no quota consumption detected by the captured text.
- Audio elements: 5 → 5.
- New result/download control: none.
- V0.4.0 classifier gap: `processing_observed` was false because it only recognized disabled/aria-busy Generate controls, not `Hủy` or Generate disappearance.
- Defect recorded as `BUG-20260917-009`.

### V0.4.1 corrective implementation

- Added processing detection for visible `Hủy/Cancel` and Generate disappearance after click.
- Added best-effort network-idle settling before controlled attempts.
- Added `--retry-after-reload-error`; retry is off by default.
- Exactly one retry is allowed only when attempt 1 returns an explicit reload-page error.
- D3 BAT requires operator Y confirmation and warns that the run may use at most two generation attempts.
- Added per-attempt traces/screenshots while preserving `d3_before_generate.png` / `d3_after_generate.png` compatibility.
- Lifecycle schema advanced to 1.1; runner/package to 0.4.1; report schema to 1.4.
- Added regressions for `Hủy` processing and reload-only retry eligibility.
- Real V0.4.1 provider verification: PENDING.

## 2026-09-17 — D3 Generation Lifecycle V0.4.0 automated verification

- Branch: `feat/saydivoice-d3-generation-lifecycle`; PR #8.
- Runner/package: `0.4.0`; report schema `1.3`.
- Added explicit `--allow-generate` gate; default discovery remains non-generating.
- Added disposable same-session generation tab; no audio download action.
- Added structural lifecycle trace for Generate busy/disabled state, audio/result controls, quota text, and alert/toast changes.
- Added pre-existing-alert baseline handling so an old provider toast is not mislabeled as a generation failure.
- Added fixed sample privacy contract: structured output stores sample length/SHA-256, not editor text.
- Added tests for success by quota decrease, success by audio appearance, new error classification, processing timeout, no-signal, and runner opt-in behavior.
- Windows Actions run `35199227801`: **PASS**.
- Operator artifact `MAGASIN_SAYDIVOICE_DISCOVERY_V0.4.0`: produced successfully.
- Downloaded/extracted operator ZIP compile: **PASS**.
- Downloaded/extracted operator ZIP pytest: **46 tests PASS**.
- ZIP structure/privacy check: 38 packaged files; D3 BAT/generation module/tests present; no `.venv`, `browser_profile`, cookie/token/secret path detected.

## 2026-09-17 — D2 V0.3.2 final field acceptance

- Real run: `20260917_151143_da1bfcc6`.
- Privacy: PASS — visible editor phrase absent from uploaded DOM/map/selectors/settings/voice JSON files.
- Voice catalog: PASS — one semantic option, `Tự động — Hệ thống tự chọn giọng`; modal navigation tabs excluded.
- Language catalog: PASS — 32 visible language choices captured, including English, Tiếng Việt, 中文, 日本語, 한국어, Deutsch, Español, Français.
- Settings: PASS — stability `2.8`, expression `Ổn định`, speed `1.00×`.
- Output formats: PASS — WAV/MP3/FLAC/OGG with MP3 selected.
- Pause: PASS — automatic checkbox off; `0.45s`, `0.25s`, `0.3s`, `0.6s`; default button present; closed after observation.
- `BUG-20260917-008`: VERIFIED.
- D2 PR #7 merged to `main` as `ec7ee7c0b18e488a3bc43361e8e38ca4e88ce54b`.

## 2026-09-17 — D2 corrective history

- V0.3 run `20260917_135249_9534c523`: runtime PASS; custom voice/language/settings surfaces under-captured; `BUG-20260917-008` opened.
- V0.3.1 run `20260917_142133_bd48aed7`: privacy/settings/pause PASS; language options still empty and voice modal tabs miscounted; packaged pytest 35 PASS.
- V0.3.2: privacy-safe visible-leaf custom-surface pass added; Windows Actions `35195143308` PASS; packaged pytest 40 PASS.

## 2026-09-17 — D1/V0.2

- Surface Map and ranked selectors implemented.
- Contenteditable privacy regression fixed and verified on real V0.2 run `20260917_110310_7bf1810a`.
- Login/history semantic regression fixed.
- Windows Actions `35172844321`: PASS; D1 suite 23 PASS.

## 2026-09-17 — D0/V0.1

- Discovery Runner implemented and merged.
- Initial Windows field run `20260917_011521_dcb358a9`: `TTS_READY` / `CAPTURED`, exit 0.
- Local/CI suite: 16 tests PASS.

## Repository initialization

- Repository access and scaffold creation: PASS.
- Default branch: `main`.
