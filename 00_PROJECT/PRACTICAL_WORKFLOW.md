# SAYDI Practical Workflow — First Runnable Path

This document supports the Source of Truth. The Source of Truth remains authoritative.

## Why this exists

The project must expose the real workflow early so implementation decisions are based on actual runs rather than architecture assumptions.

## Operator flow — first usable slice

```text
1. Select a small supported input
2. Inspect extracted/canonical text
3. Inspect ORIGINAL / NORMALIZED / SPOKEN text
4. Inspect detected book profile / genre
5. Inspect suggested narration profile
6. Inspect representative sample passages
7. Approve/reject TEXT PREVIEW
8. Generate bounded audio sample
9. Listen
10. Approve/reject VOICE SAMPLE
11. Persist narration fingerprint + decision
```

No full-book synthesis is allowed at this stage.

## Intelligence behavior

```text
Rules
  -> solve deterministic cases
Local LLM
  -> semantic classification/interpretation
Schema validator
  -> reject malformed analysis
Decision engine
  -> AUTO / LOG / REVIEW
Human
  -> book-wide narration approval
```

Cloud LLM use is optional and off by default.

## Book-level decisions

The system should infer candidate values, not silently lock them:

- genre/subgenre;
- overall tone;
- dialogue density;
- technical density;
- likely narration style;
- representative sample passages.

The operator can override the final narration profile.

## Sample design

The initial sample set should normally include 3-5 representative passages when enough source material exists:

- ordinary prose;
- difficult pronunciation/number/term case;
- genre-specific passage;
- dialogue/emotion passage where applicable;
- punctuation/annotation edge case.

For the first technical vertical slice, generating one real audible sample is sufficient for the task exit gate; later SAYDI-005 expands to the full representative-set UX.

## Provider behavior

Analysis and voice are separate provider contracts.

```text
AnalysisProvider:
  rule fallback
  local LLM default
  optional cloud LLM

VoiceProvider:
  local TTS target
  SaydiVoice optional/verified
```

The first live workflow may use SaydiVoice because it is already field-verified. V1 production acceptance still requires an all-local TTS path.

## First implementation acceptance

A developer/operator can run one command/runner that creates:

- run manifest;
- canonical excerpt;
- structured analysis JSON;
- narration profile/fingerprint;
- text-preview decision state;
- real audio sample file;
- VoiceResult metadata/hash;
- audio approval/rejection state;
- sanitized logs.

A rerun must not blindly duplicate a previously completed side effect.
