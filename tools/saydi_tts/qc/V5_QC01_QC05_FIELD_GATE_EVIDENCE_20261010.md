# SAYDI V5 — QC-01 to QC-05 safe expansion: field evidence and gating

Date: 2026-10-10, DESKTOP-H4A16IL. Branch: `feat/saydi-v5-ch02-qc01-qc02-audit`. **No production activation, no V5 engine change, no SOT NEXT task promotion.**

## Scope and authority

Read `00_PROJECT/SOURCE_OF_TRUTH.md` on main before changes (SHA `7b5d2a1bc2ce55710c6228863fd326ebf6ca4971`); `SAYDI-002` remains the sole authoritative NEXT. The V5/V6 Narration Quality directives explicitly forbid atempo/pitch shift, blind whole-chapter rerender, unbounded repairs, and false FINAL. Full QC08 production gate remains dependent on upstream SAYDI-004/005 contextual narration metadata; this experimental QC work must not bypass it.

Existing stable components untouched: VieNeu V5 ONNX, `render_owner_approved_v5.py` (pause/clean/assemble), `qc_local_segments.py` (Whisper ASR), `saydi_quality_improve.py` (bounded candidate loop), Media Control, Windows Scheduled Tasks and chapter checkpoints.

## Delivered source — experimental and disabled by default

1. `tools/saydi_tts/qc/qc_v5_five_gates.py` — stdlib-only *read-only* chapter gate with explicit `--enable-experimental-qc`, consumes existing V5 `manifest.json`, `concat.txt`, `QC_AFTER_RENDER.json`, optional `REVIEW_QC_GATE.json`, Owner feedback, candidate R2 ASR evidence and SHA-verified candidate WAV. Produces a separate local JSON report. Does not load TTS/Whisper models.
   - **QC-01:** verifies source WAV/gap order/duration, punctuation or structural gap warnings and concentration of uniform pauses.
   - **QC-02:** inspects 20ms PCM WAV endpoints/rate for mechanical seam warnings, **also includes Owner-confirmed two-tone seam**, because smooth amplitude does not guarantee timbre continuity.
   - **QC-03:** checks whether per-segment semantic/prosodic context has evidence; missing context is REVIEW. It **does not invent emotion, style or revoice unverified text**.
   - **QC-04:** consumes baseline ASR, detects REVIEW and abbreviations, checks expected source text; a replacement ASR row is accepted only with matching SHA-256 of its actual candidate WAV. ASR PASS still cannot certify Vietnamese accent or tone.
   - **QC-05:** confirms source and staged REVIEW output hashes and Owner listening scope; requires whole-chapter approval rather than assuming a 5-min sample is sufficient. Latest code adds comparison of source and staged concat WAV/gap references to receipt and enforces pause changes inside the approved segment window.
2. `tools/saydi_tts/qc/qc_v5_repair_plan.py` — separate `--enable-experimental-plan` planner, **proposal only**, up to 8 candidates, max 2 attempts per candidate, immutable text/reference SHA, excludes Owner-approved R2 and segments whose repair limit was exhausted; no autonomous TTS/ASR subprocess, live job writes, Control actions or deployment.
3. `test_qc_v5_five_gates.py` and `test_qc_v5_repair_plan.py` — 12 synthetic local unit checks for default-OFF gating, coverage, source and candidate hash, Owner timecoded fault precedence, bounded retries and approved-segment protection.

## Field evidence (Chapter 3, reviewed source)

Data from `D:\SAYDI\OWNER_APPROVED_NATURAL_V5\Chuong_03`, 285 segments, 285 baseline ASR rows. Accepted sample is **`B_QC02_146_R2_5PHUT.REVIEW.mp3`** (Owner approval applies only to this five-minute sample). Whole-chapter staged REVIEW remains `CHUONG_03_V5_QC01_B_QC02_R2.REVIEW.mp3` SHA-256 `8ce6b51e17eb50402222e68e0f3d20dda2f7fa4b52752189ad12ea2cac6e5a36`. Source production Chapter 3 MP3 SHA-256 remains `4809f72dd6b10c1172e8f029cfa6c492cb2a68d9733f19ad2045595c98e3618f`.

