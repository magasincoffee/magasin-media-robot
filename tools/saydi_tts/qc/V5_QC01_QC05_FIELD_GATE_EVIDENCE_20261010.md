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
