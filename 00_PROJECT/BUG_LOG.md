# Bug Log

Use one entry per significant reproducible defect. Keep unresolved defects visible until verified fixed.

## Open

### BUG-20260917-011 — Production preflight JSON output used Windows legacy console encoding

Status: OPEN — fix prepared, awaiting rerun verification.

Detected in: Voice Engine Live Preflight run `35243563844`.

Symptom:
- production backend reached the read-only preflight result;
- serializing/printing the result containing Vietnamese text raised `UnicodeEncodeError` in Windows `cp1258`;
- workflow failed before it could print/assert the preflight payload.

Expected: privacy-safe preflight metadata prints deterministically on the Windows self-hosted runner regardless of the inherited console code page.

Root cause: the temporary live-preflight workflow did not set `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8`, and the script used `ensure_ascii=False`, so Python inherited the legacy Windows stdout encoding.

Fix:
- force Python UTF-8 mode in the workflow;
- serialize the preflight payload with ASCII-safe JSON for the workflow log.

Safety impact: none. The workflow contains no Generate or Download operation; the failure occurred while printing the already-computed read-only preflight result.

Regression: pending rerun on `MAGASIN-PC`.

### BUG-20260917-009 — Anonymous Saydi session bootstrap rejected before generation

Status: OPEN — authenticated persistent-profile path prepared in PR #9.

Detected in: controlled D3 operator diagnostics V0.4.2/V0.4.3 and independent browser reproduction.

Symptoms:
- anonymous voice catalog exposes only `Tự động`;
- `/api/session/start` returns HTTP 403;
- safe provider detail: `Verification failed. Please retry.`;
- `/api/samples` returns HTTP 401;
- safe provider detail: `Invalid or missing credentials.`;
- during the earlier attempt `/api/gpu/eta` also returned 401;
- anonymous Generate returns a generic provider error and does not create a result.

Expected: a valid session can load the real voice catalog and reach a bounded controlled generation lifecycle.

Root cause status: provider-side anonymous verification/authentication requirement is confirmed as the blocking layer; the exact server-side policy is external to this project.

Mitigation/next verification:
- reuse one manually authenticated Playwright persistent profile on the same trusted Windows machine/network context;
- orchestrate non-destructive live checks through a Windows self-hosted GitHub Actions runner;
- keep the profile local and out of Git/artifacts;
- do not authorize Generate until the authenticated session gate passes.

Safety behavior verified in V0.4.3: `PREFLIGHT_BLOCKED`, `attempt_count: 0`, no Generate click, no quota decrease.

Branch/PR: `feat/saydi-github-live-profile`, PR #9.

### BUG-20260917-008 — D2 custom SaydiVoice surfaces under-captured

Status: VERIFIED by later field evidence.

Detected in: V0.3 field run `20260917_135249_9534c523`.

V0.3 symptoms:
- voice catalog promoted generic `Xoá`;
- language options were empty;
- visible custom slider values were not represented well;
- pause panel remained expanded after observation.

V0.3.1 partial fixes:
- structured evidence remained free of script/editor text;
- stability `2.8`, expression `Ổn định`, speed `1.00×`, output formats and pause structure were captured;
- pause restoration worked.

V0.3.2 fix:
- second privacy-safe visible-leaf before/after delta pass;
- editable/input/contenteditable/textbox content excluded at the browser boundary;
- language labels collected from newly visible leaf nodes;
- modal navigation and generic controls filtered from voice options;
- current automatic voice card recognized as `Tự động — Hệ thống tự chọn giọng` when exposed;
- regression coverage added.

Later field runs confirm the language catalog and automatic voice-card evidence are now captured correctly while prior D2 settings remain stable.

## Resolved

### BUG-20260917-010 — New live workflow used unavailable `runner` context in top-level concurrency
Status: FIXED in PR #9.
Detected in: Actions run `35210309047`, which failed workflow validation with no jobs created.
Root cause: top-level `concurrency.group` referenced `${{ runner.name }}`, but the `runner` context is only available after a job is assigned.
Fix: changed the top-level group to `${{ github.repository }}`, which is valid before job scheduling.
Regression: workflow validation re-check pending on the next branch push/PR synchronize event.

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
