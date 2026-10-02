# SAYDI-002 Temporary Execution Source of Truth

Last updated: 2026-10-02

## Purpose

This file is the temporary execution authority for decomposing and completing **SAYDI-002 — Executable vertical slice + provider/AI contracts**.

Project-level authority remains:

`00_PROJECT/SOURCE_OF_TRUTH.md`

This temporary source MUST NOT redefine product architecture, scope, privacy policy, or the authoritative project task queue. It only decomposes the currently authoritative project task `SAYDI-002` into robot-executable steps.

When all tasks in this file are complete and `SAYDI-002` is closed in the main Source of Truth, this temporary file should be deleted to avoid stale parallel state.

## Current verified state

- Architecture generation: `SAYDI-AUDIOBOOK-V1.2`.
- Main authoritative task: `SAYDI-002`.
- Windows SAPI vertical workflow mechanics: PASS.
- Windows SAPI production narration quality: REJECT.
- Production-quality validation path: SaydiVoice.
- Discovery Tests run `36755846022`: PASS.
- SaydiVoice audiobook sample run `36755899556`: FAIL.
- Failure boundary: persistent SaydiVoice browser profile remained `auth=ANONYMOUS`.
- The failed run explicitly stopped before Generate.
- No live Generate side effect occurred in run `36755899556`.
- No MP3 transfer artifact was produced.
- Related open defect: `BUG-20260917-009 — Anonymous Saydi session bootstrap rejected before generation`.

## Execution rules

1. Re-read this file from the beginning before every robot cycle.
2. Re-read `00_PROJECT/SOURCE_OF_TRUTH.md` only when required to validate that `SAYDI-002` is still the project-level authoritative task.
3. Execute exactly one task from the queue at a time.
4. Never skip ahead because a later task appears easier.
5. Do not rebuild already field-verified SaydiVoice discovery behavior from scratch.
6. Keep provider/browser automation outside audiobook-domain logic.
7. Keep browser profiles, credentials, generated audio, runtime state, and manuscript content out of Git.
8. Use synthetic or public-domain text for live validation.
9. No Generate action is allowed during authentication/profile recovery or preflight tasks.
10. If a task requires owner interaction that the robot cannot perform safely (for example manual SaydiVoice login), return `BLOCKED` with the exact minimum owner action. Do not misclassify that as a technical failure.
11. A live Generate task must be bounded to exactly one intended sample. Do not blindly retry after an uncertain side effect.
12. Never expose credentials, cookies, profile data, tokens, manuscript/private text, or unsafe browser evidence in GitHub logs/artifacts.
13. Completion requires concrete evidence: test output, workflow run, persisted sanitized metadata, or equivalent inspectable proof.
14. Do not mark `SAYDI-002` complete until all tasks in this temporary queue are DONE and the completion gate below is satisfied.

## Task queue

### SAYDI002-001 — Recover authenticated persistent SaydiVoice profile

Status: **NEXT**

Goal:
Restore the trusted Windows self-hosted runner's SaydiVoice persistent browser profile so the non-generative preflight can prove an authenticated session.

Required work:
- identify the exact profile path/account context used by the workflow;
- verify the workflow and helper scripts are opening that same persistent profile;
- remove any logic that accidentally creates/uses a fresh anonymous profile;
- preserve the profile locally only;
- open/prepare the visible browser for manual login only if required;
- after login state exists, verify the robot detects authenticated state without clicking Generate.

Acceptance:
- same trusted Windows runner;
- persistent profile is reused across process restarts;
- authenticated state is detected explicitly rather than inferred from page load alone;
- voice/catalog surface needed by the adapter is accessible;
- no Generate click;
- no quota-consuming TTS side effect;
- no cookies/tokens/profile files enter Git or artifacts;
- sanitized evidence is recorded.

If manual login is required:
- robot returns `BLOCKED`;
- report exactly where the owner must log in;
- after owner login, the same task resumes and must verify persistence before it can be DONE.

### SAYDI002-002 — Freeze SaydiVoice VoiceProvider adapter contract

Status: PENDING

Goal:
Place SaydiVoice behind the existing provider-neutral `VoiceProvider` boundary without leaking browser/provider mechanics into the audiobook core.

Required work:
- map provider-neutral request fields to only field-verified SaydiVoice controls;
- map result/download metadata back into the provider-neutral result contract;
- keep unsupported semantic controls explicitly unsupported rather than fabricated;
- preserve narration fingerprint inputs relevant to SaydiVoice;
- implement schema/contract validation and safe failure states;
- add/update offline tests.

Acceptance:
- adapter can be exercised with mocked/non-live provider behavior;
- audiobook core does not import browser-specific SaydiVoice details;
- unsupported emotion/prosody controls are not invented;
- unit/contract tests PASS;
- no live Generate occurs in this task.

### SAYDI002-003 — Authenticated non-generative SaydiVoice preflight