After integrating the Owner-confirmed tone fault and the SHA-validated candidate ASR R2, the standalone QC gate field run produced:

| Gate | Findings | Status | Interpretation |
|---|---:|---|---|
| QC-01 pause | 2 | REVIEW | One too-short structural pause; concentration of identical silence lengths |
| QC-02 join | 1 | REVIEW | Owner-confirmed original WAV145→146 tone mismatch, even though PCM edges were zero |
| QC-03 semantic prosody | 285 | REVIEW | Required structured narration/emotional context **not present** in this V5 manifest |
| QC-04 pronunciation | 163 | REVIEW | 115 distinct ASR REVIEW segments plus 48 abbreviation-review findings (may overlap) |
| QC-05 post-repair | 1 | REVIEW | Chapter FINAL listening gate pending; five-minute B+R2 alone is not enough |

Total **452 dimension-specific findings, not 452 proven audible defects**. The candidate-integrated view correctly reduces baseline ASR-review count from 116 to 115 and preserves the original Chapter 3 source SHA. Explicit original Owner voice-mismatch ledger is present: `OWNER_QC_FEEDBACK.json` with sample time 03:13 and chapter time about 13:06.

The separate repair proposal selected up to six lowest-ASR-score candidate segments (`77, 277, 211, 202, 6, 234`) and **excluded WAV 146**. This does **not** request rendering these segments; each still needs eligibility and resource/Owner gates.

## QA status and honesty limits

- **12/12 local focused tests PASS** before the final standalone concat-diff-verification amendment (7 gate tests + 5 repair-planner tests). The initial real Ch3 gate run and Owner/candidate integration succeeded.
- A later attempt to execute the enhanced full concat-diff gate was blocked by safety controls. **That newly added check is NOT field PASS** and must be rerun in authorized local QA before merge.
- Prior earlier PR work: sample A/B generation, two R2 targeted candidates, 5-minute Owner preference, isolated new Chapter 3 REVIEW, original/source SHA safeguards. None equates to full book QC completion.
- No tests were performed for a live production START/STOP after this change, no deploy, no full emotion classifier, no automatic accent listening, no full original↔staged acoustic A/B all-chapter Owner verdict, and no automatic repair dispatch integration. These are explicit remaining tasks.
- Fail-closed behavior: `status=REVIEW`, `final_eligible=false`, `production_changed=false`; local-only reports include source hash, review hash, segment evidence and rollback path. Existing production modules never import these experimental scripts.
- Rollback: leave new feature flags OFF, ignore staging JSON/MP3; original WAVs, manifest, Windows guardian and existing Control unchanged. Do not merge until QA gates, Owner-reviewed exceptions and upstream SOT prerequisites pass.

Local reports, kept off GitHub:
`D:\SAYDI\QC_STAGING\QC01_QC05_V5_GATES_20261010\CH03_ALL_FIVE_QC_RESULT.json`
`D:\SAYDI\QC_STAGING\QC01_QC05_V5_GATES_20261010\CH03_BOUNDED_REPAIR_PROPOSAL.json`

**Next necessary controlled implementation, not yet DONE:** semantic structured prose/emotion plans (SAYDI-004/005), QC03 confidence/continuity validation, robust Vietnamese accent verification independent of Whisper, all-chapter QA against original source, one-at-a-time guarded repair dispatch into existing job model, and exact-main Control/regression verification before Owner deployment approval.


## 2026-10-10 ~23:15 local: QC-03/04 context/ambiguity extension and read-only Control status

The following additional optional modules were added to this same **Draft** branch and verified on the local host:

