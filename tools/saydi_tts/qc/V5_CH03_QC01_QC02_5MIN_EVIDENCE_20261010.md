# SAYDI V5 Chapter 3 — five-minute QC-01/QC-02 owner listening package

Date: 2026-10-10 (Asia/Ho_Chi_Minh). Status: **PREVIEW_READY; OWNER_LISTENING_PENDING; production disabled**.

## Provenance and runtime safety

- Source-of-truth checked from `main` before operation: `00_PROJECT/SOURCE_OF_TRUTH.md`. Authoritative NEXT remains `SAYDI-002`; this is subordinate non-production QA.
- Host: DESKTOP-H4A16IL (connected through authorized Remote Desktop Commander).
- Original source MP3: `D:\SAYDI\OWNER_APPROVED_NATURAL_V5\Chuong_03\CHUONG_03_OWNER_APPROVED_V5.REVIEW.mp3`.
- Original MP3 SHA-256 before and after: `4809f72dd6b10c1172e8f029cfa6c492cb2a68d9733f19ad2045595c98e3618f` — verified **unchanged**.
- Chapter 3 source baseline: **285/285 rendered segments, 285/285 basic QC**, `REVIEW_READY`, not `FINAL`. Active Control job last observed `DONE`, scheduled guardian remains enabled; no render/TTS/recheck command was issued by this QC task.
- VieNeu voice/narrator, native speaking pace, original text, approved audio, existing Control and scheduler untouched. No time stretching or `atempo`; FFmpeg-only short preview, using 1 encoding thread.

## Local listening output