Status: PENDING

Goal:
Prove the production adapter can reach the authenticated SaydiVoice surface on the trusted runner before any live generation.

Required work:
- load the persistent authenticated profile from SAYDI002-001;
- verify authenticated state;
- verify required voice/catalog/settings/output-format controls;
- prepare the exact bounded synthetic/public-domain sample request;
- emit sanitized preflight evidence.

Acceptance:
- `AUTHENTICATED` gate PASS;
- target voice/settings are resolvable;
- requested output format is resolvable;
- exactly zero Generate clicks;
- exactly zero new audio results;
- no secret/private content in logs/artifacts.

### SAYDI002-004 — Run exactly one bounded SaydiVoice narration sample

Status: PENDING

Goal:
Produce one controlled high-quality-provider audio sample through the production SaydiVoice adapter.

Preconditions:
- SAYDI002-001 DONE;
- SAYDI002-002 DONE;
- SAYDI002-003 DONE;
- all offline tests PASS;
- authenticated preflight PASS;
- sample contains no sensitive/private manuscript content.

Live side-effect boundary:
- exactly one intended Generate action;
- no automatic second Generate if completion state is uncertain;
- if the provider response is ambiguous after the click, stop and report the observed state rather than retrying blindly.

Acceptance:
- one intended live generation side effect;
- local audio file is obtained successfully;
- sanitized result metadata and file hash are recorded;
- transfer artifact may be uploaded only if it contains the authorized non-sensitive sample and no session/profile data;
- operation ID is persisted so reruns do not duplicate a known-successful generation.

### SAYDI002-005 — Operator audio approval gate

Status: PENDING

Goal:
Evaluate the SaydiVoice sample as an audiobook narrator candidate using the existing human approval model.

Evaluation dimensions:
- naturalness;
- emotional/expressive delivery;
- pace;
- intelligibility;
- obvious pronunciation defects;
- suitability for long-form listening.

Robot responsibility:
- present the produced sample/artifact and relevant settings/fingerprint;
- do not invent an operator listening verdict.

Acceptance:
- owner records `APPROVE` or `REJECT`;
- verdict is persisted with the narration fingerprint/sample identity;
- if REJECT, record the precise rejection reasons and keep SAYDI-002 open;
- if APPROVE, continue to SAYDI002-006.

If owner listening/input is required:
- return `BLOCKED` with the sample location and exact requested verdict.

### SAYDI002-006 — Close SAYDI-002 and hand off to SAYDI-003

Status: PENDING

Goal:
Reconcile evidence, close the executable vertical slice, and return authority to the main project Source of Truth.

Required work:
- verify all SAYDI002-001 through SAYDI002-005 are DONE;
- verify VoiceProvider/provider isolation, approval state, privacy, schema tests, idempotency guard, and one bounded production-provider sample evidence;
- update `00_PROJECT/SOURCE_OF_TRUTH.md` so `SAYDI-002` becomes DONE only if its acceptance criteria are actually satisfied;
- promote `SAYDI-003` as the single authoritative NEXT project task;
- update any status/changelog documents only if required and keep them subordinate to the main SOT;
- delete this temporary execution source after the authoritative SOT update is committed and verified.

Acceptance:
- `SAYDI-002 = DONE` in the main Source of Truth;
- `SAYDI-003 = NEXT`;
- no unresolved blocker from SAYDI-002 is hidden;
- main branch evidence is consistent;
- this temporary file is removed after handoff.

## Completion gate for SAYDI-002

SAYDI-002 may close only when all of the following are true:

- runnable operator-visible vertical slice exists;
- provider-neutral AnalysisProvider and VoiceProvider contracts exist;
- deterministic fallback works without an LLM;
- local-LLM adapter boundary exists;
- SaydiVoice production adapter is frozen behind VoiceProvider;
- authenticated SaydiVoice preflight passes on the trusted runner;
- narration fingerprint exists and is stable;
- text-preview approval state exists;
- audio-approval state exists;
- idempotency/duplicate-operation guard exists;
- privacy/schema/contract tests pass;
- exactly one bounded production-provider sample has completed successfully;
- operator has recorded the audio approval verdict;
- no secrets/private runtime state are committed.

## Robot control protocol

For discovery/bootstrap turns, do not execute project work. Identify exactly one authoritative next task from this temporary source.

For execution turns, validate the requested task ID against this file and execute only that task.

Machine-readable ending:

```text
MAGASIN_TASK_CONTROL_V1
STATUS=<READY|RUNNING|COMPLETE|BLOCKED|DONE>
TASK_ID=<current task id or NONE>
NEXT_TASK_ID=<next task id or NONE>
CHECK_AFTER_SECONDS=<0-3600>
END_MAGASIN_TASK_CONTROL_V1
```

Initial authoritative next task:

`SAYDI002-001`
