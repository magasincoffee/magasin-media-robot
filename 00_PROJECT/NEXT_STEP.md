# Next Step

## Read first

The authoritative project state is `00_PROJECT/SOURCE_OF_TRUTH.md`.

## NEXT — SAYDI-002: Executable vertical slice + provider/AI contracts

The immediate goal is **not** to build every audiobook module in isolation. The goal is to make the project runnable early so the operator can see the real workflow, hear a real sample, and validate the contracts before the system scales.

## First runnable workflow

```text
small synthetic/public-domain input
 -> canonical text
 -> original / normalized / spoken layers
 -> simple structured book profile
 -> representative sample selection
 -> text preview
 -> narration fingerprint
 -> real VoiceProvider sample
 -> listen
 -> APPROVE / REJECT
 -> durable run state
```

A CLI/operator runner is acceptable. Desktop UI is not required yet.

## Required architecture contracts

### AnalysisProvider

Must support structured analysis without coupling the domain to one model.

Target adapters:

- deterministic/rule fallback;
- local LLM adapter as the default semantic path;
- optional ChatGPT/cloud adapter later, disabled by default.

AI output must be schema-validated before it can influence production state.

### VoiceProvider

Must expose a provider-neutral request/result contract.

First real provider path:

- field-verified SaydiVoice adapter.

V1 production later also requires an all-local TTS adapter so paid/cloud services are never mandatory.

## Required implementation behavior

1. Create the minimal audiobook package/runner rather than only documentation.
2. Keep provider/browser details outside audiobook-domain logic.
3. Persist operation IDs and approval state.
4. Build a narration fingerprint before audio generation.
5. Separate text approval from audio/voice approval.
6. Make reruns idempotent where possible.
7. Never send manuscript text to cloud AI unless explicitly enabled.
8. Keep all production text/audio local by default.
9. Use synthetic/public-domain fixtures in Git.
10. Emit inspectable JSON/log artifacts for each run.

## Offline acceptance before any real voice side effect

- AnalysisProvider schema tests;
- VoiceProvider request/result tests;
- narration-fingerprint stability tests;
- approval invalidation tests;
- operation-id duplicate guard;
- privacy/redaction tests;
- runner smoke test using fixtures;
- deterministic behavior with no LLM available.

## Current implementation checkpoint

Completed offline:

- core runner exists;
- rules AnalysisProvider exists;
- local Ollama adapter boundary exists;
- VoiceProvider contract exists;
- Windows SAPI local prototype exists;
- text/audio approval state exists;
- duplicate successful voice operation is reused;
- local development compile + 5 unit tests PASS;
- offline prepare + text-approve smoke PASS.

Next inside the same SAYDI-002 task:

1. let GitHub Windows CI validate the branch;
2. run the manual self-hosted `SAYDI Local Audible Sample` workflow on the trusted Windows machine to produce a local WAV sample;
3. listen to that sample and validate the approval flow;
4. implement/freeze the production SaydiVoice adapter behind the same VoiceProvider contract;
5. only then close SAYDI-002.

## Bounded live acceptance

After offline gates pass, run one non-sensitive sample through a real voice path. The first zero-cost field run may use Windows SAPI solely to validate workflow mechanics; production narrator quality is evaluated separately.

Pass criteria:

- one intended generation side effect;
- audible local file produced;
- result metadata/hash recorded;
- operator can mark APPROVE or REJECT;
- rerun does not blindly generate a duplicate;
- no secret/private content in Git artifacts.

## After SAYDI-002

Proceed to `SAYDI-003 — PDF-first book ingest + canonical manifest`, keeping the vertical runner alive and extending it rather than replacing it.
