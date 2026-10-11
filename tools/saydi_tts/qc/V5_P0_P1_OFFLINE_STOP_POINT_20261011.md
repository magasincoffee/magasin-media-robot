# SAYDI P0/P1 offline execution stop point — 2026-10-11

Authority: **\`00_PROJECT/SOURCE_OF_TRUTH.md\` on \`main\`**. \`SAYDI-002\` remains the sole NEXT top-level task. Draft PR #101 carries subordinate QC preparation only. **No production code, audio, Windows task, Control Center service, Supabase record, narrator/reference or approved checkpoint was touched.**

## Offline implementations created / tested

| Capability | Repo file | Evidence |
|---|---|---|
| Vietnamese editorial drift triage, bounded and paginated | \`v5_editorial_review_triage.py\` | 16 synthetic tests |
| SHA-pinned original/candidate WAV/neighbor technical QC | \`v5_p1_wav_candidate_gate.py\` | 17 synthetic tests |
| Source-safe Owner chapter exception bundle with real/unknown timecodes | \`v5_p1_owner_review_bundle.py\` | 14 synthetic tests |
| Retry journal deterministic replay safety, at most 2 attempts and unverified sample receipt (NOT authenticated Owner acceptance) | \`v5_p1_repair_replay.py\` | 19 synthetic tests |

**Test command:** \`python -m unittest discover -s <isolated-offhost-source-folder> -p "test_v5_*" -q\`

**Actual result:** \`Ran 66 tests / OK\` in the independent container. Four modules and their test files were byte-matched against GitHub Draft branch content by git blob SHA (not merely similar source text).

\`\`\`text
v5_editorial_review_triage.py       86a04436b036174203d3fa5465afe2ed510ae22e
test_v5_editorial_review_triage.py  40114204bbb2e93d506bc26f6ccebfce4d852527
v5_p1_wav_candidate_gate.py        52ff704bfde9734644871427b6d7f6bf3c5200a7
test_v5_p1_wav_candidate_gate.py   817e9c39ccbb2d07d6c41a374ded7325186d898b
v5_p1_owner_review_bundle.py       12a6b400d933ddbcec39a59e32f1c027975ba4a8
test_v5_p1_owner_review_bundle.py  9a66437f02d11e9acd3c80b09476ae54e1292e19
v5_p1_repair_replay.py             88dc72cd1985d2bbf8164587353b5f602b1daddc
test_v5_p1_repair_replay.py        512e99a8574d1f9c5968969195f21fd0104386c0
\`\`\`

**Receipt safety:** A sample receipt containing a SHA-256 does NOT prove the Owner authored or approved it. The replay gate explicitly emits `owner_identity_verified=false`; event status `SAMPLE_RECEIPT_UNVERIFIED_NOT_FINAL` never grants approval or production action.
\n**Limit of this proof:** 66 cases cover only these four synthetic source-safe modules and do not include all existing SAYDI V5 regression fixtures, the prior P1 readiness module, production integration, hosted CI, speech/audio listening, original chapter text, or field checkpoints. Tests run off-host on synthetic PCM signals, **not** on the user's real WAVs.

## What is still blocked for completion (not optional)

1. P0 independent original-manuscript spelling/semantic review and resolution/triage of the 60 old paraphrase *suspects*, bound to the real Ch3 source; old-V4 wording is not a substitute for the original.
2. Actual Vietnamese tone/pronunciation, emotion/prosody continuity, timbre and audible seam confirmation. Technical PCM jump/rms/format heuristics cannot prove these dimensions.
3. Confirm the approved Chapter 3 sample and 285 actual V5 segments and preserve their identity. Chapter 2 V5 existing 640 checkpoints remain protected; resource gate requires actual free RAM check (historical minimum 2.3 GiB). Do not reboot/start unsafe workers blindly.
4. Connect \`v5_qc_bounded_worklist\` -> \`v5_p1_repair_readiness\` -> existing authorized single-segment VieNeu worker -> new WAV candidate gate -> neighbor/Whisper secondary audio QC -> replay safety -> Owner review bundle. **This pipeline has NOT been installed or exercised on the local host.** Do not create a new parallel robot or default-on worker.
5. Run full impacted regression and exact-PR-head GitHub Actions checks; CI GREEN is NOT established by empty workflow API result sets. Test PowerShell start/stop/reboot/resume, durable checkpoint/worker ownership, no duplicated renders.
6. Follow the SOT gate order. Require Owner chapter listening and genuine release approval before PR merge, chapter \`FINAL\` or production dispatch.

## Precise safe return-to-host sequence

1. When H4 is actually online, capture device identity, active worker/mutex, RAM, scheduled tasks and precise last durable checkpoint **without starting a worker**.
2. In a scratch checkout of the exact PR head, run \`python -m unittest discover -s tools/saydi_tts/qc -p "test_v5_*" -v\` and main core tests. Classify PASS, FAIL, SKIP separately.
3. Only after verifying real UTF-8 chapter source SHA locally, run the opt-in P0 \`v5_source_lineage.py\` and existing multiround QC, then resolve *real* textual exceptions.
4. For one Owner-confirmed error, create a single candidate in the existing safe runner under checkpoint/source/voice hashes, with at most two attempts. Do **not** automatically run on ASR-only anomalies.
5. Inspect real original/candidate/neighbor WAV bytes and audit/replay receipts in a new staging folder; compare original and unmodified neighbor hashes. Require independent pronunciation listening and no new join or prosody defects. Refuse to replace approved source WAVs automatically.
6. Expose the whitelisted QC exception summary in the already established Control Center UI **only after** approved UI integration gates. No separate dashboard/robot needed.
7. STOP/START, low-RAM and reboot regression plus exact-head CI and SOT verification are required before any deployment.

All new scripts are OFF by default, output \`REVIEW\` or \`REVIEW_ONLY_NO_DISPATCH\`, write only exclusive staging metadata if explicitly opted in, and cannot assert \`FINAL\`.

**Owner approval already available for the sample remains narrowly scoped to the particular approved Chapter 3 ~5-minute R2/B excerpt; not Chapter 3 as a whole.**
