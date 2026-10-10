# -*- coding: utf-8 -*-
"""SAYDI Media Control: localhost-only, lightweight, read-only runtime monitor."""
import json
import os
import re
import secrets
import threading
import time
import control_commands as jobs
import activity_monitor
from datetime import datetime
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import psutil

ROOT = Path(os.getenv("SAYDI_RUNTIME_ROOT", r"C:\SAYDI\output\OWNER_APPROVED_NATURAL_V5"))
DESKTOP = Path(os.getenv("SAYDI_DESKTOP", r"C:\Users\admin\Desktop"))
WEB = Path(__file__).resolve().parent
CH = ROOT / "Chuong_01"
R2 = ROOT / "Chuong_01_R2"
CH2_STATE = ROOT / "CH02_V5_STATUS.json"
HOST, PORT = "127.0.0.1", int(os.getenv("SAYDI_CONTROL_PORT", "8776"))
CSRF_TOKEN = secrets.token_urlsafe(32)
_STATUS_CACHE_LOCK = threading.Lock()
_STATUS_CACHE_AT = 0.0
_STATUS_CACHE = None
AUDIOS = {
    "full": DESKTOP / "CHUONG_01_V5_R2_SUA_LOI_NANG.REVIEW.mp3",
    "begin": DESKTOP / "CHUONG_01_V5_R2_DAU_CHUONG_5PHUT.mp3",
    "middle": DESKTOP / "CHUONG_01_V5_R2_GIUA_CHUONG_5PHUT.mp3",
    "chapter2": Path(r"D:\SAYDI\OWNER_APPROVED_NATURAL_V5\Chuong_02\CHUONG_02_OWNER_APPROVED_V5.REVIEW.mp3"),
}
PROCESS_TYPES = {
    "render_owner_approved_v5.py": "render",
    "qc_local_segments.py": "qc",
    "repair_chapter1_owner_v5_r2.py": "repair",
    "repair_owner_v5_pilot.py": "repair",
    "chapter2_v5_qc_guarded.py": "chapter2",
    "chapter_v5_job.py": "render",
    "saydi_review_qc.py": "qc",
    "saydi_quality_improve.py": "repair",
}
ACTIVE_PHASES = {"RENDERING", "QC_RUNNING", "QC_TARGETED", "RENDERING_CANDIDATES", "ASSEMBLING_MP3", "REPAIRING"}

def jread(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, UnicodeError):
        return {}

def stamp(path):
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
    except OSError:
        return None