- `qc_v5_semantic_contract.py`: builds a hierarchy-aware, source-hash-pinned *context contract* for each segment and validates optional provider-neutral Director suggestions (role/emotion/intensity/confidence/pauses). It rejects changed canonical or spoken-text fingerprints, unsupported values, excessive pauses, large unexplained emotion-intensity discontinuities, and incomplete/low-confidence coverage. It **does not call any LLM or TTS**. Field run on Chapter 3 formed **285 segment envelopes within 31 paragraph/context groups**; all are pending actual semantic interpretation. 6 synthetic tests PASS.
- `qc_v5_vietnamese_triage.py`: compares immutable expected Vietnamese text with existing Whisper output, classifies **diacritic ambiguity** (e.g. hè/he), token substitutions, phrase mismatch, possible omission, and extra/repeated tokens. It refuses expected-text drift, does **not** auto-correct the manuscript or infer acoustic pronunciation faults from ASR alone. Field Chapter 3 with R2 ASR row yielded **262 segments with one or more textual disagreement flags**, containing 151 diacritic-only mismatch events, 227 substitutions, 34 phrase mismatches, 3 potential omissions and 3 potential extra/repeated-token events. *These are ambiguity events, not independently proven utterance mistakes, and may overlap or co-occur.* 6 synthetic tests PASS.
- `qc_v5_control_status.py`: assembles a read-only, disabled-by-default **QC01–QC05** status JSON from the existing staged reports, without touching the live Control UI, API, worker scheduler or production code. Field file `CH03_CONTROL_QC_STATUS.json` was generated with `phase=QC_REVIEW_PENDING` and six safe repair *proposals*, never automatic dispatch. 3 tests PASS.
- `qc_v5_five_gates.py` now has optional original-versus-REVIEW concat reference-diff validation: verifies exactly which spoken WAV and silence references changed against `REVIEW_QC_GATE.json`, and bounds silence edits to the approved five-minute window. A synthetic test rejects falsely declared diffs. This exact new concat-diff gate is **NOT YET field-passed**: an earlier host command with field args was blocked by safety controls. Avoid implying it passed; the original full-Chapter-3 REVIEW production proof remains separately backed by the earlier assembly-stage exact-diff check.

**Total focused local synthetic unit tests: 28/28 PASS** (8 evidence-gate tests, 5 bounded repair plan tests, 6 Vietnamese-language tests, 6 semantics/continuity contract tests, 3 Control status tests). The experimental status and proposal were field run; **full pipeline / historical Control START-STOP regression not rerun**. New files are add-on tools, no stable pipeline refactor, no automatic deployment, no hidden audio changes.

Local evidence location (private book metadata/audio must stay local):
`D:\SAYDI\QC_STAGING\QC01_QC05_V5_GATES_20261010`
- `CH03_ALL_FIVE_QC_RESULT.json` — five QC stage findings and SHA-pinned approved sample, from first field run before latest diff validator.
- `CH03_BOUNDED_REPAIR_PROPOSAL.json` — six candidate IDs for review only; WAV146 protected.
- `CH03_QC03_CONTEXT.json` — 285 source-aware context envelopes, 31 groups; **not** fully-semantic narration directives.
- `CH03_VIETNAMESE_TRIAGE.json` — ASR ambiguity classification, not a pronunciation verdict.
- `CH03_CONTROL_QC_STATUS.json` — consolidated non-live QC status, **not yet wired into Control**.

**Remaining functional gates before SAYDI automatic QC01–05 can be called complete:** validated AI-generated semantic/emotion plans from the existing local Director on every scene (SAYDI-004/005); audio/prosody-based QC03 human calibration; verified Vietnamese sound/diacritic listening beyond Whisper QC04; bounded repair *execution* and reassessment by the existing responsible worker under safe Owner latch; a field GREEN exact-diff and all-chapter regression; full-chapter listening acceptance; CI and exact-main rollout approval. These tasks remain REVIEW/OPEN and must not be conflated with the present 28 unit PASS.

