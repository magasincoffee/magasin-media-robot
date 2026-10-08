# SAYDI V6 — Owner-Approved Narration Quality Upgrade and Execution Plan

Status: **APPROVED FOR IMPLEMENTATION PLANNING; NOT IMPLEMENTED / NOT PRODUCTION-ACCEPTED**  
Owner directive: **2026-10-08**  
Host for the active local VieNeu field workflow: **DESKTOP-H4A16IL**  
Authority: subordinate to [SOURCE_OF_TRUTH.md](./SOURCE_OF_TRUTH.md); existing authoritative task queue / next task remain unchanged.

## 1. Owner outcome and boundaries

The Owner wants a complete, natural Vietnamese audiobook chapter that matches the quality of an approximately four-minute listening-approved sample. It was perceived as approximately 90% satisfactory; this is an **Owner subjective listening estimate, not a measured automatic QC score**. Remaining defects include unclear/slurred words, incorrect or weakened Vietnamese tones, missing breath/pauses and audible joins. Example: canonical **“Mỗi khi hè về”** may be heard as **“mỗi khi he về”**. Do not conclude the cause from ASR alone: inspect source text, the exact submitted TTS text, reference clip, audio and independent transcription.

**Locked outcomes:**
1. Deliver manuscript-faithful, natural-sounding long-form narration, not merely 100% Whisper PASS.
2. ChatGPT may serve as *editor / narration director*; routine execution, verification and bounded repair belong to the **local SAYDI robot**, not hundreds of ChatGPT or Remote Desktop calls.
3. The local, approved sample governs narrator identity, native articulation speed, broad phrasing and emphasis. Do **not** use FFmpeg `atempo`, pitch shifting or time-stretch to force similarity. Do not fake unavailable VieNeu emotion/speed controls. The narrator sample must be rights-authorized.
4. Sentence punctuation, semantic line breaks, breathing and pronunciation notes are prepared **before** TTS; post-render pronunciation / prosody / acoustic QC remains mandatory.
5. Owner approval is required only for representative sample / materially changed voice fingerprint, genuine textual ambiguity, and unresolved high-impact listening exceptions. Owner must **not** have to find individual defects manually.
6. Keep canonical manuscript, source PDF, owner audio reference, intermediate WAV/MP3, credentials and profile content local; do **not** commit them to Git, job logs or Actions artifacts.
7. Do not automatically overwrite accepted raw WAVs or label a chapter `FINAL` while unresolved material quality findings exist.
8. Local machine is 8 GB RAM / 2 physical cores / 4 logical threads: never run heavy VieNeu synthesis and Whisper QC simultaneously.

## 2. Field baseline (evidence on DESKTOP-H4A16IL, 2026-10-08)

These are **local field observations**, not repo CI acceptance:

- Approved sample is a ~237-second WAV; a local checksum has been used to verify identity. The binary remains local.
- V5 chapter 1: **347/347 segments rendered**; MP3 preview approximately **35m 11s**. Chapter-level source and joined audio exist locally.
- Initial V5 QC: **227 PASS / 120 REVIEW** under the existing local Whisper rule; the stricter ASR review criterion flagged 283. These measures are not interchangeable.
- V5 R1 reused four verified pilot WAVs and reduced basic REVIEW from 120 to 119.
- V5 R2 attempted 35 targeted alternatives, selected 12 ASR-improving candidates, resulting in **115 basic REVIEW / 279 strict ASR REVIEW**. This is still a **REVIEW**, not proof of Owner-accepted listening quality.
- Reference WPM and pauses are acoustic/ASR estimates only. Listening acceptance prevails over fixed WPM targets.
- Existing Windows watchdog has been pointed to V5, but the Github repo implementation and the standalone local scripts may differ: reconcile before using either in production.

Sample files in local runtime are **diagnostic evidence only**; the Github source does not contain the book or its audio.

## 3. Proposed end-to-end flow

```text
SOURCE / LEGAL RIGHTS + IMMUTABLE MANUSCRIPT
 -> Book / chapter / scene / paragraph context
 -> Director: EDITORIAL_QA + semantic punctuation and pauses
 -> Source/normalized/spoken token-diff and pronunciation risk register
 -> Locked OWNER_SAMPLE narrator fingerprint + representative 3-5 passage gate
 -> Segment-addressed VieNeu synthesis at native articulation speed
 -> Structural + pronunciation/tone + prosody + acoustic/join QC
 -> Root-cause classifier (source/editorial/TTS/ASR-only/stitching/unknown)
 -> Bounded, SHA-verifiable isolated repair, only if clear improvement
 -> Validate neighbors + rebuild dependent chapter MP3
 -> Final chapter technical gate + human listening exception gate
 -> READY / REVIEW (never false FINAL)
```

