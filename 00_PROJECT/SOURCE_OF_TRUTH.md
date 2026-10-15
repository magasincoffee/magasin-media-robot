# SAYDI Audiobook — Source of Truth

Last updated: 2026-10-15

## Authority

This file is the single authoritative project state for the SAYDI Audiobook track in this repository.

Precedence:

1. `00_PROJECT/SOURCE_OF_TRUTH.md`
2. architecture and decision records referenced by this file
3. current implementation and tests on `main`
4. historical status/changelog/discovery notes

If another document conflicts with this file, this file wins until it is deliberately updated.

## OWNER DIRECTIVE — FULL SAYDI V6 PROJECT EXECUTION GRANT (2026-10-15)

**Explicit Owner decision, highest priority within this SAYDI SOT:** "Tập trung vào V6. Tôi cấp toàn quyền thực hiện dự án SAYDI V6 đến khi hoàn thành." This is **ONE project-wide execution approval**, not one approval per `TASK_ID`. The grant is effective for the authorized SAYDI V6 project work until objective project acceptance `SAYDI V6 DONE` is substantiated in this canonical SOT, or until Owner explicitly revokes/restricts it. It overrides older passages that require **additional human Owner approval solely because** a new SAYDI V6 phase, child task, internal edit, PR, merge, QA run, technical retry, or already-scoped read page begins. **No repeated Owner questions for those actions.** It does not imply the robot can cross safety/permission boundaries or override a live STOP.

**Project scope covered by this one decision:** existing `magasincoffee/magasin-media-robot` SAYDI V6 plan and subordinate `SAYDI-002..011`, `SAYDI002-VN-001..005`, `SAYDI-ND`, `SAYDI-QC`, `V6-P0/P1` acceptance work, in their authoritative SOT order; implementation, refactoring, tests, security and resource hardening, documented migrations within the project, reviewed PR creation, corrections and merge when gates are GREEN, exact-main verification, staging/rollback preparation, synthetic and authorized read-only H4 inspection, checkpoint provenance verification through a qualified read gate, resource preflight, safe QC, bounded repair of non-approved candidates and generation of new V6 candidates under verified runtime permission. The robot should select the next executable SAYDI V6 task by re-reading this SOT and **continue autonomously through all dependent tasks** until the project's actual acceptance criteria are met; it must not pause after every PR or return merely to request a new "tiếp tục".

**Autonomous cycle:** `DISCOVER → IMPLEMENT → CHECK → FIX (bounded) → INDEPENDENT REVIEW → MERGE (if GREEN) → EXACT-MAIN VERIFY → ACCEPT/RECORD → NEXT`. Batch related defects, reuse passing evidence when the exact head has not changed, avoid redundant per-CI reports, maintain durable task/child-operation ledger and crash-safe resumability. Publish concise milestone or meaningful BLOCKED reports, rather than asking Owner to authorize routine engineering steps. Successful CI, merged PRs, simulated gates, and online H4 status are **not** proof of V6 deployment or quality acceptance.

**Authentication is automatic after task admission, not repeated human consent:** implement one independently authenticated project-scope Owner grant bound to the canonical SAYDI project, allowed operations, exact roots, time/generation and revocation state. Subsequent approved task/read steps use the persistent grant and their own finite, ordered idempotency/replay records. Independently verify the grant, exact-main authority, unchanged scope, trusted transport, root identity, and Owner STOP generation immediately before and after **every** protected-root read; suppress entire receipts on failure. This SOT paragraph records Owner's policy decision but is **not by itself cryptographic evidence of a verified H4 runtime grant**, nor a substitute for implementing/testing the trusted host, Windows no-follow scan, journal or qualified local MCP entrypoint.

**Safety and Owner STOP always take precedence:** never forge authentication or Secrets, reset checkpoints, delete/overwrite accepted V5 source/reference/voice/WAV/MP3, replay a consumed command, silently change the narrator, bypass model-memory/Whisper unload validation, disable safeguards, spend money or publish/release externally outside the actually qualified scope. The observed `owner_stop=true` / `STOPPED` is **not** automatically revoked by this grant. With STOP active, continue all safe source/QA/offline implementation and diagnostics but **do not START/resume a stopped production worker or perform STOP-prohibited field operations**. Ask Owner **only** when an actually necessary runtime START/STOP decision, secret/credential, third-party authorization, unapproved destructive action, cost/externally visible release, change beyond V6 scope, or failed safety gate cannot be resolved within existing authority. Make that request once with the precise blocker and smallest action; do not repeatedly request separate approval for already-granted V6 tasks.

**Task status and completion:** at issuance, `SAYDI-002 NEXT` / `SAYDI002-VN-001 IN_PROGRESS`; all subsequent tasks remain gated by their true acceptance evidence. The project-wide grant does **not** falsely mark VN-001 or V6 DONE and does not itself certify a H4 runtime. The robot may advance tasks and publish exact-main SOT state as each verified gate becomes GREEN. Project-wide execution authority ends at verified V6 acceptance or earlier explicit Owner revocation. Earlier "one task, one approval" wording is **superseded on approval frequency by this project-wide V6 decision**; its atomic anti-replay, scope and STOP protections remain binding.

## OWNER LOCK — ONE SAYDI SOURCE OF TRUTH / V6 QUALITY UPGRADE (2026-10-11)

**ONE AND ONLY CURRENT TASK AUTHORITY: `00_PROJECT/SOURCE_OF_TRUTH.md` on `main`.** Three former `*TEMP_SOURCE_OF_TRUTH.md` documents and duplicate status/plan trackers have been retired from the current branch. Git history preserves their old evidence, NOT their executable authority. A future ChatGPT/robot must read this SOT from the beginning and derive exactly one active task ID here. README, old links, PRs, branches, code comments, older chat, historical QC/ND "NEXT" statements, plans, matrices and test fixtures cannot authorize a different task or bypass Owner gates. Historical links to deleted SOTs are invalid for execution: open this canonical SOT directly (no automatic GitHub redirect is implied); never fetch Git history to reactivate a retired task.

### 2026-10-15 OWNER DECISION — ONE TASK, ONE OWNER APPROVAL, AUTONOMOUS COMPLETION

**Owner-approved operating principle:** "Tôi giao nhiệm vụ một lần, robot tự hoàn thành trong phạm vi đã được cấp quyền." Owner supplies a clearly bounded task objective and approves its scope **once at task admission**; thereafter the robot may execute all permitted *internal* steps, rechecks, bounded error repairs, focused CI/Codex reviews, progress recording and acceptance checks without requesting another manual Owner approval for every small step, hash page, technical retry or QA result. Owner manages **goal, scope, exceptions and outcome** instead of micromanaging individual tool calls.

**Delegation contract (required fields):** `task_id` from this SOT; target host/project; allowed operations and read/write class; exact data/root scope; immutable baseline/protected assets; resource/budget/time limits; start/end or expiry condition; authenticated Owner identity, approval channel and generation; current durable STOP policy; retry limits; acceptance evidence; escalation conditions; and revocation/rollback response. Missing or ambiguous terms fail closed; a general instruction "continue" cannot silently enlarge an approved scope.

**Single approval, multiple bounded suboperations:** one independently authenticated, scope-bound Owner task grant may cover a sequence of finite inventory pages or other already-approved read-only steps. The **Owner is not asked again for each page**. The trusted host must record one durable task-grant admission with anti-replay protection, then separately log each permitted child operation with a unique idempotency key/nonce, ordered progress and immutable scope binding. Verify the SAME live approved task grant, exact-main/task state, active scope, STOP generation/latch, trusted transport, safe Windows root identity, journal ownership and per-step replay protection **immediately before and after every protected read**, before releasing any receipt. Fail closed and suppress partial receipts on any mismatch. One task grant is **not** an unlimited reusable execution token; it cannot be replayed for another task, widened by a caller, reactivated after revocation, or used to skip child-operation validation.

**Owner interruption ONLY for genuine boundaries:** new or expanded scope, any previously unapproved production write/destructive action, checkpoint/audio replacement or rerecord, model START/resume outside an expressly authenticated existing runtime permission, release/publication/final preview, fee/budget change, unsafe resource state, changed Owner STOP or unresolved security/safety failure. The robot must mark `BLOCKED` with a specific reason and smallest necessary Owner action, instead of repeatedly asking approval for unchanged technical steps. STOP always overrides grants; it is never implicit START. If a worker cannot safely proceed, do not silently restart it.

**Implementation/acceptance truth:** this is an authoritative **product and delegation requirement**, NOT retroactive evidence that the current one-shot-per-read code already implements a durable per-task grant. The existing `vn001_one_shot_read_gate.py` remains SOURCE/QA-only; do not relabel it as production task-grant admission, remove replay/STOP checks, invoke unqualified H4 MCP, read protected V5 files, start VieNeu/Whisper or change production before independently reviewed on-host implementation, tests and Owner-scoped field permission. Older SOT language requiring one-shot Owner authorization remains a **security requirement at task-grant admission**, but must **not** be interpreted as repeated *manual* Owner approvals for every already-approved suboperation after the new host integration is qualified. Exact-head/independent review, exact-main evidence, protected V5 checkpoint provenance and actual sequential unload qualification remain prerequisites for `SAYDI002-VN-001 DONE`.

**Current task authority unchanged:** `SAYDI-002 NEXT`; `SAYDI002-VN-001 IN_PROGRESS`. Focus the next implementation on an authenticated per-task grant with bounded ordered child reads, durable anti-replay and STOP checks, plus the already-required H4 field acceptance. Do not invent a new task namespace or bypass the current production STOP.

**Owner approved:** V5 VieNeu audiobook robot is the protected, already functioning baseline; **V6 is the latest quality/autonomy upgrade target, not a deployed release**. Preserve existing voice, references, model, book text, original/derived manifests, WAV/MP3, checkpoints, durable queues, Supabase state, active workers, credentials and QC evidence. Do not replace VieNeu, invoke paid SaydiVoice, start from scratch or rerecord accepted sections without separately approved and hash-proven invalidation. Quality / correct pronunciation / natural emotion and pauses / auto-QC and safe isolated repair take precedence over render speed and 24/7 throughput.

**Authoritative selected task remains `SAYDI-002 = NEXT`; currently actionable subordinate task `SAYDI002-VN-001 = IN_PROGRESS`.** SAYDI-001 is DONE, SAYDI-003..011 not yet formally accepted. The 24 numbered V6 steps below are checkboxes, **not new alternative TASK_ID/NEXT_TASK_ID namespaces**; mapped to existing SAYDI, SAYDI002-VN, SAYDI-ND, SAYDI-QC and V6-P0/P1 IDs. A SOT update alone NEVER advances a gate. Work on later quality modules must not be dispatched independently while SAYDI-002 is still NEXT unless the current task explicitly permits an offline preparatory dependency.

### V5 protections and V6 quality gates

- Active TTS = local VieNeu v3 Turbo / ONNX, H4 only (`DESKTOP-H4A16IL`), Owner-approved `SAYDI Nam Mien Nam`. Keep the approved approximately 237-second narration reference/fingerprint; V5 pacing/intonation/emphasis accepted in a Chapter 4 sample are not permission to change voice or slow down audio. **NO `atempo`, pitch shifting, time stretch, invented discrete VieNeu emotion controls or forced waveform tempo.** Convey feeling through sentence/clause editorial preparation, punctuation, natural breaths and safe join intervals within actual provider capability. A materially changed fingerprint requires separate new Owner sample approval.
- H4 retains 8 GB RAM (7.88 GiB OS-visible). VieNeu and Whisper are **strictly sequential**: only one heavy worker, resource preflight, model/process fully unloaded before other is started, mutex and checkpoint owner proven, durable Owner STOP obeyed. 2026-10-11 C: free ~1.25 GiB, D: ~56.2 GiB; 2.1 GiB stable RAM TTS / 2.5 GiB ASR over five samples, C: 2 GiB and D: 10 GiB are **proposed** safety floors pending validation. Cannot launch real new work while C: below safe floor / Owner START generation unverified / composite V5 inner unload barrier unqualified. No blind TEMP bulk deletion: ~22,192 C: TEMP files (~1.45 GiB) include only ~0.4 MiB older than 7 days. Reversible per-SAYDI storage remedy only after inventory and proper authorization; no global OS TEMP redirects.
- Preserve Chapter 2 V5 640/640 WAV and QC and approved MP3; Chapter 4 440/440; Chapter 5 346/346. All recorded REVIEW_READY, **not FINAL**. Chapter 1 V5 347/347 chunks and 35m11s preview; R2 35 candidate tries / 12 selected, 115 basic ASR REVIEW and 279 strict ASR REVIEW are warning counts, **not directly 115 audible pronunciation mistakes or Owner FINAL**. Original source/voice/first/last and full checkpoint SHA ownership need field proof before resuming or altering anything. Never reset/revoice/double-QC protected 640 chunks, corrupt approved audio, kill existing active Chapter 5 ASR process, or overwrite accepted WAVs.
- Heading-only G music design approved: original soft 2-second instrumental before title, ~160ms separation, low-level ducked sound during structural heading ONLY, absolutely none under body. Design preset approval is not entire chapter audio acceptance.
- Preserve immutable `original_text`; derive separate `normalized_text`, `spoken_text`, semantic units, source spans and SHA. Reconstruct punctuation/phrases/dialogue but never silently omit, rewrite or change book meaning. Uncertain editorial decisions -> REVIEW. Do not send private manuscript, audio/reference, credentials or exact personal material to public GitHub or cloud without explicit Owner enablement.
- QC is default-on after synthesis: coverage, exact-text/word and Vietnamese tone, suspect-token + timecode, Whisper/ASR plus independent confirmation where required, emotional pacing/pause/F0/dynamics, acoustic clip/silence and joins, voice consistency. Each result bound to **actual source/TTS text/voice/WAV hash and QC version**. ASR agreement alone is not human-quality proof; an ASR mismatch alone is not proof of wrong Vietnamese tone.
- Repair only a verified, retry-safe defective chunk: maximum **two** attempts; only promote a candidate demonstrably better than baseline, with exact SHA and unchanged neighboring audio, rerun affected+neighbor QC; unresolved/ambiguous -> REVIEW (never infinite loop or false FINAL). Preserve native articulation speed.
- Control Center target: one Owner UI for SAYDI/Supervisor/SAPO after qualified cutover. Until isolated lifecycle approval, old scheduled tasks are not silently altered; the new target is **OFF after reboot until authenticated Owner START**, durable STOP must not be auto-restarted. Existing disabled START/STOP in UI is NOT evidence of a functioning actuator. Never start heavy worker or change production system during source-only documentation migration.