def tail(path, count=6):
    try:
        with path.open("rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 11000))
            lines = f.read().decode("utf-8", errors="replace").splitlines()
        return [s.strip()[:400] for s in lines if s.strip()][-count:]
    except OSError:
        return []

def processes():
    active, worker = [], []
    for p in psutil.process_iter(["pid", "name", "cmdline", "memory_info"]):
        try:
            if (p.info.get("name") or "").lower() not in ("python.exe", "pythonw.exe", "powershell.exe"):
                continue
            cmd = " ".join(p.info.get("cmdline") or []).lower()
            role = next((r for match, r in PROCESS_TYPES.items() if match in cmd), None)
            if role:
                mem = p.info.get("memory_info")
                active.append({"pid": p.pid, "kind": role, "ram_mb": round(mem.rss / 1048576, 1) if mem else None})
            elif "saydi_worker.py" in cmd:
                worker.append(p.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return active, worker

def snapshot():
    state = jread(CH / "render_state.json")
    gate = jread(CH / "FINAL_GATE.json")
    repair = jread(R2 / "AUTO_REPAIR_STATUS.json")
    r2 = jread(R2 / "REVIEW_STATUS.json")
    ch2 = jread(CH2_STATE)
    job_now = jobs.job_status()
    active, workers = processes()
    types = {p["kind"] for p in active}
    phase = str(job_now.get("state") or repair.get("phase") or state.get("status") or "UNKNOWN")
    if "chapter2" in types:
        chapter2_stage = ch2.get("stage", "PROCESS_ACTIVE")
        kind, title, detail = ("running", "ĐANG XỬ LÝ CHƯƠNG 2",
                               "SAYDI V5 đang thực thi: " + chapter2_stage)
    elif "qc" in types:
        kind, title, detail = "running", "ĐANG QC ÂM THANH", "Whisper đang kiểm duyệt âm thanh."
    elif "render" in types:
        kind, title, detail = "running", "ĐANG RENDER", "VieNeu đang tạo giọng."
    elif "repair" in types:
        kind, title, detail = "running", "ĐANG SỬA LỖI", "Robot đang kiểm tra/sửa các đoạn bị cảnh báo."
    elif job_now.get("state") in ("QUEUED_RESOURCE", "WAIT_OTHER_WORKER", "QUEUED"):
        kind, title, detail = ("warning", "LỆNH ĐANG CHỜ — CHƯA CHẠY",
                               "Công việc mới đang chờ đủ RAM hoặc đợi tác vụ khác; không có tiến trình xử lý.")
    elif job_now.get("state") == "FAILED":
        kind, title, detail = ("warning", "LỆNH BỊ LỖI", "Kiểm tra lỗi của công việc mới trong nhật ký.")
    elif ch2.get("stage") in ("QUEUED_RESOURCE", "PAUSED_RESOURCE"):
        kind, title, detail = ("warning", "CHƯƠNG 2 CHỜ ĐỦ TÀI NGUYÊN",
                               "Đã chuẩn bị V5; chưa khởi chạy mô hình do RAM hoặc ổ đĩa không đủ.")
    elif ch2.get("stage") == "REVIEW_READY":
        kind, title, detail = ("review", "CHƯƠNG 2 ĐÃ QC — CHỜ NGHE DUYỆT",
                               "Chương 2 đã có MP3 và báo cáo QC, không phải FINAL.")
    elif r2.get("final") and r2.get("owner_approved"):
        kind, title, detail = "done", "ĐÃ NGHIỆM THU", "Bản audio đã có trạng thái phát hành."
    elif r2.get("status") == "FULL_R2_READY_FOR_OWNER_REVIEW" or phase == "REVIEW_READY":
        kind, title, detail = "review", "CHỜ NGHE DUYỆT", "Bản đầy đủ đã xuất; không có QC/render đang chạy."
    elif phase.startswith("PAUSED") or phase.endswith("FAILED"):
        kind, title, detail = "warning", "TẠM DỪNG / LỖI", "Xem log để xác định lý do."
    elif phase in ACTIVE_PHASES:
        kind, title, detail = "warning", "NGỪNG BẤT THƯỜNG", "Dữ liệu báo đang xử lý nhưng không tìm thấy tiến trình."
    elif state:
        kind, title, detail = "review", "CHƯA CÓ FINAL", "Đã có dữ liệu, đang chờ QC hoặc duyệt."
    else:
        kind, title, detail = "idle", "CHƯA CÓ DỮ LIỆU", "Chưa tìm được tiến độ trong thư mục đã cấu hình."
    vm = psutil.virtual_memory()
    info = {}
    for key, path in AUDIOS.items():
        try:
            st = path.stat()
            info[key] = {"exists": True, "url": "/audio/" + key, "bytes": st.st_size,
                         "modified": datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec="seconds")}
        except OSError:
            info[key] = {"exists": False, "url": "/audio/" + key}
    chapter_for_activity = job_now.get("chapter") or jobs.selected_chapter()
    job_log = WEB / ("job_" + str(job_now.get("id")) + ".log") if job_now.get("id") else None
    activity = activity_monitor.summarize(
        job_now, jobs.JOB, WEB / "job_guardian.log", jobs.LOG, job_log,
        chapter_for_activity, round(vm.available / 1073741824, 2), active)
    entries = activity["events"]
    basic_review = r2.get("basic_qc_review_remaining")
    if basic_review is None:
        basic_review = len(gate.get("legacy_qc_flagged") or [])
    strict_review = r2.get("strict_asr_review_remaining")
    if strict_review is None:
        strict_review = gate.get("strict_asr_review_count")
    return {
        "updated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "last_record": activity["last_event"],
        "activity": activity,
        "hostname": os.getenv("COMPUTERNAME", "DESKTOP-H4A16IL"),
        "version": "V5 / mẫu Owner chốt",
        "phase": phase,
        "status": {"kind": kind, "title": title, "detail": detail, "active": bool(active)},
        "progress": {"render": int(state.get("rendered") or r2.get("segments") or 0),
                     "total": int(state.get("total") or r2.get("segments") or 0),
                     "qc": int(gate.get("qc_checked") or state.get("qc_checked") or 0),
                     "repair": int(r2.get("repaired_candidates") or repair.get("complete") or 0),
                     "repair_total": int(r2.get("repaired_candidates") or repair.get("total") or 0),
                     "improved": int(r2.get("improved_segments") or 0)},
        "quality": {"review": int(basic_review),
                    "strict_review": strict_review,
                    "final": bool(r2.get("final", False)), "duration_sec": r2.get("duration_sec")},
        "system": {"cpu": round(psutil.cpu_percent(interval=0.05), 1),
                   "ram": round(vm.percent, 1), "free_gb": round(vm.available / 1073741824, 2),
                   "total_gb": round(vm.total / 1073741824, 2)},
        "processes": active, "worker": bool(workers), "audio": info,
        "events": entries, "read_only": False,
        "chapter2": ch2,
        "control": {"selected_chapter":jobs.selected_chapter(),
                    "chapters":jobs.catalog(),"job":job_now,
                    "csrf":CSRF_TOKEN,"actions_enabled":True,
                    "resource_policy":{"logical_cpu_threads":jobs.OWNER_CPU_THREADS,
                                       "max_concurrent_heavy_jobs":1,
                                       "min_start_free_ram_gb":jobs.OWNER_MIN_GB,
                                       "automatic_resume":True}},
    }

def cached_snapshot():
    """Share one status scan across simultaneous UI panels; avoids double CPU scans."""
    global _STATUS_CACHE_AT, _STATUS_CACHE
    with _STATUS_CACHE_LOCK:
        now = time.monotonic()
        if _STATUS_CACHE is None or now - _STATUS_CACHE_AT >= 4.0:
            updated = snapshot()
            _STATUS_CACHE = updated
            _STATUS_CACHE_AT = time.monotonic()
        return _STATUS_CACHE

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # pythonw has no stderr stream; BaseHTTPRequestHandler logging would
        # otherwise abort successful HTTP responses to the web UI.
        return

    def send_data(self, body, kind, code=200, headers=None):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        if headers:
            for key, value in headers.items():
                self.send_header(key, str(value))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def allow_local_host(self):
        host = self.headers.get("Host", "").strip().lower()
        return host in (HOST + ":" + str(PORT), "localhost:" + str(PORT))

    def do_GET(self):
        if not self.allow_local_host():
            return self.send_data(b"Local host only", "text/plain", 403)
        path = urlsplit(self.path).path
        if path == "/":
            try:
                data = (WEB / "index.html").read_bytes()
                return self.send_data(data, "text/html; charset=utf-8")
            except OSError:
                return self.send_data(b"UI not installed", "text/plain", 503)
        if path == "/api/status":
            try:
                return self.send_data(json.dumps(cached_snapshot(), ensure_ascii=False).encode("utf-8"),
                                      "application/json; charset=utf-8")
            except Exception as exc:
                return self.send_data(json.dumps({"error": type(exc).__name__}).encode(), "application/json", 503)
        if path == "/healthz":
            return self.send_data(b"ok", "text/plain")
        if path.startswith("/audio/chapter/"):
            chapter_text = path.rsplit("/", 1)[-1]
            if not chapter_text.isascii() or not chapter_text.isdecimal():
                return self.send_data(b"Invalid chapter", "text/plain", 404)
            chapter = int(chapter_text)
            if chapter not in range(1,12):
                return self.send_data(b"Invalid chapter", "text/plain", 404)
            base = jobs.base(chapter)
            quality = sorted([p for p in (base/"quality_v5").glob("round_*")
                              if (p/"REVIEW_STATUS.json").exists()])
            if quality:
                result = jobs.read(quality[-1]/"REVIEW_STATUS.json")
                file = Path(result.get("audio_path", ""))
                if file.parent != quality[-1] or file.suffix.lower()!=".mp3":
                    return self.send_data(b"Unsafe audio path", "text/plain", 404)
                return self.audio(file)
            if chapter==1:
                return self.audio(AUDIOS["full"])
            return self.audio(base/f"CHUONG_{chapter:02d}_OWNER_APPROVED_V5.REVIEW.mp3")
        if path.startswith("/audio/"):
            key = path.split("/")[-1]
            if key not in AUDIOS:
                return self.send_data(b"Unknown audio", "text/plain", 404)
            return self.audio(AUDIOS[key])
        return self.send_data(b"Not found", "text/plain", 404)

    def audio(self, path):
        try:
            size = path.stat().st_size
        except OSError:
            return self.send_data(b"Missing audio", "text/plain", 404)
        begin, end = 0, size - 1
        rng = self.headers.get("Range")
        if rng:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", rng)
            if not match:
                return self.send_data(b"", "text/plain", 416, {"Content-Range": "bytes */" + str(size)})
            if match[1]:
                begin = int(match[1])
                if match[2]:
                    end = int(match[2])
            elif match[2]:
                begin = max(0, size - int(match[2]))
            if begin >= size or end < begin:
                return self.send_data(b"", "text/plain", 416, {"Content-Range": "bytes */" + str(size)})
            end = min(end, size - 1)
        length = end - begin + 1
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Accept-Ranges", "bytes")
        if rng:
            self.send_header("Content-Range", "bytes " + str(begin) + "-" + str(end) + "/" + str(size))
        self.end_headers()
        try:
            with path.open("rb") as fp:
                fp.seek(begin)
                while length > 0:
                    block = fp.read(min(length, 65536))
                    if not block:
                        break
                    self.wfile.write(block)
                    length -= len(block)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def do_POST(self):
        if not self.allow_local_host():
            return self.send_data(b"Local host only", "text/plain", 403)
        if urlsplit(self.path).path != "/api/command":
            return self.send_data(b"Unknown command endpoint", "text/plain", 404)
        origin = self.headers.get("Origin", "")
        if origin not in ("http://127.0.0.1:"+str(PORT), "http://localhost:"+str(PORT)):
            return self.send_data(b"Origin not allowed", "text/plain", 403)
        if self.headers.get("X-Saydi-Csrf") != CSRF_TOKEN:
            return self.send_data(b"CSRF token missing", "text/plain", 403)
        if self.headers.get("Content-Type", "").split(";")[0].strip()!="application/json":
            return self.send_data(b"JSON required", "text/plain", 415)
        try:
            length=int(self.headers.get("Content-Length","0"))
        except ValueError:
            length=0
        if length<2 or length>1024:
            return self.send_data(b"Invalid request size", "text/plain", 413)
        try:
            payload=json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload,dict) or set(payload)!={"action","chapter"}:
                raise ValueError("Invalid action payload")
            result=jobs.submit(payload["action"],payload["chapter"])
            body=json.dumps(result,ensure_ascii=False).encode("utf-8")
            return self.send_data(body,"application/json; charset=utf-8",202)
        except (ValueError,TypeError) as exc:
            return self.send_data(json.dumps({"error":str(exc)}).encode("utf-8"),
                                  "application/json",400)
        except RuntimeError as exc:
            return self.send_data(json.dumps({"error":str(exc)}).encode("utf-8"),
                                  "application/json",409)

def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True
    print("SAYDI Media Control http://" + HOST + ":" + str(PORT), flush=True)
    server.serve_forever()

if __name__ == "__main__":
    main()
