# Test Log

## 2026-09-17 — First field artifact review + D1/V0.2 validation

Scope: review uploaded artifacts from real Windows run `20260917_011521_dcb358a9` and validate D1 Surface Map branch.

### Uploaded artifact review

- `discovery_report_20260917_011521_dcb358a9.json`: PASS structurally; runner `0.1.0`, `TTS_READY`, `CAPTURED`, no runtime error.
- `discovery_20260917_011521_dcb358a9.jsonl`: PASS; clean start/completion lifecycle with no exception.
- Screenshot: PASS for visible TTS page; anonymous login controls are visible while TTS editor remains usable.
- `dom_inventory.json`: functional control capture PASS (37 elements), privacy FAIL for V0.1 because a contenteditable script editor persisted its visible text.
- Privacy defect tracked as `BUG-20260917-006`; fixed in V0.2 with browser-probe and serializer suppression plus regression coverage.
- Locator semantic defect `BUG-20260917-007` also fixed so login explanatory copy is not confused with the History tab.

### D1/V0.2 branch verification

- Branch: `feat/saydivoice-d1-surface-map`.
- Version: `0.2.0`.
- D1 writes `saydi_map.json` and `selectors.json` in the per-run directory.
- Windows GitHub Actions run `35172844321`: PASS.
- Environment: `windows-latest`.
- Dependency install: PASS.
- Compile package: PASS.
- Unit-test step: PASS.
- D1 suite: 23 tests, including contenteditable privacy suppression and locator semantic regression coverage.

### Remaining live gate

Run V0.2 on the real Windows/SaydiVoice page and verify:

- no script/editor text in structured evidence;
- `saydi_map.json` and `selectors.json` are generated correctly;
- real slider/settings nodes are resolved where the current DOM exposes stable semantics;
- persistent-profile reuse behaves correctly on a second run.

## 2026-09-17 — Real Windows SaydiVoice field run

Scope: first operator-run field verification of SaydiVoice Discovery Runner V0.1 on the target Windows laptop.

- Playwright Chromium download/install: PASS.
- Bundled regression tests: PASS — 16 tests.
- Discovery run ID: `20260917_011521_dcb358a9`.
- Final page classification: `TTS_READY`.
- Final run status: `CAPTURED`.
- Process status: `0`.

## 2026-09-17 — SaydiVoice Discovery Runner V0.1

- Local compile: PASS.
- Local pytest: PASS — 16 tests.
- Package import/version: PASS (`0.1.0`).
- PR GitHub Actions Windows run `35130561175`: PASS.
- Post-merge `main` GitHub Actions run `35130819104`: PASS.

## 2026-09-17 — Repository initialization checks

- Repository access: PASS (`magasincoffee/magasin-media-robot`, admin/push access available).
- Default branch: `main`.
- Documentation/source-of-truth scaffold creation: PASS.
