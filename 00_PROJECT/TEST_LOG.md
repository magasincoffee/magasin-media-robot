# Test Log

## 2026-09-17 — D2 Voice/Settings Catalog V0.3

Scope: D2 implementation on branch `feat/saydivoice-d2-catalog` after D1 field acceptance and merge.

### Local/distribution verification

- Runner/project version: `0.3.0`.
- `python -m compileall -q src`: PASS.
- `PYTHONPATH=src python -m pytest -q`: PASS — **37 tests**.
- Package version import: PASS (`0.3.0`).
- D2 catalog privacy tests: PASS.
- Numeric setting-range value preservation: PASS.
- Menu-control diffing: PASS.
- Voice-option deduplication: PASS.
- Settings-context sanitization: PASS.
- Unsafe trigger rejection: PASS.
- Trigger whitelist regression: PASS — Generate/delete are absent.
- Runner orchestration: PASS with mocked D2 catalog artifacts and cleanup.

### Windows CI

- Workflow: `Discovery Tests`.
- Latest D2 branch run: `35185941236`.
- Conclusion: **PASS**.
- Branch head for that run: `1b059eeb8f79b9f486db0e7f65eea1b236846ee0`.

### Packaging

- Operator distribution: `MAGASIN_SAYDIVOICE_DISCOVERY_V0.3.zip`.
- ZIP built after removing local pytest/bytecode caches.
- Archive contains 31 files; no browser profile/session data is bundled.
- SHA-256 of distributed archive: `6b7dc96aebcf9b2f5f2aee0c077efd59787a305b4382064e737725669132e469`.

### Remaining gate

Real V0.3 provider-side pass is required to validate current voice menu options and the actual custom setting/slider mechanics.

## 2026-09-17 — D1 V0.2 real provider acceptance

Real run: `20260917_110310_7bf1810a`.

- Runner `0.2.0`: PASS.
- `TTS_READY` / `ANONYMOUS` / `CAPTURED`: PASS.
- 38 visible interactive elements: captured.
- `dom_inventory.json`: privacy PASS — contenteditable editor present but script text absent.
- `saydi_map.json`: PASS.
- `selectors.json`: PASS.
- Login controls vs standalone History semantic mapping: PASS.
- Lifecycle log: PASS; no runtime exception.
- `BUG-20260917-006`: VERIFIED fixed live.
- `BUG-20260917-007`: VERIFIED fixed live.
- D1 PR #2 CI: PASS; PR merged as `51869ab54dac1e5f0202455cf1f9b40f48dde0b0`.

## 2026-09-17 — V0.2 Windows distribution packaging self-test

- Distribution: `MAGASIN_SAYDIVOICE_DISCOVERY_V0.2.zip`.
- Compile: PASS.
- Pytest: PASS — 29 tests.
- Version import: PASS (`0.2.0`).
- Structural field-fixture semantic replay: PASS.
- Privacy regression replay: PASS.

## 2026-09-17 — First field artifact review + D1/V0.2 validation

- V0.1 report/log: functional PASS.
- V0.1 DOM inventory: privacy FAIL due to contenteditable script text; tracked as `BUG-20260917-006` and fixed in V0.2.
- Login-vs-History semantic defect tracked as `BUG-20260917-007` and fixed.
- D1 Windows Actions run `35172844321`: PASS.

## 2026-09-17 — Real Windows SaydiVoice V0.1 field run

- Playwright Chromium install: PASS.
- Bundled tests: PASS — 16 tests.
- Run `20260917_011521_dcb358a9`.
- `TTS_READY` / `CAPTURED`, exit `0`.

## 2026-09-17 — SaydiVoice Discovery Runner V0.1

- Local compile: PASS.
- Local pytest: PASS — 16 tests.
- Package import/version: PASS (`0.1.0`).
- PR Windows CI run `35130561175`: PASS.
- Post-merge main Windows CI run `35130819104`: PASS.

## 2026-09-17 — Repository initialization checks

- Repository access: PASS (`magasincoffee/magasin-media-robot`).
- Default branch: `main`.
- Documentation/source-of-truth scaffold: PASS.