### Sole authorized SAYDI-002 local VieNeu queue (migrated from retired temporary SOT)

| TASK_ID | Current status | To complete / evidence |
|---|---|---|
| **SAYDI002-VN-001** | **IN_PROGRESS / active** | Read-only H4 checkpoint/source/voice/model SHA, PID/mutex and authenticated Owner STOP generation, RAM/disk/C: consumer inventory, safe reversible storage plan, exact-head+main Windows offline CI; qualify legacy V5 inner VieNeu-unload-to-Whisper barrier before any real trial. No new heavy worker/production write. |
| SAYDI002-VN-002 | PENDING after VN-001 | Verify local VieNeu adapter and versioned VoiceProvider/AI contracts, narrator fingerprint, source/spoken hashes, deterministic local fallback, unsupported controls, security/idempotency unit tests. No live synthesis. |
| SAYDI002-VN-003 | PENDING after VN-002 | Prefer read-only existing real VieNeu sample with exact-hash source/voice/WAV/MP3 and Owner approved reference; only a separately authorized safe bounded local sample if absolutely required. No duplicate 640-chunk render. |
| SAYDI002-VN-004 | PENDING after VN-003 | Connect editorial/heading G staging/first-word+join+pronunciation QC + bounded repaired clips into repeatable chapter `REVIEW` receipt, zero music under body and protected WAV unchanged. |
| SAYDI002-VN-005 | PENDING after VN-001..004 | Final safe VieNeu vertical slice/AI/Voice/fingerprint/local QC + Owner preview approvals, privacy/idempotency, H4 field proof, exact PR CI and exact-main readback; only then `SAYDI-002 DONE`, `SAYDI-003 NEXT`. |

### 2026-10-15 Owner directive — 5-step closure of SAYDI002-VN-001 (execution simplification, NOT gate relaxation)

Owner directs application of the ordered five-step engineering method: **question requirements → delete needless process → simplify → accelerate → automate last**. Existing `SAYDI-002 NEXT` / `SAYDI002-VN-001 IN_PROGRESS` authority is unchanged. This section streamlines the **work sequence**, not the protected-data or STOP controls.

1. **Question every requirement:** distinguish (a) actual V5 asset identity/SHA, authenticated Owner issue-bound one-shot STOP+replay proof, checkpoint/mutex ownership and VieNeu→Whisper unload safety — mandatory; from (b) repeated SOT-only PRs, duplicate synthetic demonstrations, generalized Supervisor activation and blanket C: cleanup before a genuinely zero-write bounded metadata check — not independently required for VN-001. A historical **proposed** 2 GiB C: safety floor is not by itself evidence that a protected *read-only* inventory must delete/move files. Heavy-model start retains independently measured safe headroom and its own gate. The Owner's 1 GiB available RAM / one CPU thread preference is not proof that VieNeu/Whisper can load safely.
2. **Delete wasted steps:** no separate new task namespace, temporary SOT, extra relay/tunnel service, replacement voice, duplicated baseline simulated-unload PR, or all-book rerender. Reuse accepted merged `main` code, existing H4 MCP and existing immutable V5 assets. Do not reactivate historical tunnel or generic Supervisor `execute_task`.
3. **Simplify to one constrained field acceptance package:** one independently authenticated, Owner-scoped **read-only** H4 operation — only after exact-`main` pin, durable one-shot consumption/replay and Owner STOP generation verified immediately **before and after each protected-root read**, trusted transport and Windows root/no-follow safety. Collect sanitized V5 source/voice/model/checkpoint/audio SHA pages, PID/mutex owners, fresh RAM/disk and C: capacity evidence. Reject a changed/replayed/missing witness and suppress the entire receipt; never equate mere GitHub Issue identity or an ordinary MCP heartbeat with authorization. Build the VieNeu-unload/Whisper barrier as a separate non-actuating validation within the same VN-001 acceptance review. A real model-loaded handoff requires its own qualified, separately approved START generation; the read-only permission must not launch models.
4. **Accelerate:** batch closely related fixes and exact-head offline security tests in **one focused PR** when real code changes are necessary, then independent Codex P1/P2 review and exact-main check. Stop rerunning full CI or reviewing unrelated files when the relevant checks already passed and no code changed. Publish exactly one clear `DONE` or `BLOCKED` receipt with missing evidence, not another general status plan. Do not invent completion percentages or dates.
5. **Automate last:** only after a single trusted H4 field receipt and actual lifecycle/resource/unload acceptance, make the validated read-only sequence reusable through the existing qualified local channel. Never auto-START the V5 worker, defeat durable STOP, consume unverified Owner permission or turn a synthetic PASS into execution authority.

**Fresh 2026-10-15 H4 resource observation (non-authorizing):** H4 online, available RAM about **1.982 GiB**, free C: about **1.969 GiB**, free D: about **56.034 GiB**; zero heavy-process matches in a bounded process-name/command-line sample. OS telemetry and name sampling are not checkpoint ownership, model-unload, runtime STOP, or Owner-identity proof. No protected SAYDI files scanned or modified. **Actionable blocker remains Owner-bound protected-read admission and independently verified live model handoff, not more offline simulated QA.** Owner consent for a read-only SHA request is distinct from any future model START.

**Existing evidence (not closure):** PR #104 / #105 merged H4 read-only collector, resource diagnostics, protected checkpoint/temp inventory, D: staged *inactive* controller bridge; H4 synthetic sequence and 21/21 tests PASS without VieNeu/Whisper model load. PR #106 hardened read-only fresh H4 telemetry; Windows checks PASS on exact main. **This is NOT live integration**; C: headroom, authenticated Owner witness, full fingerprint/checkpoint ownership and internal unload barrier remain blockers. On block, log `BLOCKER_ID, TASK_ID, STATUS, TYPE, SUMMARY, OWNER_ACTION, EVIDENCE, RESUME_WHEN` in this SOT; no infinite wait/repair loops.

### 2026-10-12 execution receipt — V6 step 1.1, protected read-only inventory

**Task:** SAYDI-002 / SAYDI002-VN-001 / checklist 1.1, still **IN_PROGRESS**. Added `tools/saydi_tts/qc/vn001_v5_readonly_inventory.py` and synthetic unit tests/Windows+Linux hosted CI. Inventory accepts explicitly verified local roots and outputs only bounded file class/count/metadata identity; optional small SHA256 batches use anonymous file IDs. It never writes local audio/book, changes a checkpoint, starts any worker or authenticates Owner. CLI is host-guarded to `DESKTOP-H4A16IL`, and output always denies START/DISPATCH. A metadata fingerprint or partial hashes alone DO NOT prove full approved WAV/reference provenance or durable STOP. Real H4 read-only source/voice/checkpoint hashing remains mandatory.

**Actual H4 access attempt 2026-10-12:** Desktop Commander listed H4 ONLINE, but a read-only `C:\SAYDI` directory request remained pending and a separate aggregated no-write PowerShell RAM/disk/process query timed out without device response. No trustworthy **fresh** file/process/disk observation was returned. Do not recycle historical 2026-10-11 checks as current evidence; no real worker, model, audio or checkpoint was touched.

**BLOCKER_ID=BLK-SAYDI-V6-11-REMOTE**
- TASK_ID=SAYDI002-VN-001; STATUS=OPEN; TYPE=ENVIRONMENT.
- SUMMARY=H4 remote filesystem/PowerShell evidence not returned; read-only 1.1 inventory cannot be marked complete.
- OWNER_ACTION=NONE unless authorized local MCP/remote connection fails on a later recheck.
- EVIDENCE=H4 device listed Online; directory request pending; process query timeout; no output or write proof.
- RESUME_WHEN=verified responding H4 read-only local or Remote MCP, fresh PID/STOP/checkpoint/voice identity and bounded SHA inventory with sanitized receipts. Never force restart a live chapter QC job just to inspect.

**Follow-up 2026-10-12 ~10:03 ICT:** The registered H4 device was explicitly **OFFLINE** (last seen ~2 hours earlier). A single ping returned `No Desktop Commander device is currently online`; no file/worker probe was attempted after this finding. The earlier pending/timeout remains historical evidence, not a successful fresh snapshot. If this persists, Owner or an authorized operator must bring the existing remote agent back online on H4; do not reboot or remotely override STOP/worker merely to fix connectivity.

**Offline step 1.1 hardening:** `vn001_v5_readonly_inventory.py` initial proof only hashed the first bounded 16 candidate files per call. Extend that same *read-only* CLI with deterministic `--hash-offset`, `--expected-metadata-sha256` per-batch consistency, fail-closed unreadable-directory detection and an explicit `hash_page_final` flag (which **never** claims global acceptance after the last page without all earlier receipts). Validate on hosted Windows/Linux synthetic CI. Example usage pattern for an Owner-verified local root: metadata first; then `--mode hash --hash-offset 0`, record its metadata fingerprint locally; repeat with each `next_hash_offset` and `--expected-metadata-sha256 <first_digest>`. Abort on `METADATA_FINGERPRINT_CHANGED`, `BATCH_LIMIT_NO_PROGRESS` or unreadable files. These paged receipts still do not attest the correct narrator, protected full checkpoint set, active worker owner, STOP or backup copy; independent H4 confirmation is mandatory before 1.1 DONE.

**Status discipline:** PR/CI code may be merged when offline tests GREEN; checklist 1.1 and VN-001 stay IN_PROGRESS until real local receipts, exact checkpoint ownership and Owner control gates are verified. Do not start SAYDI002-VN-002 or V6 quality rendering prematurely.

### 2026-10-12 Owner direction — Prefer existing H4 local MCP for SAYDI VN-001 read-only inventory

**Owner selected local MCP as the preferred future H4 task transport over repeated Remote Desktop Commander calls.** This is permission to build/test a non-actuating bridge, **NOT** proof that this chat has a connected MCP tool, that local MCP service/runner is online, or that Supervisor business dispatch has passed its own authority gates.

**Implemented source-only integration candidate:** `tools/saydi_tts/qc/vn001_local_mcp_readonly_bridge.py` exports `handle_inventory()` for an **already trusted local MCP service**; it does not create/install a new MCP server, listener, task queue or startup service. Request contract is `MAGASIN_SAYDI_VN001_MCP_READONLY_V1`, exact `task_id=SAYDI002-VN-001`, `target=saydi`, `action=inventory_v5_readonly`, locally configured root key and only `metadata` or bounded `hash` modes. All other command types (START, STOP, render, EXECUTE, project switch, shell scripts) are rejected. Request never carries a file path, executable or credential.

**Mandatory independent gates before any future H4 invocation:**
1. H4 host is exactly `DESKTOP-H4A16IL`. Only approved C:\SAYDI or D:\SAYDI canonical roots; do not permit private arbitrary host paths, junction escape or user-provided root paths. Locally configured allowlist is admin-controlled.
2. Existing local MCP transport must independently authenticate the caller. The separately trusted local SOT verifier must freshly confirm `magasincoffee/magasin-media-robot`, `00_PROJECT/SOURCE_OF_TRUTH.md` on exact live `main` commit and `SAYDI002-VN-001=IN_PROGRESS`, with production dispatch unauthorized. Neither the request body nor old chat supplies these proofs.
3. Execute only the pure file inventory already implemented: bounded, paginated SHA, fail closed if metadata drifts or files are unreadable. The response includes no manuscript, filenames or full local paths, no persistent write, no job launch. Every response has `approved_to_start=false`, `approved_to_dispatch=false`, `worker_started=false`, `task_completed=false`. A successful read is not a checkpoint ownership, STOP attestation or V6 step 1.1 DONE receipt.
4. Supervisor SOT is independent and controls its own P1 (source/QA-only), later P2 (MCP transport acceptance) and P3 (Business Executor) gates. Do **not** call its `C:\MAGASIN_MCP\dispatch_gateway.py` generic `MAGASIN_DISPATCH_V1/action=execute_task`, create a GitHub dispatch issue, replay an existing Issue, clear STOP or install this bridge into Supervisor pending independent qualification/Owner cutover approval.
5. Actual MCP wiring/H4 live root allowlist, fresh worker/voice/checkpoint identity, reliable local transport and read-only receipts remain **BLOCKED** until H4 is reachable through a qualified connected channel. The last 2026-10-12 check reported Remote Desktop Commander H4 OFFLINE; whether a different MCP local daemon runs cannot be inferred. Do not equate source CI with a local installation.

**Work status:** Task `SAYDI002-VN-001` / step **1.1 stays IN_PROGRESS**. Source tests/PR may be marked CODE_READY only after exact-head and exact-main GREEN. No V5 asset change, no production render or Supervisor activation; don't advance to 1.2 solely due to this adapter.

### 2026-10-12 H4 MCP integration — fresh pinned SOT proof (source/QA ONLY)

**OWNER APPROVED CONTINUATION** of the SAYDI `SAYDI002-VN-001` local read-only inventory route. This does not override the independent SC-013 Supervisor SOT: its P1 source-only selection, P2 MCP transport acceptance and P3 business-executor gates remain incomplete. No local MCP server was reachable in this ChatGPT session, and Remote Desktop Commander still showed H4 **OFFLINE**, last seen around 4 hours earlier as of this check. Thus no live installation, root permission test or V5 inventory result is claimed.

