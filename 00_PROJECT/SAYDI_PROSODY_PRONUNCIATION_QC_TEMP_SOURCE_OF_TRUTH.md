# SAYDI Prosody + Pronunciation QC — Temporary Source of Truth

Status: ACTIVE
Owner directive date: 2026-10-04
Authority scope: local VieNeu audiobook quality control only.

## Owner objective

The Owner should be able to request an audiobook style/genre and let SAYDI handle routine narration quality automatically.

The local pipeline must not stop at "the words roughly match the manuscript". It must also detect and reduce:

- unclear or slurred Vietnamese words ("lơ lớ", swallowed syllables, weak consonants/vowels);
- wrong or unstable pronunciation of names, abbreviations, numbers and foreign terms;
- robotic/flat intonation;
- pace that is too fast or too slow for the selected narration profile;
- unnatural pauses or missing pauses;
- low expressive variation inconsistent with the selected audiobook style;
- clipping/technical defects.

The target is materially more natural long-form listening, not a false promise of perfect human equivalence.

## Non-negotiable design rules

1. QC is DEFAULT-ON after synthesis.
2. Never regenerate an entire chapter when only one chunk is defective.
3. Every QC verdict is attached to the exact audio SHA-256 it evaluated.
4. Automatic repair is bounded. Never create an infinite rerender loop.
5. A repair that changes meaning, narrator identity, or materially changes narration style requires Owner review.
6. Private manuscript text/audio remains local and must not be uploaded to GitHub artifacts.
7. ASR similarity alone is insufficient for final acceptance.
8. Preserve source text separately from any TTS-only spoken-form/pronunciation rewrite.
9. If a pronunciation defect remains after the retry budget, escalate the exact word/chunk/timecode instead of hiding it.

## Target pipeline

```text
SOURCE TEXT
   |
   v
spoken normalization + pronunciation lexicon
   |
   v
VieNeu TTS render
   |
   v
ASR / forced-alignment pronunciation QC
   |
   +--> unclear/mispronounced word? --> targeted spoken-form/segmentation repair --> rerender chunk
   |
   v
prosody/style QC
   |
   +--> flat / wrong pace / bad pause pattern? --> bounded narration repair --> rerender chunk
   |
   v
acoustic/join QC
   |
   v
PASS -> chapter assembly/export
```

## Required measurements per chunk

Minimum local measurements:

- ASR text similarity;
- word-level confidence/alignment where available;
- exact suspect/unclear tokens;
- speaking rate (words per minute);
- pause/silence ratio and abnormal pause locations;
- pitch/F0 variation or equivalent intonation metric;
- energy/dynamics variation;
- clipping/technical validity;
- attempt number and exact audio hash.

## Automatic pronunciation repair order

For a suspect Vietnamese word or phrase:

1. keep canonical/original text unchanged;
2. apply an explicit pronunciation lexicon/spoken-form override when a known entry exists;
3. normalize abbreviation/number/name/foreign-term reading;
4. split the chunk near the suspect token to reduce TTS context failure;
5. rerender only that chunk;
6. run ASR + pronunciation QC again;
7. if the bounded retry budget is exhausted, require review or a voice/model fallback.

Do not "fix" pronunciation by silently changing semantic content.

## Automatic prosody/style repair order

For a chunk outside the active narration profile:

1. adjust sentence/chunk boundaries;
2. adjust supported pace/pause controls;
3. add TTS-only punctuation/spoken-form hints when semantically safe;
4. rerender only the affected chunk;
5. rerun pronunciation + prosody + acoustic QC;
6. escalate after the retry budget instead of looping forever.

## Owner sequencing note

Owner directive 2026-10-05: QC-005 may proceed in parallel while QC-004 correct-host field acceptance remains pending. This does **not** mark QC-004 DONE and does **not** waive its final acceptance gate. Project completion still requires QC-004 field PASS on DESKTOP-H4A16IL.

## Task queue

### SAYDI-QC-001 — Core quality contracts and deterministic repair policy

Status: DONE — merged to main in PR #60; CI PASS

Required:
- provider-neutral quality observation/report contracts;
- pronunciation/prosody/acoustic decision policy;
- bounded auto-repair plan;
- tests proving unclear pronunciation, flat delivery, retry exhaustion and incomplete metrics behavior.

Acceptance:
- code compiles;
- unit tests pass;
- no provider/browser dependency enters the audiobook core.

### SAYDI-QC-002 — Local worker metric extraction

Status: DONE — field acceptance PASS on DESKTOP-H4A16IL

