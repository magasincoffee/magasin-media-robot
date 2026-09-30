# SAYDI Audiobook QA Strategy

## Objective

SAYDI must prove three things before an audiobook export is accepted:

1. **structural correctness** — the right text exists in the right order exactly once;
2. **audio correctness** — the produced audio is decodable and technically valid;
3. **traceability** — every accepted artifact can be mapped back to source text, narration configuration and QA evidence.

## Test layers

### Static / contract checks

- Python syntax/imports;
- formatting/linting;
- JSON schema validation;
- deterministic IDs/hashes;
- secret/runtime-artifact guard;
- migration compatibility checks.

### Unit tests

Pure logic including:

- source parsing helpers;
- normalization;
- number/date/unit pronunciation rules;
- segmentation boundaries;
- segment ID/hash generation;
- pronunciation-lexicon application;
- narration fingerprint;
- retry classification;
- invalidation rules;
- state transitions;
- export naming/metadata mapping.

### Provider-contract tests

Offline tests around the production Voice Engine:

- request/result validation;
- preflight behavior;
- provider-control mapping;
- one-attempt guard;
- operation-id idempotency;
- ambiguous outcome/reconciliation;
- safe error classification;
- local-path policy;
- redaction.

### Live provider smoke

Real SaydiVoice checks are intentionally scarce and explicit.

A live generation test must verify:

- authenticated preflight;
- requested voice/style state;
- exactly one authorized Generate side effect;
- terminal result classification;
- local audio download;
- decode/metadata/hash validation;
- privacy-safe diagnostics.

### Book ingest tests

For each supported format:

- deterministic chapter/block extraction;
- source hash;
- stable ordinals/IDs;
- malformed input behavior;
- no destructive source changes.

Fixtures in Git must be synthetic or public-domain.

### Long-run orchestration tests

Required scenarios:

- interruption before generation;
- interruption during generation;
- interruption after provider success before local commit;
- restart/resume;
- duplicate work suppression;
- stale lease recovery;
- partial chapter rebuild;
- cancellation;
- disk-full/permission failure;
- re-auth requirement.

### Audio processing tests

Verify:

- decode;
- expected stream shape;
- duration plausibility;
- silence handling;
- deterministic concatenation order;
- processing profile tracking;
- raw artifact immutability.

### Structural/text coverage QA

A full book must prove:

- every canonical segment has exactly one accepted audio artifact;
- no duplicate/out-of-order segment;
- accepted audio hash is the one evaluated by QA;
- alignment/ASR mismatches above threshold are reviewed or repaired.

### Acoustic QA

Detect at minimum:

- zero/near-zero audio;
- decode failure;
- suspiciously short/long duration;
- unexpected long silence;
- clipping/peak anomalies;
- inconsistent sample/channel format when prohibited by profile.

### Export validation

For each final output:

- artifact exists and is non-empty;
- container parses;
- duration is plausible;
- chapter count/order matches manifest;
- metadata matches configured book metadata;
- embedded chapter markers are valid where applicable;
- export manifest hashes the final artifacts;
- QA report hash is linked.

## Repair workflow

```text
QA FINDING
   |
   +--> deterministic processing fix -> rebuild dependent local artifacts
   |
   +--> TTS/content mismatch -> review exact segment
                                |
                                +--> regenerate only approved segment
                                |
                                +--> rerun segment QA
```

Unaffected accepted provider audio must not be regenerated.

## Privacy gate

CI and Git artifacts must never contain private production book text/audio or authentication state. Diagnostics must support structural evidence without copying sensitive content.

## Phase completion

A task exits only when its acceptance evidence is recorded and the Source of Truth advances the NEXT task.
