# SAYDI — Preparation after P2: authoritative SAYDI-009 → 010 → 011

**Recorded:** 2026-10-11 (Asia/Ho_Chi_Minh)  
**Status:** PREPARED ONLY / NO HOST OR PRODUCTION EXECUTION  
**Authority:** `00_PROJECT/SOURCE_OF_TRUTH.md` on `main`; current sole NEXT remains **SAYDI-002**. This is a subordinate planning/evidence attachment on Draft PR #101, not a new SOT task queue.

## Is there a P3/P4?

**No.** `00_PROJECT/SAYDI_V6_NARRATION_QUALITY_EXECUTION_PLAN.md` explicitly defines V6-P0-01..06 and V6-P1-07..08. The earlier P2 release inventory is an **unofficial preparation label**, not an authoritative V6-P2 task. No V6-P3/P4 is authorized. The rest of the official product roadmap is `SAYDI-003..011`; prepare but do not execute out of order or relabel unfinished tasks DONE.

## Next preparations (not permission to execute)

| Official SOT task | Input prerequisites | Evidence needed before DONE |
|---|---|---|
| **SAYDI-009 — M4B/chapter-MP3 export + metadata** | Completed ingest, source/normalized/spoken lineage, chapter sequencing, current narration/voice fingerprint, all segment WAV and mastering QC, full chapter listening acceptance | Chapter-count/segment-count coverage, unique chapter order, no unresolved substantive QA, exact chapter master SHA, FFprobe decode/duration/bitrate, title/author/chapter metadata and seek markers, complete M4B chapter map, artifact hash and persisted release QC receipt; no overwrite of approved audio |
| **SAYDI-010 — Windows desktop control center** | Working SAYDI backend and explicit SOT-authorized safe Control migration path | Single MAGASIN Control Center at `http://127.0.0.1:8781`, SAYDI backend remains separately recoverable, accurate read-only health/progress/Owner listening, authenticated START and durable STOP generation latch, Origin/CSRF safeguards, exact job ownership, RAM and mutex; **OFF after reboot** until Owner START; no legacy scheduled restart after STOP; Supervisor/SAPO unaffected |
| **SAYDI-011 — Clean-machine installer + end-to-end acceptance** | Qualified 009/010, approved migration and rollback | Supported clean Windows installation (no hidden H4 assumptions); locally configured legal voice, secure credentials, model/ffmpeg/dependency checks, application data under local directory, durable restart/backup/uninstall behavior, full book import → narration → isolated QC/repair → mastered/exported chapters → M4B with real Owner-approved audio; sanitized recovery diagnostics and reversible rollback |

### 009: export contract before making an exporter

- The canonical original source, final chapter WAV/MP3, narration reference and book metadata remain **on H4**. Do not push book text, audio, passwords or local profile to GitHub.
- The export inventory must record at most metadata IDs, lengths, hashes, ordering, pending material review count and approved book fields; never infer listening acceptance from a hash.
- Verify with an actual local media decoder/container validator (FFprobe where available), **not** from the presence of a `.mp3`/`.m4b` suffix or a self-declared PASS report.
- If the chapter master is a REVIEW preview (e.g., previous V5 examples), exclude from release. Do not reuse Owner approval of one five-minute Ch3 sample as approval of full Ch3.
- Until task 009 gates are authoritative, a draft export packaging plan must always return `export_allowed=false`.

### 010: one Control Center without rewriting worker ownership

- A future dashboard may read current SAYDI engine status but must not become the owner of books, private audio, queues, checkpoints, SOT or narrator credentials.
- **STOP policy precedence:** the newer 2026-10-09 SOT directive requires post-cutover `OFF after reboot`; existing legacy Windows task triggers remain intact until a controlled migration is separately approved and verified.
- Before activating any Start actuator, verify actual Owner session identity, explicit target job, CSRF/Origin, durable generation latch, free RAM (Chapter 2 V5 QC historical floor **≥2.3 GiB**, field-recheck), no competing VieNeu/Whisper, active mutex and checkpoint status.
- Do not impersonate Owner approvals with a bare SHA token, self-reported receipt or unauthenticated local UI request.
- STOP, restart and rollback must not inadvertently stop Supervisor or SAPO.

### 011: clean installation and safe reversal