Required on `C:\SAYDI\worker`:
- preserve current ASR similarity QC; **IMPLEMENTED**
- add word-level confidence/alignment evidence; **IMPLEMENTED via faster-whisper word timestamps**
- calculate speaking rate; **IMPLEMENTED**
- calculate pause/silence ratio; **IMPLEMENTED**
- calculate pitch/intonation variation; **IMPLEMENTED coarse local F0 variation**
- calculate energy/dynamics variation; **IMPLEMENTED**
- emit one structured observation per chunk keyed by audio SHA-256. **IMPLEMENTED**

Acceptance:
- works on DESKTOP-H4A16IL;
- metrics are persisted locally;
- no private audio/text is uploaded.

### SAYDI-QC-002 field evidence

Accepted on 2026-10-04 using Chapter 1 in non-mutating `--observe-only` mode.

Observed evidence:

- chunks observed: 24/24;
- word-confidence metric: 24/24;
- speaking-rate metric: 24/24;
- pause-ratio metric: 24/24;
- pitch-variation metric: 24/24;
- energy-variation metric: 24/24;
- audio SHA-256 traceability: 24/24;
- field gate result: `FIELD GATE CORE METRICS: PASS`;
- observe-only safety confirmed: no WAV deletion and no `repair_chunks` request.

This proves metric extraction and local persistence. It does **not** mean the chapter itself is quality-clean: the same QC pass reported 25 warnings and 1 error, which become input evidence for subsequent pronunciation/prosody repair tasks.

### SAYDI-QC-003 — Vietnamese pronunciation lexicon + spoken-form repair

Status: DONE — merged in PR #64; CI PASS

Required:
- versioned pronunciation lexicon; **IMPLEMENTED: vi-pronunciation-v1 + custom lexicon loader**
- safe TTS-only spoken-form layer; **IMPLEMENTED**
- rules for abbreviations, numbers, names and foreign terms; **IMPLEMENTED with conservative explicit-entry policy**
- record exact suspect tokens and applied overrides; **IMPLEMENTED**
- keep canonical source immutable. **IMPLEMENTED + regression tested**

Acceptance:
- known hard words can be corrected without changing source text;
- regression fixtures cover Vietnamese diacritics and common ambiguous forms.

### SAYDI-QC-003 completion evidence

Accepted on 2026-10-04.

Evidence:

- PR #64 merged to `main`;
- SAYDI Core Tests: PASS;
- versioned default lexicon: `vi-pronunciation-v1`;
- custom/local lexicon loader implemented;
- TTS-only spoken-form generation preserves canonical text;
- explicit provenance records lexicon key, category, source text, spoken text and source span;
- targeted repair planning accepts QC suspect tokens and leaves unknown tokens unresolved for review;
- conservative standalone-integer Vietnamese normalization implemented;
- names and foreign terms require explicit lexicon entries instead of guessing;
- regression fixture covers Vietnamese diacritics, abbreviations, units and unresolved foreign terms;
- local `pronunciation-preview` CLI added for non-destructive inspection.

### SAYDI-QC-004 — Targeted automatic rerender loop

Status: CODE_MERGED — LOCAL FIELD ACCEPTANCE PENDING ON DESKTOP-H4A16IL

Required:
- rerender only failed chunks; **IMPLEMENTED with chunk-scoped queue reset and local WAV staging**
- bounded retry budget (default maximum two attempts); **IMPLEMENTED in Edge API**
- re-run all QC layers after each repair; **IMPLEMENTED for repaired chunk(s)**
- prevent duplicate/infinite jobs; **IMPLEMENTED with repair-request idempotency + per-chunk attempt counter**
- rebuild only dependent chapter artifact after chunk acceptance. **IMPLEMENTED through existing worker chapter assembly**

Acceptance:
- one bad chunk does not regenerate accepted chunks;
- retry exhaustion becomes REVIEW with exact location/evidence.

### SAYDI-QC-004 implementation / field-gate evidence

Implementation merged on 2026-10-05.

Evidence:

- PR #66 merged; GitHub `SAYDI Core Tests` PASS;
- Supabase migration `saydi_qc004_targeted_rerender` applied to MAGASIN-NOIBO;
- `saydi-tts-worker` Edge Function v7 ACTIVE;
- durable chunk state now separates canonical `text_content` from TTS-only `spoken_text_override`;
- per-chunk `qc_repair_attempts` + `last_repair_request_id` enforce bounded/idempotent repair;
- repair eligibility is checked before local WAV staging;
- failed queue calls restore staged WAVs instead of losing accepted audio;
- repaired chunks are re-QC'd and persistent defects route to REVIEW;
- self-hosted field run 37246808272 failed before execution because Windows PowerShell execution policy blocked the wrapper; fixed by PR #67;
- retry field run 37246911756 reached the field script but was routed to `DESKTOP-4K7IM13`, not the authoritative TTS host `DESKTOP-H4A16IL`; the machine guard stopped before any audiobook mutation;
- one-command correct-host launcher added: `tools/saydi_tts/qc/INSTALL_QC004_FIELD_H4A16IL.ps1`.

