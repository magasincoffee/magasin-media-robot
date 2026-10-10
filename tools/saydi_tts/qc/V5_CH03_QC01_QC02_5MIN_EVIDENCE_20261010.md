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
