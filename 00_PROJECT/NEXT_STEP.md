# Next Step

## Immediate next step — `02_VOICE_ENGINE` production interface

SaydiVoice discovery D0–D6 is complete and contract v1 is frozen. Do not extend the discovery runner unless a material provider change invalidates a frozen assumption.

## Bounded implementation step V1

Create `02_VOICE_ENGINE` with a provider-neutral core before adding live Playwright control.

V1 should define and unit-test:

1. **Domain models**
   - voice request/configuration;
   - output format;
   - generation lifecycle status;
   - provider error/action classification.
2. **Provider interface**
   - session readiness;
   - validate request;
   - configure/select voice;
   - generate;
   - materialize/download result.
3. **Frozen Saydi contract loader**
   - consume `01_DISCOVERY/saydivoice/contracts/saydivoice_contract_v1.json`;
   - expose the 1–20,000 character boundary and safety gates without duplicating magic values.
4. **Validation policy**
   - reject empty input;
   - reject >20,000 characters rather than silently relying on Saydi UI clamp;
   - reject unsupported formats/settings before browser interaction.
5. **Failure model**
   - `SUCCESS`;
   - `RETRYABLE_FAILURE`;
   - `ACTION_REQUIRED`;
   - `FATAL_FAILURE`;
   - explicit `needs_reauth`/fix-input semantics where appropriate.

This first step must be pure/unit-testable and must not open Chrome, Generate, Download, or touch quota.

## Next bounded step after the core passes

Implement a Saydi Playwright adapter that satisfies the provider interface and contract v1. Start with read-only session/configuration smoke tests. Live Generate/Download integration tests remain separately gated and should reuse previously verified evidence unless a code path materially changes.

## Non-goals for V1 core

- no application-level text splitting/chunking policy;
- no content rewriting;
- no retry storms;
- no quota/rate-limit exhaustion tests;
- no authentication bypass;
- no raw cookies/profile/media in repository or artifacts;
- no desktop UI yet.

## Rediscovery rule

Increment the Saydi contract and re-run only the minimum discovery needed if a material provider change affects session state, locators, control semantics, generation/download lifecycle, provider errors, privacy behavior, or the 20,000-character boundary.
