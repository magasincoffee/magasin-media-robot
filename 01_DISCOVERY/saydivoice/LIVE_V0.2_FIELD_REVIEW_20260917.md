# SaydiVoice V0.2 Live Field Review — 2026-09-17

Run: `20260917_110310_7bf1810a`

## Result

D1 live gate: **PASS**.

Observed from the uploaded V0.2 artifact set:

- runner version `0.2.0`;
- page state `TTS_READY`;
- auth state `ANONYMOUS`;
- run status `CAPTURED`;
- no runtime error;
- 38 visible interactive elements captured;
- `saydi_map.json` generated;
- `selectors.json` generated;
- script editor captured as `contenteditable: true` with structured text suppressed;
- the prior V0.1 script phrase was absent from report, DOM inventory, surface map, selectors, and lifecycle log;
- login controls and standalone History tab classified independently;
- language, voice selector, Generate, Settings/History, pause selector, format tabs, editor utility actions, and assistant chat mapped.

## Settings still unresolved at D1

The screenshot visibly shows stability, expression, and reading-speed controls, but the D1 DOM inventory did not expose stable interactive nodes for these controls. D1 intentionally leaves them unresolved rather than inventing selectors. D2 will inspect those settings live and catalog their values/ranges.

## Session note

The field state is anonymous-ready. Authenticated session reuse is therefore not required to close D1. Persistent local browser-profile support remains in place and will be exercised when a later phase requires authentication.

## Privacy verification

The V0.1 contenteditable leakage is verified fixed on the real provider page. Structured evidence did not contain the visible script text from the editor.
