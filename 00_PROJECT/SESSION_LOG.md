# Session Log

Chronological handoff record across implementation sessions. Each session must append one concise entry before stopping.

## 2026-09-17 — Session 009 — D2 accepted → D3 Generation Lifecycle V0.4.0

### Workbox

Started approximately 15:15 ICT under the 28-minute maximum-task rule. Stopped at the next operator gate after implementation, CI, package extraction, and local regression verification.

### D2 field acceptance

Reviewed real V0.3.2 artifacts from run `20260917_151143_da1bfcc6`.

PASS:
- 32 structured language options captured;
- one automatic voice card captured as `Tự động — Hệ thống tự chọn giọng`;
- modal-navigation tabs no longer counted as voices;
- voice/language/pause surfaces report restored after observation;
- stability `2.8`, expression `Ổn định`, speed `1.00×` retained;
- MP3 selected with WAV/MP3/FLAC/OGG present;
- pause values `0.45s`, `0.25s`, `0.3s`, `0.6s` retained;
- structured JSON remains free of the visible editor phrase.

`BUG-20260917-008` VERIFIED. PR #7 merged to `main` as `ec7ee7c0b18e488a3bc43361e8e38ca4e88ce54b`.

Provider observation: final UI showed `Không tải được giọng. Vui lòng tải lại trang.` after voice-surface observation. D3 explicitly records alerts present before Generate as baseline, so an existing toast cannot be misclassified as a new generation failure.

### D3 work completed

- Created branch `feat/saydivoice-d3-generation-lifecycle`; PR #8.
- Runner/package advanced to V0.4.0; report schema 1.3.
- Added `generation.py` and `generation_lifecycle.json` evidence.
- Generate action is impossible by default; requires explicit `--allow-generate`.
- D3 uses a disposable same-session tab and exactly one fixed short test sentence.
- Captures Generate busy/disabled state, quota changes, audio/result-control appearance, and new alerts/toasts.
- Does not download audio.
- Does not persist editor text; stores only fixed-sample length/SHA-256.
- Added `CAI_DAT_VA_CHAY_D3.bat` with Y/N warning that one provider generation/quota unit may be consumed.
- Added lifecycle and runner opt-in tests.

### Verification

- Windows Actions run `35199227801`: PASS.
- Operator artifact `MAGASIN_SAYDIVOICE_DISCOVERY_V0.4.0`: generated.
- Extracted ZIP compile: PASS.
- Extracted ZIP pytest: **46 tests PASS**.
- ZIP privacy/structure: 38 files; D3 runner included; no `.venv`, `browser_profile`, cookie/token/secret path.

### Next gate

Operator runs `CAI_DAT_VA_CHAY_D3.bat`, confirms Y, and returns `generation_lifecycle.json`, D3 before/after screenshots, report JSON, and JSONL log from the same run ID. This is the first discovery stage that intentionally triggers one Generate action; D4 download remains disabled.

## 2026-09-17 — Session 008 — V0.3.1 field review → V0.3.2 final D2 corrective build

- V0.3.1 verified privacy/settings/pause but still missed custom language labels and miscounted voice tabs.
- Built V0.3.2 privacy-safe visible-leaf capture, multilingual extraction, voice navigation filtering and automatic-card recognition.
- Windows Actions `35195143308`: PASS; packaged pytest 40 PASS.

## 2026-09-17 — Session 007 — D2 V0.3 field review → V0.3.1 corrective build

- Reviewed real run `20260917_135249_9534c523`.
- Found `BUG-20260917-008` and built V0.3.1 corrective capture/restoration.
- Windows CI/packaging PASS; packaged pytest 35 PASS.

## 2026-09-17 — Session 006 — D2 Voice/Settings Catalog V0.3

- Added D2 catalog pipeline, privacy-safe observation, structured outputs, graceful fallback and regression coverage.
- Local pytest 38 PASS; Windows Actions PASS.

## 2026-09-17 — Session 005 — Package D1/V0.2

- One-click V0.2 package built; compile PASS; pytest 29 PASS.

## 2026-09-17 — Session 004 — D1 Surface Map

- Reviewed V0.1 field evidence, fixed editor privacy and login/history semantics, added surface map/selectors.
- Windows Actions PASS; 23 tests.

## 2026-09-17 — Session 003 — First real Windows run

- Run `20260917_011521_dcb358a9`: `TTS_READY` / `CAPTURED`, exit 0.

## 2026-09-17 — Session 002 — Discovery Runner V0.1

- V0.1 implemented/merged; 16 tests PASS; Windows CI PASS.

## 2026-09-17 — Session 001 — Repository foundation

Repository/document scaffold: PASS.
