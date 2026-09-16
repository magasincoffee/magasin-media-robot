# Test Log

## 2026-09-17 — Real Windows SaydiVoice field run

Scope: first operator-run field verification of SaydiVoice Discovery Runner V0.1 on the target Windows laptop.

### Evidence observed from operator screenshot

- Playwright Chromium download/install: PASS.
- Chromium version shown: `143.0.7499.4` (Playwright build `v1200`).
- Bundled regression tests: PASS — `16 passed in 0.29s`.
- Discovery run ID: `20260917_011521_dcb358a9`.
- Final page classification: `TTS_READY`.
- Final run status: `CAPTURED`.
- Process status: `0`.
- Report path printed by runner: `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\reports\discovery_report_20260917_011521_dcb358a9.json`.

### Result

PASS for real Windows setup, real browser launch/navigation, test execution, and page classification/capture.

### Remaining field checks

- Full contents of the generated report, DOM inventory, screenshot, and JSONL log have not yet been reviewed by the project implementation session.
- Persistent-session reuse still needs a second run while the SaydiVoice session remains valid.
- D0 will be marked fully field-verified only after those checks pass.

## 2026-09-17 — SaydiVoice Discovery Runner V0.1

Scope: D0 runner foundation implemented on PR #1 and merged to `main`.

### Local self-test

- `python -m compileall -q src`: PASS.
- `PYTHONPATH=src python -m pytest -q`: PASS — 16 tests.
- Package import/version check: PASS (`0.1.0`).
- Tested pure logic: runtime path construction, URL/text/error sanitization, page-state classifier, report serialization, evidence privacy, runner orchestration/cleanup, and manual-login re-probe.
- First privacy test exposed editor-text persistence risk; fixed and regression-tested.
- Full real-browser navigation in the implementation sandbox: NOT RUN. Chromium navigation is blocked there by administrator policy (`ERR_BLOCKED_BY_ADMINISTRATOR`), including local/data test navigation. This is an environment limitation documented in `01_DISCOVERY/saydivoice/SMOKE_TEST_NOTES.md`.

### GitHub Actions — PR validation

- Workflow: `Discovery Tests`.
- Run ID: `35130561175`.
- Code head: `06d39030f08b1de635122c4edd1c0875001a5458`.
- Environment: `windows-latest`, Python 3.13.
- Dependency install: PASS.
- Compile package: PASS.
- Unit tests: PASS.
- Overall conclusion: PASS.

### GitHub Actions — merged `main`

- Merge/squash commit: `f5d35eb157b26ca0425267979be2d32e359b7f55`.
- Workflow run ID: `35130819104`.
- Environment: `windows-latest`, Python 3.13.
- Checkout/setup: PASS.
- Dependency install: PASS.
- Compile package: PASS.
- Unit tests: PASS.
- Overall conclusion: PASS.

### Acceptance note

Code/unit/CI verification for V0.1 is complete on `main`.

## 2026-09-17 — Repository initialization checks

- Repository access: PASS (`magasincoffee/magasin-media-robot`, admin/push access available).
- Default branch: `main`.
- Initial repository state before scaffolding: empty.
- Documentation/source-of-truth scaffold creation: PASS for files recorded in the initialization changelog.
- Production code tests: NOT APPLICABLE — implementation had not started at that point.

## Test entry template

```text
Date/time:
Scope:
Environment:
Commit/branch:
Commands/checks:
Expected:
Result: PASS | FAIL
Evidence:
Related bug IDs:
Notes:
```
