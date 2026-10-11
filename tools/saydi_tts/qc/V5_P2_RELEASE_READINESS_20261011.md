# SAYDI P2 — Release and Control Center acceptance preparation (2026-10-11)

**Scope:** Preparing the *release/field acceptance phase* ("P2") for the ongoing SAYDI narration/QC work. **P2 is NOT a new authoritative SOT task**, does not close V6-P0/P1, and may not bypass \`SAYDI-002\` (sole NEXT on \`main\`). Authority: \`00_PROJECT/SOURCE_OF_TRUTH.md\` plus \`00_PROJECT/SAYDI_V6_NARRATION_QUALITY_EXECUTION_PLAN.md\`.

**Current disposition: PREPARED_OFFLINE / NOT FIELD_TESTED / NOT RELEASE_ELIGIBLE.**
Owner-confirmed: \`DESKTOP-H4A16IL\` lost electrical power when this preparation began. Do not attempt host services, scheduled task changes or unattended restarts from GitHub. PR #101 remains **Draft** and separate from \`main\`.

## A. Code deliverable and offline proof

- \`tools/saydi_tts/qc/v5_p2_release_evidence.py\`: versioned, **opt-in read-only evidence inventory**. Validates exact PR-head SHA and \`main\` SOT SHA, enumerates required gates, refuses stale/duplicate/malformed receipt metadata, fails closed on missing evidence, and prevents production/Owner actions.
- \`tools/saydi_tts/qc/test_v5_p2_release_evidence.py\`: 19 synthetic regression tests, including the crucial case in which **all 11 receipts CLAIM PASS** but the result remains \`RECEIPTS_SUBMITTED_UNVERIFIED\`; SHA strings or claimed PASS statuses are NOT authentic GitHub, host, or Owner identities.
- The already-existing \`.github/workflows/saydi-core-tests.yml\` runs \`test_v5_*\` on QC-related PR changes. Do not introduce another costly overlapping workflow solely for P2; confirm actual run status on **the exact eventual PR head**.

**Actual off-host execution, separate Python standard-library test environment:**
\`\`\`text
python -m unittest discover -s /mnt/data/saydi_offline -p "test_v5_*" -q
Ran 85 tests in 10.723s
OK
\`\`\`
This is 66 previously implemented synthetic P0/P1 module tests + 19 new P2 cases; it is NOT the entire historical repo regression, not hosted Actions, not field audio listening. Git content blob hashes for new P2 source and tests equal local tested bytes:
\`\`\`text
v5_p2_release_evidence.py       4041d062aeb2b060a36074e6954c0949aa9cc9bb
test_v5_p2_release_evidence.py  9f6d09b062dc454f0dc2531f0b5e53194fde794e
\`\`\`

## B. P2 evidence gates (must be verified independently)

| ID | Required evidence | Trusted verification location | What can be established now? |
|---|---|---|---|
| 1 \`exact_head_ci\` | All affected checks GREEN for the *same PR head*; no stale-base/main inference | GitHub Actions/checks | **NOT VERIFIED** |
| 2 \`h4_targeted_regression\` | Python QC regression and Windows-specific runner/PowerShell syntax/Control smoke | H4 scratch checkout | **NOT RUN** |
| 3 \`source_fidelity\` | SHA-bound original chapter/source spans, no unresolved material lexical or semantic loss | H4, real book | **NOT VERIFIED** |
| 4 \`independent_vietnamese_audio\` | Tone/accent, narrator identity, joins/prosody and independent audio corroboration | H4, real WAV/audio | **NOT VERIFIED** |
| 5 \`worker_checkpoint_and_ram\` | Exact checkpoints, active PID/mutex, RAM, queue/ref SHA; no duplicate or heavy-model overlap | H4 read-only inventory | **NOT VERIFIED** |
| 6 \`off_after_reboot\` | Following an *authorized* Control cutover, SAYDI OFF after reboot until Owner START | H4 + real reboot witness | **NOT RUN** |
| 7 \`owner_stop_start_durable\` | Owner identity, Origin/CSRF, STOP latch persists through reboot; START only safe exact named job | H4 Control Center | **NOT RUN** |
| 8 \`no_duplicate_repair_resume\` | Interrupt/restart at durable checkpoint does not rerender or double-QC accepted chunks | H4 under controlled rehearsal | **NOT RUN** |
| 9 \`rollback_rehearsal\` | Hash-pinned backup, restore legacy task definitions, independent Supervisor/SAPO unaffected | H4 after authorized stage | **NOT RUN** |
| 10 \`owner_full_chapter_listening\` | Real chapter audio plus 3–5 minute representative clips, documented Owner verdict | Owner | **PENDING** |
| 11 \`parent_sot_authorization\` | Existing \`SAYDI-002\` closure/parent gates, exact-main validation, accepted controlled release scope | GitHub \`main\` SOT | **NOT CLOSED** |

Historic proof for an approved **5-minute Ch3 B + WAV146 R2 sample** is sample-scoped; it does not satisfy the full chapter listening gate. The Chapter 2 V5 paused state and 640 protected checkpoints must not be reset or double-QC'd. A historic free-RAM safety threshold for safe Ch2 QC resume is **at least 2.3 GiB**: remeasure on H4, do not blindly start workers.

## C. Exact resume sequence after electrical power returns

**Phase 1 — read-only discovery; no START/STOP:**
1. Confirm this is the authorized \`DESKTOP-H4A16IL\`. Check the exact current \`main\` SOT and PR head; if HEAD has moved, all previously attached CI/manifest witness hashes must be re-bound/retested.
2. Preserve original Windows Task Scheduler actions, triggers, enabled state, installed script hashes, worker identity/mutex and actual existing checkpoint manifests before doing any configuration write. Collect process tree, disk/RAM budget and recovery policy.
3. Create only a new, isolated scratch checkout and staging output directory. Do not modify the production V5 checkout or active audio paths.
4. Execute impacted Python tests and existing PowerShell syntax/Control contract tests. Diagnose all FAIL/skip and check hosted Actions on exact SHA. A missing check is **UNKNOWN**, never GREEN.
5. Compare actual Ch3 source UTF-8 and original V5 manifest with the P0 source-lineage gate. Review 60 historical paraphrase *suspects* against original, with independent spell/semantic decisions. Do not treat old V4 text as source authority.

**Phase 2 — explicit authorization to test worker/cutover:**
6. Verify actual Owner START/STOP authentication, per-robot STOP generation latch, CSRF/Origin and idempotency. Deny if Owner approval, RAM, mutex, checkpoint, or exact named job identity is missing.
7. With approved isolated session only, test one targeted repair (maximum 2 attempts) through the existing authorized V5 robot, then QC actual WAV/candidate/neighbor hashes, independent voice and joins, preserve unrelated segments. Do not replace approved audio merely because an ASR score improved.
8. Stage a reversible backup of task definitions, active scripts, queue + checkpoint metadata and Control config. **Cutover must remain OFF after reboot** per 2026-10-09 Owner SOT directive. Reboot and disable conflicting legacy auto-triggers **only after** verified project gates and a separate approved stage/apply. Never simulate approval.
9. Verify Owner STOP persists, watchdog/scheduler cannot revive SAYDI, Owner START resumes the correct queue under resource safeguards, and Supervisor/SAPO remain independent. Confirm accurate \`PAUSED_RESOURCE\`, \`QC_RUNNING\`, \`WAIT_OWNER\`, etc., from actual heartbeat rather than UI guesses.
10. Exercise rollback rehearsal; verify integrity, source/reference/checkpoint/audio hashes and service/task restoration. Keep the pre-cutover state recoverable.

**Phase 3 — release decision:**
11. Produce a sanitized exception/timecode bundle in the *existing* Control Center; hear full Ch3 and representative samples with Owner; require explicit authoritative acceptance. Any unresolved pronunciation, narrator identity, CI, reboot or original-text issue leaves \`REVIEW\`.
12. Only the SOT-authorized release workflow, with exact-main tests and qualified approvals, can merge or deploy. No tool added in this PR can mark FINAL.

## D. Running the offline evidence inventory (no actual acceptance)

Use unique JSON staging paths. The input is a *metadata inventory*, **not** an authenticated receipt. Never include book text, credentials or audio bytes. Obtain SHA values from actual immutable sources; no placeholder hash counts as verified. Skeleton input:
\`\`\`json
{
  "schema": "saydi-v5-p2-release-evidence-inventory-v1",
  "pr_head_sha": "<actual 40-hex sha>",
  "sot_main_sha": "<actual 40-hex sha>",
  "chapter": 3,
  "checkpoint_sha256": null,
  "reference_sha256": null,
  "receipts": []
}
\`\`\`
Run after substituting actual SHAs:
\`\`\`powershell
python tools/saydi_tts/qc/v5_p2_release_evidence.py --input "<NEW_STAGING_INPUT.json>" --expected-head "<VERIFIED_PR_HEAD_SHA>" --expected-sot-main "<VERIFIED_MAIN_SOT_COMMIT_SHA>" --output "<NEW_STAGING_P2_RESULT.json>" --enable-p2-inventory
\`\`\`
A report with 11 self-declared PASS labels will still say \`RECEIPTS_SUBMITTED_UNVERIFIED\` and have \`chapter_final=false\`, \`worker_start_allowed=false\`, \`production_write_allowed=false\`. This is intentional. Run fields cannot be cryptographically verified by the offline checker; use live host, GitHub Actions, and genuine Owner session witnesses.

## E. Release decision and rollback

**GO criteria** exist only after all P0/P1 quality exceptions, exact-head CI and SOT parent gates are satisfied; the Control Center cutover is staged with signed/verified Owner confirmation, hash-pinned backup, H4 stop/start/reboot/dedup/RAM regression and rollback witness; and full-chapter listening is accepted.

**Current decision: NO-GO / DRAFT / REVIEW.**
Rollback now is simply **do not invoke the opt-in P2 script** and leave production untouched. Nothing in this preparation schedules a worker, disables legacy Windows tasks, changes \`main\`, or grants real start/stop authority.
