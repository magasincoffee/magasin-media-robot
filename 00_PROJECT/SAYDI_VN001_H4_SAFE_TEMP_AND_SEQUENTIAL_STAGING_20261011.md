# SAYDI002-VN-001 — H4 read-only TEMP/checkpoint/worker audit and staged serial Control bridge

**Date:** 2026-10-11 ICT. **Authority:** main SOURCE_OF_TRUTH.md and SAYDI_002_TEMP_SOURCE_OF_TRUTH.md. Owner keeps installed 8GB RAM, uses VieNeu only, never runs TTS and Whisper simultaneously. This report documents safe partial implementation, NOT production installation.

## 1. C: temporary/cache check

- Windows C: free ~1.25 GiB, D: free ~56.20 GiB. Safety is measured afresh before any further action.
- TEMP: ~1,453.6 MiB in 22,192 files. Only 4 files older than 7 days, totaling ~0.4 MiB. Files written in last 2 days ~71.9 MiB. **No evidence for bulk deleting TEMP**, and ownership/open handles remain unverified.
- Earlier read-only size audit: pip Cache 210 MiB, Hugging Face model cache 608 MiB, installed VieNeu virtualenv 776 MiB, C:\SAYDI\output 2,132 MiB, QC virtualenv 295 MiB. Do NOT delete these: even apparent cache may contain protected models, and output files have private book and checkpoint provenance.
- Preferred future mitigation is ONLY per-SAYDI new child process TEMP/TMP redirected to a guarded dedicated folder on D:, with staged tests, backups/rollback and exact Owner authorization. No global OS TEMP changes, no automatic user file cleanup.
- The proposed conservative min C: 2 GiB is not met, so all new heavy job dispatch should **HOLD**; it is a staged project safety threshold rather than an OS minimum.

## 2. Worker and protected checkpoint observation

| Chapter | Physical WAV count | Job status | Status file SHA256 |
|---|---:|---|---|
| 2 | 640 | 640 render/640 basic QC, REVIEW_READY, not FINAL | 9D6AC758F85C62D0FA9CA6362D9EC86D96582C1E2D30CC9A3BCA13F971B63CEE |
| 4 | 440 | 440 render/440 basic QC, REVIEW_READY, not FINAL | 127B0BCBF333C9E3561F6870892101D247B47C40B1C6E83B998C16A985A16905 |
| 5 | 346 | 346 render/346 basic QC, REVIEW_READY, not FINAL | 71BFD032B9B45FB19B4ABB9207FA0148C2311FBDB78917375D234CC3614897B7 |

WAV first/last per chapter SHA and file size checked read-only, retained in local field output. Not a full hash inventory of all 1426 WAV, so exact checkpoint ownership and approved narrator-reference provenance still need evidence. No deletion or rerender.

Current Control job observed: chapter=5, action=recheck, state=RUNNING. The processes saydi_review_qc.py and qc_local_segments.py belong to the same old Chapter 5 QC parent/child tree. Wrapper child PIDs must not be mistaken for separate concurrent full TTS+ASR model loads. No process was forcibly terminated. Durable authenticated Control Owner START/STOP generation still unverified.

## 3. Staged integration of the EXISTING Control coordinator

Installed source: C:\SAYDI\control\control_commands.py, original SHA256 **21A23231AA363B713A0AF19B1EAD6A1F04F773FDFFA5241CC223CA5D8571F3EB**.

- vn_8gb_controller_bridge.py: pure fail-closed bridge for existing Control job actions, resource gate, verified Owner generation and checkpoint. Legacy resume is composite VieNeu + Whisper, blocked until internal unload barrier field-qualified; legacy improve remains unqualified. This bridge does not authenticate Owner or dispatch.
- vn_8gb_stage_controller_patch.py: exact-SHA-pinned copy-only generator; writes only a new file on D:\SAYDI\QC_STAGING, inserts a pre-dispatch guard ahead of the controller's subprocess launch, refuses duplicate patch and never modifies C: controller.
- vn_8gb_sequential_dryrun.py: simulated TTS_CHECK -> SYNTHETIC_TTS_DONE -> UNLOAD_BARRIER -> ASR_CHECK -> SYNTHETIC_ASR_DONE -> REVIEW_ONLY. No real VieNeu/Whisper was loaded, no audio/checkpoint modified.
- test_vn_8gb_controller_bridge.py: 21 no-dispatch and negative safety tests. H4 Python unittest **21/21 PASS**; sequential simulated trial **PASS**; staged copy Python compile **PASS**.
- H4 staged copy path D:\SAYDI\QC_STAGING\VN001_CTL_INTEGRATION_20261011_B\control_commands.py; staged SHA256 24947FA39B594690B4C7DB61CEF0F62705880DC7EBC5C537799F2351D694E131. Installed original SHA before and after **exactly unchanged**.
- **No new production worker**, service reload, scheduled task adjustment, actual Owner START/STOP action, Supabase modification or audio output performed by this PR.

## 4. Remaining mandatory gates

1. Identify C: ownership and a reversible per-SAYDI disk remedy that actually restores free capacity. Do not delete 22k temp files blindly.
2. Prove Control Center authenticated Owner START/STOP generation, mutex and durable STOP; preserve prior Control Guardian and post-cutover OFF-after-reboot directive.
3. Full approved source/voice/checkpoint SHA inventory and active worker ownership, including original 640 protected Chapter 2 chunks. Re-check immediately before any model start.
4. Internally gate the existing V5 combined VieNeu-to-Whisper transition; preflight only at top-level cannot prove non-overlap during combined job.
5. Exact-head hosted Windows CI GREEN and H4 safe dry-run. Only then isolated Owner-authorized bounded real local VieNeu trial, with C:/RAM sufficient and Whisper started only after VieNeu fully unloaded. Existing protected WAV cannot be regenerated for this test.
6. Rollback-backed Owner cutover approval before touching actual controller, scheduled tasks or production dispatch.

**Status: VN-001 IN_PROGRESS / genuine C: capacity, Control Owner witness and model-stage barrier blockers.** This is not an autonomous render/QC success, not FINAL and not SAYDI-002 DONE.
