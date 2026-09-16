# Development Rules

## Mandatory session protocol

Every implementation session must follow this order:

1. Read `CURRENT_STATUS.md` and `NEXT_STEP.md`.
2. Read relevant decisions, bugs, tests, and recent changes.
3. Reproduce/verify the current state before changing code when practical.
4. Implement one bounded step.
5. Run the smallest relevant tests first.
6. If a test fails, record the failure in `BUG_LOG.md` before or while fixing it.
7. Fix the root cause, not only the observed symptom.
8. Re-run the failed test and relevant regression tests.
9. Record test evidence in `TEST_LOG.md`.
10. Update `CHANGELOG.md`, `CURRENT_STATUS.md`, and `NEXT_STEP.md`.
11. Commit a coherent change with no secrets or runtime artifacts.

## Continuation contract

When the user says **“Tiếp tục dự án magasin-media-robot”**, the repository is the source of truth. Do not rely on stale chat memory when repository status disagrees.

## Quality gates

A step is not complete because code was written. It is complete only when:

- intended behavior is implemented;
- relevant tests pass;
- known failure paths are handled or documented;
- logs/state are updated;
- the next step is explicit.

## Browser automation rules

- Prefer Playwright semantic locators: role, label, accessible name, stable text, stable data attributes.
- Avoid brittle generated IDs/classes where possible.
- Use a locator fallback strategy when justified.
- Capture evidence when discovery or browser smoke tests fail.
- Never log passwords, raw cookies, tokens, or authorization headers.
- Persistent browser profiles are local runtime data and must never enter Git.

## Media rules

- FFmpeg/FFprobe are the rendering/inspection source of truth.
- Rendering must be deterministic for the same render specification and source assets where codecs permit.
- Every final artifact must be validated after render.
- Destructive changes to source media are forbidden; create outputs in project working/output directories.

## Dependency rules

- Pin production dependencies once implementation begins.
- Keep browser/site integrations behind adapters.
- Prefer local, reproducible dependencies over manual GUI applications.
- Do not add heavy AI models until a concrete requirement and performance budget justify them.

## Secrets and privacy

Never commit: `config.local.json`, `.env`, browser profiles, cookies, tokens, credentials, downloaded customer/private media, generated private audio/video, or diagnostic dumps containing sensitive data.

## Change discipline

- Keep changes scoped.
- Record architectural choices in `DECISIONS.md`.
- Record recurring or significant bugs in `BUG_LOG.md`.
- Do not silently change documented behavior; update architecture/roadmap/status as needed.
