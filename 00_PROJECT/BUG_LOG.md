# Bug Log

Use one entry per significant reproducible defect. Keep unresolved defects visible until verified fixed.

## Open

### BUG-20260917-008 — D2 custom SaydiVoice surfaces under-captured

Status: FIXED IN V0.3.2 — awaiting final real-provider verification.

Detected in: V0.3 field run `20260917_135249_9534c523`.

V0.3 symptoms:
- voice catalog promoted generic `Xoá`;
- language options were empty;
- visible custom slider values were not represented well;
- pause panel remained expanded after observation.

V0.3.1 real-field result: PARTIAL FIX on run `20260917_142133_bd48aed7`.

Verified fixed in V0.3.1:
- structured evidence remains free of the visible script/editor phrase;
- stability display value `2.8` captured;
- expression `Ổn định` captured;
- speed `1.00×` captured;
- MP3 + WAV/MP3/FLAC/OGG captured correctly;
- pause structure captured (`0.45s`, `0.25s`, `0.3s`, `0.6s`, checkbox off, default button present);
- pause reports `closed_after_observation: true`.

Still incorrect in V0.3.1:
- language screenshot visibly contains English, Tiếng Việt, 中文, 日本語, 한국어, Deutsch, Español, Français, but `language.options` is empty;
- voice screenshot visibly contains one `Tự động / Hệ thống tự chọn giọng` card, but structured catalog counts navigation tabs (`Khám phá`, `Đã chọn`, `Giọng của tôi`, `Yêu thích`) as four voice options.

Root cause: SaydiVoice renders language entries and voice-card text as custom visible leaf nodes without the conventional option/ARIA roles used by the first D2 probe.

Fix in V0.3.2:
- added a second visible-leaf before/after delta pass;
- input/textarea/contenteditable/textbox content excluded at the browser boundary;
- language labels collected from newly visible leaf nodes;
- modal navigation and generic controls filtered from voice options;
- current automatic voice card recognized as `Tự động — Hệ thống tự chọn giọng` when that label/descriptor pair is present;
- enhanced results replace weak base-catalog options only when meaningful data exists;
- added multilingual, automatic-card, modal-filter, visible-delta, and runner-integration regressions.

Automated regression result: PASS. Windows Actions run `35195143308` PASS; packaged V0.3.2 compile PASS; packaged pytest **40 tests PASS**.

Remaining verification: one real V0.3.2 SaydiVoice run.

Commit/PR: branch `feat/saydivoice-d2-voice-settings-catalog`, PR #7.

## Resolved

### BUG-20260917-006 — Contenteditable editor text leaked into DOM inventory
Status: VERIFIED on V0.2 real run `20260917_110310_7bf1810a`.
Fix: blank editor text in browser probe and suppress again in serializer.

### BUG-20260917-007 — Login explanatory copy could be misclassified as History control
Status: VERIFIED on V0.2 real run.
Fix: authentication semantics evaluated before exact standalone History mapping.

### BUG-20260917-001 — Editor text could enter DOM inventory
Status: VERIFIED.
Fix: serializer privacy boundary suppresses editor text even if a probe supplies it.

### BUG-20260917-002 — Setup did not install the project package
Status: VERIFIED.
Fix: setup installs the local package before tests/run.

### BUG-20260917-003 — Error logging could leak sensitive URL/query content
Status: VERIFIED.
Fix: sanitize URL/query/token/email-like values and avoid raw tracebacks by default.

### BUG-20260917-004 — Browser resources could leak after navigation/probe failure
Status: VERIFIED.
Fix: persistent context and Playwright are closed/stopped on failure.

### BUG-20260917-005 — First login could not populate persistent browser profile
Status: VERIFIED.
Fix: manual-login polling keeps the visible robot browser open and persists the local profile.

## Entry template

```text
ID: BUG-YYYYMMDD-NNN
Status: OPEN | FIXED | VERIFIED
Detected in:
Symptom:
Expected:
Reproduction:
Evidence/log:
Root cause:
Fix:
Tests added/run:
Regression result:
Commit/PR:
```
