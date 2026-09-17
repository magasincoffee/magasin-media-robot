# D1 Field Acceptance — SaydiVoice Surface Map V0.2

Date: 2026-09-17

Real Windows run reviewed: `20260917_110310_7bf1810a`.

## Result

**PASS**

- Runner version `0.2.0`.
- Page state `TTS_READY`.
- Auth state `ANONYMOUS`.
- Run status `CAPTURED`.
- 38 visible interactive elements captured.
- `dom_inventory.json`, `saydi_map.json`, and `selectors.json` generated.
- Contenteditable script editor is represented without script text.
- Login controls and standalone History tab map separately and correctly.
- Language, voice selector, Generate, Settings, History, pause selector, editor utility controls, format tabs, and assistant chat map successfully.
- Visible stability/expression/speed settings do not expose stable interactive nodes in this capture; D1 does not invent selectors and defers provider-specific setting discovery to D2.
- Lifecycle log contains a clean start/completion sequence and no runtime error.

## Privacy conclusion

`BUG-20260917-006` is field-verified fixed. The V0.2 structured evidence no longer contains the script text that was visible in the editor.

## Decision

D1 is accepted for merge. Proceed to D2 Voice/Settings Catalog. Authenticated session-reuse is not a D1 blocker because the accepted field state is anonymous-ready; the persistent local profile remains available for later authenticated phases.