### Separate five classes of findings

| Class | Diagnosis | Permitted automatic action |
|---|---|---|
| SOURCE/OCR | Canonical has wrong/missing accent, noise, page furniture, uncertain name | Apply high-confidence deterministic fixes to derived normalized layer only; ambiguity -> REVIEW |
| EDITORIAL | Correct source but text split/line break loses semantic context or overly short one-word units | Repair derived punctuation/segment boundaries and validate stable source tokens |
| VIENEU_PRONUNCIATION | Exact TTS text contains correct tone but audio is heard incorrectly by corroborating QC | Re-render **localized** phrase with adjoining meaningful context; bounded variants, no altered meaning |
| ASR_FALSE_POSITIVE | Whisper differs yet actual sound/source may be correct | Seek second independent signal or listening; do **not** continuously rerender on ASR alone |
| AUDIO_JOIN / PROSODY | Click, harsh cut, missing breath, inappropriate pause, flat/choppy sequence | Adjust stitch/semantic pause/fade at edges; preserve native spoken waveform rate |

**Specific example:** For “Mỗi khi hè về”, keep these four Vietnamese words together. Store the exact canonical text, normalized text, TTS text, waveform SHA and timecodes. If source/TTS says “hè” and intelligible playback says “he”, classify as suspected pronunciation/tonal failure, not spelling; test phrase-level regeneration with its nearby context. A Whisper “he” hypothesis alone cannot conclusively diagnose a missing huyền tone.

## 4. Data contracts (versioned, validated, local-only payload)

Create/extend provider-neutral schemas; sample fields:

```json
{
  "schema": "saydi-narration-plan-v6",
  "book_id": "local-id",
  "chapter_id": "chapter-01",
  "segment_id": "stable-id",
  "canonical_sha256": "hex",
  "original_span": {"start": 0, "end": 0},
  "normalized_text": "<local-only>",
  "spoken_text": "<local-only>",
  "source_token_equivalence": "PASS",
  "context": {"chapter_role": "NARRATOR_BODY", "previous_id": null, "next_id": null},
  "delivery": {"emotion": "reflective", "intensity": 0.3, "pause_before_ms": 0, "pause_after_ms": 0, "emphasis_tokens": []},
  "must_check": [{"token": "<local-only>", "reason": "Vietnamese tone"}],
  "reference_audio_sha256": "hex",
  "voice_fingerprint": "hex",
  "provider_capabilities": ["reference_voice", "segment_synthesis"],
  "confidence": 1.0,
  "review_required": false
}
```

- Versioned `narration_fingerprint` binds reference audio SHA, local VieNeu version/model, voice/reference settings, native tempo policy, editorial/lexicon/prosody/stitch policy and source/segment hashes. A material change **invalidates the earlier approval** and affected audio/QC caches.
- Runtime QC record includes `segment_id`, `canonical_sha256`, `tts_text_sha256`, `wav_sha256`, `qc_model_version`, `expected`, `asr_heard`, phoneme/tone indicators (when independently validated), `pause_metrics`, `join_metrics`, `timecode`, `finding_class`, `confidence`, `repair_attempts`, `decision_reason`.
- Metadata and editable editorial plan are distinct from spoken bytes. TTS must never read narrator/director instructions aloud.
- All QC records are tied to **the actual WAV hash checked**. A modified WAV invalidates cached QC.
- Use SHA-addressed, atomic checkpoints, durable queues and process locks to avoid duplicate renders/restarts.

## 5. Required quality checks

**Pre-TTS editorial gate:** Validate source span and all word tokens against canonical; punctuation changes permitted only when meaning preserved; no paraphrase; annotation policy explicit; headings/body/dialogue classified; paragraph context passed to VieNeu; high-risk tones/names in `must_check` queue.

**Pronunciation gate:** Whisper/forced alignment can localize suspect words and mismatches but cannot alone certify Vietnamese tonal clarity. For high-risk findings use a second independent verifier (e.g., different local ASR, validated phonetic evidence, or listening). Never assume 100% ASR similarity implies a natural voice; never assume an isolated one-word ASR failure is actual mispronunciation. Classify findings before retrying.

**Prosody/style gate:** Compare approved sample and candidate on native articulation continuity, phrase-level rate, pause distribution, pitch dynamics, emotional arc and neighbor continuity. No global time stretch. Use corpus/sample baselines with tolerance bands supported by A/B evidence, not unconditional hard-coded WPM. Do not re-render an accepted chunk just because the global duration changed.

