# -*- coding: utf-8 -*-
"""SAYDI Media Control: localhost-only, lightweight, read-only runtime monitor."""
import json
import os
import re
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
HOST, PORT = "127.0.0.1", int(os.getenv("SAYDI_CONTROL_PORT", "8776"))
AUDIOS = {
    "full": DESKTOP / "CHUONG_01_V5_R2_SUA_LOI_NANG.REVIEW.mp3",
    "begin": DESKTOP / "CHUONG_01_V5_R2_DAU_CHUONG_5PHUT.mp3",
    "middle": DESKTOP / "CHUONG_01_V5_R2_GIUA_CHUONG_5PHUT.mp3",
}
PROCESS_TYPES = {
    "render_owner_approved_v5.py": "render",
    "qc_local_segments.py": "qc",
    "repair_chapter1_owner_v5_r2.py": "repair",
    "repair_owner_v5_pilot.py": "repair",
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
    active, workers = processes()
    types = {p["kind"] for p in active}
    phase = str(repair.get("phase") or state.get("status") or "UNKNOWN")
    if "qc" in types:
        kind, title, detail = "running", "ĐANG QC ÂM THANH", "Whisper đang kiểm duyệt âm thanh."
    elif "render" in types:
        kind, title, detail = "running", "ĐANG RENDER", "VieNeu đang tạo giọng."
    elif "repair" in types:
        kind, title, detail = "running", "ĐANG SỬA LỖI", "Robot đang kiểm tra/sửa các đoạn bị cảnh báo."
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
    entries = []
    for label, path in [("R2", R2 / "auto_repair.log"), ("V5", ROOT / "run.log"), ("Watchdog", ROOT / "resume.log")]:
        for line in tail(path, 5):
            entries.append({"group": label, "text": line})
    basic_review = r2.get("basic_qc_review_remaining")
    if basic_review is None:
        basic_review = len(gate.get("legacy_qc_flagged") or [])
    strict_review = r2.get("strict_asr_review_remaining")
    if strict_review is None:
        strict_review = gate.get("strict_asr_review_count")
    return {
        "updated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "last_record": max([t for t in [stamp(R2 / "REVIEW_STATUS.json"),
                        stamp(R2 / "AUTO_REPAIR_STATUS.json"), stamp(CH / "render_state.json")] if t], default=None),
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
        "events": entries, "read_only": True,
    }

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
                return self.send_data(json.dumps(snapshot(), ensure_ascii=False).encode("utf-8"),
                                      "application/json; charset=utf-8")
            except Exception as exc:
                return self.send_data(json.dumps({"error": type(exc).__name__}).encode(), "application/json", 503)
        if path == "/healthz":
            return self.send_data(b"ok", "text/plain")
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
        self.send_data(b"Read-only: no action endpoint", "text/plain", 405)

def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True
    print("SAYDI Media Control http://" + HOST + ":" + str(PORT), flush=True)
    server.serve_forever()

if __name__ == "__main__":
    main()
