# SAYDI VieNeu — 8 GB H4 resource and sequential execution

**Owner decision: 2026-10-11 — KEEP 8 GB RAM on DESKTOP-H4A16IL.** Optimize the existing local VieNeu + Whisper workflow to run **one heavy model at a time**. No SaydiVoice. Keep the existing approved narrator SAYDI Nam Mien Nam and the G heading-music preset.

**State:** measured field baseline; read-only offline admission/check tools on Draft PR; **NOT installed as a production actuator**. The authoritative task remains SAYDI-002 / SAYDI002-VN-001 in the existing main SOT. No Owner START, service edits or new audio was performed.

## Actual H4 measurement at ~20:58–21:02 ICT on 2026-10-11

| Metric | Actual value |
|---|---|
| CPU | Intel Core i5-6300U; 2 cores, 4 logical threads |
| RAM | 2 × 4 GB DDR4 2400; Windows sees 7.88 GiB |
| Free RAM five samples across seconds | 2.19, 2.27, 2.17, 2.21, 2.33 GiB; **min=2.17 GiB** |
| RAM other single observations | 1.28 GiB and 2.29 GiB; do not admit from a single high sample |
| C: free | **1.29 GiB — CRITICAL SYSTEM DRIVE HEADROOM** |
| D: free | 56.39 GiB |
| Windows tasks | SAYDI Control Job Guardian Running; CH02 QC Guardian, V4 Resume and V4 Watchdog Disabled |
| Chapter 2 | 640 rendered + checked, REVIEW_READY, not FINAL; all checkpoints protected |
| Chapter 4 | 440 rendered + checked, REVIEW_READY, not FINAL |

### Existing H4 components — read-only hashes and guards

- C:\SAYDI\control\control_commands.py: SHA256 21A23231AA363B713A0AF19B1EAD6A1F04F773FDFFA5241CC223CA5D8571F3EB. Existing CPU cap=1, process-list exclusion, Windows mutex, RAM start floor=1.5 GiB. This floor does **not** satisfy protected Chapter 2 QC 2.3 GiB requirement.
- C:\SAYDI\narration_director_v1\render_owner_approved_v5.py: SHA256 CE563C15BB4CE86E04BE159BCA3C03B69FFB6D5F159889CB966D18CF34C65FEF. Native VieNeu load floor=1.9 GiB; unloads VieNeu before its ASR pass.
- C:\SAYDI\narration_director_v1\chapter_v5_job.py: SHA256 8E0E6E9FB53D193EF86803217C299C6236B991DD52F45F90E3D52CFDD45E9D17. Has a process-tree-aware external heavy worker check.
- These are **existing installed scripts**, not modified by this PR. Do not introduce a second guardian or duplicate worker.

### Real Chapter 4 throughput from local job.log

| Stage | Field window | Measured observation |
|---|---|---|
| VieNeu render | 2026-10-10 23:16:42 through 2026-10-11 00:25:12 | **440 chunks / 68.5 minutes = 6.42 chunks/minute**, including many RAM-triggered pauses |
| Whisper QC | 00:33:28 (40 chunks) through 01:34:34 (440 chunks) | 400 additional chunks / 61.1 minutes = **6.55 chunks/minute**; initial 440 QC approximately 67 minutes |
| QC results | 01:34:35 2026-10-11 | **264 PASS / 176 REVIEW**; not listener-quality acceptance or FINAL |

From first logged rendered chunk to initial QC completion: approximately **2h18m** wall-clock. This is **one historical 440-chunk workload**, not a promised per-chapter ETA; it excludes editorial fixes, rerender attempts, G music QA and Owner listening. Future ETA must be updated using actual throughput by stage and must stop counting while PAUSED_RESOURCE.

## Execution policy for the 8 GB H4 machine