`D:\SAYDI\QC_STAGING\CH03_V5_QC01_QC02_20261010\listening_5phut\`

Windows Desktop shortcut: `C:\Users\admin\Desktop\SAYDI QC CHUONG 3 - 5 PHUT.lnk`.

| Name | Measured duration | SHA-256 | What to evaluate |
|---|---:|---|---|
| `A_BAN_GOC_5PHUT.mp3` | 300.890s | `c8734137963a9426c4f238af826d6e544f3afba4d06afdfd9e99c478295634eb` | Original V5 pause placement |
| `B_THU_NHIP_NGHI_5PHUT.mp3` | 301.770s | `da87d75f1682e207c2c948e0ed99522420e3ac92ce0b432c51cfdf6122bc6087` | QC-01 trial of cadence |
| `QC02_CHUONG_03_GOC_5PHUT.mp3` | 300.024s | `d6ae2b8a4adc51a26b1fb20abde1fdd0cc4fd065460a969d367472c84d8c4fae` | QC-02 join listening, **no repair applied** |

- The A/B pair contains the exact **59 identical cleaned spoken WAV references**, segments 107–165. A/B assembly differs **only at 25 punctuation-based silence boundaries**, net difference **+880ms**, verified against the actual MP3 duration delta. No render from VieNeu was performed.
- The QC-02 original excerpt is a stream-copy sample of the same 5-minute portion of Chapter 3's produced MP3, giving a continuous context for listening rather than very short 8-second clips.
- **58 cleaned WAV joins** were inspected for endpoint amplitude outliers; none exceeded the conservative technical endpoint threshold. This **does not establish that all audible joins are clean**: internal TTS transients and perceptual discontinuities can still exist.
- Report with every changed silence and examined seam: `CH03_QC01_QC02_5PHUT_REPORT.json` on local disk (not in GitHub, to avoid source/segment metadata leakage). An Owner-facing `HUONG_DAN_NGHE.txt` was also created.

## Acceptance and rollback

This is an **opt-in, disconnected comparison script**: `tools/saydi_tts/qc/preview_chapter3_5min.py` reuses the existing scoped helpers `preview_5phut_context.py` and `v5_ch02_seam_edges.py`. There are **no changes to live production modules, API, templates, voice models, scheduled tasks, or current chapter outputs**. Rollback is immediate: do not invoke the preview script, remove preview files after review if desired, leave source unchanged.

- Functional checks PASS: three MP3s decode with FFprobe and have durations ~5min, MP3 source SHA-256 unmodified, identical spoken WAV references across A/B, 25 candidate pause changes matching +880ms runtime length, 58 seam endpoints scanned, baseline report and production state preserved.
- Quality acceptance: **REVIEW/PENDING**. Owner must select A or B on naturalness, identify any timecoded strange pauses, and listen for actual join faults in the QC-02 original. Technical metadata is not proof of human perceptual PASS. QC-03 to QC-05 not advanced.


## Owner QC adjudication — 2026-10-10 (21:55 Asia/Ho_Chi_Minh)

**QC-01 listening choice:** Owner listened to the ~5-min Chapter 3 pair and explicitly reported **"bản B hay hơn"** (B sounds better). Preserve the preferred B trial (same 59 spoken WAVs, 25 isolated pauses, +880ms) as the **provisional narration-cadence reference for this pilot**. This is Owner preference on this sample, **not** production release approval or proof all chapter pauses are correct.

**QC-02 confirmed listening exception:** Owner heard two noticeably different voice tones **from 03:13 onward** in `QC02_CHUONG_03_GOC_5PHUT.mp3`. The QC-02 stream-copy starts at approximately 592.89s into the original chapter, so 03:13 of the preview maps to **785.89s = Chapter 3 ~13:05.89**. The closest real assembled seam occurs at **785.04s**, between original cleaned WAV **145 → 146**, with 610ms configured silence. The subsequent voice starts around **785.65s**. Owner's audible timestamp is ~0.24s after the start of WAV 146, strongly narrowing the candidate seam.

**Source and existing QA evidence:**
- 145 says (short context): "Giải thích cho nhóm ...". 146 starts a sentence introducing "VOC". Do not rewrite the source or substitute a phonetic paraphrase without a source-safe pronunciation review.
- Source manifest carries the **same canonical reference SHA-256** for both indices; this excludes an obvious reference-file identity swap but does **not** prove stable synthesized timbre.
- Current baseline ASR: **index 145 REVIEW**, similarity 0.9299; **index 146 REVIEW**, similarity 0.9341. ASR alone cannot explain or certify the Owner-heard tone discontinuity.
- Previous zero-valued PCM seam endpoints only eliminate one class of impulsive click, **not** a two-tone speaker/prosody drift. Do **not** crossfade or globally normalize as a supposed voice correction.
- The source Chapter 3 MP3 remained unchanged, SHA-256 `4809f72dd6b10c1172e8f029cfa6c492cb2a68d9733f19ad2045595c98e3618f`. Control job was `DONE` for Chapter 3; no active render changed by this follow-up.

**New local focused listening evidence:** `D:\SAYDI\QC_STAGING\CH03_V5_QC02_VOICE_JOIN_145_146\CH03_OWNER_CONFIRMED_JOIN_145_146_1PHUT_ORIGINAL.mp3` is a 70.032s untouched source excerpt from 02:38 through 03:48 of the Owner's QC02 clip, SHA-256 `e0e08c9cbe48ae3019086b30325d7fc0a4c3d5153629b9e6f8e9d3b98fcb7db0`. No new TTS candidate or repair file has yet been generated; an attempted remote creation of an isolated rerender script was rejected by tool safety checks, so the task must remain **REVIEW / REPAIR_PENDING** rather than claiming a repaired voice. Do not retry by unreviewed production modification.

**Targeted repair acceptance gate:** Isolate index 146 (and check neighbor 145) with the same immutable V5 approved voice source and original text; at most a bounded 1–2 candidate attempts in a protected, separate staging area. Compare original versus candidate with preceding and following sentences at native pace, ASR pronunciation/diacritics, reference fingerprint and decoded acoustic properties. Keep the original WAV and original chapter MP3 unchanged. Only promote after a real 30–60s A/B listening comparison confirms tonal continuity and content preservation; failures stay REVIEW, never auto FINAL. Avoid touching unrelated book/chapter jobs.

