"""Safe review-only bridge between existing SAYDI Control and 8 GiB resource gate.

Not installed on H4 production. This module never invokes VieNeu, Whisper,
Supabase, a Windows Scheduled Task, or a Control Center START/STOP endpoint.
The bridge must NOT interpret job JSON fields as authenticated Owner approval.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

try:
    from vn_8gb_resource_gate import evaluate as assess_resource
except ImportError:
    from .vn_8gb_resource_gate import evaluate as assess_resource

SCHEMA = "saydi-vn8gb-coordinator-bridge-v1"
ALLOWED_STAGE_ACTIONS = {"recheck": "ASR", "resume": "TTS"}
# resume actually invokes a composite rendering+QC legacy script; not yet
# acceptable until its internal phase barrier is separately qualified.
COMPOSITE_ACTIONS = {"resume", "improve"}

def evaluate_existing_job(
    job: Mapping[str, Any],
    snapshot: Mapping[str, Any] | None,
    *,
    authenticated_owner_start: bool = False,
    trusted_generation_witness: bool = False,
    internal_tts_to_asr_barrier_qualified: bool = False,
) -> dict[str, Any]:
    """Provide admission diagnostics only; do not grant production authority.

    Caller-supplied job fields are NEVER sufficient to prove Owner identity.
    An external, server-verified Owner session/generation must supply explicit
    flags after the production Control Center's separate audited acceptance.
    """
    action = job.get("action")
    reasons: list[str] = []
    if action not in ALLOWED_STAGE_ACTIONS:
        reasons.append("ACTION_NOT_QUALIFIED_FOR_SEQUENTIAL_ADMISSION")
    if job.get("state") not in ("QUEUED", "QUEUED_RESOURCE", "WAIT_OTHER_WORKER"):
        reasons.append("JOB_STATE_NOT_QUEUED")
    if not authenticated_owner_start or not trusted_generation_witness:
        reasons.append("OWNER_START_WITNESS_UNVERIFIED")
    if action in COMPOSITE_ACTIONS and not internal_tts_to_asr_barrier_qualified:
        reasons.append("LEGACY_COMPOSITE_PHASE_BARRIER_UNVERIFIED")

    resource: dict[str, Any] | None = None
    if action in ALLOWED_STAGE_ACTIONS and isinstance(snapshot, Mapping):
        resource = assess_resource(snapshot, stage=ALLOWED_STAGE_ACTIONS[action])
        reasons.extend(resource["reasons"])
    else:
        reasons.append("RESOURCE_SNAPSHOT_UNAVAILABLE")

    # Resource eligibility does not confer START/STOP authority. A qualifying
    # result merely permits the existing authenticated coordinator to continue
    # with its own mutex, durable STOP and per-phase resource checks.
    permitted_to_consider = not reasons
    return {
        "schema": SCHEMA,
        "action": action if isinstance(action, str) else "UNKNOWN",
        "stage": ALLOWED_STAGE_ACTIONS.get(action),
        "decision": (
            "ELIGIBLE_FOR_EXISTING_AUTHORIZED_CHECKS"
            if permitted_to_consider else "HOLD"
        ),
        "reasons": list(dict.fromkeys(reasons)),
        "resource_gate": resource,
        "approved_to_dispatch": False,
        "approved_to_start": False,
        "already_installed_live": False,
        "composite_action_qualified": bool(
            action not in COMPOSITE_ACTIONS or internal_tts_to_asr_barrier_qualified
        ),
    }

def read_only_h4_snapshot(
    collector_script: Path, *, timeout_seconds: int = 20
) -> dict[str, Any] | None:
    """Run the source-only H4 telemetry script and parse only sanitized JSON.

    This never opens the old SaydiVoice Chrome profile or alters Windows jobs.
    A failing probe returns None and the controller must HOLD.
    """
    if not collector_script.is_file():
        return None
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(collector_script)],
            capture_output=True, text=True, check=False, timeout=timeout_seconds,
        )
        if completed.returncode:
            return None
        result = json.loads(completed.stdout.strip().removeprefix("\ufeff"))
        return result if isinstance(result, dict) else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None

def staged_guard_before_dispatch(job: Mapping[str, Any]) -> dict[str, Any]:
    """Hook for isolated controller-copy testing; production always HOLD here.

    The proper Control Center Owner latch/generation and the V5 combined TTS
    + QC stage barrier are not qualified in the installed 2026-10-11
    controller, so pass no authorization flags.
    """
    collector = Path(__file__).with_name("INSPECT_VN_8GB_H4_READONLY.ps1")
    snapshot = read_only_h4_snapshot(collector)
    return evaluate_existing_job(
        job, snapshot,
        authenticated_owner_start=False,
        trusted_generation_witness=False,
        internal_tts_to_asr_barrier_qualified=False,
    )
