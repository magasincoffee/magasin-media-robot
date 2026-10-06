# SAYDI Narration Director — Temporary Source of Truth

Status: ACTIVE
Owner directive date: 2026-10-05; accepted-pacing/editorial-QC directive: 2026-10-06
Authority scope: semantic delivery planning for long-form audiobook narration before TTS.

## Owner acceptance problem

The first 5-minute STORY_NARRATIVE golden sample was technically valid but listener-rejected because:

- delivery was too fast and felt rushed;
- sentence/scene pauses were too short;
- delivery remained recognizably AI-like;
- emotional meaning did not materially change the delivery.

The raw sample was approximately 831 words in about 3.5 minutes (~237 WPM), materially above the desired long-form story range.

Owner field finding on 2026-10-06 from the ~4-minute `Cách Sống` Chapter 4 sample:

- speed: ACCEPTED;
- overall intonation: ACCEPTED;
- emphasis/nhấn nhá: ACCEPTED;
- remaining defects: audible chunk-join artifacts and occasional slurred/unclear Vietnamese diacritics;
- concrete pronunciation example: `người phụ nữ` was heard with weak/unclear heavy-tone articulation;
- Owner requires text to be editorially compiled **before** VieNeu render, while preserving the already-built **post-render QC + targeted rerender** path.

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

Owner listening on 2026-10-05 rejected V2 despite technical PASS: the delivery was more expressive than V1, but emotion was being created by slowing the voice. Owner directive: **truyền cảm bằng nghỉ/ngắt nhịp, không phải bằng làm tốc độ giọng chậm**.

The accepted architecture is now editorial-first and QC-closed-loop:

```text
canonical text
  -> pre-render Editorial QA
     -> semantic sentence/clause segmentation
     -> breathing/pause intent
     -> emphasis intent
     -> pronunciation MUST_CHECK phrases
  -> TTS-only spoken normalization / lexicon
  -> VieNeu render at natural articulation speed
  -> post-render pronunciation + prosody + acoustic QC
     -> targeted rerender only for failed units
  -> click-safe trim/fade/crossfade assembly
  -> stitching QC
  -> final loudness normalization
  -> Owner listening
```

Pre-render editorial approval is **not** a substitute for post-render QC.

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

Status: DONE — merged in PR #83; CI PASS

Required:

- deterministic beat contract;
- story beat classifier;
- provider-safe punctuation shaping;
- scene-specific tempo/pause policy;
- canonical/spoken SHA-256 traceability;
- deterministic plan fingerprint;
- tests for sadness/reflection, tension, tender dialogue and scene transitions.

### SAYDI-ND-002 — Golden Story V2 field sample

Status: RAW_RENDER_COMPLETE — directed master build + Owner listening pending

Required:

- render all 17 semantic chunks;
- build directed master;
- duration within 290–360 seconds;
- effective WPM within 135–165;
- export final MP3 + machine-readable report;
- Owner A/B listening against V1.

### SAYDI-ND-002 render evidence

Accepted raw-render evidence on 2026-10-05:

- field job `66100000-0000-4000-8000-000000000007` completed;
- 17/17 semantic chunks rendered on `DESKTOP-H4A16IL-SAYDI-TTS`;
- render error: none;
- raw chapter output: `C:\SAYDI\output\SAYDI_STORY_GOLDEN_V2_DIRECTED__66100000\SAYDI_STORY_GOLDEN_V2_DIRECTED.mp3`;
- the listener-facing directed master is intentionally separate from this raw render and must be built with the Narration Director tempo/pause assembler before Owner review.

### SAYDI-ND-002B — Golden Story V3 natural-speed + semantic-pauses

Status: READY

Required:

- reuse the already completed 17 raw WAV chunks; do not rerender unless V3 listening proves internal phrase pauses are still insufficient;
- set all post-render tempo factors to 1.0;
- express reflective, dialogue, transition and resolution emotion primarily through pause duration, punctuation and semantic phrasing;
- build `SAYDI_STORY_GOLDEN_V3_FINAL.mp3`;
- Owner listening is the acceptance authority;
- if V3 still lacks internal pauses, advance to clause-level segmentation and targeted rerender rather than slowing audio.

Wrapper:

`tools/saydi_tts/narration/BUILD_GOLDEN_STORY_V3_H4A16IL.ps1`

### SAYDI-ND-002C — Golden Story V4 clause-level natural narration

Status: RAW_RENDER_COMPLETE — 73/73 rendered; directed master build + Owner listening pending

