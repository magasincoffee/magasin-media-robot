# SAYDI-002 Temporary Execution Source of Truth — VieNeu local only

**Last updated:** 2026-10-11  
**Current phase:** SAYDI-002 (NEXT at project level)  
**Authoritative parent:** [SOURCE_OF_TRUTH.md](./SOURCE_OF_TRUTH.md) on main.  
**Owner 2026-10-11 decision:** **RETIRE SAYDIVOICE COMPLETELY; USE LOCAL VIENEU EXCLUSIVELY** on DESKTOP-H4A16IL.

## Why this file was corrected

This temporary queue was originally written 2026-10-02 when the project still investigated a paid/quota-limited SaydiVoice provider. Since 2026-10-03 the actual production work has moved to **VieNeu v3 Turbo / ONNX on H4**, and by 2026-10-11 the Owner explicitly cancelled ALL further SaydiVoice work.

**Old subtask IDs SAYDI002-001..006 have historical value only.** Their full previous text, proof and blockers are retained in Git history; they are not executable or eligibility requirements. In particular:

- SAYDI002-001 original dedicated SaydiVoice Chrome auth on 4K7: **HISTORICAL / RETIRED** (previously DONE in old system).
- SAYDI002-002 old SaydiVoice adapter: **HISTORICAL / RETIRED** (previously DONE in old system).
- **SAYDI002-003** authenticated SaydiVoice preflight: **SUPERSEDED / CANCELLED**, not DONE, never retry.
- SAYDI002-004 one paid bounded SaydiVoice sample: **SUPERSEDED / CANCELLED**, no duplicate Generate.
- SAYDI002-005 narrator SG - Chí Đạt SaydiVoice voice-approval blocker: **SUPERSEDED / CANCELLED** by provider retirement; it is **NOT** the same as approving/changing the active VieNeu narrator.
- SAYDI002-006 old SaydiVoice-centered closing gate: **SUPERSEDED / CANCELLED**.

**DESKTOP-4K7IM13 is NOT needed.** No login to SaydiVoice, no quota-dependent provider call, no profile migration, no Chrome use, no generation, no external TTS artifact download. Historical credentials/profiles may be preserved untouched; do not delete these in this transition.

## Local VieNeu canonical baseline

- TTS provider: **VieNeu v3 Turbo / ONNX (LOCAL)**, running on **DESKTOP-H4A16IL**.
- Existing Owner-approved voice/reference: **SAYDI Nam Mien Nam**. Do not confuse this with the rejected/undecided legacy SaydiVoice SG - Chí Đạt sample.
- Existing book/chapter/chunk state and durable checkpoints: local + Supabase-based progress model; use verified receipts rather than replaying heavy workers.
- Ch04 G style: Owner **APPROVED HEADING AUDIO DESIGN**: original soft 2s instrumental before title, 160ms separation, ultra-low background only during title, never under ordinary narration. This is **NOT** a global human listening QC acceptance or FINAL permission.
- Existing Chapter 2 V5 guarded checkpoints: **640 protected chunks**, approved MP3; recent stage PAUSED_RESOURCE/QC_NEEDS_FREE_RAM, ≥2.3 GiB available RAM was a historical safety gate. Never reset/revoice/double-QC/delete them without exact checkpoint/worker ownership verification.
- Render/QC program is NOT yet proven to independently complete a new chapter with semantic preparation, local synthesis, bounded repairs, G mix, all-QC and Owner review; hosted unit tests/G media staging alone are insufficient.

## Execution rules

1. Read main Source of Truth first, then this temp file. If main has newer conflicting instructions, follow main.
2. Only execute the **one** currently authorized local VieNeu subtask from this file. Do not redirect to provider-specific legacy tasks.
3. Preserve all source text/audio/profile/checkpoint/Supabase metadata. Do not publish protected book/voice reference to public CI.
4. **No heavy VieNeu or Whisper start** during inventory or unit-test subtask. Running/starting heavy workers requires a valid Owner START / existing authorized phase plus resource preflight, 1-worker mutex, checkpoint ownership and no overlapping VieNeu+Whisper memory load.
5. No provider switch or changed voice fingerprint without separate legitimate Owner sample approval. Do not infer SG - Chí Đạt approval from G style acceptance.
6. Use local safe, synthetic source and test inputs for non-production QA, then field-verify real chapter bounded evidence when authorized. Treat repaired audio as REVIEW until meaningful audio QC and Owner listening exceptions are signed.
7. STOP/Control Center lifecycle follows main SOT: after qualified cutover the robot boots OFF and stays OFF until Owner START; do not modify legacy scheduled tasks without reviewed cutover. No forced restart of paused or protected legacy QC.
8. On block, create a sanitized and specific Blocker Register entry and continue only independent executable tasks. Never loop endlessly.
9. All source edits on a Draft PR are **unmerged work** until a verified main update and corresponding exact-main test/receipt.
10. Do not mark SAYDI-002 DONE until all *new* active VieNeu execution tasks and closure gate PASS; never use SaydiVoice historical proofs as substitutes.

## Active task queue — new IDs, no reassignment of old IDs

### SAYDI002-VN-001 — H4 read-only VieNeu inventory & freeze

**Status:** READY; NO HEAVY WORKER / NO PRODUCTION WRITE

