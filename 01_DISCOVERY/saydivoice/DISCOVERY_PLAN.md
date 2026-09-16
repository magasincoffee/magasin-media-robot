# SaydiVoice Discovery Plan

## Stage D0 — Runner foundation

Build visible Playwright runner with persistent local browser profile, run IDs, safe runtime directories, structured logging, screenshots, and JSON report serialization.

Acceptance: target page opens; basic state is classified; evidence is captured; no credentials/session secrets are written to repository or logs.

## Stage D1 — Surface map

Discover page landmarks, main input surface, buttons, comboboxes, sliders, tabs, dialogs, alerts, and accessible metadata. Export candidate locators with preference order: role/label/name -> stable text/data attributes -> CSS fallback.

Acceptance: report can identify the primary TTS surface and enumerate visible interactive controls.

## Stage D2 — Voice/settings catalog

Open relevant selectors without changing persistent settings unnecessarily. Record voices/options/settings exposed by the current UI and their labels/values.

Acceptance: structured catalog can be consumed later by the Voice Engine configuration layer.

## Stage D3 — Generation lifecycle

Using a short harmless Vietnamese test sentence, observe input, Generate action, loading/progress/success/error states, preview, and resulting audio metadata. This stage starts only after D0-D2 are verified.

Acceptance: generation state machine and completion signal are known.

## Stage D4 — Download behavior

Capture Playwright download event, suggested filename, extension, byte size, and audio validation result. Determine whether MP3/WAV selection exists and how it behaves.

Acceptance: a generated test audio file can be downloaded and validated deterministically.

## Stage D5 — Limits and error states

Test controlled text sizes and selected recoverable error scenarios. Avoid abuse, high request volumes, or bypassing provider safeguards. Record provider-visible limits rather than attempting to circumvent them.

Acceptance: chunking/retry requirements are known well enough for production adapter design.

## Stage D6 — Discovery report freeze

Produce sanitized artifacts:

- `saydi_map.json`
- `selectors.json`
- `settings_schema.json`
- `voice_catalog.json`
- `download_behavior.json`
- `error_states.json`
- discovery report and test log.

Acceptance: Voice Engine implementation can proceed without guessing UI behavior.

## Test text

Default harmless probe text for the generation stage:

`Xin chào, đây là bản kiểm tra giọng đọc của MAGASIN Media Robot.`

Use a short probe first. Longer-text tests are separate and controlled.
