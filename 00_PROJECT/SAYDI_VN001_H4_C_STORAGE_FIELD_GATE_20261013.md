# SAYDI002-VN-001 — C: storage field qualification checklist (2026-10-13)

**Subordinate implementation/acceptance note only.** Sole authority: `00_PROJECT/SOURCE_OF_TRUTH.md` on `main`. No Owner approval to deploy or execute anything on H4 is granted by this note.

## Confirmed baseline

- SAYDI-002 remains NEXT and SAYDI002-VN-001 remains IN_PROGRESS.
- Source-only fail-closed C: scanner landed via PR #114, merge `636a0eef231497945d95715b02d55dbbdb180d15`; direct H4 scanner is intentionally BLOCKED.
- Prior H4-only read-only observation: https://github.com/magasincoffee/magasin-supervisor/actions/runs/38243025301 ; 2026-10-12 18:30 ICT C: 1.20 GiB free, D: 55.89 GiB, RAM 2.47 GiB, STOP/AUTOSTART_DISABLED PRESENT. Historical observation **is not current telemetry or authentication**.
- Desktop Commander Remote connectivity was restored and checked from ChatGPT on 2026-10-13 (device listed ONLINE and ping returned). Connectivity is **not** independent Owner approval, project authority for a local scan, STOP/worker attestation, or evidence of current C: directory sizes. No C: TEMP, protected SAYDI output or checkpoint files were scanned or moved in this verification.
- Existing `vn001_local_mcp_authority.py` verifies fresh exact-main SAYDI SOT for its existing tool, but it does **not** independently attest Owner approval for a C: scan. Never substitute a client-provided Boolean for that authority.

## Gate A — authenticated read-only intent; source/QA only

The next implementation must accept exactly one `SAYDI002-VN-001` **C: aggregate metadata read-only** request. It may not accept freeform shell, paths, root selectors outside an administrator-owned allowlist, restart, delete, move, resume, or worker commands.

Before touching protected C: paths, the future trusted local adapter must independently verify:

1. Actual H4 hostname (not just a self-hosted runner label), immutable workflow/repository identity and exact requested main commit.
2. Current GitHub `main` and canonical SAYDI SOT, checking unchanged main before/after, current authorized task ID/status and source fingerprint; deny stale or unreachable revisions.
3. Owner GitHub account identity, including login `magasincoffee` and immutable numeric user ID `191064507`, with two fresh issue reads, and a *separate* issue-specific Owner lifecycle/approval record validated from trusted local sources. An Issue or its author alone grants NO authority.
4. STOP and AUTOSTART_DISABLED remain present; Owner start/dispatch stays false. Distinguish permission to **observe** from permission to **execute**. Reject duplicate/replayed request IDs and run attempts.
5. Strict time bound and fail-closed reply, with no keys, local paths, file names, book content, full command lines, or private fingerprints in public GitHub logs.

The existing live scanner remains BLOCKED until all items are implemented and independently tested. A passing hosted synthetic test must not be described as field authorization.

## Gate B — Windows traversal safety; no path substitution

PR #114 deliberately replaced unsafe queued directory traversal with an offline nonrecursive fixture; on H4 it performs **no** scan. Do not restore unprotected `os.walk`, path-based queued `os.scandir`, or `Get-ChildItem -Recurse` over mutable TEMP entries.

A future on-host scanner must bind each opened directory to a no-follow, reparse-aware **Windows directory handle**; confirm its identity and location before enumeration and reject any junction, symlink, reparse-point, path switch or inconsistency. If these guarantees cannot be tested with real Windows semantics, permit only a separately approved **nonrecursive partial read**, clearly labelled incomplete, or remain BLOCKED. This is especially important for user-writable TEMP entries and TOCTOU races.

Limits: maximum 30,000 entries per approved scope, 25 seconds per scope, hard deadline and fail-closed on access errors; no audio/text byte reads, no deletion, and no claiming safe-to-delete based on age or size. Keep C: roots out of GitHub output. Any skipped subtree means incomplete coverage.

## Gate C — offline tests and independent review

Negative tests MUST exercise: unauthenticated or stale Owner approval; wrong GitHub author/ID; mismatched Issue/task/commit; changed live `main`; wrong host; altered or missing STOP; replayed request; junction replacement between discovery and opening; inaccessible folder; incomplete subtree; deadline/file-limit exhaustion; missing schema fields; no worker/service starts and no writes.

Positive tests must use synthetic, controlled Windows fixtures (plus Linux pure-unit tests where applicable) and produce sanitized, deterministic receipts. All relevant exact-head CI, independent Codex review, reviewed PR merge and post-merge exact-main checks must be GREEN. **Do not activate a one-shot H4 job merely because source is merged**.


## Source-only QA increment — 2026-10-13 (no H4 invocation)

Expanded the existing **synthetic-only** `test_vn001_h4_c_storage_readonly.py` tests for missing and unreadable roots, reparse-marked root refusal, directory enumeration failure, entry metadata failure, strict time-bound validation, partial-report and blocked-direct-entrypoint safety, and sanitization of private paths in error messages. These tests do **not** inspect the H4 filesystem and are not proof of an authorized live scanner.

**Gate status:** A (issue-bound Owner authority + STOP/replay) NOT IMPLEMENTED; B (Windows directory-handle/no-follow guarantee) NOT IMPLEMENTED, with live H4 entrypoint explicitly blocked; C (additional offline negative fixture tests) IN PROGRESS until exact-head CI and independent review; D (one-shot H4 read) NOT AUTHORIZED. Existing tests that demonstrate no recursive descent are not a substitute for a real Windows directory handle. Do not use a chat acknowledgment, an Online Desktop Commander status or passing CI to infer A/B/D acceptance.

## Gate D — separately approved H4 observation

Only after A/B/C are qualified, obtain a fresh, explicitly scoped Owner approval for a single read-only on-host observation. No repeats, scheduling, generalized GitHub Issue dispatch, new tunnel, API credits or production changes. Verify true H4 routing **before any local read** and archive a sanitized receipt. Distinguish C: logical allocated-space estimates, skipped directories, checkpoint SHA, worker identity and Owner lifecycle: one cannot substitute for another.

Never delete, move or rehash protected audio/checkpoints as a side effect. Preserve Chapter 2 640 WAV, approved references and original/current durable state. No VieNeu or Whisper run; no transition to V6 1.2 or VN-002 before VN-001's field gates are accepted.

**Current status: SOURCE/QA DESIGN IN_PROGRESS, FIELD SCAN BLOCKED; task remains SAYDI002-VN-001 IN_PROGRESS.**
