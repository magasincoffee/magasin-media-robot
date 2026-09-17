# Bug Log

Use one entry per significant reproducible defect. Keep unresolved defects visible until verified fixed.

## Open

None currently in D1/V0.2 code. Live V0.2 verification on the target Windows laptop is still required for provider-specific slider/control resolution.

## Resolved

### BUG-20260917-006 — Contenteditable editor text leaked into DOM inventory

Status: VERIFIED

Detected in: first real Windows field artifact set, run `20260917_011521_dcb358a9`.

Symptom: `dom_inventory.json` element index 17 persisted the full text currently visible in the SaydiVoice editor even though the discovery privacy contract says editor/input values are not intentionally persisted.

Expected: Text entered or displayed inside editable TTS script surfaces must never be written to structured discovery evidence.

Reproduction: Open the SaydiVoice TTS editor with text present, run V0.1, then inspect `runs/<run-id>/dom_inventory.json`; the editable `div` text is recorded because the element is contenteditable but has no `role="textbox"`.

Evidence/log: Field artifact `dom_inventory.json` from run `20260917_011521_dcb358a9` contained editor content. The exact user script is intentionally not reproduced in Git.

Root cause: The browser probe did not persist a `contenteditable` flag per element, and `sanitize_inventory()` only suppressed text for `input`, `textarea`, `select`, or `role="textbox"`. A contenteditable `div` therefore passed through as ordinary visible text.

Fix: V0.2 records contenteditable state in the raw probe and independently suppresses structured text for every editable element in the serializer. The DOM probe itself also blanks editor text before it leaves the page context.

Tests added/run: `test_contenteditable_text_is_always_suppressed`, runner privacy regression, local 23-test suite PASS, Windows Actions unit-test step PASS on D1 branch.

Regression result: VERIFIED in code/CI; next live V0.2 artifact will confirm field evidence no longer contains editor text.

Commit/PR: branch `feat/saydivoice-d1-surface-map`.

### BUG-20260917-007 — Login explanatory copy could be misclassified as History control

Status: VERIFIED

Detected in: D1 mapping against the first real V0.1 DOM inventory.

Symptom: The anonymous login button text includes explanatory copy mentioning history, so a loose substring matcher could classify that button as `history_tab`.

Expected: Authentication controls must map to `login`; the actual standalone `Lịch sử` tab must map to `history_tab`.

Root cause: Initial D1 semantic matching used broad substring terms and evaluated history before login semantics.

Fix: Authentication controls are detected first using a login-prefix rule; common controls then use exact normalized labels.

Tests added/run: `test_login_explanatory_copy_is_not_misclassified_as_history`; local D1 suite PASS and Windows Actions unit-test step PASS.

Regression result: VERIFIED.

Commit/PR: branch `feat/saydivoice-d1-surface-map`.

### BUG-20260917-001 — Editor text could enter DOM inventory

Status: VERIFIED

Detected in: V0.1 evidence sanitizer self-test.

Symptom: If a future browser probe accidentally supplied text from an input/textarea/textbox, the generic inventory serializer could persist that text.

Expected: Discovery evidence must never persist entered script/credential values.

Root cause: Sanitization trusted the probe to blank editor text instead of enforcing the privacy boundary again at serialization.

Fix: `sanitize_inventory()` now suppresses text for editor controls regardless of probe input.

Tests added/run: privacy regression in `test_evidence.py` and runner orchestration test; local pytest and Windows CI pass.

### BUG-20260917-002 — Setup did not install the project package

Status: VERIFIED

Detected in: first Windows setup-flow review.

Symptom: Dependencies could be installed while `python -m saydivoice_discovery.cli` remained unavailable because the local package itself had not been installed.

Expected: After one setup run, `RUN_DISCOVERY.bat` must be able to import and launch the package.

Root cause: Setup originally installed requirement files only.

Fix: `SETUP_DISCOVERY.bat` installs the project in editable mode with development extras before running tests.

Tests added/run: package import/compile checks locally; Windows CI package tests pass.

### BUG-20260917-003 — Error logging could leak sensitive URL/query content

Status: VERIFIED

Detected in: security/privacy review.

Symptom: Raw exception text can contain redirect URLs, query parameters, emails, or token-like values.

Expected: Logs/reports must not intentionally persist those values.

Root cause: Raw exception output was not consistently sanitized before logging/reporting.

Fix: Errors now pass through `sanitize_error_message()`; URL query/fragment, obvious bearer/JWT values, and emails are redacted, and raw stack traces are not written by default.

Tests added/run: runtime sanitization tests; local pytest and Windows CI pass.

### BUG-20260917-004 — Browser resources could leak after navigation/probe failure

Status: VERIFIED

Detected in: orchestration self-review.

Symptom: If Chromium launched successfully but navigation or DOM probing failed before the context bundle returned to the runner, Playwright/context cleanup was not guaranteed.

Expected: Browser resources must close on launch, navigation, probe, capture, and runner failure paths.

Root cause: Cleanup responsibility began too late in the call chain.

Fix: `open_and_probe()` now closes the persistent context and stops Playwright when navigation/probing raises; runner cleanup remains responsible after a successful return.

Tests added/run: orchestration cleanup coverage plus local/CI regression suite.

### BUG-20260917-005 — First login could not populate persistent browser profile

Status: VERIFIED

Detected in: first-use workflow review.

Symptom: A login-required page would be classified and the browser would close immediately, preventing the user from logging in once to populate the persistent profile.

Expected: First use should allow manual login without storing credentials in code, then reuse the local profile.

Root cause: V0.1 had classification but no bounded manual-login observation window.

Fix: Added configurable manual-login polling. `RUN_DISCOVERY.bat` now keeps the visible browser open for up to 180 seconds when login is required and re-probes after the user logs in.

Tests added/run: `test_runner_reprobes_during_manual_login_wait`; 16 local tests pass and GitHub Actions Windows run `35130561175` passes.

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
