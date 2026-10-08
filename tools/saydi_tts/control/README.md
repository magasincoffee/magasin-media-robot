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

