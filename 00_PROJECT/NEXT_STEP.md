# Next Step

## Read first

The authoritative project state is `00_PROJECT/SOURCE_OF_TRUTH.md`.

## NEXT — SAYDI-002: Production SaydiVoice provider adapter

The discovery phase already proved the real authenticated provider path. The next step is to freeze that evidence into a production adapter used by the audiobook pipeline.

## Objective

Implement a provider-neutral boundary that can safely synthesize one canonical audiobook segment through SaydiVoice and return a durable local result.

## Required contract

Input must be equivalent to:

```text
operation_id
segment_id
text
narration_fingerprint
voice_key
style_key
provider_controls
output_format
output_directory
```

Output must be equivalent to:

```text
operation_id
segment_id
status
provider
provider_voice
local_audio_path
audio_sha256
byte_count
duration_ms
provider_reference
attempt
error_class
retryable
```

Exact schemas may evolve during implementation, but audiobook-domain code must not depend directly on browser selectors or raw SaydiVoice UI concepts.

## Required behavior

1. Reuse the local authenticated Chrome profile.
2. Run authenticated preflight before any live side effect.
3. Resolve/validate voice and style before Generate.
4. Apply controls and verify observed state.
5. Enforce one provider Generate side effect per `operation_id`.
6. Persist/reconcile ambiguous outcomes before any second attempt.
7. Download only into approved local project storage.
8. Validate the resulting audio and compute metadata/hash.
9. Classify failures as `fix_input`, `re_auth`, `retry_safe`, `reconcile_first`, or `do_not_retry`.
10. Never upload production audio, book text, browser profile, cookies or credentials.
11. Expose privacy-safe structured diagnostics.
12. Preserve existing discovery tooling as evidence/test support rather than mixing it into production code.

## Offline acceptance before live generation

Complete automated tests for:

- request/result validation;
- narration/profile mapping;
- authenticated-preflight failure;
- one-attempt guard;
- operation-id idempotency;
- ambiguous-outcome reconciliation state;
- timeout/error classification;
- local output-path policy;
- metadata/hash handling;
- privacy/redaction.

## Live acceptance

After offline tests pass, perform one explicitly authorized real generation using non-sensitive test text.

Pass criteria:

- exactly one intended Generate side effect;
- audio downloaded locally;
- audio decodes;
- byte count/duration/hash recorded;
- provider result persisted;
- no sensitive runtime state in Git/CI artifacts.

## After SAYDI-002

Proceed only to `SAYDI-003 — Book ingest + canonical manifest`.
