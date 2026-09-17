# Next Step

## Immediate next step — Merge D1 and implement D2 Voice/Settings Catalog

D1/V0.2 passed its real provider field gate on Windows run `20260917_110310_7bf1810a`.

Verified:

- `TTS_READY` / `ANONYMOUS` / `CAPTURED`;
- real report/log clean;
- contenteditable script text no longer appears in structured evidence;
- `saydi_map.json` and `selectors.json` generated;
- semantic controls map correctly, including login vs History;
- no guessed selectors were assigned to visual slider controls that lacked stable interactive DOM nodes.

## D2 implementation scope

Build a non-destructive Voice/Settings Catalog pass that can safely inspect current provider UI without generating audio.

The D2 pass should:

1. open the voice selector and capture its visible options/metadata;
2. inspect language selection if the UI exposes options safely;
3. inspect settings and discover real interactive nodes for:
   - voice stability;
   - expression;
   - reading speed;
   - pause behavior;
   - output format;
4. capture accessible names, roles, values/ranges, labels, option text, and stable attributes without persisting user script content;
5. close any opened menus/dialogs where practical so the page remains unchanged;
6. emit structured outputs such as `voice_catalog.json` and `settings_catalog.json`;
7. add unit/regression tests and Windows CI coverage;
8. package a one-click Windows D2 field build.

## D2 field acceptance target

After code/CI passes, the operator will run one real D2 discovery pass and return the generated catalog artifacts. Only then should D2 be frozen and D3 generation lifecycle discovery begin.

## Still out of scope

Do not yet click `Tạo giọng nói`, download audio, stress text limits, or implement the production Voice Engine. D3/D4 follow after D2 is field-verified.
