# Next Step

## Immediate next implementation

Build **SaydiVoice Discovery Runner V0.1**.

### Required scope

1. Create the Python project/package skeleton for discovery.
2. Add local runtime path policy under `%LOCALAPPDATA%/MAGASIN/MediaRobot/` so browser profiles/logs/screenshots/downloads are not stored in Git.
3. Add configuration for the SaydiVoice TTS URL: `https://voice.saydi.ai/vi/studio/tts/`.
4. Launch Playwright Chromium in visible mode with a persistent local profile.
5. Detect and classify basic page/login state without entering credentials automatically.
6. Capture a sanitized screenshot + HTML/DOM-oriented evidence sufficient for later selector analysis.
7. Export an initial structured `discovery_report.json`.
8. Add logging and explicit exit states.
9. Add tests for non-browser pure logic and configuration/state serialization.
10. Run tests, fix failures, update `BUG_LOG.md`, `TEST_LOG.md`, `CHANGELOG.md`, `CURRENT_STATUS.md`, then replace this file with the next concrete step.

## Acceptance gate

The step is complete only when the runner starts reliably on Windows-oriented paths, opens the target page with a persistent profile, records a structured discovery result without leaking secrets, and all implemented automated tests pass.

## Out of scope for this step

Do not yet automate voice generation, click Generate, download audio, benchmark long text, or implement the production Voice Engine. Those follow after the first discovery pass verifies the real page structure.
