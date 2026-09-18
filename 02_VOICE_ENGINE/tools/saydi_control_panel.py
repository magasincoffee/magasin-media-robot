from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


APP_NAME = "SAYDI CONTROL"
RUNNER_ROOT = Path(r"C:\actions-runner")
RUNNER_CMD = RUNNER_ROOT / "run.cmd"
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home()))
STATUS_DIR = LOCALAPPDATA / "MAGASIN" / "MediaRobot" / "saydi"
STATE_PATH = STATUS_DIR / "supervisor_state.json"
CONTROL_DIR = LOCALAPPDATA / "MAGASIN" / "MediaRobot" / "control"
RUNNER_LOG = CONTROL_DIR / "runner-console.log"
PANEL_LOG = CONTROL_DIR / "control-panel.log"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

STATUS_COLORS = {
    "OFFLINE": ("#7f1d1d", "#fee2e2"),
    "IDLE": ("#166534", "#dcfce7"),
    "RUNNING": ("#1d4ed8", "#dbeafe"),
    "WAIT_USER": ("#854d0e", "#fef9c3"),
    "RETRYING": ("#9a3412", "#ffedd5"),
    "FAILED": ("#991b1b", "#fee2e2"),
    "DONE": ("#166534", "#dcfce7"),
    "UNKNOWN": ("#475569", "#e2e8f0"),
}

STEP_LABELS = {
    "waiting_for_job": "Đang chờ việc từ ChatGPT / GitHub",
    "validate_request": "Kiểm tra yêu cầu",
    "provider_preflight": "Kiểm tra phiên Saydi",
    "production_preflight": "Kiểm tra Saydi production (chỉ đọc)",
    "apply_settings": "Áp dụng giọng / style",
    "generate": "Đang tạo giọng nói",
    "download": "Đang tải file đầu ra",
    "supervisor_status_smoke": "Kiểm tra bảng điều khiển / heartbeat",
    "complete": "Hoàn thành",
    "wait_user": "Đang chờ bạn xử lý",
    "failed": "Đã dừng vì lỗi",
}


def now_text() -> str:
    return datetime.now().strftime("%H:%M:%S")


def append_log(message: str) -> None:
    CONTROL_DIR.mkdir(parents=True, exist_ok=True)
    with PANEL_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")


def tasklist_contains(image_name: str) -> bool:
    if os.name != "nt":
        return False
    try:
        completed = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image_name}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            creationflags=CREATE_NO_WINDOW,
            timeout=5,
        )
        return image_name.lower() in completed.stdout.lower()
    except Exception:
        return False


def runner_listener_online() -> bool:
    return tasklist_contains("Runner.Listener.exe")


def runner_worker_active() -> bool:
    return tasklist_contains("Runner.Worker.exe")


def read_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        return {"status": "UNKNOWN", "message": f"Không đọc được supervisor_state.json: {exc}"}


def parse_heartbeat_age(value: str | None) -> int | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        stamp = datetime.fromisoformat(normalized)
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds()))
    except Exception:
        return None


def tail_file(path: Path, max_lines: int = 40, max_bytes: int = 64_000) -> str:
    if not path.exists():
        return ""
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(size - max_bytes)
            data = handle.read().decode("utf-8", errors="replace")
        lines = data.splitlines()
        return "\n".join(lines[-max_lines:])
    except Exception as exc:
        return f"Không đọc được log: {exc}"


def pretty_step(value: str | None) -> str:
    if not value:
        return "—"
    return STEP_LABELS.get(value, value.replace("_", " ").strip())


def start_runner_hidden() -> tuple[bool, str]:
    if runner_listener_online():
        return True, "Runner đã ONLINE."

    if not RUNNER_CMD.exists():
        return False, f"Không tìm thấy {RUNNER_CMD}"

    CONTROL_DIR.mkdir(parents=True, exist_ok=True)
    append_log("START requested from SAYDI CONTROL.")
    try:
        log_handle = RUNNER_LOG.open("ab", buffering=0)
        subprocess.Popen(
            ["cmd.exe", "/d", "/s", "/c", "call run.cmd"],
            cwd=str(RUNNER_ROOT),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW,
            close_fds=False,
        )
    except Exception as exc:
        append_log(f"START failed: {type(exc).__name__}: {exc}")
        return False, f"Không khởi động được runner: {exc}"

    deadline = time.time() + 12
    while time.time() < deadline:
        if runner_listener_online():
            append_log("Runner became ONLINE.")
            return True, "Robot đã ONLINE và sẵn sàng nhận việc từ ChatGPT qua GitHub."
        time.sleep(0.5)

    append_log("Runner did not become ONLINE within 12 seconds.")
    return False, "Runner chưa ONLINE sau 12 giây. Xem mục LỖI / NHẬT KÝ."


