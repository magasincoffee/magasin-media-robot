# SAYDI-QC-006 — VieNeu Field Acceptance Plan

Status: SYNTHETIC VIE​NEU RENDERS COMPLETE — LOCAL QC RUN + OWNER LISTENING PENDING  
Date: 2026-10-05  
Host: `DESKTOP-H4A16IL`  
Voice: `SAYDI Nam Mien Nam`

## Purpose

QC-006 is the final field acceptance layer for the pronunciation/prosody QC track. It uses only synthetic Vietnamese text created for testing. No private manuscript text is required.

The field gate must prove:

1. real VieNeu audio is rendered on the production local TTS host;
2. pronunciation defects can be localized to a chunk/token evidence set;
3. prosody/style deviations can be localized to a chunk with exact profile reasons;
4. a controlled bad chunk can be rerendered without changing accepted neighboring chunks;
5. canonical text remains immutable;
6. repair attempts remain bounded;
7. post-repair QC runs against the new audio hash;
8. the listener-facing audio contains no QC markers;
9. Owner listens to a before/after pair before QC-006 can be declared DONE.

## Synthetic field cases

| Case | Book ID | Profile | Chunks | Purpose |
|---|---|---|---:|---|
| business_clear | `66000000-0000-4000-8000-000000000001` | `BUSINESS_CLEAR` | 3 | business delivery, numbers, AI/API/CEO |
| story_narrative | `66000000-0000-4000-8000-000000000002` | `STORY_NARRATIVE` | 3 | sadness, tension, dialogue, joy |
| general_clear | `66000000-0000-4000-8000-000000000003` | `GENERAL_CLEAR` | 3 | neutral explanatory delivery |
| targeted_repair | `66000000-0000-4000-8000-000000000005` | `GENERAL_CLEAR` | 3 | controlled synthetic fault in chunk 1 + two control chunks |

The durable machine-readable manifest is:

`tools/saydi_tts/qc/fixtures/qc006_field_manifest.json`

## Controlled fault injection

QC-006 records two different ASR similarities for an override-bearing chunk:

- effective TTS similarity: compares ASR against the text actually sent to TTS;
- canonical ASR similarity: compares ASR against the immutable source text.

The controlled bad override must be detected using **canonical ASR similarity**. A high effective-TTS similarity is expected when the engine faithfully speaks the deliberately wrong override; it is not evidence that canonical content is correct.



The targeted-repair case deliberately renders chunk 1 from a wrong TTS-only spoken override while preserving the correct canonical text.

This is test data only.

The harness first proves a strong ASR mismatch, then:

- records all three pre-repair WAV SHA-256 values;
- stages only chunk 1;
- computes the correct safe spoken form using the versioned pronunciation layer;
- queues one targeted repair request;
- waits for VieNeu to regenerate the chunk;
- proves chunk 0 and chunk 2 hashes are unchanged;
- proves only chunk 1 changed;
- runs QC again;
- records bounded repair count and pre/post similarity;
- copies the before/after target WAVs into the Owner review folder.

## Render evidence

All synthetic fixture jobs completed on `DESKTOP-H4A16IL-SAYDI-TTS` on 2026-10-05 with no TTS render error.

The local QC harness can therefore run immediately; it does not need to wait for initial synthesis.

## Local command

Run on `DESKTOP-H4A16IL`:

```powershell
irm https://raw.githubusercontent.com/magasincoffee/magasin-media-robot/main/tools/saydi_tts/qc/INSTALL_QC006_FIELD_H4A16IL.ps1 | iex
```

Expected terminal end state:

```text
Technical field gate: PASS
Owner listening gate: PENDING
```

The Owner review folder is:

```text
C:\SAYDI\qc\qc006\owner_review
```

It contains:

- `target_before_repair.wav`
- `target_after_repair.wav`
- `README.txt`

## Acceptance rule

Technical PASS alone does not complete QC-006. Final state remains pending until:

- Owner listens to BEFORE and AFTER;
- Owner accepts that the repair is an improvement and no obvious regression is introduced;
- QC-004 correct-host field gate is also complete.

Only then may the pronunciation/prosody QC track be declared complete.