**Acoustic/join gate:** Validate decode, clipping, leading/trailing silence, fade/crossfade/zero-edge, phrase-boundary pauses, loudness consistency and no audible clicks. Verify master with FFprobe and independent listening. No audible QC markers.

**Release gate:** `TECHNICAL_PASS` requires complete source coverage, stable hashes, no unresolved material mismatches, successful audio decoder + structural/joins gates and zero unbounded repairs. `LISTENING_ACCEPTED` requires representative owner-approved playback or explicit Owner acceptance of the active fingerprint/quality exception policy. `FINAL` requires both; else output `REVIEW` with exact timecoded exceptions, even if the entire chapter is assembled.

## 6. Bounded repair policy and time-to-result

1. Rank by severity (suspected missing/incorrect Vietnamese word or tone, incoherent read, truncated audio, join click; isolated short headlines get special handling).
2. Try a deterministic editorial repair **only if source-fidelity invariant passes**; retain original canonical words.
3. Try up to **2 alternative VieNeu generations** for a safe isolated issue (within existing retry budget); use the same approved reference/fingerprint and do not globally slow down the waveform.
4. Verify alternative clip hash and ASR; score against original, adjacent segments and other QC. **Promote only if objectively better without a known regression**; inconclusive -> retain baseline and queue for listening.
5. Run QC **only for changed segments and their join neighbors**; only rerun full chapter structural/acoustic final gate after assembly. Do not restart full-book render or 347-part ASR after every local edit.
6. If the same failure persists after bounded attempts, classify it as `REVIEW` with exact timecode/root cause/candidate evidence. Never enter an endless repair loop or hide a blocker.
7. Give the Owner a **chapter-level audio file plus 3–5 minute representative review samples** (beginning, middle, hard words), not 100s of individual decisions. The Owner's 90% feedback means quality direction accepted, not release acceptance.

## 7. 8-GB Windows machine protection (hard gate)

- Dedicated `ResourceController` applies on **both** VieNeu and Whisper worker processes, including spawned child processes. CPU maximum initially **2 of 4 logical processors**, `BelowNormal` priority. Experiment with 3 only after measuring stable free RAM and real thermal evidence.
- Use `OMP_NUM_THREADS=2`, `MKL_NUM_THREADS=2`, `OPENBLAS_NUM_THREADS=2`, `NUMEXPR_NUM_THREADS=2`, and `WhisperModel(cpu_threads=2)` on the local QC subprocess.
- Preflight before any heavy model load: at least **2.0 GB free RAM**. While a job runs, checkpoint and stop at a **conservative free-RAM floor**, e.g. 0.75 GB, then release the model. Values must be field-tuned; merely capping CPU does not cap peak RAM.
- Never load VieNeu and Whisper together; free TTS model/process and verify resources before QC. Avoid simultaneous expensive Supervisor, TTS and browser workloads when CPU/RAM is constrained.
- Thermal throttling and temperature alerts are permitted only if a **real sensor reading** exists; CPU 100% by itself is not proof of imminent hardware damage.
- Watchdog must distinguish `RENDERING`, `QC_RUNNING`, `REPAIRING`, `PAUSED_RESOURCE`, `REVIEW_READY`, `READY`, `FAILED`, `WAIT_OWNER`; a terminal QC run must not be shown as "robot crashed".
- Stop/pause/resume preserve completed audio and logs. Scheduled tasks must never launch V4 or two V5 workers concurrently.

## 8. Incremental, subordinate implementation work items

**These are implementation substeps, not replacements for the authoritative SAYDI-002 NEXT task**. Execute only after the parent task is authorized by `00_PROJECT/SOURCE_OF_TRUTH.md`, and reconcile existing ND/QC tasks instead of duplicating them.

