import json
from pathlib import Path

from magasin_voice_engine.supervisor_status import (
    HeartbeatWorker,
    RobotStatus,
    SupervisorState,
    SupervisorStateStore,
    default_job_id,
    render_dashboard,
)


def test_publish_writes_json_and_dashboard(tmp_path, monkeypatch):
    monkeypatch.setenv("COMPUTERNAME", "MAGASIN-PC")
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    monkeypatch.setenv("GITHUB_JOB", "voice")
    monkeypatch.setenv("GITHUB_WORKFLOW", "Voice Engine")
    monkeypatch.setenv("GITHUB_REPOSITORY", "magasincoffee/magasin-media-robot")

    store = SupervisorStateStore(tmp_path)
    state = store.publish(
        RobotStatus.RUNNING,
        job_id=default_job_id(),
        current_step="provider_preflight",
        last_completed_step="validate_request",
        next_action="Wait for provider preflight",
        requires_user=False,
        message="Read-only check",
    )

    assert state.status == "RUNNING"
    assert state.job_id == "github:12345:voice"
    assert state.robot == "MAGASIN-PC"
    assert state.run_id == "12345"
    assert store.state_path.exists()
    assert store.dashboard_path.exists()

    payload = json.loads(store.state_path.read_text(encoding="utf-8"))
    assert payload["current_step"] == "provider_preflight"
    assert payload["last_completed_step"] == "validate_request"
    assert "Read-only check" in store.dashboard_path.read_text(encoding="utf-8")


def test_heartbeat_preserves_current_status(tmp_path):
    store = SupervisorStateStore(tmp_path)
    before = store.publish(
        RobotStatus.WAIT_USER,
        job_id="job-1",
        current_step="authorization",
        next_action="Authorize Generate",
        requires_user=True,
    )
    after = store.heartbeat()

    assert after.status == RobotStatus.WAIT_USER.value
    assert after.job_id == "job-1"
    assert after.requires_user is True
    assert after.last_heartbeat is not None
    assert after.last_heartbeat >= before.last_heartbeat


def test_render_dashboard_marks_user_wait_and_privacy_notice():
    state = SupervisorState(
        status=RobotStatus.WAIT_USER.value,
        job_id="job-9",
        current_step="authorization",
        requires_user=True,
        last_heartbeat="2026-09-18T03:00:00Z",
    )
    page = render_dashboard(state)

    assert "WAITING FOR USER" in page
    assert "job-9" in page
    assert "Needs user" in page
    assert "cookies" in page
    assert "STALE" in page


def test_heartbeat_worker_is_fail_safe(tmp_path):
    store = SupervisorStateStore(tmp_path)
    store.publish(RobotStatus.RUNNING, job_id="job-2", current_step="work")
    worker = HeartbeatWorker(store, interval_seconds=1)
    worker.start()
    worker.stop()

    assert store.load().status == RobotStatus.RUNNING.value


def test_status_values_are_frozen():
    assert [item.value for item in RobotStatus] == [
        "IDLE",
        "RUNNING",
        "WAIT_USER",
        "RETRYING",
        "FAILED",
        "DONE",
    ]
