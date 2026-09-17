# Bug Log

Use one entry per significant reproducible defect. Keep unresolved defects visible until verified fixed.

## Open

### BUG-20260917-008 — D2 V0.3 real-page catalog under-captured custom SaydiVoice surfaces

Status: FIXED — awaiting real-provider verification in V0.3.1.

Detected in: Windows/SaydiVoice field run `20260917_135249_9534c523` using runner `0.3.0`.

Symptom:
- `voice_catalog.json` reported one option, `Xoá`, instead of meaningful voice choices;
- language options were empty even though the language selector opened;
- stability/expression/speed were visually present, but the catalog associated nearby generic buttons instead of stable slider nodes;
- the final screenshot showed the pause panel still expanded after observation.

Expected: D2 should distinguish meaningful selector contents from generic surface controls, preserve visible current setting values even when the provider uses custom non-ARIA sliders, capture pause-panel structure, and restore opened surfaces without changing a setting.

Evidence:
- report: `TTS_READY` / `ANONYMOUS` / `CAPTURED`, no runtime exception;
- uploaded screenshot showed stability `2.8`, expression `Ổn định`, speed `1.00×`, expanded pause rows (`0.45s`, `0.25s`, `0.3s`, `0.6s`) and MP3 selected;
- uploaded V0.3 catalogs confirmed voice=`Xoá`, empty language options and generic-button setting controls.

Root cause: V0.3 depended mainly on conventional option/ARIA selectors and a nearest-interactive-control heuristic. SaydiVoice currently renders several controls as custom surfaces without stable option/slider semantics. Escape also does not reliably collapse the pause accordion.

Fix in V0.3.1:
- record a privacy-safe before/after visible-control delta for selector surfaces rather than relying only on option roles;
- exclude generic Clear/Delete and +/- controls from semantic option counts;
- parse display values from the provider's visible setting label/value text when no stable slider value exists;
- capture pause panel checkbox/row/default-button structure without pressing +/- or changing settings;
- attempt Escape restoration, then toggle the original opener only if the surface remains expanded;
- save per-surface screenshots (`d2_voice_surface.png`, `d2_language_surface.png`, `d2_pause_surface.png`) for evidence;
- expose closed-after-observation and explicit warnings instead of silently claiming a clean catalog.

Tests: updated D2 catalog/runner regression suite; Windows Actions for commit `07f43a89297066dbb5641c07dfdac70b0aebae68` PASS. V0.3.1 packaging CI is pending/being verified.

Regression result: automated PASS; real SaydiVoice verification PENDING.

Commit/PR: branch `feat/saydivoice-d2-voice-settings-catalog`, PR #7.

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