| Work item | Owning parent task | Definition of done |
|---|---|---|
| V6-P0-01 — Director schema + pre-render Editorial QA | SAYDI-004 / SAYDI-005; existing SAYDI-ND / SAYDI-QC-007 | Deterministic canonical/token audit, semantic sentence/paragraph metadata, must-check phrases; fixtures for “Mỗi khi hè về”, “người phụ nữ”; tests GREEN |
| V6-P0-02 — Golden voice consistency | SAYDI-005 / SAYDI-006 | Reference waveform + active fingerprint field-verified, 3–5 passage A/B comparison, no time stretch, no isolated micro-fragment voice drift |
| V6-P0-03 — Pronunciation root cause and dual-evidence QC | SAYDI-008; existing SAYDI-QC-003..007 | Word/tone suspect routing, ASR false-positive handling, exact timecodes, no invented 100% PASS |
| V6-P0-04 — Isolated bounded repair | SAYDI-006 / SAYDI-008; existing SAYDI-QC-004 | ≤2 safe attempts; only targeted chunks change SHA; unchanged segments preserved; conditional retries; no infinite loop |
| V6-P0-05 — Stitching/prosody QA | SAYDI-007 / SAYDI-008 | Verified click-safe joins, semantic pauses, no tempo shifts, master opens and timecodes match |
| V6-P0-06 — Resource guardian and watchdog | SAYDI-006 / SAYDI-010 | Boot/resume, child CPU/thread limits, RAM preflight/stop, no overlapping heavy workers, status reflects real phase |
| V6-P1-07 — Local Director→Robot job contract | SAYDI-005 / SAYDI-010 | One validated structured job per chapter; no manuscript leaked to ChatGPT by default; batch escalation only |
| V6-P1-08 — Owner chapter acceptance dashboard | SAYDI-009 / SAYDI-010 | Chapter MP3, representative A/B samples, remaining issues with timecodes and signed Owner verdict |

**Order for immediate Chapter 1 recovery:** baseline preservation -> (01) editorial/lexical audit -> (02) representative approval -> (03) categorize suspected wrong words -> (04) bounded targeted repairs -> (05) joins/whole-chapter QC -> (06) safety/resume -> (08) Owner listening. The already rendered 347 V5 WAVs are an input: **no full restart** unless fingerprint/source change requires it.

## 9. CI and field verification

- Offline unit tests for schema validation, immutable canonical token mapping, punctuation/line-break normalization, reference fingerprint invalidation, false-positive ASR handling, repair selection, bounded retries and checkpoint restoration.
- Synthetic Vietnamese fixture coverage: “Mỗi khi hè về”, “người phụ nữ”, short isolated “Tốt!”, long sentences, headings, quoted speech, foreign names and joins. Do not put private passages/audio in the repo.
- Smoke on Windows H4A16IL: observe CPU affinity/priority on actual subprocess, memory before/after TTS unload, ensure no overlapping VieNeu and Whisper, restart during pending QC/repair, prove WAVs resume without duplication.
- Field A/B: the Owner-approved sample is the reference, compare fresh 3–5 minute difficult excerpt and representative passages with V5 baseline using the *same original manuscript*, then demonstrate no slurring, wrong-tone regression, stretched articulation or audible joins.
- End-to-end Chapter 1: record all 347 units and exact finished MP3 SHA, file duration and QC summary; Owner accepts the real audio. Until then mark `REVIEW`, never `DONE/FINAL`.

## 10. Implementation files and authority wiring

Existing implementation entry points to extend rather than replace:

- `02_SAYDI_CORE/src/saydi_audiobook/editorial.py`
- `02_SAYDI_CORE/src/saydi_audiobook/director.py`
- `02_SAYDI_CORE/src/saydi_audiobook/pronunciation.py`
- `02_SAYDI_CORE/src/saydi_audiobook/prosody.py`
- `02_SAYDI_CORE/src/saydi_audiobook/quality.py`
- `02_SAYDI_CORE/src/saydi_audiobook/repair.py`
- `tools/saydi_tts/narration/` and `tools/saydi_tts/qc/`
- `02_SAYDI_CORE/tests/`

Existing tracks `SAYDI-ND-002D`, `SAYDI-QC-004`, `SAYDI-QC-006`, `SAYDI-QC-007` are not declared done by this plan. No bot should claim integration until exact local field evidence is read and corresponding authoritative task gates are met.

### Robot hand-off protocol

On every autonomous iteration:
1. Read `00_PROJECT/SOURCE_OF_TRUTH.md`; validate the active authorized task first.
2. Read its existing temporary execution SOT and this V6 specification as a **subordinate requirements/acceptance reference**.
3. Pick **one** allowed substep from the relevant parent task; do not silently advance the top-level `NEXT`.
4. Produce code, tests and sanitized results in a PR or authorized branch; prefer impacted tests, then complete mandatory gates.
5. Confirm exact main-branch evidence only after merge; update task status **only with evidence**.
6. For local private Chapter 1 field work, store manuscript/audio and raw ASR only on H4A16IL; publish only sanitized result summaries and non-sensitive synthetic test fixtures.

**Implementation is requested, not yet delivered by this document.**
