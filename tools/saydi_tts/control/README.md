# SAYDI Media Control — local operator dashboard (field MVP)

**Scope:** a lightweight **read-only** operator Control panel for the active H4A16IL local SAYDI V5 runtime. This is an observable interim deliverable in the V6 roadmap, **not** a claim that authoritative `SAYDI-010` is DONE; task ordering remains in `00_PROJECT/SOURCE_OF_TRUTH.md`.

## Local operator experience

Open the desktop shortcut **SAYDI MEDIA CONTROL** or visit `http://127.0.0.1:8776/` **on DESKTOP-H4A16IL itself**.

The dashboard automatically refreshes every 5 seconds and displays:
- actual process activity vs completed/review/abnormal-stop states;
- per-chapter render, first-pass QC, targeted repair and selected improvements;
- remaining ASR review flags, clearly distinguished from confirmed listening defects;
- CPU/RAM utilization and worker/process presence;
- latest sanitized local run/recovery log excerpts;
- embedded MP3 playback with seek support for full Chapter 1, the first 5 minutes and the middle 5 minutes.

**Safety:** server binds ONLY to `127.0.0.1`. It does not invoke VieNeu, Whisper, remote APIs or Supabase, and has no write/action endpoint; `POST` returns 405. Audio routes are allowlisted and may serve only the three local review MP3 filenames. The dashboard contains no private manuscript content and does not report a false FINAL. Do not expose port 8776 to the Internet.

## Install and run on the local Windows host

Requirements: Windows, `C:\MAGASIN_MCP\.venv\Scripts\python.exe` with `psutil`, existing SAYDI runtime paths. The dashboard does **not** install any new heavy TTS or ASR packages.

1. Copy the five files from this directory into `C:\SAYDI\control`.
2. Run `INSTALL_MEDIA_CONTROL.ps1` in that directory. It verifies dependencies, sets an **HKCU-at-logon** start entry, creates the desktop shortcut and health-checks the localhost server. Use `-Open` to also open the dashboard.
3. Alternatively run `START_MEDIA_CONTROL.ps1` manually, or add `-StartOnly` to avoid opening a browser.

Actual field installation of the dashboard and shortcut on H4A16IL was confirmed, and the local service returned HTTP 200. This portable `INSTALL_MEDIA_CONTROL.ps1` is included for repeatability but **was not fully rerun after packaging** because a remote execution safety gate blocked that installer invocation; validate it before generalizing to other machines.

## Local tests

```powershell
& C:\MAGASIN_MCP\.venv\Scripts\python.exe C:\SAYDI\control\test_media_control.py
```

Field observations on DESKTOP-H4A16IL:
- two synthetic unit tests PASS, testing active-vs-review classification, HTTP read-only restriction and byte-range audio;
- real `/healthz`, `/` and `/api/status` returned HTTP 200;
- real `/audio/begin` returned HTTP 206 with a 1,024-byte partial response;
- arbitrary audio route returns 404; POST returns 405;
- JavaScript syntax verification via Node: PASS;
- listener bound to **127.0.0.1:8776**, not to all interfaces.

## Phase derivation & limitations

Actual process inspection is authoritative for `RUNNING`: `render_owner_approved_v5.py`, `qc_local_segments.py` and `repair_chapter1_owner_v5_r2.py`. Checkpoint JSON is used to label the active stage and completed last run; a completed REVIEW state with no process must show **CHỜ NGHE DUYỆT**, not `robot đang chạy` and not `robot crashed`.

Current data reader is tailored to Chapter 1 V5/R2 filenames. Future pipelines (video, other books, SAYDI V6 jobs) require a versioned job/telemetry contract and job registry rather than silently inferring state from a filename. Do not create misleading progress or fake ETA.

**Next milestone:** authenticated local command API for Start/Pause/Resume with durable job ID, safe process locks, queue status, bounded retries and rollback; this read-only MVP intentionally does not advertise inert or unsafe Start/Stop buttons.

## Private files and source

Only source, installer, tests and this guide belong in Git. Owner manuscript, reference WAV, generated MP3, raw ASR transcript, secrets and runtime logs remain on H4A16IL. The app is a bridge to the V6 Owner-approved requirements in `00_PROJECT/SAYDI_V6_NARRATION_QUALITY_EXECUTION_PLAN.md`.

## Chapter 2 V5 QC (resource-gated field workflow, 2026-10-09)

Owner ordered Chapter 2 QC with the same approved V5 narrator reference. **Do not use the V4 chapter-2 wavs/QC as V5 results.**

On DESKTOP-H4A16IL Chapter 2 has a verified UTF-8 canonical source, an older **640-segment V4** manifest and audio, but initially **no V5-rendered audio**. The existing host has approximately 8 GB RAM and 4 logical CPU threads. Field preflight on 2026-10-09 15:22 local time showed 0.61 GB RAM free (92.3% used), CPU 84%, and 2.08 GB left on C:. Heavy synthesis/QC was intentionally not started under that load.

Files:
- `tools/saydi_tts/narration/chapter2_v5_qc_guarded.py`: checkpointed, source-and-reference-fingerprint-safe V5 chapter-02 render -> assemble -> batched QC (40 clips). Exit safely when RAM/disk is inadequate; do not run simultaneous TTS and Whisper.
- `tools/saydi_tts/narration/test_chapter2_v5_qc_guarded.py`: three local synthetic tests (resource probe, atomic QUEUED_RESOURCE checkpoint, named mutex duplicate guard).
- `tools/saydi_tts/control/RUN_CH02_V5_QC_SAFE.ps1`: Task Scheduler entrypoint. Windows task **SAYDI V5 CH02 QC Guardian** runs it every 15 minutes with `IgnoreNew`, subject to session/account scheduling. The runner is idempotent and can resume after restart without rerendering accepted chunks.
- The Control dashboard shows a separate Chapter 2 status card. It **must** say `QUEUED_RESOURCE` with 0/640 rendered when blocked by RAM; it must not say `QC running` until that process really exists.

Local output: `D:\SAYDI\OWNER_APPROVED_NATURAL_V5\Chuong_02` (models/source remain on C, no book content in Git). A lightweight status mirror exists at `C:\SAYDI\output\OWNER_APPROVED_NATURAL_V5\CH02_V5_STATUS.json` for Media Control.

Safety gates: >= **2.3 GB** free RAM before loading a model, pause on < **0.70 GB** during VieNeu output, at least 3 GB free on D for render; Whisper is a separate <=2-thread subprocess run **after** TTS unload, in <=40-clip batches, and stops before prolonged critical memory exhaustion. CPU affinity 2 of 4 logical processors with below-normal priority. An unconfirmed QC/ASR estimate is not Owner listening acceptance. `REVIEW_READY` is not `FINAL`.

Observed field evidence: manifest for 640 V5 segments generated and token/source integrity checked; two wrapper invocations exited 0 with `QUEUED_RESOURCE`, RAM below 2.3 GB; Windows task created and explicitly tested (last result 0, next scheduled run confirmed). Three Chapter 2 test cases and two Control test cases PASS. **No V5 chapter-2 segments had been synthesized and no V5 QC had run at the time of initial installation.** Schedule will only advance when resource preflight passes. If the machine does not naturally regain 2.3 GB RAM, Owner should close unused memory-heavy apps/tabs rather than killing unknown work.

Do not mark any V6 milestone DONE due solely to installing the V5 guard; the authoritative SAYDI SOT task sequence remains unchanged.

