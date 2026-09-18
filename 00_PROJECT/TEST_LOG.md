# Test Log

## 2026-09-18 — Production SaydiVoiceProvider offline acceptance gate

Scope: freeze the field-verified Saydi contracts behind a production provider boundary without consuming generation quota or downloading live audio.

- Branch: `feat/saydivoice-production-adapter-offline`.
- Discovery Tests run `35370775036`: **PASS**.
- Package compile: PASS.
- Pytest: **83 passed**.
- No self-hosted/live Saydi workflow invoked.
- No Generate click.
- No Download click.
- Request validation resolves presets before runtime/browser access.
- Invalid preset/text/output path: fail as `fix_input` with zero preflight/control/generation calls.
- Login/session preflight failure: `PREFLIGHT_BLOCKED / re_auth` with zero side effects.
- Voice/format overrides are verified before Generate.
- Provider adapter makes exactly one `generate_once` call and exposes retry metadata instead of performing an implicit retry.
- Timeout/provider failure classification covered.
- Download is explicit (`download_requested`) and returns local path / byte count / SHA-256 metadata.
- Sensitive error strings are redacted through the existing runtime sanitizer.
- `PlaywrightSaydiRuntime` reuses existing field-verified page classifier, preset controls, generation trace/network recorder and safe download filename behavior.
- Raw audio, cookies, credentials, authorization headers and browser profile data remain outside Git.

## 2026-09-17 — Voice/style controls, preset roundtrip, preflight, and real preset generation

Scope: verify that production-relevant SaydiVoice voice/style controls can be applied deterministically before Generate, without inventing an unsupported discrete mood API.

### Control discovery / reversible verification

- Authenticated voice catalog discovery: 60 Vietnamese voices observed.
- Voice selection roundtrip verified and final voice restored to `Adam — Giọng hot tiktok`.
- D5B3 run `35230995883`: PASS.
  - `roundtrip_pass: true`.
  - `restored: true`.
  - `restore_errors: []`.
  - `generate_clicked: false`.
  - `download_clicked: false`.
- Stability/expression axis, speed slider, MP3/WAV/FLAC/OGG format controls, and pause-enable state can be changed and verified.
- No separate Happy/Sad/Angry provider selector was observed; style presets therefore compose the real controls.

### Authenticated generation preflight

- Initial D6 parser run identified two test-harness issues: an unrelated active tab was misread as audio format and quota text parsing was too narrow.
- Parser was tightened to `.fmt-tab`; usage/quota visibility became informational rather than a mandatory provider contract.
- Corrected D6 run `35233725324`: PASS.
  - voice: `Adam — Giọng hot tiktok`.
  - Generate present/enabled: PASS.
  - editor: PASS.
  - two sliders: PASS.
  - format: MP3; WAV/MP3/FLAC/OGG present.
  - pause: PASS.
  - visible usage text at that run: `124 / 20,000`.
  - no Generate / no Download.

### Preset implementation verification

- Unit parsing/validation coverage added for reusable `voice_presets.py` and `voice_controls.py`.
- Reversible preset roundtrip run `35237679528`: PASS without Generate.
- Current preset integration branch Discovery Tests run `35241812618`: PASS.

### Real `tiktok_energetic` generation

- Authorized live run: `35241844708` on `MAGASIN-PC`.
- Workflow conclusion: SUCCESS.
- `preset_key`: `tiktok_energetic`.
- `attempt_count`: 1.
- `generate_click_count`: 1.
- `download_click_count`: 0.
- terminal state: `SUCCESS_SIGNAL`.
- configured voice: `Adam — Giọng hot tiktok`.
- stability/expression ratio: `0.2974824563` (target `0.30`).
- speed ratio: `0.6484543843` (target `0.65`).
- format: MP3.
- pause enabled: false.
- `POST /api/tts`: HTTP 200, `audio/mpeg`.
- blob audio fetch: HTTP 206, `audio/mpeg`.
- `POST /api/library/history`: HTTP 201.
- privacy-safe evidence artifact uploaded; no raw audio Download action occurred.

## 2026-09-17 — D3 anonymous-session diagnosis + GitHub live-profile infrastructure

Scope: stop repeated manual ZIP round-trips, isolate the real D3 blocker, and prepare an authenticated persistent-profile path that GitHub Actions can orchestrate without committing browser credentials.

### Real provider evidence reviewed

- D2 remains stable in the later runs:
  - language choices captured;
  - voice catalog contains `Tự động — Hệ thống tự chọn giọng` rather than modal tabs;
  - stability `2.8`, expression `Ổn định`, speed `1.00×`;
  - pause `Đang tắt` with 0.45s / 0.25s / 0.3s / 0.6s rows;
  - MP3 selected with WAV/MP3/FLAC/OGG available.
