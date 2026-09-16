# Current Status

Last updated: 2026-09-17

## Overall state

**Phase 0 — SaydiVoice Discovery. V0.1 runner is merged, unit/CI verified, and the first real Windows/SaydiVoice field run reached `TTS_READY` / `CAPTURED`. Artifact review and a session-reuse rerun remain before D0 is fully closed.**

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
- First real Windows field run observed from operator screenshot: Playwright Chromium installed, bundled tests `16 passed`, run ID `20260917_011521_dcb358a9`, final `State: TTS_READY`, `Status: CAPTURED`, process status `0`.
- Field report path shown by runner: `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\reports\discovery_report_20260917_011521_dcb358a9.json`.

## Pending before D0 field verification is fully closed

- Review the generated local artifacts for run `20260917_011521_dcb358a9`:
  - `reports\discovery_report_20260917_011521_dcb358a9.json`
  - `runs\20260917_011521_dcb358a9\dom_inventory.json`
  - `screenshots\saydivoice_20260917_011521_dcb358a9.png`
  - `logs\discovery_20260917_011521_dcb358a9.jsonl`
- Confirm the evidence contains no intentionally captured password/input values, raw cookies/storage/auth headers, or query/fragment secrets.
- Run `RUN_DISCOVERY.bat` once more while the current SaydiVoice session remains valid and confirm it reaches `TTS_READY` without requiring a new login.
- Once those checks pass, mark D0 field verification complete and begin D1 Surface Map.

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

The coding sandbox used for V0.1 blocks Chromium navigation by administrator policy (`ERR_BLOCKED_BY_ADMINISTRATOR`). The first real-browser field evidence therefore comes from the target Windows laptop. Pure logic, orchestration behavior, package compilation/import, PR CI, post-merge `main` CI, and one successful real Windows run are now verified.

## Repository visibility risk

GitHub metadata still reports the repository as **public**. No passwords, cookies, tokens, browser profiles, private media, or generated private artifacts have been committed. If the project is intended to remain private, change repository visibility in GitHub settings before any sensitive material is ever added.

## Current active objective

Review the first real local discovery artifact set and verify persistent-session reuse, then implement D1 — Surface Map from the real SaydiVoice evidence.
