# SAYDI V5 Chapter 4 — User-rejected joins, swallowed initial syllables and semantic fragmentation
**Field evidence: 2026-10-11; disposition: AUDIO QUALITY REJECTED / REVIEW, not FINAL.**

## Authority and scope
\`00_PROJECT/SOURCE_OF_TRUTH.md\` on **main** remains the only SOT. Current \`SAYDI-002\` stays NEXT. This is a **subordinate QC finding** on Draft PR #101, not permission to bypass V6 P0/P1 tasks, restart production or mark chapter 4 DONE.

The user reported: abrupt/jerky joins; unclear, swallowed first words; unnatural segmentation of sentences and disrupted narration flow. **This is an explicit listening-quality failure and must override simple decoder/PCM/tests PASS.** Do not re-label it accepted based on ASR scores or SHA-only receipts.

## Verified field evidence — H4, private assets remain local

- Uploaded \`CHUONG_04_OWNER_APPROVED_V5.REVIEW.mp3\` SHA-256 \`2ff41e5034a8dd3c4e7a695e02a8bccccd1e4c20071b2f278dbaf50f0e214b8a\` is identical to H4 production REVIEW file. **REVIEW name does not imply Owner approved the chapter:** H4 \`final=false\`, \`owner_approved=false\`, 440/440 segments, previous ASR \`review_count=176\`.
- MP3: mono 48 kHz, ~42:37.512, 128 kbit/s. Existing \`concat.txt\`: **440 voice WAVs + 440 gap WAVs**.
- Root-cause candidate identified in existing **local** \`C:\SAYDI\narration_director_v1\render_owner_approved_v5.py\`: \`clean_clip\` derives a trim threshold from 10-ms RMS windows, may remove start/end audio, then applies **12-ms fade-in + fade-out**. \`pause_after\` uses fixed semantic labels, with **610 ms for ordinary periods**. \`infer(spoken_text, ..., max_chars=320)\` synthesizes individual fragments without neighboring context.
- Read-only comparison of real Chapter 4 **raw vs cleaned** WAVs: **134/440** had more than 50 ms removed in aggregate, **16/440** more than 150 ms, maximum **310 ms**. This does **not** prove which consonants were lost or whether loss happened at the head or tail; it makes trimming a priority review risk.
- Actual voice WAV duration median **4.56 seconds**; median canonical segment **19 words**; 14 fragments shorter than one second. **359/440** gap WAVs measure **610 ms**. Different semantic units currently receive identical gaps in most sentences; pause policy may cause mechanical delivery. 5 manifest cuts are flagged at an intra-parent unit lacking strong final punctuation.
- New read-only \`v5_join_onset_audit.py\` inspects **real raw WAV, cleaned WAV, actual gap WAV, concat order and manifest without recording book text**; when applied on H4: 134 trim-warning segments, 16 severe-trim-review segments, repetitive 610-ms pause risk (359), 5 possible clause-split positions. Result \`REVIEW_NOT_FINAL\`, \`allow_automatic_repair=false\`. H4-only receipt:
  \`D:\SAYDI\QC_STAGING\CI_H4_SAFE_2ee6d2_20261011\_field_p0\CH04_JOIN_ONSET_GATE_20261011.json\` with SHA-256 \`24b55a238c0b2a52c375b47880ba04fac6ab7828a899f2f329764c42b4a4c04d\`.
- The localized chapter-start A/B uses the **first 30 existing voice WAVs**, no TTS model, no resynthesis:
  - A: original cleaned WAVs/fade and existing 610/900/1020 ms pause rules; ~142.010 s, SHA \`cdd7206a46b670652610f111e8e02b6e9b560defde52800a9e857eae9bd08eff\`.
  - B: original untouched raw WAVs and isolated **experimental context-sensitive pauses** (roughly 380ms within complete sentences and longer at paragraph/heading boundaries); ~136.750 s, SHA \`9ce42c23f0f19d1e88df3256195f30c8a5ab6486e2bb033014c85da902c84b4c\`.
  - Both are **hypothesis test clips, not corrected/Owner-approved audio**. If both have swallowed starts, original VieNeu render/text segmentation needs targeted re-render under qualified field and resource gates. If B reduces clipping and improves flow, implement a bounded, documented trim/pause policy, avoiding unsafe blanket tempo changes.
  - Open on H4:
    \`D:\SAYDI\QC_STAGING\CI_H4_SAFE_2ee6d2_20261011\_field_p0\CH04_NO_TRIM_PAUSE_AB_20261011\CH04_COMPARE_A_B.html\`
  - AB source and audio remain **local only**; do not commit.
- At last observed H4 state free RAM was **~1.14 GiB**, well below the protected Ch02 V5 heavy-QC 2.3 GiB threshold; **no VieNeu/Whisper workers, renderer or production dispatcher started**. No manifest/WAV production file was modified.

## Correction sequence — gated, no blind rerender

1. **P0 editorial segmentation first.** Re-read source SHA/punctuation and paragraph/semantic structure. Guard original authorial pause marks and produce an immutable proposed segmentation manifest in staging. Prefer complete sense units instead of arbitrary <320-character fragments; a resegmented segment is a **new manifest/checkpoint identity**, never overwrite old segment indices/hashes or interpret old approvals as transferable. Detect short fragments, breath/phrase cut-offs and clause splits. Escalate ambiguous source cases to Owner.
2. **P1 onset fidelity before silence cosmetology.** Localized A/B listen at the first words and flagged segment indices; compare original \`chunks\` waveform and its \`stitch_cleaned\` derivative, audibly check soft initials and Vietnamese tones. Do not assume ASR alone proves a correct beginning. Disable automatic energy-based trimming/fades only on a separate **new controlled candidate** once actual failure cases are verified; do not edit stable production renderer outside an authorized patch/cutover. Test gradual gains at false-start and stop consonants.
3. **Semantic pauses / continuity.** Base pause suggestions on sentence intent, paragraph, quoted speech, ellipses, and breath grouping rather than an indiscriminate 610ms pause; preserve original reading speed (no \`atempo\`), voice fingerprint, and word order. Small local A/B tests only. Compare *same words* and maintain WAV source hash evidence.
4. **Only if the native WAV already misses/garbles a word**, execute **≤2** isolated candidate repairs in an approved resource-safe session with source+submitted TTS text+reference hash bound; audit prior/following neighbor joins, dual-evidence pronunciation QC, and untouched chunk SHA. Never regenerate 440 chunks or double-QC accepted segments.
5. **P2 field review:** Complete QA of an entire 3–5min passage with head/middle/end joins and first words, plus a representative 20–40min chapter listening acceptance. Owner subjective judgment is authoritative for naturalness; if the user reports abrupt joins or swallowed words, **QC FAIL/REVIEW**, irrespective of decoder success. Then test reboot, durable STOP/START, process isolation, resource thresholds and rollback before production promotion.

## Automation status / safeguard

The added \`tools/saydi_tts/qc/v5_join_onset_audit.py\` is opt-in and OFF by default. It only reports risks. \`test_v5_join_onset_audit.py\` contains synthetic fail-closed safety tests (wrong concat order, wrong WAV path/format, pause duration mismatch, repeated pauses, overtrimming, unapproved promotion, transcript privacy). CI Windows \`test_v5_*\` runs it as part of Draft PR #101.

**Chapter 4 audio quality decision: REJECTED FOR RELEASE.** Continue P0/P1 diagnosis and listening; do not auto-mark any V6 package or \`SAYDI-008/009\` DONE. A/B excerpts are for Owner comparison and not authorization for chapter replacement.