- V0.4.2 network diagnostic:
  - anonymous `/api/session/start` returned 403;
  - `/api/samples` returned 401;
  - controlled Generate entered processing but returned provider error;
  - quota remained unchanged.
- V0.4.3 preflight diagnostic:
  - `/api/session/start` 403 detail: `Verification failed. Please retry.`;
  - `/api/samples` 401 detail: `Invalid or missing credentials.`;
  - terminal state `PREFLIGHT_BLOCKED`;
  - `attempt_count: 0`;
  - no Generate click and no quota consumption.
- Independent cloud/stealth-browser reproduction matched the anonymous limitation: only `Tự động` was available and anonymous generation failed.

### Local implementation verification

- V0.4.3 operator source compile: PASS.
- V0.4.3 pytest: **53 tests PASS**.
- New `profile_setup.py` and `ci_gate.py` compile in the V0.4.3 source tree: PASS.
- New live workflow is intentionally non-destructive until authenticated-session reuse is verified.
- PR #9 exact Windows Discovery Tests run `35210394785`: **PASS**.
- Live provider check: PENDING one-time self-hosted runner + profile bootstrap.

### GitHub live-profile design verification

- Branch: `feat/saydi-github-live-profile`.
- PR: #9.
- Persistent browser profile remains local at `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\browser_profile`.
- Workflow uploads latest evidence/report/log only; it does not stage `browser_profile`.
- First workflow does not pass any Generate flag and therefore cannot consume provider generation quota through the discovery runner.
- Acceptance gate requires `TTS_READY` and `AUTHENTICATED_OR_HIDDEN` before D3 enablement.
- Initial workflow validation run `35210309047` failed before job creation because top-level concurrency incorrectly referenced the unavailable `runner` context; fixed in `BUG-20260917-010` by switching to `${{ github.repository }}`.
- Subsequent PR CI validates the branch source successfully.

## 2026-09-17 — D2 V0.3.1 field review + V0.3.2 corrective build

- Run `20260917_142133_bd48aed7` reviewed.
- Privacy regression PASS: visible editor phrase absent from structured evidence.
- Settings PASS: `2.8`, `Ổn định`, `1.00×`, MP3 + WAV/MP3/FLAC/OGG.
- Pause structure/restoration PASS.
- V0.3.1 language/voice custom-surface capture remained partial.
- V0.3.2 added privacy-safe visible-leaf delta capture, language extraction, modal filtering, and automatic voice-card recognition.
- Windows Actions run `35195143308`: PASS.
- Packaged V0.3.2 compile PASS; pytest **40 tests PASS**.
- Later field evidence verified the V0.3.2 custom-surface fixes.

## 2026-09-17 — D2 V0.3 real-provider review + V0.3.1 corrective build

- Run `20260917_135249_9534c523`.
- Page/run `TTS_READY` / `ANONYMOUS` / `CAPTURED`.
- D1 evidence remained valid and editor text stayed suppressed.
- Provider-specific D2 gaps recorded as `BUG-20260917-008`.
- V0.3.1 added visible-control delta capture, generic control filtering, setting-value parsing, pause structure capture/restoration, and per-surface screenshots.
- Windows Actions run `35192735044`: PASS.
- Packaging run `35193609757`: PASS.
- Extracted ZIP compile PASS; pytest **35 tests PASS**.

## 2026-09-17 — D2 Voice/Settings Catalog V0.3 automated verification

- Branch `feat/saydivoice-d2-voice-settings-catalog`.
- Runner/package `0.3.0`; report schema `1.2`.
- Local distribution-derived compile PASS; pytest **38 tests PASS**.
- ZIP privacy validation PASS.
- GitHub Actions runs `35189216611`, `35189339655`, and PR run `35189814339`: PASS.

## 2026-09-17 — V0.2 Windows distribution packaging self-test

- Distribution `MAGASIN_SAYDIVOICE_DISCOVERY_V0.2.zip`.
- Compile PASS; pytest **29 tests PASS**; version `0.2.0` PASS; privacy replay PASS.

## 2026-09-17 — First field artifact review + D1/V0.2 validation

- First real V0.1 artifacts reviewed.
- Functional control capture PASS; V0.1 contenteditable privacy defect found and fixed in V0.2.
- D1 Windows Actions run `35172844321`: PASS.
- D1 suite: 23 tests PASS.

## 2026-09-17 — Real Windows SaydiVoice field run

- Playwright Chromium install PASS.
- Run `20260917_011521_dcb358a9`: `TTS_READY` / `CAPTURED`, process `0`.

## 2026-09-17 — SaydiVoice Discovery Runner V0.1

- Local compile PASS.
- Local pytest PASS — 16 tests.
- PR Windows CI and post-merge CI PASS.

## 2026-09-17 — Repository initialization checks

- Repository access PASS (`magasincoffee/magasin-media-robot`).
- Default branch `main`.
- Documentation/source-of-truth scaffold creation PASS.
