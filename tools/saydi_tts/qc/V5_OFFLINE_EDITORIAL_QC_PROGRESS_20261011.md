# SAYDI V5 — Offline QC development while H4 host has no power

**Evidence date:** 2026-10-11 (ICT). **Deployment:** NONE. **Authority:** `00_PROJECT/SOURCE_OF_TRUTH.md` on `main`; `SAYDI-002` remains the authoritative NEXT. All changes remain subordinate opt-in QC prototypes on Draft PR #101.

## What was implemented without accessing the Windows worker

1. Added `v5_editorial_review_triage.py`: lightweight, local-only V5 manifest comparison and classification of suspected Vietnamese diacritic drift, word substitution/insertion/omission/reordering, edited/spoken text discrepancies and clause-cut candidates. Returns **index, hashes and diagnostic category only**, no source text or narration, no model requests.
2. Added `test_v5_editorial_review_triage.py`, covering default OFF, SHA-independent source provenance claims, 60 legacy suspects as an aggregate count (not 60 confirmed faults or 60 identifiable segments), bounded and paginated review windows, no overwrite, no production writes, Vietnamese diacritic and lexical edge cases.
3. Hardened `v5_editorial_multiround.py`: a source-lineage report must be bound to the exact original manifest SHA and source SHA, contain complete contiguous word spans, matching per-segment canonical text digests and actual total word counts; forged or partial reports may **not** clear provenance REVIEW. Added regression tests for manipulated spans.
4. The existing `saydi-core-tests.yml` already discovers `test_v5_*` for pull requests touching the QC tree. No new workflow, no extra worker, no duplicate CI task. Hosted CI on the exact latest PR head remains unverified.
5. Source-text proofreading and Vietnamese pronunciation **cannot** be certified by V4↔V5 diffs or ASR-only disagreement. These files intentionally do not change source text, trigger any re-render, or certify `FINAL`.

## Independent synthetic smoke test

Within a disposable execution environment (not on DESKTOP-H4A16IL), a local copy of the new `v5_editorial_review_triage.py` logic and its synthetic tests ran **16/16 PASS** under Python. Test scenarios: missing/inserted/reordered words, Vietnamese accent changes, authentic repeated words, wrong index, old audit hash binding, privacy, CLI opt-in, immutable output and full pagination.

**Limit:** This is **not** a GitHub-hosted CI result and does not verify the exact PR's entire suite. The previously verified H4 run **40 PASS + 2 SKIP** predates the new commits; do not aggregate the two as one exact-head PASS.

## Commands to perform only after reconnecting the host

- Confirm no conflicting active owner control/worker, correct H4 device, RAM and exact chapter checkpoint hashes; do not start an audio model merely to run metadata tests.
- Use a separate scratch checkout of the *exact current PR head*. Then run:

```powershell
python -m unittest discover -s tools/saydi_tts/qc -p "test_v5_*" -v
python tools/saydi_tts/qc/v5_editorial_review_triage.py `
  --manifest "D:\SAYDI\OWNER_APPROVED_NATURAL_V5\Chuong_03\manifest.json" `
  --legacy-audit "D:\SAYDI\OWNER_APPROVED_NATURAL_V5\Chuong_03\editorial_audit.json" `
  --output "D:\SAYDI\QC_STAGING\CH03_EDITORIAL_REVIEW_TRIAGE_20261011.json" `
  --enable-experimental-triage
```

- If more than 25 candidate segments appear, use `--review-offset 25`, then `50`, etc., with **unique** staging output files. Previous V4 wording is a historical comparison, not original manuscript authority.
- Separately locate and hash-verify the real original UTF-8 chapter before `v5_source_lineage.py`; source hash mismatch is a real blocking audit condition, not a request to guess an alternate source path.
- Run a genuinely independent spelling/context verifier locally, document real exceptions, and do not assert that the existing 60 legacy paraphrase suspects have been resolved without original-source evidence.
- Remain `REVIEW` until independent Vietnamese pronunciation/timbre listening, bounded repair controller, STOP/START/reboot regression, exact-head CI and Owner chapter listening pass.

## Safety invariant

**No changes to** VieNeu/V5 profile, Supervisor/Control, Windows scheduled tasks, local Supabase records, chapter checkpoints, owned manuscripts, approved MP3/WAV, production startup, service state or `main`.

**Current result:** Additional safe offline QC source and unit fixtures created; production QC **NOT COMPLETE**; Chapter 2/3 acceptance still pending.
