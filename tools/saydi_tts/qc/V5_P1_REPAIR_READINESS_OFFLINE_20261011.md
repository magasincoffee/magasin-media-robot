# SAYDI P1 — bounded repair readiness, offline-only draft (2026-10-11)

**Authority:** `00_PROJECT/SOURCE_OF_TRUTH.md` on `main`. `SAYDI-002` is the current NEXT. This module is only a P1 preparation substep for the later authorized SAYDI-008/QC work. PR #101 remains Draft.

## Deliverable

`tools/saydi_tts/qc/v5_p1_repair_readiness.py` is a stand-alone opt-in pure-Python **inspection gate**. It reads the *existing* V5 QC01–QC05 report, the *existing* bounded worklist, a chapter manifest and optionally the P0 lineage report. It requires:

- Matching chapter and review-MP3 identity, correct source and narrator SHA-256 fingerprints, plausible manifest segment count and exact SHA of checked WAV in the worklist.
- Exact type/scope of owner-confirmed defect, valid original `tts_text_sha256` fingerprint, ≤2 repair attempts, no duplicate segment and no auto-run flag.
- If provided, the P0 lineage receipt matches the source and exact raw-manifest SHA and has contiguous SHA-bound per-segment lexical provenance. This receipt is still **not** independent spelling, semantic or original-source verification.
- Fail-closed for missing or stale critical receipts; if P0 evidence is absent, marks the limitation explicitly.

**Never executes repairs:** even all checks passing produces `REVIEW_ONLY_NO_RUNTIME_PERMISSION` with `approved_to_dispatch=false`, `approved_to_promote=false`, `worker_started=false`, `automatic_promotion=false` and `owner_final=false`. The code does not import VieNeu, Whisper, the Control Center, scheduler or worker APIs and does not create a second robot.

`tools/saydi_tts/qc/test_v5_p1_repair_readiness.py` adds offline synthetic test cases for stale source, changed MP3/WAV SHA, duplicate owner-confirmed action, unsupported ASR-only defect, action-count mismatch, retry >2, malformed manifest index, altered narrator/text fingerprint and the no-dispatch/no-FINAL invariant.

## Status/evidence

- **Code and tests committed on PR #101**.
- **Exact-head hosted CI:** NOT VERIFIED (commit workflow query may not expose every GitHub Check Run).
- **Local H4 execution:** NOT RUN; Owner reported power outage. No manuscript, WAV or checkpoint read in this step.
- **Production:** NOT ENABLED; no PR merge, service/robot START, chapter repair or audio acceptance.
- **P0:** still incomplete. P1 can be prepared in parallel; P1 approval, actual repair integration and deployment cannot bypass P0 or SOT tasks.

## Acceptance remaining

1. Run offline synthetic regression on an isolated checkout of the **exact PR head**.
2. After H4 returns, check RAM/worker identity/checkpoints before any audio operation; only then compare real lineage, owner-confirmed QC event and bounded worklist with actual WAV/neighbor hashes.
3. Independently corroborate Vietnamese tones and timbre, verify before/after improvement, protect approved samples and enforce unchanged-neighbor SHA during isolated repair; no ASR-only retries.
4. Exercise pause/resume/reboot and Owner STOP/START controls under authoritative SOT gates, and require exact-head GREEN before any merge.
5. Owner listening approval for complete chapter; only permitted release authority can mark a validated `FINAL`.

**Rollback:** Leave this opt-in Python script OFF; current V5 audio/render/QC and Control Center stay untouched.
