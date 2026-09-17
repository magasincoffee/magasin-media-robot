# SaydiVoice Field Review — 2026-09-17

Source: first real Windows discovery run `20260917_011521_dcb358a9` plus operator screenshot. Raw runtime artifacts remain local/user-provided and are not committed.

## Verified

- Real SaydiVoice target opened successfully on the Windows laptop.
- V0.1 self-tests passed: 16 tests.
- Final page state: `TTS_READY`.
- Final run status: `CAPTURED` / exit code 0.
- Report recorded 37 visible interactive elements.
- The TTS editor is usable while login controls are still visible, so the first field state is **anonymous-ready**, not authenticated.
- The page displayed a free-generation quota message while anonymous.

## Visible TTS surface observed

- language selector (`VI`);
- voice selector (`Tự động` in the captured state);
- editable script surface;
- add-speaker action;
- script-import action;
- subtitle-to-speech action;
- generate button (`Tạo giọng nói`);
- settings/history tabs;
- pause selector (`Đang tắt` in the captured state);
- output format tabs: WAV, MP3, FLAC, OGG;
- assistant/chat control;
- settings labels visible for voice stability, expression, reading speed, pause behavior, and file format.

## Important privacy finding

The V0.1 structured DOM inventory persisted the text inside the contenteditable script editor. This violates the intended evidence privacy boundary even though ordinary input/textarea values were already suppressed. The exact script text is deliberately not reproduced in this repository.

Tracked as `BUG-20260917-006`. D1/V0.2 changes the browser probe and serializer so every contenteditable editor is marked and its text is suppressed before persistence.

## D1 implications

D1 should distinguish **page readiness** from **authentication state**. `TTS_READY` can occur anonymously, therefore login visibility must not be treated as a failure when the editor is usable.

The D1 surface map will emit semantic control keys and ranked locator candidates, preferring test IDs and accessible role/name locators before fallbacks. The first V0.1 artifact did not expose stable nodes for all visual sliders, so slider resolution remains a live-pass item for V0.2 rather than being guessed from the screenshot.
