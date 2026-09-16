# Local smoke-test note

The implementation environment used for V0.1 can run Python/pytest, but its Chromium navigation is restricted by administrator policy (`ERR_BLOCKED_BY_ADMINISTRATOR`) even for local/data URLs. Therefore the browser navigation portion could not be verified end-to-end in that environment.

What was verified locally before PR:

- Python package compiles.
- Unit/orchestration tests pass.
- Package installs/imports with existing local build tooling.
- Playwright launch path and cleanup code are covered by mocked orchestration tests.

The first real SaydiVoice browser smoke test must run on the target Windows laptop after `SETUP_DISCOVERY.bat` installs Playwright Chromium. This is an expected deployment verification step, not a reason to bypass provider safeguards or use stored credentials.
