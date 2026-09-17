# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery. The first real Windows artifact set has now been reviewed. D1 Surface Map/V0.2 is implemented on branch `feat/saydivoice-d1-surface-map`, code/CI verified, and awaits one live V0.2 rerun on the target laptop before merge.**

## Completed

- Repository/project architecture and durable continuation records established.
- SaydiVoice Discovery Runner V0.1 merged through PR #1.
- Main implementation merge commit: `f5d35eb157b26ca0425267979be2d32e359b7f55`.
- Python package, CLI, visible Playwright Chromium, persistent local browser profile, structured report/logging, and Windows setup/run scripts implemented.
- V0.1 regression suite: 16 tests PASS; PR and post-merge Windows CI PASS.
- First real Windows field run succeeded: run `20260917_011521_dcb358a9`, `TTS_READY`, `CAPTURED`, exit code `0`.
- Uploaded field artifacts reviewed: discovery report, screenshot, DOM inventory, and JSONL log.
- The first field state is anonymous-ready: the TTS editor is usable while login controls remain visible.
- 37 visible interactive elements were captured in the V0.1 DOM inventory.
- Verified visible TTS controls include language selector, automatic voice selector, script editor, add-speaker, import-script, subtitle-to-voice, Generate, Settings/History, pause selector, WAV/MP3/FLAC/OGG format tabs, and assistant/chat control.
- D1/V0.2 surface-mapping implementation added on branch `feat/saydivoice-d1-surface-map`.
- D1 outputs include `saydi_map.json` and `selectors.json` with semantic control keys and ranked locator candidates.
- D1 distinguishes page readiness from authentication state so anonymous-ready is not misclassified as login failure.
- D1 branch Windows Actions run `35172844321`: PASS through dependency install, compile, and unit-test steps.
- D1 suite contains 23 tests and includes privacy and locator regression coverage.

## Field defect found and fixed in V0.2

The V0.1 DOM inventory persisted text from the contenteditable script editor. This violated the intended privacy boundary even though input/textarea values were already suppressed.

- Tracked as `BUG-20260917-006`.
- V0.2 blanks text from contenteditable controls in the browser probe and serializer.
- Regression test added and Windows CI passes.
- A live V0.2 artifact is still required to verify the fix on the real SaydiVoice page.

A second semantic issue was also fixed: anonymous login explanatory copy mentioning history could be confused with the actual History tab. This is tracked as `BUG-20260917-007`; login controls now receive priority over generic label matching.

## Pending before D1 merge

- Run the updated V0.2 discovery package on the target Windows laptop.
- Confirm the new DOM inventory no longer persists script/editor text.
- Confirm `saydi_map.json` and `selectors.json` are generated.
- Review unresolved visual sliders/settings controls from the new live pass.
- Run the discovery a second time while the same browser session remains valid to confirm persistent-profile reuse behavior.
- If the live artifact/privacy checks pass, merge D1/V0.2 and advance to D2 Voice/Settings Catalog.

## Not yet implemented

- D2 complete voice/settings catalog.
- D3 generation lifecycle automation/observation.
- D4 audio download discovery.
- D5 controlled limits/error characterization.
- D6 frozen discovery contracts.
- Production Voice Engine.
- Media Analyzer, Scene Planner, Subtitle Engine, Render Engine, Desktop UI, full diagnostics/resume runtime, and installer.

## Repository visibility risk

GitHub metadata still reports the repository as **public**. No passwords, cookies, browser profiles, auth tokens, private media, or generated private artifacts are committed. Keep local runtime evidence/session data out of Git.

## Current active objective

Package and run D1/V0.2 on the target Windows laptop, verify the privacy fix and surface-map outputs against the real SaydiVoice page, then merge D1 and proceed to D2.
