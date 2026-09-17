# Next Step

## Immediate next step — freeze preset controls and build the production SaydiVoice provider adapter

Authenticated live discovery has now proven the complete control path required for production: session reuse, voice/settings control, one-shot generation, and download lifecycle. The next phase is implementation against those observed contracts rather than further exploratory Generate runs.

## Current validated baseline

- Runner: `MAGASIN-PC` (`self-hosted`, `Windows`, `X64`).
- Browser: installed Google Chrome controlled by Playwright.
- Persistent profile: `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\browser_profile`.
- Session: `TTS_READY` + `AUTHENTICATED_OR_HIDDEN`.
- Voice: deterministic selection/verification supported.
- Style controls: stability/expression ratio, speed ratio, pause enable, and audio format supported.
- Application-level presets exist for common delivery styles; no separate discrete provider mood selector was observed.
- One-shot generation returns HTTP 200 `audio/mpeg` and creates history successfully.
- Download lifecycle is field-verified and raw audio can remain local.
- `tiktok_energetic` real generation run `35241844708` passed with exactly one Generate and zero Download clicks.

## Production adapter objective

Create a provider boundary that accepts a stable request similar to:

```text
text
preset_key
voice_override (optional)
format_override (optional)
output_directory
```

and returns a structured result similar to:

```text
status
provider
voice
preset_key
format
local_audio_path
byte_count
sha256
provider_history_created
error_class
retryable
```

## Required behavior

1. Reuse the local authenticated Chrome profile; never serialize credentials or cookies.
2. Run an authenticated preflight before any side effect.
3. Resolve and validate the requested preset before touching the live page.
4. Apply voice/style controls and verify observed state before Generate.
5. Enforce exactly one Generate attempt unless a caller explicitly authorizes a separate retry policy.
6. Wait for a verified terminal success/error signal with a bounded timeout.
7. Download only when requested by the production operation.
8. Keep generated audio local; GitHub artifacts may contain metadata/screenshots only.
9. Classify failures as `fix_input`, `re_auth`, `retry`, or `do_not_retry`.
10. Preserve the existing safe evidence/redaction boundary.

## Acceptance gate for the adapter

Before another live Generate is requested, complete all offline/unit verification for:

- preset validation;
- request/result models;
- preflight failure handling;
- one-attempt guard;
- timeout/error classification;
- output-path and metadata handling;
- privacy/redaction tests.

A final end-to-end production acceptance Generate may be requested separately only after these tests pass.

## After the provider adapter

1. Expose the adapter through the Windows Control Center / orchestration layer.
2. Hand local audio into the deterministic FFmpeg media pipeline.
3. Add job-level logging/state so media projects can resume safely after interruption.

No additional operator ZIP round-trip is required while the self-hosted runner is online.
