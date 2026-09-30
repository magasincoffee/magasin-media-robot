# Current Status

Last updated: 2026-09-30

## Authoritative pointer

Read `00_PROJECT/SOURCE_OF_TRUTH.md` first. It is the single authoritative project state for the active SAYDI Audiobook track.

## Overall state

**SAYDI-AUDIOBOOK-V1.2 architecture is established.** The repository is being reset from a video-first product direction to an audiobook-first product while preserving the already field-verified SaydiVoice discovery foundation.

The repository currently contains production-relevant provider discovery, but the new audiobook book/text/orchestration/audio/export modules are not yet implemented.

## Reused verified foundation

The following SaydiVoice behavior has already been field-verified on the trusted Windows path and is intentionally retained:

- persistent authenticated Chrome profile;
- self-hosted Windows execution;
- voice catalog discovery;
- voice selection;
- stability/expression and speed controls;
- pause control;
- MP3/WAV/FLAC/OGG selection;
- authenticated preflight;
- controlled one-shot generation;
- controlled download;
- application-level style presets;
- privacy-safe evidence boundary.

Historical verified runs and detailed evidence remain documented in this repository. They are provider evidence, not the active product architecture.

## Product pivot

Active product:

**SAYDI Audiobook — professional long-form audiobook production.**

Primary production chain:

```text
Book ingest
 -> canonical manifest
 -> normalization/segmentation
 -> narration plan
 -> sample approval
 -> segment synthesis
 -> audio processing/assembly
 -> alignment/acoustic QA
 -> repair exceptions
 -> M4B / chapter MP3 export
```

The prior social-video pipeline is paused and must not drive new implementation work unless the Source of Truth explicitly reactivates it.

## Architecture state

Defined:

- single Source of Truth;
- audiobook domain model;
- module boundaries;
- stable data-contract direction;
- segment-addressed idempotency model;
- durable state/resume model;
- QA-before-export rule;
- local-first privacy boundary;
- task queue SAYDI-001 through SAYDI-011;
- local-LLM-first intelligence policy with optional cloud fallback;
- no-mandatory-paid-provider requirement;
- book intelligence -> segment intelligence hierarchy;
- separate text-preview and audio-sample approval gates;
- executable-vertical-slice development strategy.

## Implementation state

Not yet implemented for the audiobook track:

- production SaydiVoice provider adapter;
- book ingestion;
- canonical book manifest;
- text normalization/segmentation;
- narration director;
- audiobook state database/orchestrator;
- audio assembly/mastering;
- alignment/acoustic QA;
- M4B/chapter-MP3 export;
- audiobook desktop UX;
- clean-machine installer.

## Current task state

- `SAYDI-001` — architecture + single Source of Truth: complete with this architecture change.
- `SAYDI-002` — executable vertical slice + provider/AI contracts: **NEXT**.

No later task should be treated as active until `SAYDI-002` produces a runnable, bounded audible-sample workflow and reaches its acceptance gate, or the Source of Truth is deliberately changed.