Field acceptance is **not** complete until the correct host proves:

1. only the selected failed chunk WAV changes;
2. canonical text remains unchanged;
3. a TTS-only spoken override is applied;
4. repair attempt count is bounded;
5. post-repair QC executes;
6. persistent defects become REVIEW rather than an infinite rerender loop.

### SAYDI-QC-005 — Prosody/style profiles by audiobook type

Status: DONE — merged in PR #69; CI PASS

Required:
- define per-profile pace, pause and intonation envelopes for at least BUSINESS_CLEAR, STORY_NARRATIVE and GENERAL_CLEAR; **IMPLEMENTED in `prosody-profile-v1`**
- map Owner's simple genre/style request to the profile; **IMPLEMENTED with deterministic Vietnamese/English aliases + BookProfile fallback**
- allow provider-supported controls only; never fabricate unsupported controls. **IMPLEMENTED with provider control whitelist**

Acceptance:
- profile-specific QC catches deliberately flat/too-fast/too-slow fixtures; **IMPLEMENTED + unit-tested**
- changing profile invalidates QC acceptance as required. **IMPLEMENTED via profile fingerprint binding**

### SAYDI-QC-005 implementation evidence

Implementation prepared on 2026-10-05.

Evidence:

- versioned profile contract: `prosody-profile-v1`;
- `BUSINESS_CLEAR`, `STORY_NARRATIVE`, and `GENERAL_CLEAR` each define speaking-rate, pause, pitch and energy envelopes;
- Owner-facing style requests map deterministically to one profile;
- unknown style requests fall back to analyzed `BookProfile`, then `GENERAL_CLEAR`;
- local QC writes exact profile key/version/fingerprint into observations and chapter reports;
- local QC emits `prosody_style_mismatch` with exact out-of-envelope reasons;
- profile fingerprint changes invalidate previous acceptance;
- provider-control filter rejects unsupported emotion/mood/prosody knobs rather than fabricating them;
- Supabase `saydi-tts-worker` Edge Function v8 deployed to persist/replace prosody QC events safely;
- profile definitions documented in `00_PROJECT/PROSODY_STYLE_PROFILES_V1.md`.

### SAYDI-QC-005 completion evidence

Accepted on 2026-10-05.

Evidence:

- PR #69 merged to `main`;
- exact-main commit after merge: `80645101f29a3562d9317b3f065594135916716b`;
- pull-request CI: PASS;
- main-branch CI: PASS;
- `prosody-profile-v1` ships versioned envelopes for `BUSINESS_CLEAR`, `STORY_NARRATIVE`, and `GENERAL_CLEAR`;
- deterministic Owner style mapping is covered by unit tests;
- deliberately too-fast, too-slow, flat-intonation and flat-dynamics fixtures are detected;
- profile fingerprints are distinct and changing profile invalidates previous acceptance;
- local QC records active profile key/version/fingerprint and emits exact prosody mismatch reasons;
- provider-control filtering rejects unsupported semantic controls rather than inventing them;
- Supabase `saydi-tts-worker` Edge Function v8 is ACTIVE for prosody event persistence;
- durable profile specification: `00_PROJECT/PROSODY_STYLE_PROFILES_V1.md`.

### SAYDI-QC-006 — Field acceptance on local VieNeu

Status: IMPLEMENTED_IN_PR — SYNTHETIC RENDER + LOCAL TECHNICAL GATE / OWNER LISTENING PENDING

Required:
- use synthetic/public-domain Vietnamese test passages; **IMPLEMENTED with synthetic-only field fixtures**
- include intentionally difficult pronunciation and expressive passages; **IMPLEMENTED across BUSINESS_CLEAR / STORY_NARRATIVE / GENERAL_CLEAR**
- demonstrate defect detection, targeted rerender, and final PASS/REVIEW; **FIELD HARNESS IMPLEMENTED; local execution pending**
- compare before/after samples by Owner listening only at the final acceptance gate. **OWNER LISTENING GATE IMPLEMENTED; pending Owner review**

Acceptance:
- pronunciation defects are localized;
- prosody defects are localized;
- automatic repairs are bounded;
- chapter output remains traceable and listener audio contains no QC markers.

### SAYDI-QC-006 implementation / field evidence

Prepared on 2026-10-05.

Evidence:

