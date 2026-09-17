# Bug Log

Use one entry per significant reproducible defect. Keep unresolved defects visible until verified fixed.

## Open

None currently blocking D3.

Provider observation for D3: during the V0.3.2 field sequence the UI displayed `Không tải được giọng. Vui lòng tải lại trang.` after voice-surface observation. D2 still produced the correct automatic-card catalog and restored surfaces. D3 treats alerts already present before Generate as baseline so a pre-existing provider toast is not misclassified as a generation failure.

## Resolved

### BUG-20260917-008 — D2 custom SaydiVoice surfaces under-captured

Status: VERIFIED on real V0.3.2 run `20260917_151143_da1bfcc6`.

Detected in: V0.3 field run `20260917_135249_9534c523`.

Root cause: SaydiVoice renders several language entries, voice-card labels, and settings as custom visible nodes without conventional option/ARIA semantics.

Fix progression:
- V0.3.1 fixed visible setting-value capture, pause-panel structure, restoration, generic-control filtering, and per-surface screenshots.
- V0.3.2 added a privacy-safe visible-leaf delta pass, multilingual option extraction, modal-navigation filtering, and automatic voice-card recognition.

Real V0.3.2 verification:
- `voice_catalog.json`: exactly 1 semantic option, `Tự động — Hệ thống tự chọn giọng`; modal navigation tabs are not counted;
- `settings_catalog.json`: 32 language options captured, including English, Tiếng Việt, 中文, 日本語, 한국어, Deutsch, Español and Français;
- language/voice/pause surfaces all report closed after observation;
- display values remain stability `2.8`, expression `Ổn định`, speed `1.00×`;
- output formats remain WAV/MP3/FLAC/OGG with MP3 selected;
- pause structure remains checkbox off with `0.45s`, `0.25s`, `0.3s`, `0.6s` rows and default button present;
- no uploaded structured JSON contains the visible editor phrase;
- no Generate/download action was part of D2.

Automated regression: Windows CI PASS; packaged V0.3.2 pytest 40 tests PASS.

Merge: PR #7 merged to `main` as `ec7ee7c0b18e488a3bc43361e8e38ca4e88ce54b`.

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
