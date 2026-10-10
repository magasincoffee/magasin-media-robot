# SAYDI V5 QC01–QC05 — controlled implementation and Chapter 3 field report

**Field observation:** 2026-10-10 ~23:15 ICT on DESKTOP-H4A16IL. **Status: new isolated QC gates work, production integration and human full-chapter acceptance are NOT complete.**

## SOT authority and safety

- Read `00_PROJECT/SOURCE_OF_TRUTH.md` on main SHA `7b5d2a1bc2ce55710c6228863fd326ebf6ca4971` before this work. Its authoritative task remains **SAYDI-002 NEXT**. QC capability is a subordinate prototype toward SAYDI-008; no top-level task promotion and no changes to the scheduled control plane.
- Existing VieNeu V5 ONNX engine, reference fingerprint, native pace, manuscript, V5 manifest, canonical text, TTS model, Windows tasks, Control API/UI, and all production WAV/MP3 are unchanged.
- All new code is on the draft branch `feat/saydi-v5-ch02-qc01-qc02-audit` (PR #101) and independently exercised from **D-drive QC staging**. No automatic job dispatch, background polling or startup registration. Users must explicitly supply `--opt-in`. Default behavior remains OFF.
- The approved local ~5-minute B+R2 sample is scope-bound only. No human approval of the entire 25:33.875 chapter exists.

## Files added

- `tools/saydi_tts/qc/v5_quality_gates_01_05.py`: **read-only** QC01 pause structure, QC02 PCM edge examination, QC03 conservative semantic/emotional candidate hints, QC04 original-versus-existing-ASR transcript/diacritic issue classification, QC05 SHA-bound repair receipts, 2-attempt upper bound and rollback gating. Writes an isolated versioned JSON report, with no original/transcript text exposed.
- `tools/saydi_tts/qc/v5_qc_bounded_worklist.py`: converts the report and explicit audio-SHA-bound Owner exceptions into a worklist; distinguishes Owner-confirmed cases from ASR-only hypotheses, validates stale evidence, routes exhausted attempts to review, caps presentation, never directly calls TTS/ASR. Already accepted sample is recorded as resolved **for that sample only**.
- `tools/saydi_tts/qc/test_v5_quality_gates_01_05.py`: 8 synthetic tests including immutable SHA, strict path/diff, spoken source correctness, Vietnamese tone-ASR suspect classification, stale Owner sample refusal, rollback and no-overwrite.
- `tools/saydi_tts/qc/test_v5_qc_bounded_worklist.py`: 5 synthetic tests including strict 2-attempt cap, ASR false-positive routing, stale/malformed Owner events, sample-scoped rather than chapter-scoped approval.

No production module or scheduler was edited for this scope. The existing core modules `quality.py`, `pronunciation.py`, `prosody.py`, `director.py` and `repair.py` remain owners of deeper engine integrations. The local V5 manifest, `QC_AFTER_RENDER.json` and exact Review concat are reused as evidence sources rather than reimplementing synthesis.

## Actual Chapter 3 field verification (source hashes checked)

Original production Chapter 3 REVIEW SHA-256:
`4809f72dd6b10c1172e8f029cfa6c492cb2a68d9733f19ad2045595c98e3618f`

New isolated Chapter 3 B-window / R2 REVIEW SHA-256:
`8ce6b51e17eb50402222e68e0f3d20dda2f7fa4b52752189ad12ea2cac6e5a36`

The Owner-approved 5-minute B+R2 sample SHA was independently bound and verified:
`4c24320f9425c140e4370ea7012c204e564ac0a959dd3c315cec1139ba48e720`

| Gate | Verified machine result | Quality conclusion |
|---|---|---|
| QC01 | Exact 25 pause replacements in the previously accepted B sample; no time-stretch | B sample preferred/accepted; outside sample REVIEW |
| QC02 | Scanned 284 clean PCM joins, 0 endpoint-level high-amplitude flags | Acoustic *edge* check only, not timbre/click listening certification |
| QC03 | 16 conservative semantic-delivery candidates (nonbinding hints) | Emotion/voice dynamics **not audio-validated**; REVIEW |
| QC04 | 285 source QC rows SHA-verified. 115 ASR REVIEW after R2 replacement. 262 ASR-word/term suspicion records (overlap possible; **NOT 262 confirmed audible errors**) | ASR-only findings routed to second-signal/human verification; REVIEW |
| QC05 | Exactly 1 altered speech WAV (index 146), 25 approved sample-window gaps, all remaining source WAVs untouched; R2 SHA verified; maximum 2 attempts | No automatic repair/retry or FINAL; one explicit scoped Owner acceptance event recorded |
| Worklist | 1 accepted sample event; 0 immediate automated render commands; 277 *candidate review records* (overlapping semantic+lexical categories, NOT individual confirmed faults), at most 12 shown | No infinite repair or uncontrolled Owner escalations |

The entire staged review MP3 has now passed **full FFmpeg decode** (1533.875s, 24,543,020 bytes, 128005 bit/s), in addition to previous source/sample hashing and exact-concat diff checks.

**13/13 new local unit cases PASS** (8 evidence, 5 disposition); repeat field run PASS after adding the full issue identity list and approved-sample SHA validation. CI result must be checked for the exact final branch commit; local unit PASS is not broad production regression.

## Local private evidence (never commit media, manuscript or transcripts)

`D:\SAYDI\QC_STAGING\CH03_V5_R2_B_WINDOW_REVIEW_20261010\qc01_05`

- `CH03_QC01_05_VERIFIED_V3.json`
- `OWNER_APPROVED_SAMPLE_SCOPED.json`
- `CH03_QC_WORKLIST_V3.json`
- `test_v5_quality_gates_01_05.py`, `test_v5_qc_bounded_worklist.py`

The report includes **all** 262 suspicion identities for internal routing, with only the first 50 as quick preview; worklist keeps the full source list but presents at most 12 Owner review entries per run. It does not publish original book text or recognized words to GitHub.

## Runtime continuity

At final read: original Chapter 3 remains `REVIEW_READY`, 285/285 rendered and 285/285 basic QC, unchanged. Main SAYDI Control had advanced to **Chapter 4 / QUEUED_RESOURCE**, Windows `SAYDI Control Job Guardian` was `Ready`, free physical RAM ~3.38 GiB. No heavy concurrent TTS/ASR was started by the new QC tools.

## Rollback and not-yet-done gates

Rollback is **do not invoke opt-in CLI; discard staging reports/branch if needed**. No production service, schema, API, checkpoint, worker or model migration was applied.

These implementation components are **not yet a fully autonomous QC robot**. Pending gates, intentionally not marked PASS:
1. Bind worklist dispatch to *existing* V5 repair controller with explicit SOT authority and bounded single-clip job IDs, rather than adding an independent scheduler.
2. Independent pronunciation validation for Vietnamese tone/dialect/abbreviations and timecoded Owner exceptions; Whisper alone cannot certify.
3. Actual acoustic pitch/timbre continuity and semantic prosody evaluation against the approved voice sample, plus listening evidence of unaffected chapter passages.
4. Run hardware resource preflight, STOP/START, reboot, checkpoint recovery and regressions against the live control runner in a separately authorized field gate.
5. Finish Owner hearing of the entire chapter and pass the authoritative SOT acceptance checks before considering production promotion / `FINAL`.

**No interpretation of tests, ASR numbers, or a five-minute sample may turn this complete chapter into FINAL.**


## Additional QC-03 acoustic continuity screen (2026-10-10, ~23:25 ICT)

The opt-in QC03 module was extended to read **only a 0.5s middle PCM window** per V5 speech WAV (no Whisper, VieNeu, pitch-shifting or audio postprocessing). It computes RMS dBFS differences between neighboring sentences. A **>8 dB** differential is classified as a *potential energy continuity review*, not a verified speaker/timbre/emotion fault. Field run on the Chapter 3 B+R2 REVIEW found **2 candidate positions**:
- join after index **29**, chapter ~**03:00.160**, measured ~**19.97 dB** difference;
- join after index **149**, chapter ~**13:27.480**, measured ~**9.20 dB** difference.

Two **unchanged audio stream excerpts**, not fixes, were created solely on the Windows host:
`D:\SAYDI\QC_STAGING\CH03_V5_R2_B_WINDOW_REVIEW_20261010\qc01_05\QC03_ENERGY_REVIEW_03M00.mp3` (40.008s), and `QC03_ENERGY_REVIEW_13M27.mp3` (40.032s). `QC03_ENERGY_EXCEPTION_LISTENING.json` contains their source hash, exact clocks, clip SHA and pending-listening status, without manuscript text.

The current final-on-host QC reports are `CH03_QC01_05_VERIFIED_V4.json` and `CH03_QC_WORKLIST_V4.json`. Both are `REVIEW`, not FINAL. **14/14 focused synthetic local cases PASS** (9 evidence, 5 bounded-worklist), and the V4 field report/worklist completes successfully. Original and staged Chapter 3 SHA remain unchanged. No acoustic measurement alone was classified as successful emotional performance or audible joining.

`saydi-core-tests.yml` was minimally extended to run `python -m unittest discover -s tools/saydi_tts/qc -p "test_v5_*" -v`. **The CI result for the exact latest commit remains unverified until a new GitHub Actions check actually completes**; local 14/14 is distinct from hosted CI.