def stop_runner() -> tuple[bool, str]:
    append_log("STOP requested from SAYDI CONTROL.")
    if os.name != "nt":
        return False, "STOP chỉ hỗ trợ trên Windows."

    commands = [
        ["taskkill", "/IM", "Runner.Worker.exe", "/F"],
        ["taskkill", "/IM", "Runner.Listener.exe", "/F"],
    ]
    for command in commands:
        try:
            subprocess.run(
                command,
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
                timeout=8,
            )
        except Exception:
            pass

    deadline = time.time() + 5
    while time.time() < deadline:
        if not runner_listener_online():
            append_log("Runner is OFFLINE.")
            return True, "Robot đã dừng."
        time.sleep(0.4)

    return False, "Không thể dừng Runner.Listener. Có thể cần đóng tiến trình thủ công."


class ControlPanel(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("980x720")
        self.minsize(820, 620)
        self.configure(bg="#f8fafc")
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._work_queue: queue.Queue[tuple[str, bool, str]] = queue.Queue()
        self._last_runner_log = ""
        self._build_styles()
        self._build_ui()
        self.after(300, self._poll_worker_results)
        self.after(300, self._refresh)

    def _build_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except Exception:
            pass
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 22), background="#f8fafc", foreground="#0f172a")
        style.configure("Sub.TLabel", font=("Segoe UI", 10), background="#f8fafc", foreground="#64748b")
        style.configure("CardTitle.TLabel", font=("Segoe UI Semibold", 10), background="#ffffff", foreground="#64748b")
        style.configure("Value.TLabel", font=("Segoe UI Semibold", 11), background="#ffffff", foreground="#0f172a")
        style.configure("Start.TButton", font=("Segoe UI Semibold", 14), padding=(28, 14))
        style.configure("Stop.TButton", font=("Segoe UI Semibold", 12), padding=(22, 12))
        style.configure("Secondary.TButton", font=("Segoe UI", 10), padding=(14, 8))

    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg="#f8fafc")
        outer.pack(fill="both", expand=True, padx=22, pady=18)

        header = tk.Frame(outer, bg="#f8fafc")
        header.pack(fill="x")
        ttk.Label(header, text="SAYDI CONTROL", style="Title.TLabel").pack(side="left")
        ttk.Label(
            header,
            text="ChatGPT  ↔  GitHub  ↔  MAGASIN-PC",
            style="Sub.TLabel",
        ).pack(side="right", pady=(10, 0))

        control = tk.Frame(outer, bg="#ffffff", highlightbackground="#e2e8f0", highlightthickness=1)
        control.pack(fill="x", pady=(16, 12))

        left = tk.Frame(control, bg="#ffffff")
        left.pack(side="left", padx=18, pady=16)
        self.start_button = ttk.Button(left, text="▶  START ROBOT", style="Start.TButton", command=self._on_start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(left, text="■  STOP", style="Stop.TButton", command=self._on_stop)
        self.stop_button.pack(side="left", padx=(10, 0))

        right = tk.Frame(control, bg="#ffffff")
        right.pack(side="right", padx=18, pady=16)
        ttk.Button(right, text="Mở ChatGPT", style="Secondary.TButton", command=lambda: webbrowser.open("https://chatgpt.com/")).pack(side="left")
        ttk.Button(right, text="Mở thư mục trạng thái", style="Secondary.TButton", command=self._open_status_dir).pack(side="left", padx=(8, 0))

        status_row = tk.Frame(outer, bg="#f8fafc")
        status_row.pack(fill="x", pady=(0, 12))

        self.runner_card, self.runner_value = self._status_card(status_row, "RUNNER", "Đang kiểm tra…")
        self.runner_card.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.robot_card, self.robot_value = self._status_card(status_row, "ROBOT", "Đang kiểm tra…")
        self.robot_card.pack(side="left", fill="x", expand=True, padx=(6, 0))

        details = tk.Frame(outer, bg="#ffffff", highlightbackground="#e2e8f0", highlightthickness=1)
        details.pack(fill="x", pady=(0, 12))

        self.current_var = tk.StringVar(value="—")
        self.next_var = tk.StringVar(value="—")
        self.last_var = tk.StringVar(value="—")
        self.heartbeat_var = tk.StringVar(value="—")
        self.job_var = tk.StringVar(value="—")
        self.error_var = tk.StringVar(value="Không có lỗi.")

        rows = [
            ("ĐANG LÀM", self.current_var),
            ("CHUẨN BỊ LÀM", self.next_var),
            ("VỪA HOÀN THÀNH", self.last_var),
            ("HEARTBEAT", self.heartbeat_var),
            ("JOB / WORKFLOW", self.job_var),
        ]
        for index, (label, var) in enumerate(rows):
            tk.Label(details, text=label, bg="#ffffff", fg="#64748b", font=("Segoe UI Semibold", 9), anchor="w").grid(
                row=index, column=0, sticky="nw", padx=(18, 12), pady=(12 if index == 0 else 7, 7)
            )
            tk.Label(details, textvariable=var, bg="#ffffff", fg="#0f172a", font=("Segoe UI", 11), anchor="w", justify="left", wraplength=700).grid(
                row=index, column=1, sticky="ew", padx=(0, 18), pady=(12 if index == 0 else 7, 7)
            )
        details.columnconfigure(1, weight=1)

        error_box = tk.Frame(outer, bg="#fff7ed", highlightbackground="#fed7aa", highlightthickness=1)
        error_box.pack(fill="x", pady=(0, 12))
        tk.Label(error_box, text="LỖI / CẦN BẠN XỬ LÝ", bg="#fff7ed", fg="#9a3412", font=("Segoe UI Semibold", 9), anchor="w").pack(fill="x", padx=16, pady=(10, 2))
        tk.Label(error_box, textvariable=self.error_var, bg="#fff7ed", fg="#7c2d12", font=("Segoe UI", 10), anchor="w", justify="left", wraplength=900).pack(fill="x", padx=16, pady=(0, 10))

        log_frame = tk.Frame(outer, bg="#ffffff", highlightbackground="#e2e8f0", highlightthickness=1)
        log_frame.pack(fill="both", expand=True)
        log_header = tk.Frame(log_frame, bg="#ffffff")
        log_header.pack(fill="x", padx=14, pady=(10, 6))
        tk.Label(log_header, text="NHẬT KÝ GẦN NHẤT", bg="#ffffff", fg="#64748b", font=("Segoe UI Semibold", 9)).pack(side="left")
        ttk.Button(log_header, text="Làm mới", style="Secondary.TButton", command=self._refresh_logs).pack(side="right")

        self.log_text = tk.Text(
            log_frame,
            height=10,
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#ffffff",
            font=("Consolas", 9),
            relief="flat",
            wrap="word",
        )
        self.log_text.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.log_text.insert("1.0", "Chưa có log.")
        self.log_text.configure(state="disabled")

        footer = tk.Label(
            outer,
            text="START = bật kênh thực thi trên MAGASIN-PC. Khi Runner ONLINE, tôi có thể giao job từ cuộc chat này qua GitHub Actions. Không cần mở PowerShell riêng.",
            bg="#f8fafc",
            fg="#64748b",
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=920,
        )
        footer.pack(fill="x", pady=(10, 0))

    def _status_card(self, parent: tk.Widget, title: str, initial: str):
        card = tk.Frame(parent, bg="#ffffff", highlightbackground="#e2e8f0", highlightthickness=1)
        tk.Label(card, text=title, bg="#ffffff", fg="#64748b", font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=16, pady=(12, 3))
        value = tk.Label(card, text=initial, bg="#ffffff", fg="#0f172a", font=("Segoe UI Semibold", 15), anchor="w")
        value.pack(fill="x", padx=16, pady=(0, 12))
        return card, value

    def _set_badge(self, label: tk.Label, status: str, text: str) -> None:
        fg, bg = STATUS_COLORS.get(status, STATUS_COLORS["UNKNOWN"])
        label.configure(text=text, fg=fg, bg=bg)
        label.master.configure(bg=bg)
        for child in label.master.winfo_children():
            try:
                child.configure(bg=bg)
            except Exception:
                pass

    def _on_start(self) -> None:
        self.start_button.configure(state="disabled")
        self.error_var.set("Đang khởi động robot…")
        threading.Thread(target=self._start_worker, daemon=True).start()

    def _start_worker(self) -> None:
        ok, message = start_runner_hidden()
        self._work_queue.put(("start", ok, message))

    def _on_stop(self) -> None:
        if runner_worker_active():
            if not messagebox.askyesno(
                "Dừng robot?",
                "Robot đang có job chạy. STOP sẽ kết thúc job hiện tại. Bạn vẫn muốn dừng?",
                parent=self,
            ):
                return
        self.stop_button.configure(state="disabled")
        threading.Thread(target=self._stop_worker, daemon=True).start()

    def _stop_worker(self) -> None:
        ok, message = stop_runner()
        self._work_queue.put(("stop", ok, message))

    def _poll_worker_results(self) -> None:
        try:
            while True:
                action, ok, message = self._work_queue.get_nowait()
                append_log(f"{action.upper()}: {message}")
                self.error_var.set("Không có lỗi." if ok else message)
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="normal")
                self._refresh_logs()
        except queue.Empty:
            pass
        self.after(300, self._poll_worker_results)

    def _open_status_dir(self) -> None:
        STATUS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(STATUS_DIR)
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc), parent=self)

    def _refresh(self) -> None:
        listener = runner_listener_online()
        worker = runner_worker_active()
        state = read_state()
        raw_status = str(state.get("status") or "UNKNOWN").upper()

        if listener:
            runner_text = "ONLINE • ĐANG CHẠY JOB" if worker else "ONLINE • CHỜ VIỆC"
            self._set_badge(self.runner_value, "RUNNING" if worker else "IDLE", runner_text)
        else:
            self._set_badge(self.runner_value, "OFFLINE", "OFFLINE")
        
        if not listener:
            robot_status = "OFFLINE"
            robot_text = "OFFLINE"
        elif raw_status in STATUS_COLORS and raw_status not in {"OFFLINE", "UNKNOWN"}:
            robot_status = raw_status
            robot_text = raw_status
        elif worker:
            robot_status = "RUNNING"
            robot_text = "RUNNING"
        else:
            robot_status = "IDLE"
            robot_text = "IDLE • CHỜ VIỆC"

        self._set_badge(self.robot_value, robot_status, robot_text)

        current = pretty_step(state.get("current_step"))
        next_action = state.get("next_action") or ("Chờ việc mới từ ChatGPT / GitHub." if listener and not worker else "—")
        last_completed = pretty_step(state.get("last_completed_step"))
        heartbeat = state.get("last_heartbeat")
        age = parse_heartbeat_age(heartbeat)

        if heartbeat:
            if age is None:
                heartbeat_text = str(heartbeat)
            else:
                heartbeat_text = f"{heartbeat}  •  {age} giây trước"
                if raw_status in {"RUNNING", "RETRYING"} and age > 90:
                    heartbeat_text += "  •  STALE"
        else:
            heartbeat_text = "Chưa có heartbeat."

        job_parts = []
        if state.get("job_id"):
            job_parts.append(str(state.get("job_id")))
        if state.get("workflow"):
            job_parts.append(str(state.get("workflow")))
        if state.get("run_id"):
            job_parts.append(f"run {state.get('run_id')}")
        job_text = "  •  ".join(job_parts) if job_parts else ("Chưa có job." if not worker else "Job đang khởi động…")

        error_message = state.get("message")
        requires_user = bool(state.get("requires_user"))
        if not listener:
            error_text = "Robot đang OFFLINE. Bấm START ROBOT để kết nối MAGASIN-PC với GitHub."
        elif raw_status == "FAILED":
            error_text = f"{error_message or 'Job thất bại.'}  |  {next_action}"
        elif raw_status == "WAIT_USER" or requires_user:
            error_text = f"{error_message or 'Robot đang chờ bạn.'}  |  {next_action}"
        elif raw_status in {"RUNNING", "RETRYING"} and age is not None and age > 90:
            error_text = "Heartbeat quá 90 giây. Job có thể bị treo; kiểm tra nhật ký trước khi STOP."
        else:
            error_text = "Không có lỗi."

        self.current_var.set(current if current != "—" else ("Đang xử lý job GitHub." if worker else "Chờ việc."))
        self.next_var.set(str(next_action))
        self.last_var.set(last_completed)
        self.heartbeat_var.set(heartbeat_text)
        self.job_var.set(job_text)
        self.error_var.set(error_text)

        self.start_button.configure(state="disabled" if listener else "normal")
        self.stop_button.configure(state="normal" if listener else "disabled")
        self._refresh_logs()
        self.after(1200, self._refresh)

    def _refresh_logs(self) -> None:
        runner_log = tail_file(RUNNER_LOG, max_lines=32)
        panel_log = tail_file(PANEL_LOG, max_lines=12)
        parts = []
        if panel_log:
            parts.append("=== CONTROL PANEL ===\n" + panel_log)
        if runner_log:
            parts.append("=== GITHUB RUNNER ===\n" + runner_log)
        output = "\n\n".join(parts) if parts else "Chưa có log."

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", output)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


def self_test() -> int:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    CONTROL_DIR.mkdir(parents=True, exist_ok=True)
    print(json.dumps({
        "app": APP_NAME,
        "runner_cmd_exists": RUNNER_CMD.exists(),
        "state_path": str(STATE_PATH),
        "control_dir": str(CONTROL_DIR),
        "tk_version": tk.TkVersion,
    }, ensure_ascii=True, indent=2))
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    append_log("SAYDI CONTROL opened.")
    app = ControlPanel()
    app.mainloop()
    append_log("SAYDI CONTROL closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