Inspect only on DESKTOP-H4A16IL: installed VieNeu version/provider adapter and source SHA; current Control Center status/Owner latch; job queue state; Chapter 2 protected 640 checkpoint+worker ownership, Chapters 1/3/4 existing stage/voice SHA; relevant scheduled tasks; available RAM/disk; active render/QC process ownership; existing approved narrator/fingerprint and G staging receipts. Record *sanitized* paths, existence, hashes, gates and outstanding missing evidence on a Draft PR. No Chrome, SaydiVoice or 4K7 calls.

**Acceptance:** rechecked source/worker/checkpoint identity, no writes, no leaked private audio/text, durable metadata receipt and immediate next VieNeu task selection by evidence.

### SAYDI002-VN-002 — Freeze/qualify local VieNeu VoiceProvider contract and narrator fingerprint

**Status:** PENDING (after VN-001)

Verify/reconcile local VieNeu adapter, versioned request/result schema, narrator identity and approved reference SHA, exact text provenance, deterministic local analysis fallback, schema validation, no cloud dependencies and explicit unsupported controls. Run synthetic contract/security/idempotency tests; preserve all existing approved source audio. No live TTS required.

**Acceptance:** VieNeu local VoiceProvider/AI contracts, local fallback, normalized/spoken manifest lineage and fingerprint tests GREEN; no profile or private content in repo.

### SAYDI002-VN-003 — Verify bounded local sample from existing evidence or safe authorized pilot

**Status:** PENDING (after VN-002 and Owner/runtime gates)

Prefer read-only verification of an **already rendered, exact-hash** local VieNeu sample and historical Owner-approved narrator. Only render a *new, isolated*, legally usable sample after a valid Owner START and checkpoint/resource/mutex preflight. Never re-render accepted 640 Chapter 2 chunks or regenerate an approved chapter merely for CI.

**Acceptance:** one real local VieNeu sample with source/ref/voice/PCM/MP3 SHA, native onset and text/audio QC, true Owner narrator fingerprint approval and explicit REVIEW state; zero duplicate operations.

### SAYDI002-VN-004 — Integrate staging G + QC receipts into idempotent local REVIEW path

**Status:** PENDING (after VN-003; do not confuse G mixing with VieNeu generation)

Use the G staging mixer only as a reference while integrating the production workflow: original/normalized/spoken text, semantic headings, corrected chunking, first-word QC, joins, bounded isolated repair, heading-only G prelude+duck, no music under body, chapter MP3 REVIEW + reproducible QC receipt. Run synthetic and limited local dry-run gates without touching existing WAV/checkpoint.

**Acceptance:** exact voice WAV source identity, 100% expected heading IDs and 0 body leaks, no clipping or masked first phonemes, material join/word defects remain REVIEW, idempotent state transitions, no protected asset writes.

### SAYDI002-VN-005 — Safe SAYDI-002 closure / handoff

**Status:** PENDING (after VN-001..VN-004)

Confirm runnable local VieNeu vertical slice, provider-neutral AI and Voice contracts, local analysis fallback, voice/text/audio approvals, privacy/duplicate guards, exact-head CI, H4 sample field evidence, G staging/QC readiness; report remaining downstream V6 quality gaps to SAYDI-003..011, not invented PASS.

**Acceptance:** only then main SOT `SAYDI-002 = DONE`, `SAYDI-003 = NEXT`; exact-main readback and removal/archive of this TEMP SOT when authorized. Do not close on planning alone.

## Open and historical blockers

There is **no current SaydiVoice blocker**. Any legacy SaydiVoice Chrome/auth/quota or SG - Chí Đạt verdict blocker is **CANCELLED / RETIRED** by the Owner's 2026-10-11 decision, not resolved by a successful test.

For active VieNeu tasks, update a new blocker using:

```text
BLOCKER_ID=<BLK-SAYDI002-VN-XXX>
TASK_ID=<SAYDI002-VN-...>
STATUS=OPEN
TYPE=<OWNER_ACTION|RESOURCE|ENVIRONMENT|DEPENDENCY|OTHER>
SUMMARY=<sanitized real boundary>
OWNER_ACTION=<minimum real action or NONE>
EVIDENCE=<timestamp/sha/log without secrets>
RESUME_WHEN=<verifiable condition>
```

Historic SaydiVoice blocker reports are preserved by prior Git commits, not destroyed as evidence.

## SAYDI002 — project-level completion gate

No SaydiVoice login/call/generation requirement remains. Local VieNeu can close SAYDI-002 only after VN-001..005 exact task evidence, a runnable provider-neutral local sample workflow, approved voice reference and preview approvals, deterministic local analysis, stable SHA/invalidation model, idempotency, resource protection, privacy QA and human exception review routing. **Never call routine VieNeu AUTO-QC complete solely because it passed structural/Whisper or media-decode checks**; full semantic/audio hearing QC is still a quality target.

## Robot control protocol

Use the existing MAGASIN task response contract but return the **current VieNeu-only** subtask; never return SAYDI002-003 as NEXT.

```text
MAGASIN_TASK_CONTROL_V1
STATUS=<READY|RUNNING|COMPLETE|BLOCKED|DONE>
TASK_ID=<current task ID or NONE>
NEXT_TASK_ID=<one current VN task ID or NONE>
CHECK_AFTER_SECONDS=<0-3600>
END_MAGASIN_TASK_CONTROL_V1
```

**Authoritative next executable subtask:** `SAYDI002-VN-001`  
**Project-level SOT next task:** `SAYDI-002`.
