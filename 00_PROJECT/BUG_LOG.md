# Bug Log

Use one entry per significant reproducible defect. Keep unresolved defects visible until verified fixed.

## Open

### BUG-20260917-009 — First D3 controlled generation ends in provider reload-page error

Status: FIXED IN V0.4.1 — awaiting real-provider verification.

Detected in: real Windows/SaydiVoice D3 V0.4.0 run `20260917_153149_2bb6c109`.

Observed lifecycle:
- initial Generate control was available;
- after click, the Generate control disappeared and the page exposed `Hủy`, proving a processing phase even though V0.4.0 did not classify it as such;
- about two seconds later Generate returned and a new provider alert appeared: `Không tải được giọng. Vui lòng tải lại trang.`;
- free quota remained 3 → 3;
- audio element count remained 5 → 5;
- no new result/download control appeared;
- `download_clicked` remained false.

Root cause classification: provider-side generation/recovery path or disposable-tab/session initialization issue. Current evidence is insufficient to claim a successful generation lifecycle. V0.4.0 also under-classified the observed `Hủy`/Generate-disappearance state as `processing_observed: false`.

Fix in V0.4.1:
- treat visible `Hủy/Cancel` or disappearance of Generate after the click as processing evidence;
- best-effort wait for network-idle before each controlled attempt;
- add explicit opt-in `--retry-after-reload-error` recovery;
- only when attempt 1 returns an error explicitly asking to reload, reload the disposable same-session page and allow exactly one second attempt;
- D3 BAT warns that the run can use at most two generation attempts;
- persist per-attempt structural traces/screenshots plus final lifecycle analysis;
- keep audio download out of scope and keep editor text out of structured evidence.

Remaining verification: one V0.4.1 real Windows run. If attempt 2 succeeds, D3 can characterize both the reload error and recovery success. If attempt 2 returns the same error, investigate login/provider availability/session requirements before D4.

Commit/PR: branch `feat/saydivoice-d3-generation-lifecycle`, PR #8.

## Resolved

### BUG-20260917-008 — D2 custom SaydiVoice surfaces under-captured
Status: VERIFIED on real V0.3.2 run `20260917_151143_da1bfcc6`; PR #7 merged as `ec7ee7c0b18e488a3bc43361e8e38ca4e88ce54b`.
Fix: custom visible-leaf capture, language extraction, automatic voice-card recognition, settings/pause restoration.

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