**Concrete increment:** `tools/saydi_tts/qc/vn001_local_mcp_authority.py` obtains two matching fresh GitHub `main` commit attestations around a SHA-pinned `SOURCE_OF_TRUTH.md` read, validates the Git blob and the active `SAYDI002-VN-001=IN_PROGRESS` row, and fails closed on stale/changed/malformed SOT. `vn001_local_mcp_readonly_bridge.py` now provides the **MCP-facing `handle_inventory`**, which invokes this verifier itself; the lower-level `_read_inventory_with_verified_sot` helper is internal/test-only. No caller-supplied proof dictionary is accepted by the public interface. Transport authentication and locally approved C:\SAYDI / D:\SAYDI bindings must come from the separately qualified existing H4 MCP host; request fields cannot carry shell commands, credentials, arbitrary paths, Owner approvals or a task override. Hosted Windows/Linux synthetic tests check correct SOT, invalid/changed SHA, modified blob, wrong host, unauthenticated request, false TASK_ID, unchanged fixture files and truthful `READ_ONLY_RECEIPT_UNATTESTED`.

**H4 pending field gate:** discover the exact already-installed MCP service entrypoint/ownership through an authenticated authorized H4 channel; inspect only (no generic Gateway Issue `execute_task`). Wire the verified handler into a reviewed **read-only inventory tool** on that service, preserving Owner STOP and host permissions. Confirm its live GitHub main read, local path allowlist, metadata snapshot, bounded hash batches, durable checkpoint+voice+worker identity and sanitizer. Require rollback-backed approval before any deployment or service restart. Never automatically infer this field acceptance from GitHub Actions. **SAYDI002-VN-001 and V6 step 1.1 remain IN_PROGRESS; do not start 1.2 or any heavy worker.**

### 2026-10-12 LATEST OWNER COST LOCK — GitHub relay, no new paid service

**SUPERSEDES the earlier 2026-10-12 Secure MCP Tunnel selection below as the default field connection method.** Owner now requires **no additional paid service fees beyond existing ChatGPT Plus** for MAGASIN messaging. Use **GitHub as a request/receipt transport**, with Owner-authenticated **GitHub mobile/web Issue creation** as the no-extra-cost submission fallback. An existing ChatGPT GitHub app may submit only if its **actual supported write action is available on that device/account**; never presume that ChatGPT Plus on a phone can write Issues. Use the existing H4 MCP/Coordinator only after it is safely qualified. Never require OpenAI Platform API credit, a runtime API key for an OpenAI tunnel, a paid VPS/domain/tunnel, a ChatGPT Business upgrade, or a cloud TTS/Whisper replacement. The Secure MCP Tunnel Python source and runbook remain historical/tested **dormant alternatives, NOT AUTHORIZED for H4 installation** under the current Owner cost decision. No source-merge implies a field cutover.

**How it is meant to work:** Owner requests in ChatGPT on phone; if this device/account has no qualified GitHub-write integration, Owner submits the request using GitHub mobile/web -> GitHub Issue **REQUEST ONLY** with task reference and non-secret parameters -> later qualified H4 process checks GitHub over outbound HTTPS and current project SOT -> approved strict read-only local tool -> sanitized GitHub receipt -> ChatGPT fetches report. Do not send private books/audio, keys, addresses, customer/finance information or passwords to Issues, GitHub PRs or CI logs. GitHub Issue author/request creation is never execution authority: any future local consumer must separately check the platform-observed Owner login `magasincoffee` and numeric account ID `191064507`, independently verified issue-bound Owner approval/lifecycle, current project SOT, STOP, deduplication and task allowlist. Existing generic Supervisor `MAGASIN_DISPATCH_V1/action=execute_task` issue/Gateway must not be reused. STOP and all independent SC-013 P1/P2/P3 and SAYDI Owner gates still apply; no new H4 polling service or actual dispatch is authorized by this document.

**First pilot remains** `SAYDI002-VN-001` V6 step **1.1 IN_PROGRESS**: approved V5 metadata/bounded SHA only, no re-render, no Worker START, no claim of actual checkpoint/narrator ownership without H4 field receipts. H4 remote last seen offline; mobile GitHub connector and local channel must be verified before pilot. GitHub usage free only within normal quotas; existing H4 electricity/Internet and ChatGPT Plus cost remain. Supervisor central cost decision: `magasincoffee/magasin-supervisor` root `SOURCE_OF_TRUTH.md`, supporting document `docs/sc013/SC013_ZERO_NEW_SERVICE_FEES_GITHUB_RELAY_2026-10-12.md`.

### 2026-10-14 SAYDI002-VN-001 — no-new-fee GitHub relay Issue preflight (SOURCE/QA ONLY)

**Current Owner decision unchanged:** use GitHub request/receipt relay with **no new paid tunnel or API service**, rather than the historical Secure MCP Tunnel. This subsection is part of the canonical SOT only, not a separate task ID. `SAYDI002-VN-001 IN_PROGRESS`; step 1.1 is NOT DONE.

**Source-only candidate:** `tools/saydi_tts/qc/vn001_github_relay_preflight.py` inspects a *caller-provided, UNTRUSTED* synthetic GitHub Issue-shaped snapshot for exact repository/Issue URL/number consistency, claimed Owner numeric account ID, allowed `SAYDI002-VN-001` action `inventory_v5_readonly`, metadata-only scope, root *key* rather than path, and exact expected main commit string. It rejects closed/PR Issues, malformed or duplicated JSON keys, extra shell/path/worker fields and protocol drift. The module **never contacts GitHub**, reads H4, consumes a book, hashes WAV/checkpoints, creates an Issue, polls, queues or dispatches anything. Even a syntactically acceptable forged Issue returns `PREFLIGHT_SHAPE_ONLY_UNATTESTED` with `github_identity_authenticated=false`, `owner_issue_approval_verified=false`, `replay_and_stop_verified=false`, `sot_main_verified=false`, `h4_mcp_transport_qualified=false`, `can_read_v5=false`, START/DISPATCH=false. Metadata claiming login/account ID is **not** independent authentication. Windows+Linux hosted synthetic negative tests are required.

**Future field gates remain HOLD:** separately authorized live authenticated GitHub fetch and immutable observed Owner identity, new independently issued one-shot issue-bound Owner consent, replay/duplicate guard with durable evidence, live exact-main SOT and trustworthy STOP generation, reviewed H4 adapter and protected root identity/no-follow traversal, Windows QA and rollback; no use of Supervisor generic `execute_task`. No new H4 service, runner dispatch, poller, public tunnel or local file scan is authorized by this candidate. No permission to access protected 640/440/346/347 V5 chunks, restart workers, read private manuscript, or advance VN-002. Code PR and exact-main CI are SOURCE/QA evidence only.

### 2026-10-14 SAYDI002-VN-001 — GitHub Owner Issue/comment evidence source/QA only

**No change to task authority or field permission:** `SAYDI-002 = NEXT`, `SAYDI002-VN-001 = IN_PROGRESS`, V6 1.1 IN_PROGRESS. This step extends the Owner-selected no-new-paid-fee GitHub relay in PR source and hosted fixtures. The earlier Issue preflight is mere format validation. A new `tools/saydi_tts/qc/vn001_github_relay_owner_evidence.py` provides a separately bounded **HTTPS GET-only** GitHub API observer for a supplied Issue number, Owner approval comment ID and pinned exact-`main` commit. It reads the bounded GitHub **git/ref/heads/main** commit SHA before and after (never a potentially oversized full commit JSON), fetches **both the exact Issue and the exact approval comment twice** to reject mid-observation edits/deletion, and rejects drift, wrong repo/number, non-Owner numeric account ID/login, comments on other Issues, edited/backdated comments, approval JSON with extra/duplicate fields, or a changed Issue body SHA. The approval intent must bind a one-shot nonce, Issue numeric ID, body SHA-256 and exact pinned `main` SHA, and explicitly permit **metadata read only**. Default HTTP client is HTTPS with strict URL allowlist, finite byte/time budgets, no redirects or non-GET methods, and no token in receipts. A mock fetch in synthetic CI is **not** authenticated live transport.

**Critical non-acceptance:** Both a successful fake-fixture observation and a future successful real GitHub GET return `OWNER_INTENT_MATCHED_NON_EXECUTABLE`, with `owner_issue_approval_verified_for_h4=false`, `owner_one_shot_consumed=false`, `replay_guard_verified=false`, `h4_stop_generation_verified=false`, `h4_root_identity_verified=false`, `can_read_v5=false`, and START/DISPATCH=false. A GitHub comment alone is NOT a one-shot action approval, STOP proof, or permission for any H4 protected-file read. A separate reviewed local authority with durable replay journal and verified Owner/STOP generation, exact-main SOT, trusted root and Windows no-follow traversal plus scoped fresh Owner one-shot approval is still required. No GitHub Issue/comment was created for this test. No H4 MCP service installed/reloaded, no scanner activated, no V5 source/WAV/checkpoint/voice read or production write; Supervisor STOP/AUTOSTART_DISABLED unchanged by source work. Require both platform Windows/Ubuntu synthetic CI, independent exact-head Codex review, reviewed merge and exact-main CI before SOURCE-ready status; **not** field-ready or task DONE.

### HISTORICAL / SUPERSEDED — 2026-10-12 Secure MCP Tunnel source/QA trial (DO NOT DEPLOY)

**Historic selection only (superseded by the latest Owner no-new-fee lock above; NOT a current instruction):** Use OpenAI Secure MCP Tunnel as the intended **outbound-only private transport** between ChatGPT and the pre-existing H4 local MCP trust boundary. Keep VieNeu fully local (no TTS cloud API). No direct public internet port, public anonymous tunnel, untrusted generic shell, automatic Supervisor activation, new background watchdog or paid narration-provider migration. Platform tunnel setup uses an **owner-managed `tunnel_id` and runtime Platform API key** for tunnel communication; those secrets are NEVER placed into source, SOT, chat or diagnostics. Existence, permissions, costs and authenticated ChatGPT/mobile support must be verified, not guessed.

**Source-only stage:** `tools/saydi_tts/qc/vn001_private_mcp_stdio.py` is one narrowly scoped Python stdio MCP endpoint for future use by officially authenticated `tunnel-client`, exposing only `saydi_vn001_inventory_readonly` with strict JSON-RPC, a fixed request schema, local-root allowlist delegated to the existing SHA-gated bridge, GitHub exact-main check and no START/STOP/shell/render commands. `00_PROJECT/SAYDI_VN001_SECURE_MCP_TUNNEL_RUNBOOK_20261012.md` is a subordinate rollout guide, NOT another SOT. Hosted Windows/Linux synthetic QA covers tool allowlist, no unapproved methods, failed-closed errors and no-worker execution. No service is installed, started, or authorized merely by merging code.

**Field gate (NOT YET PASSED):** Desktop Commander reported `DESKTOP-H4A16IL` **Offline**, last seen ~4 hours earlier at this check. No alternative H4 MCP connector exists in this chat. The H4 Owner or approved operator must separately create/authorize tunnel in official Platform settings and securely inject the runtime key on H4; confirm on-host `tunnel-client doctor` and manual authenticated connection, no exposed ports. Independently prove exact installed stdio module checksum/allowed roots/worker ownership/STOP/CLI transport, then discover exactly one ChatGPT custom tool, run metadata only, and review Owner-approved receipts. Supervisor SC-013 P1/P2/P3 are independent and remain blocked. **DO NOT** create an unreviewed GitHub Issue dispatch or deploy generic Business Executor. The private tunnel is NOT a way around Owner STOP or missing Supervisor project selection.

**Current status:** `SAYDI-002 NEXT`, `SAYDI002-VN-001 IN_PROGRESS`, V6 step **1.1 IN_PROGRESS**. Source/QA may pass without H4; **the tunnel is not yet activated**, not qualified for phone use or 24/7 operations, and no V5 SHA inventory has been executed on the real machine. Separate H4 evidence + explicit deployment gates are mandatory before DONE.

### 2026-10-13 SAYDI002-VN-001 — protected C: storage consumer audit, source/QA stage only

