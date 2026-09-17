# Next Step

## Immediate next step — freeze D6 and start the production SaydiVoice adapter

D1–D5 are now sufficiently field-verified on the authenticated `MAGASIN-PC` path. Do not spend more generation quota merely to repeat already accepted discovery evidence.

## D6 gate

The frozen contract is `01_DISCOVERY/saydivoice/contracts/saydivoice_contract_v1.json` and must be treated as the integration boundary for the first production adapter.

Before moving on:

1. contract JSON parses and contract tests pass;
2. Generate and Download remain separate explicit gates;
3. the 20,000-character boundary is enforced before provider generation;
4. no blind retry is introduced;
5. profile/auth state remains local to the runner;
6. raw generated audio is never staged into the public GitHub artifacts;
7. editor/user text remains outside structured discovery evidence.

## Production adapter scope after D6

Build a narrow provider adapter instead of extending the discovery runner indefinitely. The adapter should expose a stable application-facing interface such as:

- session readiness check;
- voice selection by catalog identity/label;
- stability/expression, speed, pause and format configuration;
- text validation (1–20,000 characters per provider request);
- one explicitly authorized generation operation;
- observable lifecycle state (`processing`, `success`, `error`, `needs_reauth`);
- one explicitly authorized download/materialization operation;
- privacy-safe diagnostics and bounded timeouts.

The adapter should not embed application-level text splitting, content rewriting, retry storms, quota exhaustion behavior, or authentication bypasses. Those policies belong in higher layers.

## Rediscovery rule

Do not re-run D1–D5 on every change. Increment the contract version and rediscover only when a material provider change invalidates a frozen assumption, for example:

- TTS page/session state changes;
- key locator/accessible-name changes;
- voice selection semantics change;
- slider/format controls change;
- generation success/error lifecycle changes;
- download mechanism changes;
- the 20,000-character limit changes;
- privacy-safe endpoint behavior materially changes.

This keeps future provider testing bounded, reproducible and quota-conscious.