- synthetic-only field manifest committed at `tools/saydi_tts/qc/fixtures/qc006_field_manifest.json`;
- one-command H4A16IL harness committed at `tools/saydi_tts/qc/INSTALL_QC006_FIELD_H4A16IL.ps1`;
- durable acceptance plan committed at `00_PROJECT/QC006_FIELD_ACCEPTANCE_PLAN.md`;
- five synthetic Supabase test jobs were created on MAGASIN-NOIBO, including three profile cases and two controlled repair probes;
- all five synthetic jobs completed successfully on production TTS worker `DESKTOP-H4A16IL-SAYDI-TTS` with no render error;
- completed outputs exist locally for BUSINESS_CLEAR, STORY_NARRATIVE, GENERAL_CLEAR, the one-chunk repair probe, and the three-chunk targeted-repair fixture;
- targeted-repair fixture uses three chunks: chunk 1 contains a synthetic wrong TTS-only override while chunks 0 and 2 are controls;
- field harness records pre/post SHA-256, profile metrics, localized pronunciation/prosody findings, bounded repair count, canonical-text preservation, and Owner before/after WAV samples;
- no private book/manuscript content is used or uploaded.

Field finding on 2026-10-05: the first QC-006 run reached all four cases but the controlled fault gate compared ASR to the effective TTS override, producing similarity 0.9534. This was a test-harness semantic error, not a TTS/QC engine failure. A canonical similarity correction now records both effective-TTS and canonical-source ASR similarity and uses the canonical value for fault acceptance.

Second field finding: the corrected run reached the targeted-repair helper, then failed because `build_spoken_form.py` executed from `C:\SAYDI\qc\qc006` and therefore could not import sibling package `C:\SAYDI\qc\saydi_audiobook`. The helper is now executed from the QC package root and the installer performs a Python import smoke check before any long QC work.

Third field finding: after the helper-import fix, the next run reported `targeted_repair: observation count mismatch`. Inspection showed the previous interrupted run had already moved target chunk `000001.wav` to the QC staging backup before the helper failed, leaving the next observe-only pass with only two audio observations and `auto_repair_indices=[1]`. The harness now recovers an interrupted staged target before QC, builds the corrective spoken form before touching the accepted WAV, and local QC emits explicit technical observations for missing/decode failures instead of silently reducing observation count.

Fourth field finding: the recovered run reached the repair API but PowerShell received `HTTP 400 Bad Request`. The only 400 path in the deployed repair endpoint was `no_chunk_indices`; this exposed a client-shape compatibility edge case for single-item PowerShell payloads. The worker API now normalizes scalar or array `chunk_indices` and scalar or array `spoken_overrides`; Edge Function v9 is ACTIVE. The field installer now also includes the API response body in any future HTTP error.

Fifth field finding: Edge v10 confirmed the failing request reached the correct deployment, but returned `received_action=""` and `normalized_action=""` while the PowerShell caller still had `action=repair_chunks`. This isolates the defect to HTTP request-body serialization/parsing between Windows PowerShell and the Edge runtime, not VieNeu, the queue, or action routing. The installer now sends JSON as explicit UTF-8 bytes with `application/json; charset=utf-8`; Edge v11 no longer silently swallows JSON parse failures and returns safe parse diagnostics (length/content-type/error) without echoing audiobook text.

Sixth field finding: the targeted repair itself completed successfully (3/3 chunks), but the immediate post-repair QC failed while loading faster-whisper with `mkl_malloc: failed to allocate memory`. Supabase confirmed the render job was complete and error-free; the local TTS worker remained online after rendering and retained enough RAM to starve the new Whisper process. QC-006 now temporarily stops the idle scheduled TTS worker before post-repair Whisper QC, limits MKL/OMP threads during that check, and restores the worker afterward.

Seventh field finding: the resume script then reported `Canonical text changed during targeted repair`, but direct Supabase verification proved the durable canonical `text_content` still exactly matched the expected source. The false failure came from Windows PowerShell 5.1 UTF-8 handling: JSON/text files without BOM were read with the legacy default encoding. The same path also corrupted the generated TTS spoken form before the first repair. Evidence: durable canonical text matched exactly, while the stored spoken override length/hash did not match the deterministic lexicon-generated UTF-8 spoken form. QC-006 now forces `-Encoding UTF8`, verifies canonical and spoken-form SHA-256 before render, and uses the second/final bounded repair attempt to regenerate only chunk 1 with verified UTF-8 text.

Final QC-006 acceptance remains blocked on the corrected local technical run and Owner listening. QC-004 correct-host field PASS remains separately required before the QC track can be declared complete.

## Current next task

Run `tools/saydi_tts/qc/INSTALL_QC006_FIELD_H4A16IL.ps1` on DESKTOP-H4A16IL after the synthetic jobs complete. Require `Technical field gate: PASS`, then Owner listens to the generated BEFORE/AFTER WAV pair. QC-004 correct-host field PASS remains separately mandatory before declaring the QC track complete.

