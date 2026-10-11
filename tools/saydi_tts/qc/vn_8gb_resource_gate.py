"""H4 8 GiB SAYDI VieNeu/Whisper read-only sequential admission assessor.

No worker dispatch, no STOP/START mutation, no checkpoint edit.  It is a
preflight/diagnostic contract for the existing authenticated coordinator ONLY.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "saydi-vn-8gb-sequential-probe-v1"
HOST = "DESKTOP-H4A16IL"
STAGES = {"TTS": ("VIENEU", 2.1), "ASR": ("WHISPER", 2.5)}
MIN_C_FREE_GIB = 2.0  # conservative staging proposal, not existing SOT requirement
MIN_D_FREE_GIB = 10.0
HISTORY_MINIMUM_GIB = {"TTS": 1.9, "ASR": 2.3}
SAMPLE_COUNT = 5
TELEMETRY_SCHEMA = "saydi-vn-8gb-h4-telemetry-v1"
MAX_SNAPSHOT_AGE_SECONDS = 30.0
MAX_FUTURE_SKEW_SECONDS = 5.0

def _number(value: Any) -> float | None:
    try:
        if isinstance(value, bool):
            return None
        n = float(value)
        return n if math.isfinite(n) and 0 <= n < 2048 else None
    except (ValueError, TypeError):
        return None

def _snapshot_age_seconds(raw: Any) -> float | None:
    """Require a recent, timezone-aware H4 capture; a string is never Owner proof."""
    if not isinstance(raw, str):
        return None
    try:
        captured = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        if captured.tzinfo is None or captured.utcoffset() is None:
            return None
        return (datetime.now(timezone.utc) - captured.astimezone(timezone.utc)).total_seconds()
    except (ValueError, OverflowError):
        return None

def evaluate(snapshot: Mapping[str, Any], *, stage: str) -> dict[str, Any]:
    """Fail closed, preserve STOP, and NEVER convert diagnosis to START authority."""
    if stage not in STAGES:
        raise ValueError("stage must be TTS or ASR")
    reasons: list[str] = []
    def check(ok: bool, error: str) -> None:
        if not ok:
            reasons.append(error)

    check(snapshot.get("schema") == TELEMETRY_SCHEMA, "TELEMETRY_SCHEMA_UNVERIFIED")
    snapshot_age = _snapshot_age_seconds(snapshot.get("captured_at"))
    check(snapshot_age is not None and -MAX_FUTURE_SKEW_SECONDS <= snapshot_age <= MAX_SNAPSHOT_AGE_SECONDS,
          "TELEMETRY_STALE_OR_UNVERIFIED")
    check(snapshot.get("host") == HOST, "WRONG_HOST")
    physical = _number(snapshot.get("physical_ram_gib"))
    check(physical is not None and 7.0 <= physical <= 9.0, "EXPECTED_8GB_MACHINE_NOT_PROVEN")
    cpu_threads = _number(snapshot.get("cpu_logical_threads"))
    check(cpu_threads is not None and 1 <= cpu_threads <= 8, "CPU_INVENTORY_UNAVAILABLE")

    samples = snapshot.get("ram_samples_gib")
    ram_values = (
        [_number(x) for x in samples]
        if isinstance(samples, list) and len(samples) >= SAMPLE_COUNT
        else []
    )
    valid = len(ram_values) >= SAMPLE_COUNT and all(x is not None for x in ram_values)
    check(valid, "RAM_SAMPLES_MISSING_OR_INVALID")
    min_ram = round(min(ram_values), 3) if valid else None
    min_admit = STAGES[stage][1]
    if valid:
        check(min_ram >= min_admit, "INSUFFICIENT_STABLE_RAM_" + stage)

    c_gib = _number(snapshot.get("disk_c_free_gib"))
    d_gib = _number(snapshot.get("disk_d_free_gib"))
    check(c_gib is not None and c_gib >= MIN_C_FREE_GIB, "LOW_C_DRIVE_HEADROOM")
    check(d_gib is not None and d_gib >= MIN_D_FREE_GIB, "LOW_D_DRIVE_HEADROOM")
    # TEMP is an advisory. Even if redirected, C: headroom still matters
    # for Windows and pagefile. Never silently relocate user's temp.
    temp_drive = snapshot.get("temp_drive")
    check(temp_drive in ("C:", "D:"), "TEMP_DRIVE_UNKNOWN")
    if temp_drive == "C:" and c_gib is not None and c_gib < 4.0:
        check(False, "TEMP_ON_LOW_SPACE_C_DRIVE")

    workers = snapshot.get("heavy_workers")
    check(isinstance(workers, list), "HEAVY_WORKER_INVENTORY_MISSING")
    worker_classes: list[str] = []
    if isinstance(workers, list):
        for worker in workers:
            if not isinstance(worker, dict):
                worker_classes.append("UNKNOWN")
                continue
            kind = worker.get("kind")
            if kind not in ("TTS", "ASR", "MIXED", "WRAPPER", "UNKNOWN"):
                kind = "UNKNOWN"
            worker_classes.append(kind)
        check(not worker_classes, "HEAVY_WORKER_ALREADY_ACTIVE")
        check(not ("TTS" in worker_classes and "ASR" in worker_classes), "CONCURRENT_TTS_ASR_DETECTED")
        check("UNKNOWN" not in worker_classes, "UNIDENTIFIED_HEAVY_WORKER")

    # No read-only status snapshot can attest actual Owner identity.
    # Even if caller claims Owner ON, this diagnostic NEVER grants START.
    stop_latch = snapshot.get("owner_stop_latch")
    check(stop_latch == "ON", "OWNER_LATCH_UNVERIFIED_OR_STOPPED")
    check(snapshot.get("checkpoint_ownership") == "VERIFIED", "CHECKPOINT_OWNERSHIP_UNVERIFIED")
    check(snapshot.get("worker_mutex_state") == "FREE", "WORKER_MUTEX_UNVERIFIED")
    # This is a local stage-admission observation, NOT authentication.
    resource_possible = not reasons
    return {
        "schema": SCHEMA,
        "stage": stage,
        "host": HOST,
        "resource_assessment": "ELIGIBLE_FOR_SEPARATE_AUTHORIZED_CHECK" if resource_possible else "HOLD",
        "reasons": reasons,
        "telemetry_age_seconds": round(snapshot_age, 3) if snapshot_age is not None else None,
        "telemetry_max_age_seconds": MAX_SNAPSHOT_AGE_SECONDS,
        "historical_stage_floor_gib": HISTORY_MINIMUM_GIB[stage],
        "conservative_stage_floor_gib": min_admit,
        "observed_min_free_ram_gib": min_ram,
        "observed_c_free_gib": c_gib,
        "observed_d_free_gib": d_gib,
        "cpu_thread_cap_recommendation": 1,
        "stage_order": ["TTS", "UNLOAD_TTS", "CONFIRM_NO_HEAVY_WORKERS", "ASR", "UNLOAD_ASR", "ASSEMBLE_G_REVIEW"],
        "approved_to_start": False,
        "approved_to_dispatch": False,
        "installed_in_production": False,
        "production_or_checkpoint_modified": False,
        "owner_approval_inferred": False,
    }

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Read-only 8GB H4 VieNeu/Whisper sequential admission report")
    p.add_argument("--input", required=True, help="sanitized JSON snapshot path or '-' (stdin)")
    p.add_argument("--stage", choices=sorted(STAGES), required=True)
    args = p.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        snapshot = json.loads(raw)
        if not isinstance(snapshot, dict):
            raise ValueError("snapshot must be object")
        result = evaluate(snapshot, stage=args.stage)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        print(json.dumps({"schema": SCHEMA, "resource_assessment": "HOLD",
                         "reasons": ["SNAPSHOT_UNAVAILABLE_OR_INVALID"],
                         "approved_to_start": False, "approved_to_dispatch": False}))
        return 21
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0 if result["resource_assessment"] == "ELIGIBLE_FOR_SEPARATE_AUTHORIZED_CHECK" else 21

if __name__ == "__main__":
    raise SystemExit(main())
