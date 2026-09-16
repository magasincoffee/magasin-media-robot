# QA Strategy

## Objective

The project must detect failures early, preserve evidence, repair root causes, and prevent regressions. QA is part of each implementation step, not a final phase only.

## Test layers

### Static checks

- Python syntax/import checks.
- Formatting/linting once code exists.
- JSON/schema validation for templates, state, selectors, and reports.
- Secret/runtime-artifact guard.

### Unit tests

Pure logic: text chunking, timeline calculations, path/state logic, render-spec generation, retry policy, validation helpers, and parsing.

### Integration tests

FFmpeg/FFprobe operations, local file pipeline, browser adapter abstractions, state persistence, and resume behavior.

### Browser smoke tests

For SaydiVoice: page reachable, expected TTS surface detected, login state correctly classified, controls discoverable, generation action observable, download captured and validated. Tests must fail with screenshots/DOM evidence instead of hanging silently.

### Render validation

After every test/final render validate at minimum:

- output exists and is non-empty;
- FFprobe can parse it;
- video stream exists;
- required audio stream exists;
- width/height match target profile;
- duration is plausible against planned timeline;
- no FFmpeg non-zero exit was ignored.

### Regression tests

Every fixed reproducible bug should receive a regression check when technically reasonable.

## Failure workflow

```text
TEST
  -> PASS -> record evidence
  -> FAIL -> capture evidence -> log bug -> diagnose -> fix -> retest
                                      |                     |
                                      +------ regression ----+
```

## Diagnostic bundle

Runtime failures should be able to produce a sanitized bundle containing relevant logs, state summary, versions, screenshots/DOM snapshots where useful, command stderr/stdout summaries, and output validation results. The bundle must exclude credentials, raw cookies, tokens, and private auth material.

## Completion gate for each phase

A phase exits only when its documented acceptance criteria pass and `TEST_LOG.md` records the evidence. Known unresolved issues must remain explicitly listed in `BUG_LOG.md` and `CURRENT_STATUS.md`.