**Field evidence available, no new H4 job:** [Supervisor H4 one-shot read-only receipt 38243025301](https://github.com/magasincoffee/magasin-supervisor/actions/runs/38243025301) from **2026-10-12 18:30 ICT**, runner host `DESKTOP-H4A16IL`, returned free RAM **2.47 GiB**, C: free **1.20 GiB**, D: free **55.89 GiB**, 10 generic Python/FFmpeg process candidates, `STOP=PRESENT`, `AUTOSTART_DISABLED=PRESENT`, MCP Python/Gateway/SQLite presence and C:/D: SAYDI roots present. This is an earlier **read-only observation**, not verified live 2026-10-13 conditions, a verified MCP transport, Owner authenticated lifecycle, worker identity or checkpoint/waveform SHA.

**Source/QA security repairs for PR #114 — P1 / P2 (2026-10-13):** Independent Codex review identified two actionable issues: P1 allowed direct host-name-gated C: reads without a fresh canonical SOT and independent Owner authorization; P2 permitted recursive directory queues to be replaced with Windows junctions between stat and a later scandir. The code is now **explicitly NON-OPERATIONAL on real H4**: `scan_scope()` immediately raises `LIVE_H4_SCAN_NOT_AUTHORIZED` before touching a root when it detects `DESKTOP-H4A16IL`; `run_h4()` and direct Python CLI always return `BLOCKED` / exit 21 without any C: scan, regardless of hostname. The offline fixture helper performs **only a single-root directory level** (no recursive descent or queued child directory), with a `PARTIAL_SKIPPED` report whenever subdirectories, symlinks or junctions are encountered. It never asserts a full directory-tree inventory if any entries were skipped. This resolves exposure in the **source-only candidate**; it does **not** qualify a production H4 scanner or provide a current C: capacity result. Later on-host operation requires a separately reviewed implementation with fresh exact-main SOT checks, independent Owner issue-bound approval, trustworthy directory-handle-bound traversal on Windows (or safe nonrecursive partial semantics), verified worker/STOP state and a new Owner-approved one-shot gate. Synthetic CI does not substitute for those gates.

**Remaining field gate:** do not use GitHub Issue `execute_task`, auto launch new H4 workflow, run a model/ASR process, change STOP or delete/move any files. A **separately qualified and Owner-authorized one-shot H4 read-only collection**, routed through reviewed source-pinned job/runner host guard and independent SC-013 request/approval gates, is required before claiming fresh C: consumer sizes or suggesting any reversible relocation. The new tool is not installed on H4 and is not allowed to launch via the existing generic Gateway. MCP transport/auth, worker PIDs/mutex, authenticated Owner generation, approved voice/source/model/checkpoint SHA and internal VieNeu-unload/Whisper barrier remain **UNVERIFIED**. Do not advance to 1.2, VN-002 or mark VN-001 done.

**STATUS: SAYDI-002 NEXT; SAYDI002-VN-001 IN_PROGRESS, C: capacity HOLD; no Owner intervention requested during source-only QA.**

### 2026-10-13 VN-001 C: live-read field gate — next qualified work

**Authoritative task remains `SAYDI002-VN-001 IN_PROGRESS`, parent `SAYDI-002 NEXT`.** The PR #114 source-only storage-audit script on `main` is deliberately **BLOCKED on real H4** after Codex P1 (missing fresh Owner/SOT authorization) and P2 (mutable Windows junction-path traversal). Neither CI GREEN nor an Online self-hosted runner is field authorization. This turn reviewed the exact-main SOT, Supervisor STOP boundary and local bridge contracts. An attempt to introduce new approval-handler code was blocked by the execution safety check; do not circumvent it, infer that any source was deployed or create an issue dispatch to substitute for it.

**Next accepted implementation boundary:** `00_PROJECT/SAYDI_VN001_H4_C_STORAGE_FIELD_GATE_20261013.md` is a subordinate checklist: fresh exact-main project SOT, independently verified issue-bound Owner approval, immutable GitHub owner identity, durable STOP and replay proof, H4-only routing before any local read; Windows handle-bound/no-follow reparse-safe traversal (or explicitly **partial nonrecursive** fallback), negative security tests, separate exact-head PR+main CI and Owner-approved one-shot field run. If the independent proof is absent, scanner must remain BLOCKED. Never delete/move C: files, inspect private manuscripts in public CI, activate workers, restore paid Secure MCP Tunnel or start V6 1.2/VN-002. Previous 2026-10-12 disk telemetry is historical only. **No H4 run or production change has occurred under this checklist.**

**2026-10-13 SOURCE-ONLY QA increment (PR #116):** Expanded synthetic negative tests for missing/unreadable roots, reparse rejection, read failures, time bounds and sanitized fail-closed receipts. Codex identified two P2 gaps on initial PR head: a mocked reparse decision and private chained exception details still appearing in formatted traces. The updated PR uses the real reparse bitmask and suppresses raw `OSError` context in formatted `AuditHold` tracebacks, with explicit negative tests; final-head CI and Codex re-review remain acceptance requirements. This is *not* H4 field evidence or Owner issue-bound authorization. Independent SOT/STOP/replay verification, a Windows handle-bound (or expressly limited partial) scan design and a newly scoped Owner-approved H4 one-shot remain missing. Do not scan, delete or move real C: files. `SAYDI002-VN-001` remains `IN_PROGRESS`; real H4 scanner `BLOCKED`, C: capacity `HOLD`.

### 2026-10-14 SAYDI002-VN-001 fresh H4 OS/MCP read-only preflight — NOT full V5 inventory

**Active authority unchanged:** `SAYDI-002 NEXT`; `SAYDI002-VN-001 IN_PROGRESS`; V6 step 1.1 **IN_PROGRESS**, no V5 asset hashes verified. Owner requested starting with an inspection-only V6 preparation, and the only authorized action actually performed was a nonmutating remote Windows OS/transport status probe on `DESKTOP-H4A16IL`, not a credentialed SAYDI local MCP `handle_inventory()` invocation.

**Observed locally, 2026-10-14T14:29:14Z:** H4 remotely reachable. OS-visible RAM 7.884 GiB; available RAM 2.253 GiB (one observation, **below** the historically required 2.3 GiB safe QC-resume floor and the 2.5 GiB provisional ASR floor); disk C: 4.058 GiB available and D: 56.037 GiB available. Both exact `C:\SAYDI` and `D:\SAYDI` top-level roots exist and neither top-level leaf was marked a reparse point; **this does not certify any child path or runtime checkpoint**. Two Python processes had matching SAYDI-related command-line patterns, each low memory footprint, but neither was independently identified as current VieNeu/Whisper/model owner. The Windows scheduled-task list showed SAYDI Control Job Guardian Ready and the observed legacy V4/V5 resume/QC tasks Disabled; Ready is NOT a running worker or approval to alter legacy tasks. Supervisor physical STOP and AUTOSTART_DISABLED both remained present.

**Separate read-only MCP transport observation, 2026-10-14T14:30:42Z:** `C:\MAGASIN_MCP` exists with installed `dispatch_gateway.py`, `local_jobs.py` and state telemetry; Gateway role matched 2 Python processes, and MCP server role matched 6 by process-command classification (a name heuristic, not independent ownership/security attestation). MCP agent heartbeat was fresh (`RUNNING`); Gateway reported GitHub `ONLINE` and Supabase `DISABLED_NOT_CONFIGURED`. The field probe neither executed SAYDI `MAGASIN_SAYDI_VN001_MCP_READONLY_V1` nor proved the SAYDI handler was deployed/bound to authenticated local MCP. No GitHub request/dispatch issue, SQLite SQL, production file walk/hash, manuscript/audio access, model worker START/STOP, QC/render, file deletion or service restart occurred.

**BLOCKER_ID=BLK-SAYDI-V6-11-FIELD-AUTH**; TASK_ID=`SAYDI002-VN-001`; STATUS=`OPEN`; TYPE=`AUTHORITY_AND_FIELD_VERIFICATION`. SUMMARY: Real checkpoint/source/approved-voice/model SHA, worker PID/mutex owner, Owner STOP generation, root child-path safety, sequential VieNeu-unload/Whisper barrier and trusted local MCP bridge binding remain unverified. The separate `vn001_h4_c_storage_readonly.py` scanner is deliberately nonoperational on real H4 after review; do **not** use direct ad hoc recursive C: scanning to bypass its explicit real-host block. OWNER_ACTION: none for continued synthetic/source review, but a separate authenticated Owner issue-bound one-shot permission and accepted no-follow traversal/partial-inventory implementation is required before real protected-file scan. EVIDENCE: [sanitized 2026-10-14 H4 read-only OS/MCP receipt](https://github.com/magasincoffee/magasin-media-robot/pull/117#issuecomment-6170948509); this is a ChatGPT-authored transcription of direct Remote Desktop Commander tool outputs, not a signed machine receipt and **not** authenticated SAYDI MCP bridge execution or protected V5 checkpoint SHA proof. RESUME_WHEN: reviewed exact-head+main source, genuine accepted authenticated transport, qualified H4 root/ownership and resource proofs, sanitized bounded read-only receipts with independent STOP/SOT provenance. Preserve existing V5 640/440/346/347 checkpoints, no heavy VieNeu+Whisper concurrent load and no advance to VN-002/step 1.2 merely for this OS telemetry.

### 2026-10-14 SAYDI002-VN-001 — offline V5 SHA-page reconciliation candidate (SOURCE/QA ONLY)

**Scope:** Add `tools/saydi_tts/qc/vn001_v5_hash_page_reconcile.py` as a pure, standalone reconciliation helper for the already versioned `vn001_v5_readonly_inventory.py` receipt schema. The future authenticated, Owner-approved H4 metadata and paginated SHA flow needs to detect missing/replayed/out-of-order pages, changed metadata fingerprint, scope/size/count drift, duplicate anonymous file IDs, malformed digests, wrong byte budgets and forged START/dispatch/worker signals **before** calling any protected V5 snapshot a reconciled file set. This helper performs NO file I/O, no network or MCP calls, no worker starts, no H4 scan, no source/voice/audio edits and no authorization. Even an apparently complete synthetic page series returns `HASH_PAGES_RECONCILED_UNATTESTED`, with Owner authorization, approved V5 asset identity, checkpoint ownership, narrator identity, H4 field proof and V6 1.1 DONE all explicitly **false**. Offline negative tests are wired into the existing Windows/Linux `SAYDI VN001 V5 Read-only Inventory QA` workflow for PR and push.

**Release status:** This is only a PR source/fixture candidate until exact-head CI GREEN, independent Codex review clean, reviewed merge and exact-main checks. No local installation or worker deployment is implied. It does NOT override the explicit H4 C: scanner `LIVE_H4_SCAN_NOT_AUTHORIZED` safeguard, Windows handle-bound traversal, issue-specific Owner approval, independent MCP transport authentication or STOP gates. `SAYDI002-VN-001 IN_PROGRESS`, V6 1.1 IN_PROGRESS, VN-002 PENDING and all protected V5 checkpoint/reference assets unchanged.

### 2026-10-14 SAYDI002-VN-001 — security gate for private stdio MCP entrypoint (SOURCE/QA ONLY)

**Active authority unchanged:** `SAYDI-002 NEXT`, `SAYDI002-VN-001 IN_PROGRESS`, V6 step 1.1 IN_PROGRESS. Independent code review identified a source-only trust-boundary gap: `vn001_private_mcp_stdio.py` previously treated the mere arrival of a JSON-RPC `tools/call` on stdin as `transport_authenticated=True`. This is NOT independent evidence of actual tunnel/workspace identity or Owner consent. A valid-looking remote request must not turn a generic pipe into an authorized protected V5 file reader.

**Candidate remediation:** default `dispatch(..., trusted_transport_authenticated=False)`, with valid `tools/call` returning `BLOCKED / MCP_TRANSPORT_NOT_AUTHENTICATED` BEFORE loading bridge module, parsing locally bound root config or touching files. Even an installed direct `run_stdio()` remains fail-closed. A future separate qualified H4 local host wrapper MAY inject the trusted Python-only flag strictly after independent real transport authentication and Owner issue-bound scoped one-shot approval; JSON-RPC request arguments/environment booleans are NOT proof. This candidate does not implement that wrapper. Synthetic unit tests exercise default rejection without invoking scanner, injection rejection, successful isolated host-trusted fixture and real subprocess JSON-RPC valid-call rejection; Windows+Linux QA is required. The subordinate Secure MCP Tunnel runbook now labels the old direct `--mcp-command` example synthetic-only/HOLD.

**Field status:** H4 authenticated SAYDI MCP binding NOT QUALIFIED; no real tunnel installation, root binding, V5 recursive scan, checkpoint/source/voice hash, TTS/Whisper execution, Windows service reload, dispatch, SQLite or Owner STOP mutation. Need exact-head CI GREEN, independent Codex review, merged exact-main CI before even proposing a qualified local wrapper. Separate Supervisor SC-013 acceptance, immutable STOP witness, Windows no-follow file traversal and V5 asset/worker ownership remain independent OPEN gates. A clean offline PR is NOT proof of authenticated production connection or step 1.1 DONE.

### 2026-10-15 SAYDI002-VN-001 — H4 MCP heartbeat and legacy unload preflight (READ-ONLY / NOT ACCEPTANCE)

**Authority unchanged:** `SAYDI-002 NEXT`, `SAYDI002-VN-001 IN_PROGRESS`, V6 step 1.1 / 1.3 not accepted. This entry is a sanitized observation from an authorized read-only H4 session, not a signed machine/Owner attestation and not authority to read protected checkpoint contents or start a worker.

**Fresh H4 observations (2026-10-15 ICT):** Desktop Commander reported `DESKTOP-H4A16IL` online. An OS-level status query showed 7.88 GiB visible physical RAM, approximately 1.43 GiB available, C: approximately 2.04 GiB free, D: approximately 56.03 GiB free. The existing MCP local agent continued producing a fresh heartbeat after its prior restart; the authenticated MCP protocol query returned `agent_healthy=true`, heartbeat age about 2.8 seconds and `pid=7420`. Two listed Python entries formed the local agent's parent/child process pair; **not** evidence of two independently owned workers. Process-name/command-line sampling did not identify a current VieNeu, Whisper, or SAYDI render/QC worker; that is not a mutex or model-unload attestation. The legacy `audiobook_status` tool still mapped to V4 and reported zero active processes; it is not a V6 dispatcher or V5 checkpoint authority.

**Owner STOP boundary:** MCP's Supervisor read-only snapshot returned `owner_stop=true`, `automation_status=STOPPED`, `watchdog_mode=INTERNAL_ERROR`, `wrapper_alive=false`. This is a reported STOP signal, **not** independently authenticated SAYDI Owner STOP generation or scope-specific START permission. Preserve STOP and reject production dispatch or render/QC initiation. Do not repair Supervisor STOP by retrying an unrelated SAYDI request.

**Legacy V5 chapter-02 static gate review:** A read-only Python AST analysis of `C:\SAYDI\narration_director_v1\chapter2_v5_qc_guarded.py` showed render and QC are called serially, `render()` calls `tts.close()` and `gc.collect()`, and `qc()` launches its Whisper/QC stage in a child process. The composite `run()` has RAM and heavy-process checks but no observed authenticated Owner-generation check or explicit, independently measured post-VieNeu unload/reaped-process barrier. These negative static findings do not prove model memory was (or was not) released at runtime. A real VieNeu-to-Whisper transition is **NOT QUALIFIED**. Never run the existing full-chapter pipeline just to verify the gate.

**Owner resource preference (not a safety proof):** Owner requested a target of 1 GiB **available** RAM and one compute thread. Existing local QC code already constrains `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` and `NUMEXPR_NUM_THREADS` to 1, but `chapter2_v5_qc_guarded.py` still uses 1.5 GiB start / 0.70 GiB running gates. Do not silently lower any production floor or treat 1 GiB target as approval of a full VieNeu or Whisper model load. Synthetic tests may evaluate 1-thread and 1-GiB proposals without heavy processes; real thresholds require fresh measured sequential single-worker qualification and sufficient C: free space.

**BLOCKER_ID=BLK-SAYDI-VN001-20261015-UNLOAD-AUTH**
- TASK_ID=`SAYDI002-VN-001`; STATUS=`OPEN`; TYPE=`AUTHORITY_AND_SEQUENTIAL_RESOURCE`.
- SUMMARY=Protected V5 source/reference/voice/checkpoint SHA set and mutex owner not authenticated; STOP generation not independently attested; no qualified unload barrier between VieNeu and Whisper; V4 MCP routing is not a V6 launch permission.
- OWNER_ACTION=NONE for source-only QA. Before any real protected-root SHA read, require independently verified exact-main SOT; narrowly scoped, independently authenticated Owner issue-bound one-shot authorization; a durable atomic one-shot consumption/replay journal, independently checked immediately **before each protected-root SHA read** and again **after that read, before returning any receipt**, with the same approved request, generation, scope and consumed-once state; independently verified current Owner STOP-generation/latch attestation at both boundaries (STOP is never permission to START); trusted MCP transport/root allowlist; and Windows safe path handling. If either journal/STOP pre-read or post-read witness is missing, changed, replayed, stale, unauthenticated or inconsistent, **suppress the entire receipt**, report BLOCKED and never promote partial hashes as accepted evidence. Do not rely on pre/post authorization-only checks. Before a bounded audio sample, require a separate authenticated authorized START generation, verified checkpoint/model ownership, sequential unload barrier, resource/volume preflight and explicit task progression. No generic Gateway issue may substitute for these proofs.
- EVIDENCE=2026-10-15 read-only H4 OS/MCP protocol response and static AST review only; no private manuscript/audio/checkpoint contents or protected SHA read, no worker launched, no model loaded, no existing checkpoint/queue or STOP mutated.
- RESUME_WHEN=Accepted independent H4 one-shot field-read gate, sanitized paginated hash/owner receipts, synthetic negative sequential/barrier tests and qualified real unload preflight with Owner approval. Until then `VN-001 IN_PROGRESS`, `V6 field trial BLOCKED`, `VN-002 PENDING`.

### Owner-approved V6 upgrade — 6 phases / 24 small jobs

Each checkbox starts TODO unless complete acceptance is proven (having a V5 implementation only means baseline exists). Report task proof: merged commit, exact-head+exact-main CI, sanitized H4 receipts, Owner listening when needed. Stages are roughly **3–5, 4–6, 4–7, 5–8, 4–7, 4–7 workdays** respectively; estimated **24–40 workdays** total, not a delivery promise. Sequential stages and dependency gates still apply.

| Step | Small job / simple user outcome | Existing owner ID(s) | Status / gate |
|---|---|---|---|
| **1.1** | Freeze and hash all approved V5 WAV/MP3, reference voice, chapter checkpoints and active worker | SAYDI-002 / VN-001 | IN_PROGRESS; read-only partial evidence, hashes/owner incomplete |
| **1.2** | Inventory C: and safely free/redirect only authorized per-SAYDI data with backup/rollback | SAYDI-002 / VN-001 | TODO; C: resource blocker |
| **1.3** | Prove VieNeu off/unloaded before Whisper starts; resource, mutex, Owner STOP/START barriers | SAYDI-002 / VN-001; V6-P0-06 | IN_PROGRESS offline; real sequence unqualified |
| **1.4** | Qualify local VieNeu contract, approved bounded sample, G/QC receipt and hand off to SAYDI-003 | SAYDI-002 / VN-002..005 | TODO, dependencies VN-001 |
| **2.1** | Recognize book, chapter, title, paragraphs; remove non-spoken PDF page debris | SAYDI-003; V6-P0-01 | TODO / canonical provenance test |
| **2.2** | Prepare speech punctuation, line joins, numbers, abbreviations, name/term lexicon | SAYDI-004; V6-P0-01 | TODO / no word loss |
| **2.3** | Label narration, dialogue, quotes, emphasis and logical pauses | SAYDI-004/005; V6-P0-01 | TODO / semantic confidence |
| **2.4** | Token/source equivalence gate: preserve meaning and send uncertain edits to REVIEW | SAYDI-004; V6-P0-01 | TODO / source immutability |
| **3.1** | Understand book/chapter/scene intent and audience, not just isolated keywords | SAYDI-005; V6-P0-01 | TODO / hierarchical context |
| **3.2** | Establish emotion/intensity, speaker continuity and smooth adjacent scene changes | SAYDI-005; V6-P0-01 | TODO / emotional arc test |
| **3.3** | Prepare provider-safe native-speed pauses, emphasis, pronunciation directions pre-render | SAYDI-005/006; V6-P0-02 | TODO / validated narration plan |
| **3.4** | Generate representative 3–5-minute V5 vs V6 listening sample with approved voice | SAYDI-005/006; V6-P0-02 | TODO / Owner A/B acceptance |
| **4.1** | Detect missing/duplicate/out-of-order segments and mismatched spoken text | SAYDI-008; V6-P0-03 | TODO / source+WAV SHA |
| **4.2** | Detect suspected wrong Vietnamese tones, slurs, names with two signals when consequential | SAYDI-008; V6-P0-03 / SAYDI-QC | TODO / guard ASR false alarms |
| **4.3** | Check pauses, phrasing, intonation, sound levels and joins against approved profile | SAYDI-007/008; V6-P0-05 | TODO / audio QC and audition |
| **4.4** | Classify root causes SOURCE/EDITORIAL/VIENEU/ASR_FALSE_POSITIVE/AUDIO_JOIN | SAYDI-008; V6-P0-03 | TODO / explain defect before repair |
| **5.1** | Select only exact damaged chunk; keep all accepted chunks unchanged | SAYDI-006/008; V6-P0-04 | TODO / SHA isolation |
| **5.2** | Try at most 2 safe targeted fixes; no rerender whole chapter | SAYDI-006/008; V6-P0-04 | TODO / bounded retry |
| **5.3** | Recheck modified WAV, neighboring joins and voice consistency; accept only better result | SAYDI-007/008; V6-P0-04/05 | TODO / before-after QC |
| **5.4** | Retain baseline if inconclusive and issue exact timecoded REVIEW exception | SAYDI-008; V6-P0-04 | TODO / no false FINAL |
| **6.1** | Assemble, validate and export chapter MP3 / book M4B with complete QC report | SAYDI-007/009; V6-P1-08 | TODO / playable metadata |
| **6.2** | Show real workflow phases, RAM, QA findings, owner-controlled lifecycle + playback in Control Center | SAYDI-010; V6-P1-07/08 | TODO / separate secure UI cutover |
| **6.3** | Full Chapter 1 recovery using 347 V5 WAVs, auto-QC/repairs then Owner chapter audition | SAYDI-008/009/010; V6-P1-08 | TODO / field and listening PASS |
| **6.4** | Test one independent new chapter from ingestion to approved output, reboot/recovery, release gate | SAYDI-011; V6-P1-08 | TODO / clean field acceptance |

**Prior V6 work-package meanings (subordinate only):** V6-P0-01 editorial/semantic Director; P0-02 approved golden voice and native articulation; P0-03 multiple-evidence pronunciation/root-cause QC; P0-04 at most 2 attempts and isolated SHA repair; P0-05 natural joins/prosody; P0-06 memory/watchdog; P1-07 local Director-to-robot schema (private manuscript default); P1-08 Owner chapter/listening dashboard. Implement in existing `02_SAYDI_CORE/src/saydi_audiobook/{editorial,director,pronunciation,prosody,quality,repair}.py` and `tools/saydi_tts/{narration,qc}`; do not build competing subsystem.

### Consolidated preexisting QC / Narration Director statuses (proof, NOT separate NEXT)

- `SAYDI-QC-001` DONE (PR #60 deterministic QC); `QC-002` DONE (H4 metrics field acceptance); `QC-003` DONE (PR #64 lexicon); `QC-004` code merged (PR #66/Edge v7) but correct-H4 targeted rerender field acceptance **PENDING**, previous wrong-machine 4K7 attempt not proof; `QC-005` DONE (PR #69 profile envelopes); `QC-006` synthetic harness available, real H4 and Owner before/after listening **PENDING**; `QC-007` editorial/stitch code present, field listening **PENDING**.
- `SAYDI-ND-001` DONE (PR #83 beat Director); `ND-002` V2 raw 17/17 finished, master/Owner listening pending; `ND-002B` V3 proposed natural-speed, not listening accepted; `ND-002C` V4 73/73 raw, Owner/master pending; `ND-002D` editorial field 33/33 raw VieNeu chunks, post-render QC/stitch/Owner listening pending, isolated Python 3.11 QC env fix PR #95; `ND-003` production integration PENDING. **Never treat any of these historical "next" tasks as current executable tasks** when `SAYDI-002`/VN-001 remains active. Preserve local files and markers.
- Audio benchmarks: Chapter 1 V5 347 chunks (R2 115 basic ASR REVIEW, 279 strict ASR REVIEW), Chapters 2/4/5 chunk counts above. Owner's perceived ~90% quality of approved sample is subjective listening guidance, NOT objective QC PASS rate or license to mark full chapter FINAL.

### Robot execution & signoff from THIS file ONLY

1. **DISCOVER:** reread main SOT from first line; take exactly one already-authorized current ID; never choose a superseded SaydiVoice task, old QC/ND tracker "NEXT", or V6 checklist row as `NEXT_TASK_ID`. No new alternative SOT, temporary queue or unreviewed status tracker.
2. **EXECUTE/CHECK:** protect production STOP, 8GB RAM, immutable audio and private manuscript; do source-only code, deterministic/synthetic fixture tests while real live gates blocked. CI test changed paths, check exact PR head and main. New heavy real worker only with verified Owner START generation, safe C:/RAM, mutex/checkpoint and unload barrier; separate controlled and reversible cutover approval required.
3. **COMPLETE:** mark an existing task DONE and advance `NEXT_TASK_ID` **only** when its written gates pass, and update only this file with auditable PR/main SHA + sanitized field proof. If blocked, retain task state and document explicit block; do not loop. Keep the 24 checklist honest; count **DONE/24** from actual acceptances, not architecture task count.
4. **Owner milestones:** A = safe V5 baseline/worker; B = actual better V6 3–5 minute listening sample; C = Chapter 1 full MP3, robot QC and minimal repair, real Owner listening acceptance. Owner intervention normally only sample/voice/meaning/quality high-impact exceptions and production lifecycle cutover, not every technical PR.


## Owner confirmation 2026-10-11 — V6 is the latest upgrade TARGET, V5 remains protected baseline

The Owner confirms: **use the latest V6 quality/automation specification to improve the existing VieNeu V5 robot, NOT rebuild V5 or substitute retired SaydiVoice.** Here **V6 means the target upgrade specification**, **not a deployed or accepted production release**. Preserve the Owner-approved V5 narrator/reference, previously rendered chapters, WAV/MP3, queues, checkpoints and local scripts unless a separately approved, reversible, evidence-backed migration permits changes. Do not automatically rerender an approved segment or upgrade the narrator fingerprint.

The V6 target is local semantic editorial preparation -> approved reference sample -> sequential VieNeu render -> layered pronunciation/tone/prosody/acoustic and join QC -> SHA-matched bounded repairs -> chapter REVIEW/Owner exception approval -> validated exports, with clear read-only progress visible in MAGASIN Control Center. The canonical detailed requirements and existing subordinate work packages remain the consolidated V6 execution section above; the task queue below and its NEXT task **do not change**.

First executable safety increment under **SAYDI-002 / SAYDI002-VN-001**: harden the *offline-only* H4 8GB read-only telemetry preflight against stale, missing, naive-time or future-dated snapshots; keep explicit Owner lifecycle witness, checkpoint ownership, disk and inner TTS-to-ASR unload-barrier gates unqualified until independently verified. This is V6-P0-06 prerequisite work and **does not install a new Control worker, enable production, mark VN-001 DONE or qualify V6 as released**. Subsequent V6 quality work remains under its existing SAYDI-004..010 owning tasks, with no bypass of current eligibility/Owner approval gates.

## Owner decision 2026-10-11 — SaydiVoice RETIRED; VieNeu local ONLY

**This newer Owner decision supersedes all previous active, optional or prerequisite SaydiVoice directions, including the old `SAYDI002-003` login preflight, old SaydiVoice sample-generation task and old provider-specific SAYDI-002 completion gates.**

1. **Sole active TTS:** VieNeu v3 Turbo / ONNX on **DESKTOP-H4A16IL**, using the existing approved local narrator/reference `SAYDI Nam Mien Nam`. No cloud/paid SaydiVoice TTS requirement. DESKTOP-4K7IM13 is not a prerequisite.
2. **Disable execution:** Never dispatch SaydiVoice browser authentication, preflight, Generate, catalog, profile recovery, external provider API or SaydiVoice voice-sample approval tasks. Legacy SaydiVoice repository code and historic evidence may remain as an **inactive archive**; do not delete private browser profiles or old logs as part of this documentation transition.
3. **Current task remains `SAYDI-002: NEXT`** — it must now be closed against verified local VieNeu evidence, *not* the retired SaydiVoice gates. Historical task IDs `SAYDI002-003..006` tied to SaydiVoice are **SUPERSEDED / NOT EXECUTABLE**, **not DONE**; follow **`SAYDI002-VN-001`** in updated this single canonical SOT. Never reuse an old legacy task ID for a different operation.
4. **Style G is Owner-approved for title signal**: original soft instrumental 2s prelude, 160ms separation and very quiet voice-ducked bed during structural headings only, never during body narration. Style approval **does not** approve the entire chapter, original first-word pronunciation, material joins, a changed narrator fingerprint or FINAL release.
5. **Preserve protected assets and control:** no modification to Chapter 2's protected 640 chunks/checkpoints, previously approved MP3/WAV/book/manifests, worker ownership, Windows scheduled tasks or Control Center cutover. Do not start heavy VieNeu/Whisper solely because of a SOT edit. Owner STOP and post-cutover OFF-after-reboot policy remain authoritative.
6. **SAYDI-002 VieNeu completion evidence:** verified provider-neutral Voice/AI interfaces, deterministic local fallback, approved narrator fingerprint, preflight of worker/RAM/checkpoint, reproducible one bounded local audible sample or existing exact-hash field receipts, text/audio approval status, idempotency/privacy tests and safe QC. No silent DONE based only on unit tests; do not skip SAYDI-003..011.
7. All old SaydiVoice prose below is **historical and NON-EXECUTABLE** where it conflicts with this directive. PR #102 is closed unmerged and must not be used for automatic runner dispatch.

## Owner decision 2026-10-11 — KEEP 8GB H4 / sequential VieNeu + Whisper

The Owner chooses to **retain H4's installed 8 GB RAM** rather than require an upgrade. All SAYDI local production must optimize for sequential resource budgeting: **VieNeu TTS and Whisper/ASR may never load concurrently**; unload and verify one heavyweight model before the next, process small resumable batches, reuse audio/checkpoint and repeat QC only on changed/neighbor segments.

- Measured 2026-10-11 on DESKTOP-H4A16IL: 7.88 GiB physical RAM visible; five short samples 2.19/2.27/2.17/2.21/2.33 GiB free. C: free only ~1.29 GiB while D: ~56.39 GiB. C: capacity is an immediate safety risk for caches, paging and temp; do not delete user files or globally redirect Windows caches without inventory and reversible Owner-authorized migration.
- Observed Ch04 native VieNeu: 440 segments / 68.5min including resource pauses; Whisper QC approximately 6.55 chunks/min, 264 PASS / 176 REVIEW. **This is a historical workload, not a guaranteed ETA or FINAL**. Dynamic timing should use actual per-stage throughput and stop ETA progress during resource pauses.
- Preserve current 640 Chapter 2 checkpoints and all approved WAV/MP3. Legacy local RAM gates vary (Control 1.5 GiB, VieNeu 1.9 GiB, Ch02 QC historical >=2.3 GiB): do not silently adopt the lowest. The read-only trial gate proposes conservative 2.1 GiB TTS and 2.5 GiB ASR minima over five samples, and at least 2 GiB C: headroom; those stricter proposed values require field testing before runtime integration.
- Implementation/receipts: [SAYDI_VIENEU_8GB_SEQUENTIAL_RUNTIME_PLAN_20261011.md](./SAYDI_VIENEU_8GB_SEQUENTIAL_RUNTIME_PLAN_20261011.md). An offline probe on source does **not** install/update the production controller or authorize Owner START. Extend the existing coordinator and mutex only after separate qualified rollout, never create a competing watchdog. Owner STOP and future OFF-after-reboot policy remain authoritative.
- Main SOT task stays **SAYDI-002 NEXT**; active subtask remains **SAYDI002-VN-001**, in progress pending protected checkpoint/worker ownership inventory. Continue VN-002+ in order; no previous SaydiVoice task is restored.

## Product identity

**Product:** SAYDI Audiobook  
**Repository:** `magasincoffee/magasin-media-robot`  
**Operating model:** local-first Windows audiobook production with replaceable AI/TTS providers and no mandatory paid/cloud dependency.  
**AI policy:** deterministic rules first; local LLM is the default semantic-analysis path; ChatGPT/other cloud LLMs are optional fallbacks only when explicitly enabled by the owner.  
**Voice policy:** provider-neutral Voice Engine with VieNeu v3 Turbo / ONNX as the ONLY active local production TTS. Retired SaydiVoice is historical reference only.

The previous social-video product direction is paused. Old SaydiVoice discovery is retained as historical evidence only; its runtime is retired.

## Product goal

Turn a legally usable manuscript into a production-ready audiobook with minimal operator work while preserving textual fidelity, resumability, privacy, and auditable QA.

Primary user flow:

```text
Import book
  -> verify chapter structure
  -> choose narrator / style
  -> approve a short voice sample
  -> create audiobook
  -> review QA exceptions
  -> export M4B and/or chapter MP3
```

## In scope for V1

- **PDF-first ingestion** as a primary user path, including:
  - text-based PDF extraction;
  - scanned/image PDF classification;
  - OCR adapter path for scanned pages;
  - page/header/footer/page-number cleanup;
  - structural reconstruction into book/chapter/block form;
  - OCR confidence and suspicious-text review for low-confidence material.
- TXT, DOCX and EPUB ingestion through adapters.
- Canonical book/chapter/paragraph/segment manifest.
- **Three-layer text model**:
  - `original_text` — immutable extracted/source text;
  - `normalized_text` — deterministic cleanup and punctuation/structure normalization;
  - `spoken_text` — speech-oriented rendering used by TTS.
- Vietnamese-first text normalization with deterministic rules.
- **Narrative interpretation** for sentence boundaries, dialogue, narrator text, rhetorical rhythm and ambiguous punctuation.
- **Annotation handling** for footnotes, endnotes, citations, page references, parentheticals, editor/translator notes and sidebars.
- **Prosody direction** for pause, pace, emphasis, energy and semantic emotion.
- Pronunciation lexicon for names, abbreviations, numbers and special terms.
- Narration plan with voice, style, speed, pause, emphasis, emotion and pronunciation directives.
- Segment-addressed TTS generation with checkpoints and resumable execution.
- **AI Analysis Interface** with structured output, schema validation, confidence and review routing.
- **Local LLM default path** for book/segment analysis with model replacement behind an adapter.
- Optional ChatGPT/cloud-LLM fallback that is disabled by default and must never receive manuscript text without explicit operator enablement.
- **Rule Engine + Local LLM + Human Approval** authority model.
- Provider-neutral Voice Engine with both:
  - VieNeu v3 Turbo / ONNX all-local production adapter;
  - inactive legacy SaydiVoice code solely for audit/history, not a selectable provider.
- Local audio processing with FFmpeg/FFprobe.
- Chapter assembly and book-level mastering.
- Text-to-audio coverage QA and acoustic QA.
- Automatic regeneration only for isolated segments when the failure is proven retry-safe.
- M4B and chapter-MP3 export with metadata and chapter markers.
- Windows desktop operator flow.
- Local runtime state, logs and diagnostics.

## Explicitly out of scope for initial V1

- Video generation/editing.
- Automatic rewriting or summarizing of the author's prose.
- Voice cloning without explicit rights/authorization.
- DRM bypass or acquisition of copyrighted books without permission.
- Fully autonomous publication to third-party stores.
- Heavy generative-AI models unless a measured requirement justifies them.

## Existing verified foundation

The repository retains historical, retired SaydiVoice discovery under `01_DISCOVERY/saydivoice`. This section records OLD evidence, not active authorization.

Verified capabilities include:

- authenticated persistent Chrome session on the trusted Windows runner;
- voice discovery and selection;
- stability/expression, speed, pause and format controls;
- one-shot generation;
- download lifecycle;
- privacy-safe evidence handling;
- application-level voice presets;
- observed pause controls for period, comma, semicolon and newline;
- current discovery control layer can read pause timing values and enable/disable pause behavior.

## Windows SAPI narration quality decision

Operator listening verdict on 2026-09-30: **REJECT for production narration quality**.

Observed result: the sample was intelligible and proved the end-to-end local workflow, but sounded strongly robotic and lacked expressive/emotional delivery. Therefore:

- Windows SAPI remains an infrastructure/test provider only;
- it must not be treated as a production audiobook narrator;
- successful SAPI execution proves plumbing, state, conversion and delivery mechanics only;
- production audio approval now uses a rights-authorized **local VieNeu** narrator/reference and listening acceptance;
- any later all-local TTS candidate must be benchmarked separately for Vietnamese naturalness and expressive narration before V1 production acceptance.

Known provider boundary:

- the current discovery control layer does **not** yet support writing arbitrary per-punctuation pause timing values;
- no separate discrete provider control for emotions such as Happy/Sad/Angry has been observed;
- therefore audiobook emotion/prosody is an application-level semantic model mapped only onto provider controls that are actually verified.

This work is retained as provider evidence and must not be reimplemented from scratch.

## Target architecture

```text
SOURCE BOOK / PDF
   |
   v
PDF Classifier / Book Ingest
   |
   +--> text PDF extraction
   +--> scanned PDF OCR
   |
   v
Canonical Book Manifest
   |
   v
Structure + Annotation Parser
   |
   v
Original -> Normalized -> Spoken Text
   |
   v
SAYDI INTELLIGENCE LAYER
   |
   +--> deterministic Rule Engine
   +--> Local LLM (default)
   +--> ChatGPT / cloud LLM (optional fallback, owner-enabled)
   |
   v
Decision Engine + confidence/review routing
   |
   v
Narrative Interpretation + Prosody Director
   |
   v
Voice Casting + Representative Sample Set
   |
   v
TEXT PREVIEW APPROVAL -> AUDIO SAMPLE APPROVAL
   |
   v
Segment Job Orchestrator
   |
   v
Voice Provider API
   |
   +--> Local TTS (required all-local V1 path)
   +--> SaydiVoice (RETIRED, never dispatch)
   |
   v
Audio Processing / Assembly
   |
   v
Alignment + Acoustic QA
   |
   +--> repair queue for isolated segments
   |
   v
Export Engine
   |
   +--> M4B
   +--> chapter MP3
   +--> metadata / QA report
```

## Architectural invariants

1. **Immutable source:** imported source files are never destructively modified.
2. **Canonical manifest:** every spoken unit has a stable ID derived from the normalized book structure.
3. **Segment-addressed generation:** the smallest regeneratable unit is a segment, not a whole chapter or book.
4. **Provider isolation:** SaydiVoice-specific browser logic never leaks into book/text/audio domain logic.
5. **Idempotent orchestration:** rerunning a completed safe step must not duplicate audio or corrupt state.
6. **Explicit side effects:** live TTS generation is a controlled side effect with bounded retry policy.
7. **Local-first privacy:** source books, generated audio, sessions and credentials remain local by default.
8. **Fidelity before style:** no text may be silently omitted, duplicated or rewritten for performance.
9. **QA before export:** an audiobook cannot reach READY until required structural, coverage and acoustic gates pass.
10. **Resume by checkpoint:** interruption must resume from the last verified safe state.
11. **Three text layers are mandatory:** `original_text`, `normalized_text`, and `spoken_text` must be stored separately; spoken improvements never overwrite source fidelity.
12. **Punctuation is interpreted, not blindly trusted:** poor or missing punctuation may be repaired only in derived normalized/spoken layers and must preserve meaning.
13. **Annotations are explicit domain objects:** footnotes/endnotes/citations/editor notes must be classified and governed by a read/skip/defer/review policy; they must never disappear silently.
14. **Emotion is semantic, provider-neutral metadata:** SAYDI may classify delivery emotion/energy, but provider adapters may use only controls the provider actually exposes.
15. **Uncertain interpretation becomes review:** low-confidence OCR, sentence-boundary, annotation or narration decisions must be surfaced instead of silently guessed.
16. **Local intelligence is default:** semantic analysis must be able to run through a local LLM adapter; cloud AI is optional, disabled by default and never an architectural dependency.
17. **Structured AI only:** LLM outputs that influence production must conform to versioned schemas and be validated before use; free-form prose is not an executable decision.
18. **Book context precedes segment context:** book-level genre/tone/profile analysis is created first; segment analysis then receives book/chapter context rather than reasoning from isolated sentences.
19. **Human approval controls expensive/long-running synthesis:** the operator must approve both text interpretation and representative audio samples before full-book synthesis.
20. **No mandatory paid provider:** V1 production acceptance requires a usable all-local path for analysis and TTS, while external providers remain optional adapters.
21. **Executable evidence before scale:** architecture work is not considered validated until a small vertical slice can be run and inspected end-to-end.

## Professional narration requirements

These requirements are mandatory for a production-quality audiobook and are not optional polish.

### 1. Three text representations

Every source span that can become spoken audio must preserve:

```text
ORIGINAL_TEXT
    |
    v
NORMALIZED_TEXT
    |
    v
SPOKEN_TEXT
```

Example:

```text
original_text:
"3kg, xem chú thích (1)."

normalized_text:
"3 kg, xem chú thích (1)."

spoken_text:
"ba ki-lô-gam. Xem chú thích số một."
```

Rules:

- `original_text` is immutable evidence.
- `normalized_text` may repair Unicode, spacing, punctuation and structural defects.
- `spoken_text` may express numbers, units, abbreviations and speech-specific phrasing.
- normalization/spoken rendering must not summarize, omit, invent or change the semantic meaning of the work.

### 2. Punctuation and sentence reconstruction

SAYDI must not assume source punctuation is correct.

The text engine must be able to:

- detect missing/duplicated/malformed punctuation;
- infer likely sentence boundaries from syntax and semantics;
- split excessively long sentences for natural narration;
- preserve ellipsis, interruption and rhetorical pauses when meaningful;
- assign confidence to repairs;
- route low-confidence changes to review.

Example:

```text
source:
"Anh nhìn cô không nói gì rồi bước đi cô vẫn đứng đó"

spoken interpretation:
"Anh nhìn cô, không nói gì, rồi bước đi. Cô vẫn đứng đó."
```

This change is derived narration text only; the source remains unchanged.

### 3. Annotation / footnote policy

Annotations must be classified into at least:

- `FOOTNOTE`
- `ENDNOTE`
- `CITATION`
- `PAGE_REFERENCE`
- `PARENTHETICAL`
- `EDITOR_NOTE`
- `TRANSLATOR_NOTE`
- `SIDEBAR`

Each annotation receives an explicit policy:

- `READ_INLINE`
- `READ_AT_CHAPTER_END`
- `SKIP_BY_APPROVED_POLICY`
- `SPEECH_NORMALIZE`
- `REQUIRE_REVIEW`

No annotation may be silently deleted merely because it is inconvenient for TTS.

### 4. Narrative interpretation

Before TTS, SAYDI must identify narration context such as:

- narrator prose;
- dialogue;
- quoted material;
- speaker turn where reasonably inferable;
- rhetorical question/exclamation;
- interruption/hesitation;
- reflective/internal passage;
- headings and chapter openings.

V1 does not require automatic multi-voice casting. The interpretation layer must still preserve speaker/context metadata so a single narrator can vary delivery and later versions can add multiple voices without reparsing the book.

### 5. Prosody plan

Each spoken segment may carry provider-neutral directives such as:

```text
emotion
emotion_intensity
pace
energy
pause_before_ms
pause_after_ms
emphasis[]
speaker_role
confidence
```

Initial semantic emotion vocabulary:

- `neutral`
- `warm`
- `joyful`
- `sad`
- `tense`
- `urgent`
- `reflective`
- `mysterious`
- `authoritative`

This is SAYDI metadata, not a claim that SaydiVoice exposes these emotions directly.

The SaydiVoice adapter may translate these semantics into verified controls such as:

- voice selection;
- stability/expression;
- speed;
- pause enable/profile;
- segment boundary pauses.

Unsupported provider controls must never be fabricated.

### 6. Confidence and review gates

Interpretation layers must emit confidence/review state for uncertain cases.

At minimum:

- OCR confidence;
- sentence-boundary confidence;
- annotation-classification confidence;
- narration/prosody confidence where automatic interpretation materially changes delivery.

High-confidence deterministic corrections may proceed automatically.

Low-confidence or materially ambiguous cases enter a **REVIEW queue** so the operator reviews exceptions rather than manually proofreading the entire book.

### 7. PDF-first quality behavior

For PDF input:

```text
PDF
 -> classify text vs scan
 -> extract or OCR
 -> remove repeated page furniture
 -> reconstruct reading order
 -> detect chapters/blocks/annotations
 -> quality review exceptions
 -> canonical book
```

The system must never read recurring page numbers, headers, footers or watermark text merely because PDF extraction returned them.

## Intelligence, classification, and decision authority

SAYDI must not depend on an LLM for tasks that deterministic code can solve reliably.

The authority stack is:

```text
DETERMINISTIC RULES
        |
        v
AI ANALYSIS INTERFACE
        |
        +--> Local LLM (default)
        +--> optional cloud LLM
        |
        v
SCHEMA VALIDATION
        |
        v
DECISION ENGINE
        |
        +--> AUTO
        +--> AUTO + LOG
        +--> REVIEW
        |
        v
HUMAN APPROVAL for book-wide narration choices
```

Examples that should remain deterministic where practical:

- repeated header/footer/page-number removal;
- exact chapter numbering patterns;
- numbers/units/date normalization with known rules;
- stable IDs/hashes;
- completed-job/idempotency checks.

Examples where semantic AI may help:

- genre/subgenre classification;
- overall tone and target narration style;
- ambiguous sentence-boundary repair;
- dialogue/context interpretation;
- annotation classification when layout/rules are insufficient;
- implied emotion, pace, energy and emphasis;
- representative sample selection.

### Book Intelligence

Before per-segment narration planning, SAYDI creates a structured `BOOK_PROFILE` from metadata, table of contents, chapter structure and representative passages.

Conceptual output:

```text
genre
subgenre
tone
audience
dialogue_density
technical_density
emotion_range
recommended_narration_profiles[]
confidence
evidence_refs[]
```

The system must not require the entire book to fit into one LLM prompt. It should use hierarchical context and summaries derived from canonical source spans.

### Segment Intelligence

Each segment analysis receives at least:

- active `BOOK_PROFILE`;
- chapter/section context;
- preceding/following context where available;
- current `spoken_text`;
- annotation/speaker metadata.

Conceptual structured output:

```text
segment_type
speaker_role
emotion
emotion_intensity
pace
energy
pause_before_ms
pause_after_ms
emphasis[]
confidence
review_required
```

### Cloud AI privacy boundary

ChatGPT or another cloud model may be used only when explicitly enabled by the operator.

Default production behavior is local. If cloud analysis is enabled, the UI must make the data boundary clear before manuscript text is transmitted.

## Voice casting and approval workflow

SAYDI separates **text correctness** from **voice suitability**.

The workflow is:

```text
BOOK_PROFILE
   |
   v
genre/style classification
   |
   v
candidate narration profiles
   |
   v
representative sample set (normally 3-5 passages)
   |
   v
TEXT PREVIEW GATE
   |
   v
generate real audio samples
   |
   v
AUDIO SAMPLE GATE
   |
   v
APPROVED NARRATION FINGERPRINT
   |
   v
FULL SYNTHESIS
```

Representative passages should cover the book's actual difficulty, not only the first paragraph. Depending on genre they may include:

- ordinary narrator prose;
- difficult names/terms/numbers;
- dialogue or emotional passage for fiction;
- explanatory/list/data passage for business/non-fiction;
- punctuation/annotation edge cases.

The narration fingerprint must include all production-relevant settings, including provider/model, voice, style, speed, expression/prosody policy, pause policy and pronunciation-lexicon version.

Any material fingerprint change invalidates the audio approval and requires a new sample review.

## Executable-first development strategy

The project will be implemented as **runnable vertical slices**, not as a long architecture-only build.

Before scaling to a full book, SAYDI must provide a small operator-visible runner that proves the real workflow.

The first executable slice may use a small synthetic/public-domain text-based PDF and a CLI instead of a desktop UI, but it must produce durable artifacts that the operator can inspect.

Minimum practical slice:

```text
small PDF
 -> extract text
 -> detect at least one chapter/block structure
 -> original/normalized/spoken text
 -> simple BOOK_PROFILE
 -> choose representative passage(s)
 -> produce text preview
 -> build narration fingerprint
 -> generate at least one real audio sample through an available VoiceProvider
 -> record approval/rejection
 -> persist run artifacts/logs
```

The first run is for workflow learning and contract validation, not a claim of production audiobook quality.

Every subsequent task must keep this runner working and expand it rather than building isolated modules that cannot be exercised end-to-end.

## Runtime authority

Book/job state is persisted locally. The initial implementation target is SQLite plus immutable/intermediate files under the local runtime root.

Recommended runtime root:

```text
%LOCALAPPDATA%/SAYDI/Audiobook/
  config/
  browser_profile/
  library/
    <book_id>/
      source/
      manifests/
      segments/
      audio/raw/
      audio/processed/
      chapters/
      exports/
      qa/
      logs/
  cache/
  diagnostics/
```

Runtime data never belongs in Git.

## Book job lifecycle

```text
IMPORTED
 -> NORMALIZED
 -> PLANNED
 -> SAMPLE_APPROVED
 -> SYNTHESIZING
 -> ASSEMBLING
 -> QA
 -> READY
 -> EXPORTED
```

Exception states:

- `ACTION_REQUIRED`
- `RETRYABLE_FAILURE`
- `FATAL_FAILURE`
- `CANCELLED`

## Quality gates

A production export requires all applicable gates:

- source structure validated;
- for PDF: text/scan classification completed and OCR/extraction quality exceptions resolved;
- no unresolved repeated header/footer/page-number artifacts in spoken content;
- three-layer text lineage is complete for every spoken segment;
- punctuation/sentence reconstruction review items are resolved;
- annotation policy is explicit for every detected annotation;
- narration/prosody review items above configured uncertainty threshold are resolved;
- every canonical segment accounted for exactly once;
- no unresolved missing/duplicate audio;
- no failed segment jobs;
- duration and silence checks within configured limits;
- clipping/decoding checks pass;
- text-to-audio verification has no unresolved material mismatch;
- chapter ordering and metadata validated;
- export artifact opens successfully with FFprobe or the relevant container validator;
- QA report is persisted with the export.

## Current authoritative status

**Architecture generation:** SAYDI-AUDIOBOOK-V1.3  
**Current phase:** SAYDI-002 executable vertical slice implementation.  
**SaydiVoice discovery:** RETIRED / historical; current active narrator path is VieNeu on H4.  
**Audiobook production implementation:** STARTED. The first core runner now has provider-neutral contracts, rules analysis, local Ollama adapter boundary, narration fingerprint, representative sample selection, text approval, local prototype voice provider, audio approval state and duplicate-operation guard.

## Authoritative task queue

- **SAYDI-001 — Audiobook architecture + single Source of Truth:** DONE.
- **SAYDI-002 — Executable vertical slice + provider/AI contracts:** NEXT.
- **SAYDI-003 — PDF-first book ingest + canonical manifest:** classify text/scanned PDF, extract/OCR, reconstruct reading order, remove repeated page furniture, detect chapters/blocks, preserve provenance and expose OCR exceptions.
- **SAYDI-004 — Text interpretation foundation:** implement `original_text -> normalized_text -> spoken_text`, punctuation/sentence reconstruction, number/date/unit/abbreviation speech normalization, annotation parser/policy, stable segmentation and confidence/review outputs.
- **SAYDI-005 — Professional narration director:** implement hierarchical book/chapter/scene/segment intelligence, contextual semantics, dialogue/speaker-role inference, semantic emotion + intensity, emotional-arc smoothing, prosody/pause/emphasis/pace delivery directives, pronunciation lexicon, narration fingerprint and representative sample approval.
- **SAYDI-006 — Segment synthesis orchestration + resume/idempotency.**
- **SAYDI-007 — Audio processing, chapter assembly and mastering.**
- **SAYDI-008 — Alignment/acoustic QA + isolated repair loop.**
- **SAYDI-009 — M4B/chapter-MP3 export + metadata.**
- **SAYDI-010 — Windows desktop control center.**
- **SAYDI-011 — Clean-machine installer + end-to-end production acceptance.**

Only one task should be treated as NEXT at a time.

## Immediate next task

**SAYDI-002 — Executable vertical slice + provider/AI contracts.**

It must verify a runnable local VieNeu vertical slice, provider-neutral AI/Voice contracts, the existing Owner-approved narrator fingerprint, idempotent synthesis/checkpoint and a bounded audible sample/QC flow. No SaydiVoice access is required.

Required SAYDI-002 evidence:

- runnable CLI/operator runner; **IMPLEMENTED OFFLINE FOUNDATION**
- local offline compile/unit/smoke evidence; **PASS (5 unit tests + prepare/approve smoke in development environment)**
- Windows-local audible sample workflow; **FIELD-RUN PASS — GitHub Actions run 36745274726**
- versioned structured contracts for AI analysis and VoiceProvider;
- deterministic fallback behavior when no LLM is available;
- local-LLM adapter boundary (model may be selected/benchmarked during implementation);
- local VieNeu v3 Turbo/ONNX adapter and approved narrator reference with auditable fingerprint;
- sample narration fingerprint;
- text-preview and audio-approval state;
- tests for idempotency/privacy/schema validation;
- one bounded real audible sample run after offline gates pass. **PASS — local Windows SAPI WAV produced on trusted runner in run 36745274726**

### 2026-10-11 — Active SAYDI-002 closure reinterpretation

The older provider-specific completion terms are historical and non-executable. Do not substitute retired SaydiVoice auth/sample evidence for local VieNeu evidence; do not mark `SAYDI-002 DONE` prematurely. The new subordinate VieNeu tasks, explicitly approved by the Owner's provider-retirement directive, are maintained in this single canonical SOT, with `SAYDI002-VN-001` as the next read-only task. Only an exact-main, gate-verified handoff can advance the main task to `SAYDI-003`.

## Completion definition for the project

SAYDI Audiobook V1 is production-ready when a clean supported Windows machine can:

1. complete local VieNeu environment, resource and approved narrator preflight on H4 without paid-provider login;
2. import a supported book;
3. validate/adjust chapter structure, OCR exceptions, annotations, punctuation interpretation and pronunciation;
4. approve a narrator sample that demonstrates the active prosody/emotion policy;
5. synthesize a complete long-form book with interruption/resume;
6. detect and isolate material QA problems;
7. repair only affected segments;
8. assemble and master chapters;
9. export a validated M4B and/or chapter MP3 package;
10. produce a sanitized diagnostic bundle when recovery is not automatic.


## Implementation ordering constraint

A full-book production acceptance is forbidden until `SAYDI-003`, `SAYDI-004`, and `SAYDI-005` satisfy their gates.

`SAYDI-002` remains the immediate NEXT task because the project must become runnable before the deeper modules are built. It must establish provider-neutral AI/Voice boundaries and a bounded audible sample workflow. Punctuation repair, annotation policy, book intelligence, emotion and prosody remain upstream audiobook-domain logic rather than hard-wired into any TTS-provider/browser automation.


## Owner decision 2026-10-09 — SAYDI operations move into one MAGASIN Control Center (future cutover policy)

**Newer Owner directive, authoritative scope:** The Owner will retire all separately operated robot **control interfaces** and manage SAYDI, Supervisor and SAPO through one MAGASIN Control Center on `DESKTOP-H4A16IL` (currently `http://127.0.0.1:8781`). The **SAYDI narration/render/QC engine, source-of-truth, book metadata, audio, queues, checkpoints, profiles and private credentials remain their own separately recoverable backend**, not merged into the Supervisor repository or deleted. The unified UI must expose SAYDI status, book/chapter progress, render/QC/R2 exceptions, RAM budgets, audio playback/Owner listening review and genuine Owner-confirmed START/STOP, without requiring the Owner to launch `C:\SAYDI\control\media_control.py` in a second window. That legacy read-only HTTP source may remain an internal data adapter during migration, but cannot itself authorize a production START/STOP.

**Boot/Owner policy precedence:** This 2026-10-09 directive **supersedes the `default-on after Windows boot` and `worker starts automatically after reboot` parts** of the 2026-10-03 production directive **as the target post-cutover policy**. After the per-robot cutover has been independently verified, SAYDI MUST be **OFF after every Windows reboot** until the Owner explicitly starts SAYDI in the unified Control Center; STOP must prevent Windows Scheduler/watchdog/recovery from reviving SAYDI. While Owner ON, the previously approved routine VieNeu render/automatic QC, checkpoint restart, audio assembly, targeted safe repair and bounded 24/7 progress *remain automatic* without individual clicks. Offline after STOP still permits a lightweight read-only status observer and local UI.

**Transition is not complete:** The current Chapter 2 V5 `SAYDI V5 CH02 QC Guardian` Windows task and `RUN_CH02_V5_QC_SAFE.ps1` remain real legacy mechanisms; related V4 watchdog/resume tasks require inventory. A verified Media Control read-only status on 2026-10-09 showed Chapter 2 V5 checkpoint `PAUSED_RESOURCE` / `QC_NEEDS_FREE_RAM`, a minimum **2.3 GiB free RAM** for its safe QC resume, and no running heavy worker. The approved MP3 and 640 existing chunk checkpoints are valuable output: **do not reset, regenerate, double-QC, delete, corrupt or declare FINAL** by attempting a Control Center START before verifying the exact checkpoint/worker ownership and resource safety. **This SOT edit does not apply changes to Windows startup entries**; until a reviewed and tested cutover is actually installed, legacy start behavior still exists and does not count as compliance with new OFF-after-reboot policy.

**Required SAYDI migration gates:** 
1. Capture original installed script hashes, scheduled task action/trigger/state, active PID/mutex, RAM/D:, V5 Chapter 2 checkpoint, current SOT task, and an independently verified Owner Stop/Start / session identity witness.
2. Add a SAYDI-specific local adapter behind Control Center with a durable **Owner generation** / STOP latch and exact named-worker scope. Explicit Owner START accepts a safe queued/chapter job (not a hard-coded blind script); refuse if insufficient RAM, a mutex/another media worker is active, checkpoint is ambiguous or Owner approval/audio reference is missing. Do not fabricate RUNNING before heartbeat.
3. Explicit Owner STOP persists through reboot, prevents scheduled restart, and safely drains a running stage to its existing durable checkpoint. No force killing a VieNeu/FFmpeg/QC child without a separately approved safety policy and actual task evidence. Wrong Origin/CSRF/actor, repeat START/STOP, start with stale status, low RAM, and corrupt checkpoint must all be rejected or idempotent.
4. After project SOT approval, hosted tests and an isolated local dry-run pass, perform **one Owner-approved, hash-pinned backup/stage/apply**; preserve scheduled task definitions for rollback but disable only the conflicting legacy automatic execution triggers. Verify **OFF after reboot** and STOP/START of SAYDI independently of Supervisor/SAPO and Owner-selected 24/7 continuation while ON.
5. Only when the unified Control Center shows the complete live SAYDI operational view and a verified owner lifecycle may separate SAYDI Control **windows/shortcuts** be retired. Never retire its backend/status API, sources, queues or audio merely to achieve one-window UX.

**Authority and status:** The Supervisor project SOT at `magasincoffee/magasin-supervisor/SOURCE_OF_TRUTH.md` holds only the **shared Control Center control-plane/cutover** gates; this SAYDI SOT remains sole authority for SAYDI book/audio task readiness and acceptance. This decision is policy/implementation direction, **NOT proof that SAYDI START/STOP has already been installed**; `SAYDI-002` and downstream book production gates keep their existing statuses. The current Control Center's disabled SAYDI START/STOP buttons are intentional safety gates, not evidence of a functioning actuator. Do not change current service/task settings from this documentation merge alone.

## Owner production directive — default local audiobook QC (2026-10-03)

This directive is authoritative for the active local audiobook production path.

### Default local runtime

The default production narrator path is now:

- local machine: `DESKTOP-H4A16IL`;
- engine: VieNeu v3 Turbo / ONNX;
- approved voice: `SAYDI Nam Mien Nam`;
- durable queue/checkpoints: Supabase-backed TTS book/chapter/chunk state;
- Windows boot recovery: SAYDI worker starts automatically and resumes queued/in-progress work;
- output unit: one mastered MP3 per chapter, with chunk WAVs treated as intermediate artifacts.

The local worker path is **default-on**. The Owner does not need to request VieNeu startup, queue polling, checkpoint resume, chapter assembly, or ordinary QC for every book.

### Invisible QC is mandatory and default-on

Production audio must carry technical traceability that is inaudible to the listener. Do not insert audible beeps, spoken IDs, tones, or other markers into the audiobook.

Every chapter/segment/chunk must remain traceable through stable metadata sufficient to identify:

- book;
- chapter;
- chunk/segment;
- source text span;
- generated artifact;
- chapter timecode after assembly;
- QA status and findings.

After each chapter is assembled, the default local pipeline must automatically run a QC pass before the chapter is considered final.

Minimum QC classes:

1. **Structural/coverage QC** — missing, duplicate, out-of-order or unexpectedly short/long segments.
2. **Acoustic QC** — decode failure, near-zero audio, clipping/peak anomaly, excessive silence, discontinuity at joins, and inconsistent format/loudness.
3. **Text/audio verification** — ASR/forced-alignment comparison when the local verification module is available, with mismatch confidence and exact segment/timecode routing.

QC findings are recorded as metadata only and must not alter listener audio.

### Owner experience rule

The Owner's normal role is to listen for enjoyment/acceptance, not to manually hunt errors.

The system must:

- automatically mark suspicious locations;
- report exact chapter + segment/chunk + timecode;
- regenerate only the affected segment when a repair is safe and approved;
- rebuild only dependent chapter artifacts;
- preserve unaffected accepted audio.

Routine local QC runs automatically. Owner approval is required only when:

- source text interpretation is ambiguous;
- repair would change spoken content/meaning;
- a voice/narration fingerprint changes materially;
- confidence is below the configured automatic-repair threshold.

### Current implementation boundary

Already field-validated on `DESKTOP-H4A16IL`:

- VieNeu v3 Turbo local synthesis;
- `SAYDI Nam Mien Nam` voice;
- automatic queue polling;
- per-chunk checkpoint/resume;
- restart-safe Windows boot recovery;
- FFmpeg chapter assembly;
- book/chapter/chunk progress state;
- invisible QC metadata/event storage.

The full local ASR/forced-alignment verification pass is now part of the **mandatory default architecture** but is not yet field-validated on the active worker. It must be implemented and accepted before claiming fully autonomous semantic audio QA.


## Owner listening verdict — narration preprocessing is mandatory (2026-10-04)

The first full local VieNeu render is now classified as a **DRAFT BASELINE**, not a final audiobook.

Owner listening feedback from Chapter 1 established that technically correct TTS is insufficient. Production acceptance now requires a mandatory **Narration Preprocess** stage before synthesis.

Default pre-TTS behavior must:

1. analyze the complete source book before chunk generation;
2. remove non-spoken PDF artifacts such as page numbers, repeated headers/footers, extraction debris and meaningless layout residue;
3. reconstruct sentences and paragraphs from PDF line wrapping;
4. detect chapters, section headings, subheadings, lists, quotations, dialogue and transitions;
5. preserve source meaning while producing a derived `spoken_text`;
6. assign provider-neutral narration metadata per semantic block;
7. create explicit title/heading delivery with stronger prominence and longer pauses before/after;
8. use paragraph/semantic boundaries for segmentation rather than character-count boundaries alone;
9. preserve low-confidence edits as REVIEW rather than silently guessing.

### Heading delivery policy

Headings are semantic audio landmarks.

Minimum default behavior:

- chapter title is rendered as its own segment;
- section/subsection headings are rendered as separate segments;
- heading pace is slightly slower than body narration where supported;
- heading energy/emphasis is elevated where supported;
- insert a deliberate pause before and after headings;
- do not merge the first body sentence into the heading chunk;
- unsupported emotional/prosody controls must be approximated only through verified provider behavior such as segmentation, punctuation and pause policy; never fabricate provider controls.

### Narration-state classification

Every semantic block should carry a provider-neutral role such as:

```text
CHAPTER_TITLE
SECTION_HEADING
NARRATOR_BODY
DIALOGUE
QUOTE
LIST_ITEM
REFLECTIVE
EXPLANATORY
EMPHATIC
TRANSITION
ANNOTATION
```

and a narration plan such as:

```text
pace
energy
pause_before_ms
pause_after_ms
emphasis
emotion
confidence
review_required
```

### Current-book disposition

The current "Doanh Nghiệp Tự Hành" render remains useful for infrastructure/QC evidence, but must not be labeled FINAL. A production rerender should be based on the new narration-preprocessed manifest, beginning with a Chapter 1 approval sample before replacing the whole book.

## Owner architecture lock — hierarchical semantic narration (2026-10-04)

The Owner has approved the target architecture for determining tone, meaning, emotion and delivery from a supplied book.

This is now a product invariant:

```text
BOOK
 -> BOOK INTELLIGENCE
 -> CHAPTER INTELLIGENCE
 -> SCENE INTELLIGENCE
 -> SEGMENT INTELLIGENCE
 -> EMOTIONAL ARC
 -> DELIVERY DIRECTIVE
 -> TTS
 -> PRONUNCIATION QC
 -> PROSODY/STYLE QC
 -> ACOUSTIC/JOIN QC
 -> PASS / bounded isolated repair / REVIEW
```

Mandatory interpretation behavior:

- analyze the complete canonical book hierarchically rather than treating one excerpt as sufficient book context;
- infer scene semantics and emotional state with context, not keyword matching;
- support emotion intensity and confidence, not only a single binary emotion label;
- distinguish narrator prose, dialogue and speaker/character role where reliably inferable;
- preserve narrator/character continuity across scenes;
- smooth emotional transitions across neighboring segments so delivery does not jump unnaturally;
- translate semantic intent into provider-neutral pace/energy/pause/emphasis/pronunciation directives;
- map only to controls actually supported by the active TTS provider;
- keep canonical source meaning immutable;
- route low-confidence semantic decisions to REVIEW;
- run pronunciation/prosody/acoustic QC after synthesis and repair only affected units with a bounded retry policy.

The durable implementation checklist is:

the consolidated V6 capability and acceptance matrix above

That matrix may grow whenever the Owner discovers a missing or improvable capability. It records implementation coverage only; authoritative task ordering remains in this Source of Truth.

The Owner's intended end-state is minimal-input operation: supply the legally usable book and optional narrator/style preference; SAYDI handles routine semantic narration planning, generation, QC and safe repair. Owner intervention should normally be limited to initial narration approval and genuine semantic/quality exceptions.

## Owner directive — SAYDI V6 narration quality production upgrade (2026-10-08)

**Decision:** Owner approves **V6 capability upgrade planning**, building on the existing local VieNeu V5 rather than rebuilding the robot. The complete normative implementation and acceptance specification is:

the consolidated V6 execution section above

This directive is **requirements approval, not implementation completion**. Do not claim V6 shipped, Chapter 1 FINAL, or full-book production passed without runnable code, QC results, field evidence and Owner listening acceptance.

### Newly locked requirements

1. Preserve the Owner's ~4-minute approved narration reference as the canonical *local* narrator/style anchor. The subjective ~90% Owner assessment is directional listening feedback, **not an automated PASS rate**; the remaining unclear words, Vietnamese tone errors, slurring and joins remain real acceptance concerns.
2. The standard flow is **editorial before render, verification after render, bounded isolated repair**. ChatGPT can supply schema-validated narration directives/biên soạn when Owner enables the cloud boundary; default local Director/robot handles all routine tasks. No manuscript upload or audio/reference file committed to GitHub.
3. Text correctness, source-vs-spoken equivalence, Vietnamese tone and word clarity, emotional/phrase continuity, acoustic joins and narrator-fingerprint consistency are distinct QC dimensions. Whisper alone cannot settle accent/diacritic listening defects. “Mỗi khi hè về” vs “mỗi khi he về” must be diagnosed using original/TTS text and audio evidence before changing text.
4. **Never use `atempo`, time stretching or pitch shifting to simulate human pacing.** Native VieNeu articulation is preserved; semantic punctuation, source-faithful phrasing, reference selection and natural inter-phrase pauses are the allowed initial levers. Changing approved voice/fingerprint requires a new sample acceptance gate.
5. Correct only affected segments with safe retry limit, SHA-matched candidate QC and unchanged-neighbor evidence; no endless renders, no automatic whole-book regeneration, no false `FINAL`.
6. DESKTOP-H4A16IL has approximately 8 GB RAM / 4 logical CPU threads. The active host requires resource preflight, child-process limits, no simultaneous heavy VieNeu+Whisper models, RAM safeguards, checkpoint/resume and watchdog phase accuracy. CPU 100% alone is not proof of hardware damage; thermal limits require real sensor evidence.
7. The Owner receives a **complete chapter MP3** and a small set of representative samples/timecoded true exceptions for listening—not an instruction to hunt defects individually.

### Integration into existing authoritative sequence

- `SAYDI-004`: structured source-safe editorial/text layering and segment context.
- `SAYDI-005`: Narration Director, approved sample fingerprint and pre-render direction.
- `SAYDI-006`: stable segment-addressed TTS, resource guard, idempotency/restart.
- `SAYDI-007`: native-speed assembly and acoustic joins.
- `SAYDI-008`: layered pronunciation/tone/prosody/acoustic QC plus bounded repair.
- `SAYDI-009/010`: chapter listening package / operator progress and exceptions.

Continue using the existing `SAYDI-ND` and `SAYDI-QC` subtracks; do not create an alternative top-level task queue. **`SAYDI-002` remains the current authoritative NEXT task** until its documented closure gates pass. Work items in the V6 plan are subordinate acceptance work packages only; robots may not skip SOT prerequisites or fabricate DONE.

### Latest local observation (not repo field acceptance)

On 2026-10-08, Chapter 1 V5 was rendered in 347 WAV segments. Initial QC flagged 120 basic REVIEW; a locally generated V5 R2 candidate package reduced basic ASR REVIEW to 115 after selecting 12 improved variants out of 35 targeted attempts. This does **not** establish audible Owner approval; Chapter 1 remains `REVIEW`, and V6 remains unimplemented. Intermediate WAVs, manuscript and listening files stay on the local host.
