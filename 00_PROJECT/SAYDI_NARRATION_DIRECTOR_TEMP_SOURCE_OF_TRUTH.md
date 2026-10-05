# SAYDI Narration Director — Temporary Source of Truth

Status: ACTIVE
Owner directive date: 2026-10-05
Authority scope: semantic delivery planning for long-form audiobook narration before TTS.

## Owner acceptance problem

The first 5-minute STORY_NARRATIVE golden sample was technically valid but listener-rejected because:

- delivery was too fast and felt rushed;
- sentence/scene pauses were too short;
- delivery remained recognizably AI-like;
- emotional meaning did not materially change the delivery.

The raw sample was approximately 831 words in about 3.5 minutes (~237 WPM), materially above the desired long-form story range.

## Objective

Move STORY_NARRATIVE from a post-render QC label to a real pre-TTS narration plan.

The system must:

1. classify semantic narration beats;
2. choose scene-specific pacing;
3. create meaningful pauses between semantic beats;
4. use punctuation only as a provider-supported TTS hint;
5. keep canonical source text immutable;
6. never claim VieNeu has a discrete emotion control unless field-verified;
7. preserve deterministic evidence for every delivery choice;
8. generate a listener-facing Golden Sample before production-book rollout.

## Provider-safe architecture

VieNeu local currently has verified support for:

- semantic segmentation;
- punctuation;
- pause insertion through segment assembly;
- approved voice/reference selection.

VieNeu local does **not** currently have a verified discrete control for:

- sadness;
- happiness;
- anger;
- arbitrary emotion labels;
- direct scene-level speaking-rate parameter.

Therefore Narration Director v1 creates emotion structurally:

```text
canonical text
  -> semantic beat
  -> sentence/scene segmentation
  -> punctuation hint
  -> VieNeu render
  -> pitch-preserving scene-specific time stretch
  -> explicit semantic pause insertion
  -> final loudness normalization
  -> QC + Owner listening
```

This is not presented as equivalent to a native expressive/emotional TTS model.

## Beat vocabulary v1

- `NARRATIVE`
- `REFLECTIVE_SAD`
- `TENSION`
- `DIALOGUE_TENDER`
- `DIALOGUE_TENSION`
- `WARM_RELIEF`
- `SCENE_TRANSITION`
- `RESOLUTION`

Each beat owns:

- tempo factor;
- pause before;
- pause after;
- semantic emphasis label;
- energy intent;
- evidence cues.

## STORY_NARRATIVE target v1

Golden Sample target:

- effective pace: 135–165 WPM;
- duration for the current synthetic story: 290–360 seconds;
- scene-transition pauses: roughly 0.9–1.3 seconds;
- reflective/tender pauses: roughly 0.7–0.9 seconds;
- tension may move slightly faster but must not become rushed;
- final resolution must receive the longest reset/landing pause.

## Golden Sample V2

Fixture:

`tools/saydi_tts/narration/golden_story_v2_manifest.json`

Builder:

`tools/saydi_tts/narration/build_directed_audio.py`

Local one-command wrapper:

`tools/saydi_tts/narration/BUILD_GOLDEN_STORY_V2_H4A16IL.ps1`

Supabase field job:

- book: `66000000-0000-4000-8000-000000000007`
- job: `66100000-0000-4000-8000-000000000007`
- title: `SAYDI_STORY_GOLDEN_V2_DIRECTED`
- chunks: 17 semantic units
- voice: `SAYDI Nam Mien Nam`

The worker renders semantic units from TTS-only spoken text. The builder then applies beat-specific, pitch-preserving tempo and explicit inter-beat pauses.

## Task queue

### SAYDI-ND-001 — Narration Director core

Status: IMPLEMENTED_IN_PR — CI / merge verification pending

Required:

- deterministic beat contract;
- story beat classifier;
- provider-safe punctuation shaping;
- scene-specific tempo/pause policy;
- canonical/spoken SHA-256 traceability;
- deterministic plan fingerprint;
- tests for sadness/reflection, tension, tender dialogue and scene transitions.

### SAYDI-ND-002 — Golden Story V2 field sample

Status: RUNNING — VieNeu render queued on DESKTOP-H4A16IL

Required:

- render all 17 semantic chunks;
- build directed master;
- duration within 290–360 seconds;
- effective WPM within 135–165;
- export final MP3 + machine-readable report;
- Owner A/B listening against V1.

### SAYDI-ND-003 — Production integration

Status: PENDING

After Owner accepts Golden V2:

- integrate Narration Director into Pipeline V3 preprocessing;
- generate narration manifest automatically for Chapter 1 preview;
- connect active plan fingerprint to QC acceptance;
- use targeted rerender for individual rejected beats;
- only then allow full production-book rollout.

## Current next task

Complete CI/merge for `SAYDI-ND-001`, allow field job `66100000-0000-4000-8000-000000000007` to finish, then run the Golden Story V2 local builder and require Owner listening acceptance.