- Prepare a hash-pinned inventory of all installed scripts, Service/Task Scheduler definitions, local queue/manifest/checkpoint versions, permitted model packages and dependency versions **before any migration write**.
- Never ship personal browser profiles, Google/Meta/Saydi credentials, private manuscripts or WAVs inside an installer or CI artifact.
- Verify clean-machine install and first-run without changing an already working production host; test upgrade and uninstall/rollback while preserving media/library data.
- Declare production release only after exact-main/SOT, hosted CI, native Windows H4 smoke (or qualified clean Windows host), source fidelity, independent audio QC, Control START/STOP/reboot and Owner full-chapter listening are accepted.

## Offline preparation tool

- `tools/saydi_tts/qc/v5_future_delivery_inventory.py`: **opt-in read-only** future 009/010/011 metadata checker. It enforces official task order, exact PR-head and main SOT SHA binding, uniqueness and ordering of chapters, chapter segment counts, master/QC fingerprints, duration and unresolved review count. It always emits `PREPARATION_ONLY_NO_SOT_ADVANCE` and **cannot** export audio, START robots, deploy installers, or mark FINAL.
- `tools/saydi_tts/qc/test_v5_future_delivery_inventory.py`: 18 synthetic offline tests (stale refs, unwanted "P3", wrong task order, extra private manuscript field, incorrect hashes/chapters, false media acceptance, OFF-by-default CLI, output path protections).
- **Actual isolated test:** `Ran 18 tests ... OK` with Git blob hashes matching the two files committed to Draft PR #101:
  - Source blob: `2aceca397ffa601a8f35b09a255ba77bb3cc952e`
  - Test blob: `9f4afd53222880d4c5161ace20fcc03104dfc058`
- This **does not** imply 18/18 GitHub Actions PASS, a full repo regression or real book QA. P2 prior focused 85/85 was a separate offline run; do not report a combined CI outcome.

**Suggested offline invocation once real metadata exists** (replace placeholders with *actual* commit IDs and unique staging paths; no private audio or secrets in JSON):

```powershell
python tools/saydi_tts/qc/v5_future_delivery_inventory.py `
  --input "<NEW_LOCAL_STAGING_TASK_PLAN.json>" `
  --expected-head "<EXACT_PR_HEAD_40_HEX>" `
  --expected-sot "<ACTUAL_MAIN_SOT_COMMIT_SHA_40_HEX>" `
  --output "<NEW_LOCAL_STAGING_FUTURE_INVENTORY.json>" `
  --enable-next-task-inventory
```

Required schema (illustrative `null` means **NOT VERIFIED**, not zero work):
```json
{
  "schema": "saydi-future-009-011-inventory-v1",
  "pr_head_sha": "<EXACT_PR_HEAD_40_HEX>",
  "sot_main_sha": "<ACTUAL_MAIN_SOT_COMMIT_SHA_40_HEX>",
  "targets": ["SAYDI-009", "SAYDI-010", "SAYDI-011"],
  "chapters": [{
    "chapter": 3,
    "segment_count": 285,
    "master_mp3_sha256": null,
    "qc_report_sha256": null,
    "duration_ms": null,
    "material_review_count": 0
  }]
}
```
**Caution:** `material_review_count: 0` is only a format example, NOT a claim that Ch3 has no problems. Do not use placeholder or guessed values for real cases.

## Current stage and next required evidence

- 009: **PREPARED/NOT STARTED**; M4B and chapter export cannot proceed until approved source/audio.
- 010: **REQUIREMENTS PREPARED/NO AUTHORIZED CUTOVER**; H4 read-only discovery, controlled STOP/START/reboot and rollback not verified.
- 011: **ACCEPTANCE CHECKLIST PREPARED/INSTALLER NOT ACCEPTED**; no clean Windows qualification.
- PR #101 must stay **Draft** until appropriate SOT/CI/field approval. `SAYDI-002` remains NEXT. No new P3 or task queue, no changes to `main`, watchdog, local models, production WAV or the 640 protected Chapter 2 V5 checkpoints.

**Next real operational milestone when electricity returns:** read-only H4 inventory → targeted offline H4 QA + exact-head CI → P0/P1 issues → P2 field acceptance → continue the existing SOT tasks in order before 009/010/011.
