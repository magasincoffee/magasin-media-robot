# Next Step

## Immediate next step — orchestration integration without live Saydi side effects

The production `SaydiVoiceProvider` boundary is implemented and offline-verified on branch `feat/saydivoice-production-adapter-offline`.

Discovery Tests run `35370775036` passed with **83 tests**. No live Generate or Download was executed.

## Frozen provider contract

Request:

```text
text
preset_key
voice_override (optional)
format_override (optional)
output_directory
download_requested (explicit; default false)
generation_timeout_ms
download_timeout_ms
```

Result:

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
attempt_count
sanitized error
```

The provider validates before runtime/browser access, applies verified controls before Generate, calls Generate at most once, and never turns `retryable=true` into an implicit second attempt.

## Current night-run constraint

The approved Business OS night window forbids:

- live SaydiVoice Generate;
- live SaydiVoice Download;
- credential/session extraction;
- destructive provider actions.

Therefore the next safe step is contract-level orchestration integration and cross-project resume/isolation testing only.

## After offline orchestration/QA

A single production acceptance Generate may be requested separately by Owner. Only after that explicit authorization should the real provider path be field-accepted.

After production acceptance:

1. expose the provider through the Windows Control Center / orchestration layer;
2. hand explicitly downloaded local audio to the deterministic FFmpeg media pipeline;
3. add job-level media state/checkpoints for resume after interruption.

The authenticated persistent browser profile remains local and must never be committed or uploaded.
