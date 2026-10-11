# SAYDI V5 — Source lineage + punctuation QC pilot (2026-10-11)

**State:** SOURCE / TEST CODE CREATED ON DRAFT PR #101, **HOST EXECUTION PENDING**. SOT: `00_PROJECT/SOURCE_OF_TRUTH.md` on `main` alone determines task authority; `SAYDI-002` remains NEXT. No production promotion, render, scheduler or model changes.

## Changed files

- `v5_source_lineage.py`: opt-in, read-only, raw-manifest-SHA-bound comparison of the *exact local canonical UTF-8 chapter text* with all ordered V5 canonical segments, Vietnamese NFC/casefold word tokens, punctuation drift, immutable source span hashes and local legacy paraphrase-audit warning. It cannot reword, synthesize, transcribe or publish. If source SHA does not match one of the explicitly supported UTF-8 representations, it refuses the check.
- `test_v5_source_lineage.py`: synthetic checks for 1:1 ordered source spans, removed/moved words, wrong Vietnamese accent, punctuation difference, stale source/legacy SHA, preserved author repetitions, no manuscript in reports, no source/audio mutation and default OFF.
- `v5_editorial_multiround.py`: existing editorial multi-pass checker now accepts only a `RAW_MANIFEST_BYTES` SHA-bound lineage report from exactly the same manifest and source. When complete, it replaces the aggregate source-provenance uncertainty with grounded lexical coverage. Punctuation and semantic/independent-review exceptions are **still REVIEW**, never a false FINAL.
- `test_v5_editorial_multiround.py`: linked lineage, tampered/stale evidence and punctuation cases.

## SAFE validation steps (when DESKTOP-H4A16IL is connected)

1. Confirm that the actual Source of Truth, active worker identity, RAM budget, chapter checkpoint and Git branch still match before doing anything. Do not start VieNeu, Whisper, Windows tasks or Control actions.
2. In a **separate temporary branch checkout** of PR #101 (not the production directory), execute:
   `python -m unittest discover -s tools/saydi_tts/qc -p "test_v5_*" -v`
   Distinguish PASS, FAIL and SKIP; do not claim GREEN if CI on the **exact head** is absent.
3. On an **already available, owner-authorized, local chapter text in UTF-8** (not the PDF or externally scraped text), explicitly identify its real path. Do **not** assume manifest `source_path` is text, and never auto-OCR a private PDF for this pilot. Confirm the document content/source hash locally.
4. Run (paths to match actual files):

   ```powershell
   python tools/saydi_tts/qc/v5_source_lineage.py `
     --manifest "D:\SAYDI\OWNER_APPROVED_NATURAL_V5\Chuong_03\manifest.json" `
     --source-utf8 "<VERIFIED_LOCAL_CANONICAL_CHAPTER_UTF8_PATH>" `
     --legacy-audit "D:\SAYDI\OWNER_APPROVED_NATURAL_V5\Chuong_03\editorial_audit.json" `
     --out "D:\SAYDI\QC_STAGING\CH03_V5_SOURCE_LINEAGE_20261011.json" `
     --opt-in-source-lineage

   python tools/saydi_tts/qc/v5_editorial_multiround.py `
     --manifest "D:\SAYDI\OWNER_APPROVED_NATURAL_V5\Chuong_03\manifest.json" `
     --legacy-editorial-audit "D:\SAYDI\OWNER_APPROVED_NATURAL_V5\Chuong_03\editorial_audit.json" `
     --source-lineage "D:\SAYDI\QC_STAGING\CH03_V5_SOURCE_LINEAGE_20261011.json" `
     --report "D:\SAYDI\QC_STAGING\CH03_V5_EDITORIAL_MULTIPASS_20261011.json" `
     --enable-experimental-editorial-qc
   ```

5. Refuse to overwrite existing reports or canonical audio. If `SOURCE_SHA256_MISMATCH`, stop the source-coverage claim and determine whether the original manifest refers to a different representation; do not bypass SHA. If source lexical mismatch exists, return exact *indices and counts only*, then verify locally against original manuscript.
6. Before claiming multi-pass editorial success: resolve historical 60 paraphrase suspects against original text with a genuinely independent reviewer (local model or authorized human), then explicitly verify spelling/semantics and neighboring paragraph context. Two nominal validator IDs are not evidence that checks were independent.
7. Spoken Vietnamese tone/accent, early-utterance timbre and joins still require audio-based confirmation beyond Whisper. Do not dispatch any real repair from this read-only audit.
8. Existing SAYDI V5 checkpoints, approved narrator, reference, WAV/MP3, Control/START/STOP, scheduled tasks and Supabase stay untouched; rollout remains gated by CI, SOT authority, regression and Owner listening.

## Current proof and limitations

GitHub draft code and synthetic fixtures exist; **no actual hardware run or CI GREEN has been verified for these new source-lineage changes**. DESKTOP-H4A16IL appeared **offline** at time of this checkpoint. The previously measured 40 PASS / 2 SKIP regression and V4 Chapter 3 editorial findings refer to the **earlier** code, not the new branch head.

**Release decision: REVIEW / NOT FINAL / NOT PRODUCTION.**
