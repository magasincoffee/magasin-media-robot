# Bug Log

Use one entry per significant reproducible defect. Keep unresolved defects visible until verified fixed.

## Open

None currently blocking D1/V0.2. The real SaydiVoice page does not expose stable interactive DOM nodes for the visible stability/expression/speed sliders in the D1 capture; those settings are intentionally deferred to D2 live catalog discovery instead of using guessed selectors.

## Resolved

### BUG-20260917-006 — Contenteditable editor text leaked into DOM inventory

Status: VERIFIED

Detected in: first real Windows field artifact set, run `20260917_011521_dcb358a9`.

Symptom: `dom_inventory.json` persisted the full text currently visible in the SaydiVoice editor even though the discovery privacy contract says editor/input values are not intentionally persisted.

Expected: Text entered or displayed inside editable TTS script surfaces must never be written to structured discovery evidence.

Root cause: The browser probe did not persist a `contenteditable` flag per element, and the V0.1 serializer did not independently suppress contenteditable text.

Fix: V0.2 records contenteditable state, blanks editor text inside the browser probe, and suppresses editor text again in the serializer.

Tests added/run: contenteditable privacy regression, runner privacy regression, D1 suite PASS, Windows Actions PASS.

Live regression result: VERIFIED on real Windows/SaydiVoice V0.2 run `20260917_110310_7bf1810a`. The contenteditable editor is present at element index 18 with `text: null`; no script text appears in the uploaded structured DOM inventory, surface map, selectors, report, or JSONL lifecycle log.

Commit/PR: branch `feat/saydivoice-d1-surface-map`.

### BUG-20260917-007 — Login explanatory copy could be misclassified as History control

Status: VERIFIED

Detected in: D1 mapping against the first real V0.1 DOM inventory.

Symptom: The anonymous login button text includes explanatory copy mentioning history, so a loose substring matcher could classify that button as `history_tab`.

Expected: Authentication controls must map to `login`; the actual standalone `Lịch sử` tab must map to `history_tab`.

Root cause: Initial D1 semantic matching used broad substring terms and evaluated history before login semantics.

Fix: Authentication controls are detected first using a login-prefix rule; common controls then use exact normalized labels.

Tests added/run: `test_login_explanatory_copy_is_not_misclassified_as_history`; D1 suite PASS and Windows Actions PASS.

Live regression result: VERIFIED on run `20260917_110310_7bf1810a`: three login controls map to `login`, while standalone element index 31 maps to `history_tab`.

Commit/PR: branch `feat/saydivoice-d1-surface-map`.

### BUG-20260917-001 — Editor text could enter DOM inventory

Status: VERIFIED

Detected in: V0.1 evidence sanitizer self-test.

Symptom: If a future browser probe accidentally supplied text from an input/textarea/textbox, the generic inventory serializer could persist that text.

Expected: Discovery evidence must never persist entered script/credential values.

Root cause: Sanitization trusted the probe to blank editor text instead of enforcing the privacy boundary again at serialization.

Fix: `sanitize_inventory()` suppresses text for editor controls regardless of probe input.

Tests added/run: privacy regression in `test_evidence.py` and runner orchestration test; local pytest and Windows CI pass.

### BUG-20260917-002 — Setup did not install the project package

Status: VERIFIED

Detected in: first Windows setup-flow review.

Symptom: Dependencies could be installed while `python -m saydivoice_discovery.cli` remained unavailable because the local package itself had not been installed.

Expected: After one setup run, `RUN_DISCOVERY.bat` must be able to import and launch the package.

Fix: `SETUP_DISCOVERY.bat` installs the project in editable mode with development extras before running tests.

### BUG-20260917-003 — Error logging could leak sensitive URL/query content

Status: VERIFIED

Fix: Errors pass through `sanitize_error_message()`; URL query/fragment, obvious bearer/JWT values, and emails are redacted, and raw stack traces are not written by default.

### BUG-20260917-004 — Browser resources could leak after navigation/probe failure

Status: VERIFIED

Fix: `open_and_probe()` closes the persistent context and stops Playwright when navigation/probing raises; runner cleanup remains responsible after a successful return.

### BUG-20260917-005 — First login could not populate persistent browser profile

Status: VERIFIED

Fix: Added configurable manual-login polling. The visible browser remains open during first-use login and re-probes afterward; persistent profile storage remains local-only.

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
