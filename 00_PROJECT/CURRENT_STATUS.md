# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery. D1 Surface Map/V0.2 is merged to `main`. D2 Voice/Settings Catalog has now completed real field runs on V0.3 and V0.3.1. V0.3.1 fixed pause restoration and visible setting-value capture, but still under-captured custom voice/language option text. V0.3.2 is implemented and awaiting one final D2 field rerun before PR #7 can merge.**

## Completed

- D0 / Discovery Runner V0.1 completed and merged.
- D1 / Surface Map V0.2 completed, field-verified, and merged through PR #6 as `79bb057f4adc7ba010645bc63461564fa037e7a8`.
- Real V0.2 field run `20260917_110310_7bf1810a` confirmed `TTS_READY` / `ANONYMOUS` / `CAPTURED`, 38 interactive elements, correct D1 outputs, and the V0.1 contenteditable privacy leak fixed on the real provider page.
- D2 is on branch `feat/saydivoice-d2-voice-settings-catalog`, PR #7.
- Real V0.3 run `20260917_135249_9534c523` exposed `BUG-20260917-008` around custom provider surfaces.
- Real V0.3.1 run `20260917_142133_bd48aed7` field evidence reviewed:
  - script phrase visible in the browser screenshot is absent from uploaded DOM/map/selectors/settings/voice JSON evidence;
  - stability display value captured as `2.8`;
  - expression captured as `Ổn định`;
  - speed captured as `1.00×`;
  - output formats captured as WAV/MP3/FLAC/OGG with MP3 selected;
  - pause panel structure captured: checkbox off, period `0.45s`, comma `0.25s`, semicolon `0.3s`, newline `0.6s`, default button present;
  - pause surface reports `closed_after_observation: true`;
  - language surface visibly contains English, Tiếng Việt, 中文, 日本語, 한국어, Deutsch, Español, Français, but `language.options` remained empty;
  - voice surface visibly contains one `Tự động / Hệ thống tự chọn giọng` card, but catalog incorrectly promoted modal navigation tabs as four voice options.
- V0.3.2 implemented to address the remaining D2 gap:
  - second privacy-safe visible-leaf delta pass for custom surfaces;
  - editable/input content excluded at the browser probe boundary;
  - language labels extracted from newly visible leaf nodes;
  - voice modal navigation/generic controls filtered;
  - current automatic voice card recognized as `Tự động — Hệ thống tự chọn giọng` when exposed;
  - enhanced results override weak V0.3.1 option results only when meaningful data is found;
  - runner bumped to `0.3.2` and regression coverage added.

## Current live gate

Run V0.3.2 once on the target Windows laptop. D2 can merge if:

- voice catalog identifies the automatic voice card instead of modal navigation tabs;
- language catalog contains the visible language choices instead of an empty list;
- pause remains restored after observation;
- stability/expression/speed/output-format evidence remains correct;
- no setting is changed;
- no Generate/download action occurs;
- no script/editor value appears in structured outputs;
- D1 evidence remains valid.

## Not yet implemented

- D2 V0.3.2 field verification and merge.
- D3 generation lifecycle observation/automation.
- D4 audio download discovery.
- D5 controlled limits/error characterization.
- D6 frozen discovery contracts.
- Production Voice Engine.
- Media Analyzer, Scene Planner, Subtitle Engine, Render Engine, Desktop UI, full diagnostics/resume runtime, and installer.

## Repository visibility risk

GitHub metadata has reported the repository as public. Never commit passwords, cookies, browser profiles, auth tokens, private media, voice catalogs from a private account, or raw local runtime/session artifacts.

## Current active objective

Finish V0.3.2 Windows CI/package, perform one final D2 field rerun, merge PR #7 if accepted, then begin D3 Generation Lifecycle.
