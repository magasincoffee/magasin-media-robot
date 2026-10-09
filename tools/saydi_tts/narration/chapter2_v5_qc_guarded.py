# -*- coding: utf-8 -*-
"""SAYDI V5 chapter-02: idempotent, resource-gated render -> QC -> REVIEW.

The audiobook source and audio are never uploaded to GitHub.
Runs at most one expensive operation on this 8GB host, keeps all checkpoints on D.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "2"
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

ROOT = Path(r"C:\SAYDI")
V5_MODULE = ROOT / "narration_director_v1" / "render_owner_approved_v5.py"
WORK = Path(r"D:\SAYDI\OWNER_APPROVED_NATURAL_V5\Chuong_02")
CHUNKS = WORK / "chunks"
QC_BATCHES = WORK / "qc_batches"
STATUS_PATH = WORK / "job_status.json"
POINTER = ROOT / "output" / "OWNER_APPROVED_NATURAL_V5" / "CH02_V5_STATUS.json"
RUN_LOG = WORK / "job.log"
MIN_START_RAM_GB = 2.3
MIN_RUN_RAM_GB = 0.70
MIN_DISK_GB = 3.0
CHAPTER = 2
QC_BATCH_SIZE = 40
WIN_MUTEX = r"Local\SAYDI_OWNER_V5_CH02_EXCLUSIVE"
V5_PY = ROOT / "VieNeu-TTS" / ".venv" / "Scripts" / "python.exe"
QC_PY = ROOT / "qc2" / ".venv" / "Scripts" / "python.exe"
QC_SCRIPT = ROOT / "narration_director_v1" / "qc_local_segments.py"

def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

def atomic_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".pending")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def log(message: str):
    WORK.mkdir(parents=True, exist_ok=True)
    s = f"[{now()}] [V5-CH02] {message}"
    print(s, flush=True)
    with RUN_LOG.open("a", encoding="utf-8") as out:
        out.write(s + "\n")

def free_ram_gb() -> float:
    # No psutil dependency: production VieNeu venv does not include it.
    class Memory(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                    ("total", ctypes.c_ulonglong), ("available", ctypes.c_ulonglong),
                    ("total_page", ctypes.c_ulonglong), ("available_page", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong), ("available_virtual", ctypes.c_ulonglong),
                    ("extended", ctypes.c_ulonglong)]
    mem = Memory()
    mem.length = ctypes.sizeof(mem)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
        raise RuntimeError("MEMORY_PROBE_FAILED")
    return mem.available / (1024 ** 3)

def free_disk_gb() -> float:
    return shutil.disk_usage(str(WORK.anchor)).free / (1024**3)

def status(phase: str, **fields):
    old = {}
    try:
        old = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    data = {
        **old,
        "schema": "saydi-v5-chapter-job-1",
        "profile": "OWNER_SAMPLE_20261008_NATIVE_TEMPO",
        "chapter": CHAPTER,
        "stage": phase,
        "updated": now(),
        "output_root": str(WORK),
        "final": False,
        "owner_approved": False,
        **fields,
    }
    atomic_json(STATUS_PATH, data)
    atomic_json(POINTER, data)
    return data

def lock():
    # A named Windows mutex ensures Task Scheduler cannot run duplicate expensive jobs.
    kernel = ctypes.windll.kernel32
    kernel.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
    kernel.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel.CreateMutexW(None, True, WIN_MUTEX)
    if not handle:
        raise RuntimeError("MUTEX_CREATION_FAILED")
    if kernel.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        kernel.CloseHandle(ctypes.c_void_p(handle))
        return None
    return handle

def unlock(handle):
    kernel = ctypes.windll.kernel32
    kernel.ReleaseMutex(ctypes.c_void_p(handle))
    kernel.CloseHandle(ctypes.c_void_p(handle))

def cap_cpu():
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetProcessAffinityMask.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
    kernel.SetPriorityClass.argtypes = (ctypes.c_void_p, ctypes.c_uint)
    handle = kernel.GetCurrentProcess()
    if not kernel.SetProcessAffinityMask(handle, 0x5):
        raise RuntimeError("COULD_NOT_LIMIT_CPU")
    kernel.SetPriorityClass(handle, 0x00004000)  # BelowNormal

def active_heavy_jobs():
    # Short, read-only Windows process inventory; no model runtime imported.
    command = (
        "$ErrorActionPreference='SilentlyContinue';"
        "Get-CimInstance Win32_Process | Where-Object {"
        "$_.Name -eq 'python.exe' -and $_.CommandLine -match "
        "'render_owner_approved_v5|qc_local_segments|repair_chapter1_owner_v5_r2|"
        "render_business_natural_v4' } |"
        "Select-Object -ExpandProperty ProcessId"
    )
    run = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                         capture_output=True, text=True, timeout=15, check=False)
    return [{"pid": int(line.strip())} for line in run.stdout.splitlines()
            if line.strip().isdigit()]

def load_v5():
    spec = importlib.util.spec_from_file_location("saydi_owner_v5", str(V5_MODULE))
    v5 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v5)
    return v5

def prepare(v5):
    reference_hash = v5.reference_verified()
    old = v5.load_legacy_segmenter()
    manifest, audit = v5.owner_manifest(old, CHAPTER, 0, reference_hash)
    if not manifest["segments"]:
        raise RuntimeError("CHAPTER_02_SOURCE_EMPTY")
    src = Path(manifest["source_path"])
    source = src.read_text(encoding="utf-8")
    if "\ufffd" in source:
        raise RuntimeError("CHAPTER_SOURCE_CONTAINS_UNICODE_REPLACEMENT")
    assert int(manifest["chapter_number"]) == CHAPTER
    mf_path = WORK / "manifest.json"
    if mf_path.exists():
        previous = json.loads(mf_path.read_text(encoding="utf-8"))
        if (previous.get("reference_sha256") != reference_hash
                or previous.get("source_sha256") != manifest.get("source_sha256")
                or len(previous["segments"]) != len(manifest["segments"])
                or [s["tts_text_sha256"] for s in previous["segments"]] !=
                   [s["tts_text_sha256"] for s in manifest["segments"]]):
            raise RuntimeError("V5_CHAPTER_02_INPUT_CHANGED_REFUSE_UNSAFE_RESUME")
    else:
        atomic_json(mf_path, manifest)
        atomic_json(WORK / "editorial_audit.json", {
            "chapter": CHAPTER,
            "source_sha256": manifest["source_sha256"],
            "reference_sha256": reference_hash,
            "segments": len(manifest["segments"]),
            "word_integrity": "PASS",
            "legacy_paraphrase_suspects": len(audit),
            "v5_spoken_text_diff": False,
            "canonical_source_utf8": True,
        })
    return manifest, old, reference_hash

def already_rendered(item, ref_hash):
    idx = int(item["index"])
    wave = CHUNKS / f"{idx:06d}.wav"
    key = CHUNKS / f"{idx:06d}.sha256"
    if not wave.exists() or wave.stat().st_size <= 1024 or not key.exists():
        return False
    return key.read_text(encoding="utf-8").strip() == item["tts_text_sha256"]

def render(manifest, v5, ref_hash):
    from vieneu import Vieneu
    import soundfile as sf
    import gc
    items = manifest["segments"]
    CHUNKS.mkdir(parents=True, exist_ok=True)
    done = sum(already_rendered(item, ref_hash) for item in items)
    status("RENDERING", rendered=done, total=len(items), qc_checked=0, total_qc=len(items))
    if done >= len(items):
        return
    log(f"Loading VieNeu only for missing V5 segments; {done}/{len(items)} retained.")
    tts = Vieneu(backend="onnx", precision="fp32")
    tts.add_voice(v5.VOICE, str(v5.REF), denoise=False, save=False,
                  description="Owner-approved V5 native tempo", gender="male")
    try:
        for item in items:
            if already_rendered(item, ref_hash):
                continue
            if free_ram_gb() < MIN_RUN_RAM_GB:
                status("PAUSED_RESOURCE", reason="LIVE_LOW_RAM_DURING_RENDER", rendered=done,
                       total=len(items), free_ram_gb=round(free_ram_gb(), 2))
                log("Pausing: live free RAM below safety floor, checkpoint saved.")
                return
            idx = int(item["index"])
            audio = tts.infer(item["spoken_text"], voice=v5.VOICE, max_chars=320)
            temp = CHUNKS / f"{idx:06d}.partial.wav"
            wave = CHUNKS / f"{idx:06d}.wav"
            tts.save(audio, str(temp))
            if sf.info(str(temp)).duration < .25:
                raise RuntimeError(f"BAD_RENDER_CH02_SEGMENT_{idx}")
            os.replace(temp, wave)
            (CHUNKS / f"{idx:06d}.sha256").write_text(item["tts_text_sha256"] + "\n", encoding="utf-8")
            done += 1
            if done == 1 or done % 5 == 0 or done == len(items):
                status("RENDERING", rendered=done, total=len(items),
                       free_ram_gb=round(free_ram_gb(), 2))
                log(f"Rendered {done}/{len(items)} V5 chapter 2 segments")
    finally:
        try:
            tts.close()
        except Exception:
            pass
        del tts
        gc.collect()
    status("RENDER_COMPLETE", rendered=done, total=len(items), qc_checked=0)

def assemble(manifest, v5, old):
    expected = WORK / "CHUONG_02_OWNER_APPROVED_V5.REVIEW.mp3"
    if expected.exists() and expected.stat().st_size > 10240:
        return expected
    if free_ram_gb() < 0.9:
        status("PAUSED_RESOURCE", reason="RAM_INSUFFICIENT_FOR_JOIN")
        return None
    status("ASSEMBLING_MP3")
    tmp = expected.with_name(expected.stem + ".pending.mp3")
    seconds = v5.assemble(manifest["segments"], CHUNKS, tmp, old)
    if seconds < 120:
        raise RuntimeError("UNEXPECTED_SHORT_CHAPTER_02_AUDIO")
    os.replace(tmp, expected)
    status("RENDER_COMPLETE", duration_sec=round(seconds, 2), chapter_audio=str(expected),
           chapter_audio_sha256=sha256(expected), rendered=len(manifest["segments"]))
    log(f"Built V5 Chapter 2 review MP3; duration={seconds:.2f}s")
    return expected

def qc(manifest):
    items = manifest["segments"]
    QC_BATCHES.mkdir(parents=True, exist_ok=True)
    count = len(items)
    complete = 0
    all_rows = []
    for start in range(0, count, QC_BATCH_SIZE):
        slice_ = items[start:start + QC_BATCH_SIZE]
        first, last = int(slice_[0]["index"]), int(slice_[-1]["index"])
        report = QC_BATCHES / f"qc_{first:04d}_{last:04d}.json"
        def check_batch():
            if not report.exists():
                return None
            d = json.loads(report.read_text(encoding="utf-8"))
            rows = d.get("rows", [])
            expected_ids = {int(x["index"]) for x in slice_}
            if {int(x["index"]) for x in rows} != expected_ids:
                return None
            for row in rows:
                idx = int(row["index"])
                wav = CHUNKS / f"{idx:06d}.wav"
                if not wav.exists() or row.get("audio_sha256") != sha256(wav):
                    return None
            return rows
        old_rows = check_batch()
        if old_rows is not None:
            complete += len(old_rows)
            all_rows.extend(old_rows)
            continue
        # No model is loaded while paused. Resume when resources are available.
        mem = free_ram_gb()
        if mem < MIN_START_RAM_GB:
            status("PAUSED_RESOURCE", reason="QC_NEEDS_FREE_RAM", rendered=count, total=count,
                   qc_checked=complete, total_qc=count, free_ram_gb=round(mem, 2))
            log(f"QC checkpoint: {complete}/{count}, RAM {mem:.2f}GB; waiting for >= {MIN_START_RAM_GB} GB.")
            return
        status("QC_RUNNING", rendered=count, total=count, qc_checked=complete, total_qc=count,
               current_batch=f"{first}-{last}")
        indices = ",".join(str(x["index"]) for x in slice_)
        console = QC_BATCHES / f"qc_{first:04d}_{last:04d}.log"
        command = [str(QC_PY), str(QC_SCRIPT), "--manifest", str(WORK / "manifest.json"),
                   "--chunk-dir", str(CHUNKS), "--report", str(report), "--indices", indices]
        with console.open("w", encoding="utf-8") as output:
            proc = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
            low_hits = 0
            while proc.poll() is None:
                time.sleep(3)
                if free_ram_gb() < 0.30:
                    low_hits += 1
                else:
                    low_hits = 0
                if low_hits >= 3:
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
                    status("PAUSED_RESOURCE", reason="QC_CHILD_RAM_CRITICAL",
                           rendered=count, qc_checked=complete, total_qc=count)
                    log("QC child stopped safely due to critical RAM pressure; batch may be retried.")
                    return
        if proc.returncode != 0:
            status("QC_FAILED", reason=f"QC_BATCH_EXIT_{proc.returncode}",
                   qc_checked=complete, total_qc=count)
            raise RuntimeError(f"QC batch {first}-{last} failed with {proc.returncode}")
        checked_rows = check_batch()
        if checked_rows is None:
            raise RuntimeError(f"QC_RESULT_HASH_MISMATCH_{first}_{last}")
        complete += len(checked_rows)
        all_rows.extend(checked_rows)
        status("QC_RUNNING", rendered=count, total=count, qc_checked=complete,
               total_qc=count, current_batch=f"{first}-{last}")
        log(f"QC chapter 2 V5: {complete}/{count} checked")
    all_rows.sort(key=lambda x: x["index"])
    flagged = [int(x["index"]) for x in all_rows if x["status"] != "PASS"]
    strict = [int(x["index"]) for x in all_rows if x["status"] != "PASS" or x.get("asr_similarity", 0) < .985]
    atomic_json(WORK / "QC_AFTER_RENDER.json", {
        "schema_version": "saydi-v5-ch02-qc-checkpointed",
        "checked": len(all_rows), "flagged_indices": flagged, "strict_review_indices": strict,
        "pass": not flagged, "rows": all_rows, "human_listening_approved": False
    })
    audio = WORK / "CHUONG_02_OWNER_APPROVED_V5.REVIEW.mp3"
    if audio.exists() and shutil.disk_usage("C:\\").free > 1024**3 + audio.stat().st_size:
        destination = Path(r"C:\Users\admin\Desktop") / audio.name
        shutil.copy2(audio, destination)
        if sha256(audio) != sha256(destination):
            raise RuntimeError("DESKTOP_COPY_HASH_FAILED")
        url = str(destination)
    else:
        url = str(audio)
    status("REVIEW_READY", rendered=count, total=count, qc_checked=count, total_qc=count,
           pass_count=count - len(flagged), review_count=len(flagged), strict_review_count=len(strict),
           chapter_audio=url, human_listening_approved=False, final=False)
    log(f"CH02 V5 QC completed {count}/{count}; PASS={count-len(flagged)} REVIEW={len(flagged)}; not FINAL")

def run(prepare_only: bool) -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    cap_cpu()
    handle = lock()
    if handle is None:
        log("Already running: refusing duplicate.")
        return 0
    try:
        v5 = load_v5()
        manifest, old, reference = prepare(v5)
        items = manifest["segments"]
        state = {}
        try:
            state = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        if state.get("stage") == "REVIEW_READY" and state.get("qc_checked") == len(items):
            log("Completed QC previously; no duplicate work.")
            return 0
        done = sum(already_rendered(item, reference) for item in items)
        status("PREPARED", total=len(items), rendered=done, total_qc=len(items),
               source_validated=True, reference_sha256=reference,
               audio_speed_policy="NATIVE_ONLY_NO_ATEMPO", output_root=str(WORK))
        if prepare_only:
            status("QUEUED_RESOURCE", total=len(items), rendered=done, total_qc=len(items),
                   reason="PREPARED_ONLY", min_start_ram_gb=MIN_START_RAM_GB)
            log(f"Prepared chapter 2 V5 (segments={len(items)}), no heavy models loaded.")
            return 0
        if free_disk_gb() < MIN_DISK_GB:
            status("PAUSED_RESOURCE", reason="LOW_D_DRIVE_SPACE", free_disk_gb=round(free_disk_gb(), 2))
            return 0
        heavy = active_heavy_jobs()
        if heavy:
            status("PAUSED_RESOURCE", reason="OTHER_HEAVY_SAYDI_JOB_RUNNING", blocking_jobs=heavy)
            return 0
        if done < len(items):
            if free_ram_gb() < MIN_START_RAM_GB:
                status("QUEUED_RESOURCE", total=len(items), rendered=done, total_qc=len(items),
                       reason="RAM_BELOW_SAFETY_GATE", free_ram_gb=round(free_ram_gb(), 2),
                       min_start_ram_gb=MIN_START_RAM_GB)
                log(f"Queued until machine has {MIN_START_RAM_GB}GB free RAM; currently {free_ram_gb():.2f}GB.")
                return 0
            render(manifest, v5, reference)
        if sum(already_rendered(item, reference) for item in items) != len(items):
            return 0
        audio = assemble(manifest, v5, old)
        if audio is None:
            return 0
        qc(manifest)
        return 0
    finally:
        unlock(handle)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    try:
        raise SystemExit(run(args.prepare_only))
    except Exception as exc:
        log(f"FAILURE: {type(exc).__name__}: {exc}")
        status("FAILED", reason=type(exc).__name__, error=str(exc)[:400])
        raise