Owner directive:

- keep articulation speed natural; never simulate emotion by slowing the entire waveform;
- create emotion through sentence/clause boundaries, breathing space, dialogue timing, semantic landing and scene resets;
- render a new independent field job so V2/V3 evidence remains immutable.

Locked V4 field contract:

- job: `66100000-0000-4000-8000-000000000008`;
- title: `SAYDI_STORY_GOLDEN_V4_CLAUSE_LEVEL`;
- source parent blocks: 17;
- rendered semantic units: 73;
- every unit uses `tempo_factor = 1.0`;
- manifest: `tools/saydi_tts/narration/golden_story_v4_manifest.json`;
- wrapper: `tools/saydi_tts/narration/BUILD_GOLDEN_STORY_V4_H4A16IL.ps1`;
- output: `SAYDI_STORY_GOLDEN_V4_FINAL.mp3`;
- Owner listening is the acceptance authority.


V4 render evidence on 2026-10-05:

- Supabase job `66100000-0000-4000-8000-000000000008` completed successfully;
- 73/73 clause-level chunks rendered on `DESKTOP-H4A16IL-SAYDI-TTS`;
- render error: none;
- raw output: `C:\SAYDI\output\SAYDI_STORY_GOLDEN_V4_CLAUSE_LEVEL__66100000\SAYDI_STORY_GOLDEN_V4_CLAUSE_LEVEL.mp3`;
- final directed master still requires the V4 wrapper on DESKTOP-H4A16IL, then Owner listening acceptance.

Acceptance:

- no dragged/slow-motion articulation;
- audible breathing inside former 17-block boundaries;
- dialogue has human turn-taking space;
- reflective/emotional sentences land before the next thought;
- transitions reset clearly without becoming theatrical or choppy;
- only after Owner acceptance may production integration proceed.

### SAYDI-ND-002D — Editorial-first long-form field acceptance

Status: IMPLEMENTED_IN_PR — LOCAL RERENDER / OWNER LISTENING PENDING

Owner has accepted the speed, general intonation and emphasis behavior of the ~4-minute Chapter 4 sample. Do not change those accepted dimensions by applying global slowdown.

Required:

- compile the private/local chapter excerpt through Editorial QA before VieNeu;
- preserve canonical text and source hash;
- mark difficult phrases for MUST_CHECK pronunciation QC;
- render natural-speed semantic units;
- rerun the existing pronunciation/prosody/acoustic QC after synthesis;
- use bounded targeted rerender for unclear units instead of rerendering the whole sample;
- assemble with click-safe edge fades and stitching gate;
- keep private book text/audio local; do not commit the manuscript to GitHub;
- Owner listening is final acceptance.

### SAYDI-ND-003 — Production integration

Status: PENDING

After Owner accepts Golden V4:

- integrate Narration Director into Pipeline V3 preprocessing;
- generate narration manifest automatically for Chapter 1 preview;
- connect active plan fingerprint to QC acceptance;
- use targeted rerender for individual rejected beats;
- only then allow full production-book rollout.


Field execution evidence on 2026-10-06:

- private Chapter 4 editorial field book: `66000000-0000-4000-8000-000000000009`;
- field render job: `66100000-0000-4000-8000-000000000009`;
- semantic units: 33;
- units carrying explicit MUST_CHECK pronunciation phrases: 13;
- production TTS host: `DESKTOP-H4A16IL-SAYDI-TTS`;
- raw render: COMPLETE 33/33, error: none;
- raw output: `C:\SAYDI\output\CACH_SONG_CH4_EDITORIAL_QC_FIELD__66100000\CACH_SONG_CH4_EDITORIAL_QC_FIELD.mp3`;
- post-render QC / targeted rerender / click-safe final assembly: PENDING LOCAL H4 HARNESS;
- harness: `tools/saydi_tts/narration/RUN_EDITORIAL_FIELD_H4A16IL.ps1`;
- GitHub remote execution cannot claim this final gate because the connected self-hosted runner is not the H4 TTS host.

## Current next task

Run `tools/saydi_tts/narration/RUN_EDITORIAL_FIELD_H4A16IL.ps1` on DESKTOP-H4A16IL for field job `66100000-0000-4000-8000-000000000009`. It must execute post-render pronunciation/prosody/acoustic QC, bounded targeted rerender, click-safe final assembly, and require `stitching_gate_pass=true`. Owner listening remains the final acceptance gate.
