# SAYDI V5 editorial multi-pass QA — isolated field evidence (2026-10-10)

**Authority:** `00_PROJECT/SOURCE_OF_TRUTH.md` on `main` remains authoritative. `SAYDI-002` is NEXT. This is an opt-in, subordinate **read-only** QC experiment on Draft PR #101; not a production activation, not release acceptance, not a replacement for existing `editorial.py`, VieNeu, Supervisor or Control.

## Delivered

- `v5_editorial_multiround.py`: deterministic, distinct checks for structural coverage, Unicode/orthographic artifacts, continuity/overlap *candidates*, original/canonical/editorial/spoken token mismatches and optional independent-review receipts.
- Exact manifest SHA-256 binding for external review receipts; rejects duplicate/stale reviewer IDs and independent source identity claims. Does not generate its own "independent" LLM review.
- Binds existing local `editorial_audit.json` to source SHA, approved reference SHA and segment count, without exporting manuscript or relying on an unverified narrator control.
- Existing `tts_text_sha256` is a legacy producer-specific fingerprint: on real Chapter 3 it is **not** SHA-256 of `spoken_text`, `canonical_text`, `editorial_text` or `origin_spoken_text_v4` UTF-8. Therefore it is treated as opaque unless a versioned `sha256_utf8_spoken_v1` scheme is explicitly declared. Previous blanket comparison incorrectly flagged all 285 records, which was fixed and regression-tested. It must not recur.
- No auto-correction, text rewriting, TTS or ASR calls, voice switching, control/scheduler changes, auto-dispatch, publishing, `FINAL`, or source/audio overwrites. Disabled by default and reports can never issue audio acceptance.

## Verification on DESKTOP-H4A16IL

Source: Draft PR #101, tested after commit `020892bfe8af35af96cfc4ca2f76eb677f835b46`; independent checkout in scratch, not the production checkout.

`python -m unittest discover -s tools/saydi_tts/qc -p "test_v5_*" -v`

**42 test cases executed successfully; 2 additional field-asset-dependent cases SKIPPED**. Exit code 0. This is local focused regression, **not hosted CI GREEN**, not full start/stop/boot testing, and not listening acceptance.

Field: `D:\SAYDI\OWNER_APPROVED_NATURAL_V5\Chuong_03\manifest.json` and `editorial_audit.json`; output only in `D:\SAYDI\QC_STAGING\CH03_V5_EDITORIAL_GATE_20261010\EDITORIAL_MULTIPASS_REVIEW_V4.json`.

- 285 segments; status `REVIEW`; **0 blocking findings**.
- **7 compact finding records**, including **one aggregated `SOURCE_PROVENANCE_UNVERIFIED` alert with count=285** because per-segment original manuscript text/span cannot be independently authenticated from this V5 manifest; **not 285 known textual errors**. This aggregation avoids 285 redundant Owner-facing alerts.
- 3 possible boundary word repeats and 1 possible clause cut within a parent group; all are **REVIEW candidates**, not automatic edits.
- 1 pending independent spelling/semantic-review receipt.
- 1 legacy-audit paraphrase-review category; it references **60 historical paraphrase suspects**, not 60 proven active narration errors or 60 new render requests.
- Legacy editorial audit: `word_integrity=PASS`, `v5_spoken_text_diff=false`, `canonical_source_utf8=true`. The audit is verified to the same source SHA, voice/reference SHA and 285 segments; it is **not independent semantic/spelling acceptance**.
- All 285 V5 TTS text fingerprints are intentionally tracked as opaque, rather than falsely blocking on an undocumented hash scheme.

The earlier V1 field audit falsely returned `BLOCKED` with 285 hash mismatches; **superseded by the corrected V4 report**. Keep earlier report as diagnostic regression evidence only, never release status.

## Safe next gates (NOT DONE)

1. Source-aware editorial second review using the real book text *locally* and explicit word/paragraph provenance; investigate the 60 legacy paraphrase suspects, distinguish genuine changes from valid deterministic normalization, and explicitly verify spelling and narrative continuity across neighboring chunks. Never pass by simply repeating the same algorithm.
2. Add second independent verification method for Vietnamese accent/tone/pronunciation versus the exact WAV; Whisper-only ASR does not establish correctness.
3. Bind the existing source-safe review worklist to the existing authorized repair runner (single segment, max two attempts, SHA evidence and neighbor checks); no new worker or scheduler.
4. Complete CI/checks on the exact PR head, relevant Controller stop/start/resume/reboot regression and Owner listening of full-chapter samples. Keep SOT task precedence and rollback rules.
5. Only after source integrity and listening gates can any chapter be considered `FINAL`. This opt-in module is still OFF in the running production system.

**Rollback:** do not invoke the new CLI/feature flag; existing production, checkpoints, manuscript and source WAV/MP3 remain unchanged.
