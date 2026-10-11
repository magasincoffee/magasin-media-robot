# SAYDI P1 offline QC — WAV repair candidate + Owner review bundle (2026-10-11)

**State:** Implemented and **synthetic offline tested** on the working assistant container while the Owner's Windows H4 host has no power. **NOT deployed**, PR #101 remains Draft. Current authority: \`00_PROJECT/SOURCE_OF_TRUTH.md\` on main, with \`SAYDI-002\` NEXT. This work is subordinate to, and does not bypass, P0 / SAYDI-008 / runtime readiness.

## Code and capabilities

- \`v5_p1_wav_candidate_gate.py\`: compares the **actual bytes** of an original V5 WAV, one SHA-receipted candidate and optional immediate neighbor WAVs. Checks SHA, PCM mono 16-bit format and sample rate, decode/truncation, duration/rate changes, near-silence, clipping, RMS gain, and PCM boundary-jump *risk*. Technical signals are heuristic; they are **not evidence of correct spoken Vietnamese tone, timbre, prosody or inaudible seams**. CLI opt-in, read-only, exclusive staging report. Fails closed on stale/changed WAV and malformed hash. Never invokes TTS/ASR or overwrites a WAV.
- \`test_v5_p1_wav_candidate_gate.py\`: 17 synthetic WAV test cases (generated sine-tone PCM using Python's standard library); checks silent/clipped/too-short candidates, tampered SHA, unsupported codecs, truncated file, neighbor hashes, no-repair repeat, max-two retry policy, CLI off by default and no report overwrite.
- \`v5_p1_owner_review_bundle.py\`: assembles a **read-only JSON candidate** for an eventual existing MAGASIN Control Center Owner QC view. Consumes P0 editorial, P1 repair-readiness, QC01-05 and optional WAV candidate reports with SHA / chapter / fingerprint checks. Only exports whitelisted issue codes, indices, counts and timecodes from already available QC04 metadata; does not export private book text, speaker metadata, book paths or model prompts. Unknown timecodes are null, not invented. Paginates 25 issues, preserves full totals. The six still-unverified release gates remain explicit.
- \`test_v5_p1_owner_review_bundle.py\`: 14 synthetic unit tests, including non-leakage of a deliberately injected private text field, report SHA mismatch, invalid chapter, false FINAL, altered WAV approval, invalid codes, true/unknown timecodes and pagination.

**Neither module** connects itself to Supervisor, the existing repair worker, VieNeu, Whisper, Chrome, scheduled tasks or Supabase. Outputs always remain REVIEW and \`approved_to_dispatch=false\`, \`approved_to_promote=false\` or equivalent.

## Actual test execution and proof

Off-host sandbox: CPython standard-library \`unittest\`, no internet, real/local manuscript or user-owned WAV:
\`\`\`text
python -m unittest discover -s /mnt/data/saydi_offline -p 'test_v5_*' -q
Ran 47 tests
OK
\`\`\`

Tests include the already-pushed \`v5_editorial_review_triage.py\` (16), \`v5_p1_wav_candidate_gate.py\` (17) and \`v5_p1_owner_review_bundle.py\` (14). Git **blob hashes** of the six local source/test files matched the corresponding GitHub Draft branch file SHA values:

\`\`\`text
v5_editorial_review_triage.py        86a04436b036174203d3fa5465afe2ed510ae22e
test_v5_editorial_review_triage.py   40114204bbb2e93d506bc26f6ccebfce4d852527
v5_p1_wav_candidate_gate.py         52ff704bfde9734644871427b6d7f6bf3c5200a7
test_v5_p1_wav_candidate_gate.py    817e9c39ccbb2d07d6c41a374ded7325186d898b
v5_p1_owner_review_bundle.py        12a6b400d933ddbcec39a59e32f1c027975ba4a8
test_v5_p1_owner_review_bundle.py   9a66437f02d11e9acd3c80b09476ae54e1292e19
\`\`\`

These **47 focused synthetic tests are not** a hosted GitHub Actions CI GREEN result, nor verification of all other V5 tests / P1 readiness code, H4 audio listening, checkpoint resume, Windows service behavior, or original-chapter fidelity. No new chapter status/approval or WAV changed.

## Safe demonstration with private field artifacts (H4 only after power returns)

Do not assume any example WAV path exists or its provenance is verified. The existing authorized worker must supply a stable original WAV, staged candidate WAV, neighboring WAVs, and actual byte hashes. Build a **new** \`saydi-v5-p1-wav-candidate-gate-1\` receipt with exact:\n- \`schema\`, \`segment\`, \`attempts_used\`, \`manifest_sha256\`, \`source_sha256\`, \`voice_reference_sha256\`, \`tts_text_fingerprint\`\n- \`original_wav_sha256\`, \`candidate_wav_sha256\` and optional \`left_wav_sha256\`, \`right_wav_sha256\` **verified locally**, not invented.
Use a staging path, not source WAV folder:

\`\`\`powershell
python tools/saydi_tts/qc/v5_p1_wav_candidate_gate.py \`
  --original "<ACTUAL_VERIFIED_V5_ORIGINAL_WAV>" \`
  --candidate "<SINGLE_STAGED_CANDIDATE_WAV>" \`
  --receipt "<SHA_BOUND_LOCAL_CANDIDATE_RECEIPT.json>" \`
  --left "<ACTUAL_VERIFIED_LEFT_NEIGHBOR_WAV>" \`
  --right "<ACTUAL_VERIFIED_RIGHT_NEIGHBOR_WAV>" \`
  --output "<NEW_UNIQUE_QC_STAGING_WAV_REPORT.json>" \`
  --enable-wav-candidate-inspection
\`\`\`

Then combine existing metadata reports **only if their chapter/SHA chains match**:

\`\`\`powershell
python tools/saydi_tts/qc/v5_p1_owner_review_bundle.py \`
  --editorial "<P0_EDITORIAL_REPORT.json>" \`
  --repair-readiness "<P1_REPAIR_READINESS_REPORT.json>" \`
  --qc01-05 "<CURRENT_QC01_05_REPORT.json>" \`
  --wav-candidate "<NEW_STAGING_WAV_REPORT.json>" \`
  --output "<NEW_UNIQUE_OWNER_REVIEW_BUNDLE.json>" \`
  --enable-review-bundle
\`\`\`

If the segment is at the edge of a chapter and a neighbor does not exist, omit its parameter and let the tool keep that boundary **REVIEW**; do not supply an unrelated WAV to fabricate a pair.

## Still blocked from P1 completion

1. **P0 not signed off:** original manuscript/source lineage, 60 historical paraphrase suspects and independent Vietnamese spelling/semantics need field inspection and genuinely independent review.
2. **P1 audio identity and expressive QC:** local narrator fingerprint and listening of whole chapter; independent Vietnamese tone and join verification beyond ASR/PCM heuristics.
3. **P1 worker integration:** the read-only readiness/worklist contracts must be connected to the *existing* authorized worker only after SOT gates, exact hash-pinned checkpoint, RAM/mutex, ≤2 retries and idempotent recovery are proven.
4. **Hosted CI:** exact-head run and any failures must be inspected. Empty workflow API lists cannot certify GREEN.
5. **SAYDI-002 / Control Center** START/STOP/reboot acceptance and chapter Owner listening remain separate and must pass before production.

**Rollback:** None required in production. New modules are OFF by default and exist only in Draft PR #101. Never reset existing Chapter 2 V5 640 checkpoints or replace approved Chapter 3 five-minute sample.
