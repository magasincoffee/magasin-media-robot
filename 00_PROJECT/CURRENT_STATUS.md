# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery. V0.1 runner is merged to `main` and unit/CI verified; first real Windows/SaydiVoice smoke test is the current gate.**

## Completed

- Repository/project architecture and durable continuation records established.
- SaydiVoice Discovery Runner V0.1 merged through PR #1.
- Main implementation merge commit: `f5d35eb157b26ca0425267979be2d32e359b7f55`.
- Python package and CLI created.
- Playwright persistent-profile browser runner created; browser is visible by default.
- Local runtime policy implemented under `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice`.
- Basic states implemented: `TTS_READY`, `LOGIN_REQUIRED`, `ACCESS_BLOCKED`, `UNKNOWN`, plus `BROWSER_ERROR` run status.
- Manual login support added: `RUN_DISCOVERY.bat` waits up to 180 seconds when login is required so the user can authenticate in the robot browser; credentials are not automated or committed.
- Local screenshot, sanitized DOM inventory, structured discovery report, JSONL logs, and explicit exit codes implemented.
- Privacy safeguards implemented for editor values, URLs/query strings, token-like text, emails, cookies/storage/auth-header boundaries.
- Windows setup/run scripts implemented.
- Regression tests implemented: 16 local tests PASS.
- PR Windows CI run `35130561175`: PASS.
- Post-merge `main` Windows CI run `35130819104`: PASS for merge commit `f5d35eb157b26ca0425267979be2d32e359b7f55`.
- Five defects discovered during self-test/review were fixed and recorded in `BUG_LOG.md`.

## Pending before D0 field verification

- Run `SETUP_DISCOVERY.bat` once on the target Windows laptop.
- Run `RUN_DISCOVERY.bat` against the real SaydiVoice Studio page.
- If login is required, complete login manually inside the Chromium window opened by the runner; the local profile will be reused.
- Review the generated local `discovery_report_*.json`, `dom_inventory.json`, screenshot, and log.
- Confirm the page is classified correctly and that the evidence is sufficient to begin D1 surface mapping.

## Not yet implemented

- D1 complete surface/locator map.
- D2 voice/settings catalog.
- D3 generation lifecycle automation/observation.
- D4 audio download discovery.
- D5 controlled limits/error characterization.
- D6 frozen discovery contracts.
- Production Voice Engine.
- Media Analyzer, Scene Planner, Subtitle Engine, Render Engine, Desktop UI, full diagnostics/resume runtime, and installer.

## Known environment limitation

The coding sandbox used for V0.1 blocks Chromium navigation by administrator policy (`ERR_BLOCKED_BY_ADMINISTRATOR`), including local/data navigation. For that reason the actual SaydiVoice browser smoke cannot be truthfully claimed as completed there; it must be run on the target Windows laptop. Pure logic, orchestration behavior, package compilation/import, PR CI, and post-merge `main` CI are verified.

## Repository visibility risk

GitHub metadata still reports the repository as **public**. No passwords, cookies, tokens, browser profiles, private media, or generated private artifacts have been committed. If the project is intended to remain private, change repository visibility in GitHub settings before any sensitive material is ever added.

## Current active objective

Field-verify SaydiVoice Discovery Runner V0.1 on the target Windows laptop, then use the first real discovery evidence to implement D1 — Surface Map.
