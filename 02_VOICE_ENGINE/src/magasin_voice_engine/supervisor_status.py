from __future__ import annotations

import argparse
import html
import json
import os
import socket
import threading
import time
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any


class RobotStatus(StrEnum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAIT_USER = "WAIT_USER"
    RETRYING = "RETRYING"
    FAILED = "FAILED"
    DONE = "DONE"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _default_status_dir() -> Path:
    override = os.environ.get("MAGASIN_STATUS_DIR")
    if override:
        return Path(override)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "MAGASIN" / "MediaRobot" / "saydi"
    return Path.home() / ".magasin" / "MediaRobot" / "saydi"


def default_job_id() -> str:
    run_id = os.environ.get("GITHUB_RUN_ID")
    job = os.environ.get("GITHUB_JOB")
    if run_id:
        return f"github:{run_id}:{job or 'job'}"
    return f"local:{os.getpid()}"


@dataclass(slots=True)
class SupervisorState:
    schema_version: int = 1
    project: str = "saydi"
    robot: str = "MAGASIN-PC"
    status: str = RobotStatus.IDLE.value
    job_id: str | None = None
    current_step: str | None = None
    last_completed_step: str | None = None
    next_action: str | None = None
    retry_count: int = 0
    requires_user: bool = False
    message: str | None = None
    started_at: str | None = None
    updated_at: str | None = None
    last_heartbeat: str | None = None
    runner_name: str | None = None
    repository: str | None = None
    workflow: str | None = None
    run_id: str | None = None
    run_attempt: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SupervisorState":
        known = {field for field in cls.__dataclass_fields__}
        return cls(**{key: value for key, value in payload.items() if key in known})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SupervisorStateStore:
    """Local, privacy-safe Saydi supervisor state and self-refreshing HTML dashboard."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = Path(directory) if directory is not None else _default_status_dir()
        self.state_path = self.directory / "supervisor_state.json"
        self.dashboard_path = self.directory / "saydi_status.html"
        self._lock = threading.RLock()

    def _runtime_metadata(self) -> dict[str, str | None]:
        return {
            "runner_name": os.environ.get("RUNNER_NAME") or os.environ.get("COMPUTERNAME") or socket.gethostname(),
            "repository": os.environ.get("GITHUB_REPOSITORY"),
            "workflow": os.environ.get("GITHUB_WORKFLOW"),
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        }

    def load(self) -> SupervisorState:
        with self._lock:
            if not self.state_path.exists():
                return SupervisorState(robot=os.environ.get("COMPUTERNAME") or "MAGASIN-PC")
            try:
                payload = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return SupervisorState.from_dict(payload)
            except (OSError, ValueError, TypeError):
                pass
            return SupervisorState(robot=os.environ.get("COMPUTERNAME") or "MAGASIN-PC")

    def publish(
        self,
        status: RobotStatus | str,
        *,
        job_id: str | None = None,
        current_step: str | None = None,
        last_completed_step: str | None = None,
        next_action: str | None = None,
        retry_count: int | None = None,
        requires_user: bool | None = None,
        message: str | None = None,
    ) -> SupervisorState:
        status_value = RobotStatus(status).value
        now = _utc_now()
        with self._lock:
            current = self.load()
            new_job_id = job_id if job_id is not None else current.job_id
            started_at = current.started_at
            if status_value in {RobotStatus.RUNNING.value, RobotStatus.RETRYING.value}:
                if current.job_id != new_job_id or not started_at:
                    started_at = now
            state = SupervisorState(
                project=current.project,
                robot=current.robot or os.environ.get("COMPUTERNAME") or "MAGASIN-PC",
                status=status_value,
                job_id=new_job_id,
                current_step=current_step,
                last_completed_step=last_completed_step if last_completed_step is not None else current.last_completed_step,
                next_action=next_action,
                retry_count=current.retry_count if retry_count is None else retry_count,
                requires_user=current.requires_user if requires_user is None else requires_user,
                message=message,
                started_at=started_at,
                updated_at=now,
                last_heartbeat=now,
                **self._runtime_metadata(),
            )
            self._write_state(state)
            return state

    def heartbeat(self) -> SupervisorState:
        now = _utc_now()
        with self._lock:
            state = self.load()
            state.updated_at = now
            state.last_heartbeat = now
            metadata = self._runtime_metadata()
            for key, value in metadata.items():
                if value is not None:
                    setattr(state, key, value)
            self._write_state(state)
            return state

    def ensure_dashboard(self) -> SupervisorState:
        with self._lock:
            state = self.load()
            if state.updated_at is None:
                now = _utc_now()
                state.updated_at = now
                state.last_heartbeat = now
                self._write_state(state)
            else:
                self._write_dashboard(state)
            return state

    def open_dashboard(self) -> Path:
        self.ensure_dashboard()
        webbrowser.open(self.dashboard_path.resolve().as_uri())
        return self.dashboard_path

    def _write_state(self, state: SupervisorState) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state.to_dict(), ensure_ascii=False, indent=2) + "\n"
        temporary = self.state_path.with_suffix(".json.tmp")
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, self.state_path)
        self._write_dashboard(state)

    def _write_dashboard(self, state: SupervisorState) -> None:
        page = render_dashboard(state)
        temporary = self.dashboard_path.with_suffix(".html.tmp")
        temporary.write_text(page, encoding="utf-8")
        os.replace(temporary, self.dashboard_path)


class HeartbeatWorker:
    def __init__(self, store: SupervisorStateStore, interval_seconds: float = 30.0) -> None:
        self.store = store
        self.interval_seconds = max(1.0, float(interval_seconds))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> "HeartbeatWorker":
        if self._thread and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="saydi-heartbeat", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=min(self.interval_seconds + 1.0, 5.0))

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                self.store.heartbeat()
            except Exception:
                # Monitoring must never crash the production robot.
                pass

    def __enter__(self) -> "HeartbeatWorker":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()


_STATUS_META = {
    RobotStatus.IDLE.value: ("●", "#16a34a", "ONLINE / IDLE"),
    RobotStatus.RUNNING.value: ("●", "#2563eb", "RUNNING"),
    RobotStatus.WAIT_USER.value: ("●", "#ca8a04", "WAITING FOR USER"),
    RobotStatus.RETRYING.value: ("●", "#ea580c", "RETRYING"),
    RobotStatus.FAILED.value: ("●", "#dc2626", "FAILED"),
    RobotStatus.DONE.value: ("✓", "#16a34a", "DONE"),
}


def render_dashboard(state: SupervisorState) -> str:
    symbol, color, label = _STATUS_META.get(state.status, ("●", "#64748b", state.status))
    def esc(value: Any) -> str:
        return html.escape("" if value is None else str(value))

    heartbeat = esc(state.last_heartbeat)
    requires_user = "YES" if state.requires_user else "NO"
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="5">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SAYDI CONTROL</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#f8fafc;color:#0f172a;margin:0;padding:28px}}
.card{{max-width:760px;margin:auto;background:white;border:1px solid #e2e8f0;border-radius:16px;padding:24px;box-shadow:0 8px 24px rgba(15,23,42,.08)}}
h1{{margin:0 0 18px;font-size:28px;letter-spacing:.03em}}
.status{{font-size:24px;font-weight:700;color:{color};margin-bottom:20px}}
.grid{{display:grid;grid-template-columns:190px 1fr;gap:10px 14px}}
.key{{color:#64748b}} .value{{font-weight:600;word-break:break-word}}
#freshness{{margin-top:18px;padding:10px 12px;border-radius:10px;background:#f1f5f9}}
.stale{{background:#fee2e2!important;color:#991b1b;font-weight:700}}
.small{{margin-top:18px;color:#64748b;font-size:13px}}
</style>
</head>
<body>
<div class="card">
<h1>SAYDI CONTROL</h1>
<div class="status">{symbol} {esc(label)}</div>
<div class="grid">
<div class="key">Robot</div><div class="value">{esc(state.robot)}</div>
<div class="key">Job</div><div class="value">{esc(state.job_id) or "—"}</div>
<div class="key">Current step</div><div class="value">{esc(state.current_step) or "—"}</div>
<div class="key">Last completed</div><div class="value">{esc(state.last_completed_step) or "—"}</div>
<div class="key">Next action</div><div class="value">{esc(state.next_action) or "—"}</div>
<div class="key">Retry count</div><div class="value">{state.retry_count}</div>
<div class="key">Needs user</div><div class="value">{requires_user}</div>
<div class="key">Message</div><div class="value">{esc(state.message) or "—"}</div>
<div class="key">Workflow</div><div class="value">{esc(state.workflow) or "local"}</div>
<div class="key">Run ID</div><div class="value">{esc(state.run_id) or "—"}</div>
</div>
<div id="freshness" data-heartbeat="{heartbeat}">Last heartbeat: {heartbeat or "—"}</div>
<div class="small">Auto-refresh: 5s · Heartbeat target: 30s · STALE threshold: 90s. No prompts, cookies, tokens, or generated audio are stored here.</div>
</div>
<script>
(function(){{
 const box=document.getElementById('freshness');
 const raw=box.dataset.heartbeat;
 if(!raw) return;
 const t=Date.parse(raw);
 if(Number.isNaN(t)) return;
 const age=Math.max(0,Math.floor((Date.now()-t)/1000));
 box.textContent='Last heartbeat: '+raw+' ('+age+'s ago)';
 if(age>90){{box.classList.add('stale');box.textContent+=' — STALE';}}
}})();
</script>
</body>
</html>
"""


def _main() -> int:
    parser = argparse.ArgumentParser(description="Saydi local supervisor status dashboard")
    parser.add_argument("--open", action="store_true", help="Open the local HTML dashboard")
    parser.add_argument("--show", action="store_true", help="Print current state JSON")
    parser.add_argument("--heartbeat", action="store_true", help="Touch the heartbeat timestamp")
    parser.add_argument("--set-status", choices=[item.value for item in RobotStatus])
    parser.add_argument("--current-step")
    parser.add_argument("--last-completed-step")
    parser.add_argument("--next-action")
    parser.add_argument("--message")
    parser.add_argument("--retry-count", type=int)
    parser.add_argument("--requires-user", action="store_true")
    args = parser.parse_args()

    store = SupervisorStateStore()
    if args.set_status:
        store.publish(
            args.set_status,
            job_id=default_job_id(),
            current_step=args.current_step,
            last_completed_step=args.last_completed_step,
            next_action=args.next_action,
            retry_count=args.retry_count,
            requires_user=args.requires_user,
            message=args.message,
        )
    elif args.heartbeat:
        store.heartbeat()
    else:
        store.ensure_dashboard()

    if args.show:
        print(json.dumps(store.load().to_dict(), ensure_ascii=False, indent=2))
    if args.open:
        store.open_dashboard()
    if not (args.show or args.open or args.set_status or args.heartbeat):
        print(store.dashboard_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
