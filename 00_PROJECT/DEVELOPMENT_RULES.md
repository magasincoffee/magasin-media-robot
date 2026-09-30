# Development Rules

## Mandatory authority rule

Every implementation session must begin with:

1. read `00_PROJECT/SOURCE_OF_TRUTH.md` from the beginning;
2. identify the single authoritative NEXT task;
3. read only the architecture/decision/test files relevant to that task;
4. verify current `main` before changing code.

Do not choose a different task because an old README, historical status note or stale conversation suggests it.

## Mandatory implementation protocol

1. Scope work to one authoritative task.
2. Reproduce/verify current state before change where practical.
3. Define the acceptance evidence for the bounded step.
4. Implement the smallest coherent slice.
5. Run unit/static tests first.
6. Record reproducible failures in `BUG_LOG.md`.
7. Fix root cause, not only symptoms.
8. Run relevant integration/regression tests.
9. Record concrete evidence in `TEST_LOG.md`.
10. Update `SOURCE_OF_TRUTH.md`, `CURRENT_STATUS.md`, `NEXT_STEP.md` and `CHANGELOG.md` when task state changes.
11. Commit/PR a coherent change with no runtime/private artifacts.
12. Verify exact `main` after merge before declaring completion.

## Audiobook fidelity rules

- Original extracted text is immutable after ingest.
- Normalized spoken text is stored separately.
- Never silently summarize, paraphrase or omit prose.
- Every spoken segment has a stable identity and source linkage.
- Every accepted audio artifact is tied to the exact text hash + narration fingerprint.
- A book export cannot pass with unresolved missing/duplicate segments.
- Regeneration should target only invalid/failed segments when dependencies permit.
- Human pronunciation overrides are versioned and auditable.

## Provider automation rules

- SaydiVoice is an adapter behind `05_VOICE_ENGINE`.
- Prefer Playwright semantic locators and field-verified controls.
- Run authenticated preflight before side effects.
- A Generate action is a controlled side effect.
- Do not automatically click Generate twice for an ambiguous result.
- Use operation IDs and reconciliation before retry.
- Never log passwords, raw cookies, auth tokens or raw session storage.
- Persistent browser profiles remain local.

## Audio rules

- FFmpeg/FFprobe are the technical processing/validation source of truth.
- Raw provider audio is immutable after acceptance.
- Processing writes derivatives.
- Do not hide decode errors, clipping, impossible duration or missing streams.
- Mastering/loudness settings are explicit export profiles, not undocumented constants.
- Destructive modification of source books or accepted raw voice artifacts is forbidden.

## State/resume rules

- Long-form production must use durable state.
- A file existing is not enough to mark a task complete.
- Persist state transitions and artifact hashes.
- Idempotent steps must be safe to rerun.
- Unsafe/ambiguous provider operations enter reconciliation rather than blind retry.

## Test and fixture rules

- Use synthetic/public-domain test text in Git.
- Never commit private books or generated production audio.
- Every fixed reproducible bug should receive a regression test where technically reasonable.
- Long-run/resume tests are required before production completion.

## Dependency rules

- Pin production dependencies.
- Keep provider/site integrations replaceable.
- Prefer local reproducible tooling.
- Add heavy models only when a measured requirement/performance budget justifies them.

## Secrets and privacy

Never commit:

- `.env` / local secrets;
- passwords/tokens;
- cookies/browser profiles;
- source manuscripts;
- generated private audio;
- local production databases;
- diagnostics containing private text/audio.

## Change discipline

- Keep changes scoped to the authoritative task.
- Record architecture changes in `DECISIONS.md`.
- Do not silently change data contracts.
- Version schemas/contracts when compatibility changes.
- Do not revive the paused video track unless `SOURCE_OF_TRUTH.md` is deliberately updated.