1. Respect current Owner STOP/START rights and existing workflow/task authority. Read-only diagnostics do not constitute authenticated permission to START.
2. Probe at least five short-interval free RAM readings; use the **minimum**, not the max. Before new work verify model ownership, mutex, checkpoint state, free disk and existing current heavy worker.
3. **VieNeu stage only:** batch the remaining immutable segment IDs, use the existing checkpoint and 1 CPU thread. Do not load Whisper during this phase.
4. **Barrier:** unload VieNeu, confirm no model process/lock remains, persist hashes and progress. Unknown ownership → HOLD, not QC START.
5. **Whisper QC only:** process bounded batches, write SHA/timecode-based findings and preserve all previously accepted WAV. Do not load VieNeu while Whisper remains resident. Unload Whisper before rerender.
6. **Repair loop:** queue safe isolated defects, run VieNeu replacement only after ASR completely exits, then rerun ASR only on changed chunks and affected neighbors. Bounded retries and no duplicate work.
7. **Lightweight assembly and G:** only after heavy workers are absent, rebuild affected joins and apply G at manifest-authorized headings, never under body narration. Run postmix acoustic and source-coverage QC and export REVIEW only.
8. **Resource pause:** return PAUSED_RESOURCE/QUEUED_RESOURCE with exact reason. No busy retry, no model overlap, no forced Windows process termination and no scheduler-trigger changes without a separate, approved cutover.

### Conservative proposed trial thresholds (not live acceptance yet)

- Existing local VieNeu threshold 1.9 GiB and Chapter 2 QC protected threshold 2.3 GiB are **field code/history**, not universal physical performance guarantees.
- Trial preflight proposes **2.1 GiB minimum for VieNeu, 2.5 GiB minimum for Whisper**, based on lowest of five samples to allow roughly 0.2 GiB headroom above prior stage limits.
- Trial C: headroom **>=2 GiB** and D: **>=10 GiB** before a heavy model; values are conservative safety proposals, NOT operating-system specifications. C: currently **fails** this proposal. Even with SAYDI disposable TMP/cache relocated to D: after validated isolated testing, Windows still needs adequate C: free space.
- Do not lower the protected 2.3 GiB Ch02 QC threshold merely to bypass PAUSED_RESOURCE. No automatic relocation/deletion or global TEMP changes. Confirm exact disk consumers first and require a reversible staging-specific configuration.
- H4 requires **safe sequential phases**, not multiple independent robot daemons. Use current Control job mutex/generation identity and protect STOP through reboot after the qualified Control Center cutover.

## Implementation on this PR — no production side effects

- tools/saydi_tts/qc/INSPECT_VN_8GB_H4_READONLY.ps1 collects sanitized H4 RAM, C/D capacity and possible heavy worker classes, without script arguments, secrets or source excerpts. Auth/latch/worker ownership are deliberately UNKNOWN.
- tools/saydi_tts/qc/vn_8gb_resource_gate.py computes a fail-closed TTS or ASR admission analysis from the snapshot, rejects missing Owner STOP/identity and checkpoint/mutex proofs, and always reports approved_to_start=false and approved_to_dispatch=false even if resource_possible.
- tools/saydi_tts/qc/test_vn_8gb_resource_gate.py contains synthetic no-dispatch, insufficient-RAM, low-disk, wrong-host, unknown-worker, concurrent-model and STOP cases.
- .github/workflows/saydi-vn-8gb-readonly-checks.yml: Windows hosted offline compile, PowerShell parsing and unit tests, no H4 model invocation.

## Completion and next stage

To close VN-001, finish **read-only** inspection of exact model/reference/checkpoint hashes, PID/worker ownership, true current Control Owner STOP witness, Windows C drive consumers and irreversible action risks; keep a sanitized evidence receipt. H4 dry-run of the five-sample CLI and exact-head hosted CI must PASS. Then continue VN-002 local VieNeu adapter/fingerprint work in official SOT order.

A resource status of ELIGIBLE_FOR_SEPARATE_AUTHORIZED_CHECK means **only capacity appears suitable**. It never grants permission to dispatch TTS, QC or Supabase work. Integration into installed C:\SAYDI\control\control_commands.py, actual START/STOP, GPU/model changes, cache relocation and new render remain deferred to a separately gated and Owner-authorized phase.
