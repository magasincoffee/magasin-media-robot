"""VN-001 bounded offline diagnostic cycle with sanitized JSONL evidence.

SOURCE / FIXTURE ONLY: NEVER touches real V5 assets, deploys MCP, modifies
Supervisor, loads VieNeu/Whisper, starts workers or grants field acceptance.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import socket
import sys
from typing import Callable

TASK = "SAYDI002-VN-001"
SCHEMA = "SAYDI_VN001_STAGING_CYCLE_V1"
H4_NAME = "DESKTOP-H4A16IL"
H4_STAGE_ROOT = Path(r"D:\SAYDI_V6_STAGING\VN001")
MAX_REPAIRS = 2
ALTERNATIVES = {
    "GRANT": "ISOLATED_GRANT_FIXTURE_ONLY",
    "WINDOWS_NOFOLLOW": "HOSTED_WINDOWS_FIXTURE_ONLY",
    "SEQUENTIAL_RESOURCE": "SEQUENCE_SIMULATION_ONLY",
    "CHECKPOINT": "METADATA_ONLY_HOLD_CHECKPOINT",
}
SHA40 = re.compile(r"[a-f0-9]{40}\Z")

@dataclass(frozen=True)
class Probe:
    code: str
    check: Callable[[], bool]
    repair_fixture: Callable[[], None] | None = None

class StageRefusal(Exception):
    pass

def _validate_stage(root: Path) -> None:
    if type(root) is not type(Path(".")) or not root.is_absolute():
        raise StageRefusal("STAGE_NOT_ABSOLUTE")
    if any(part in ("..", ".") for part in root.parts):
        raise StageRefusal("STAGE_TRAVERSAL")
    if socket.gethostname().upper() == H4_NAME:
        if root != H4_STAGE_ROOT:
            raise StageRefusal("H4_STAGE_NOT_ALLOWLISTED")
        if not root.is_dir():
            raise StageRefusal("H4_STAGE_NOT_PREPROVISIONED")
    # Deny filesystem links and junction/reparse ancestors.
    for p in list(reversed(root.parents)) + [root]:
        if p.is_symlink() or (p.exists() and getattr(
                p.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400):
            raise StageRefusal("STAGE_REPARSE_REJECTED")
    if not root.is_dir():
        raise StageRefusal("STAGE_MISSING")

def _log(fh, *, run_id: str, commit: str, probe: str,
         phase: str, attempt: int, result: str, code: str,
         route: str = "") -> None:
    record = {
        "schema": SCHEMA, "task": TASK, "run_id": run_id,
        "at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": commit, "probe": probe, "phase": phase, "attempt": attempt,
        "result": result, "code": code, "field_accepted": False,
        "worker_started": False, "production_modified": False,
    }
    if route:
        if route not in ALTERNATIVES.values():
            raise StageRefusal("ALTERNATIVE_NOT_ALLOWLISTED")
        record["alternate_route"] = route
    fh.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")
    fh.flush()
    os.fsync(fh.fileno())

def run_cycle(root: Path, probes: tuple[Probe, ...], *,
              commit: str = "0"*40, run_id: str | None = None) -> dict:
    """Run only fixed source-fixture probes; max two repairs then alternate HOLD."""
    _validate_stage(root)
    if type(commit) is not str or not SHA40.fullmatch(commit):
        raise StageRefusal("COMMIT_NOT_PINNED")
    if run_id is None:
        run_id = secrets.token_hex(12)
    if type(run_id) is not str or re.fullmatch(r"[a-f0-9]{24}", run_id) is None:
        raise StageRefusal("RUN_ID_INVALID")
    if (type(probes) is not tuple or not probes or len(probes) > len(ALTERNATIVES)
            or any(type(p) is not Probe or p.code not in ALTERNATIVES
                   or not callable(p.check) or
                   (p.repair_fixture is not None and not callable(p.repair_fixture))
                   for p in probes)
            or len({p.code for p in probes}) != len(probes)):
        raise StageRefusal("PROBES_NOT_ALLOWLISTED")
    name = "vn001-fixture-" + run_id + ".jsonl"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(root / name), flags, 0o600)
    passed, held, alternates = [], [], {}
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        for p in probes:
            success = False
            for attempt in range(1, MAX_REPAIRS + 2):
                try:
                    success = p.check() is True
                except BaseException:
                    success = False  # Never log raw exception / private details.
                _log(fh, run_id=run_id, commit=commit, probe=p.code,
                     phase="PROBE", attempt=attempt,
                     result="PASS" if success else "FAIL",
                     code="OK" if success else "FIXTURE_REJECTED")
                if success:
                    passed.append(p.code)
                    break
                if attempt <= MAX_REPAIRS and p.repair_fixture is not None:
                    try:
                        p.repair_fixture()
                        repaired = True
                    except BaseException:
                        repaired = False
                    _log(fh, run_id=run_id, commit=commit, probe=p.code,
                         phase="FIXTURE_REPAIR", attempt=attempt,
                         result="ATTEMPTED" if repaired else "FAILED",
                         code="OK" if repaired else "REPAIR_INEFFECTIVE")
                elif attempt <= MAX_REPAIRS:
                    break
            if not success:
                held.append(p.code)
                alternates[p.code] = ALTERNATIVES[p.code]
                _log(fh, run_id=run_id, commit=commit, probe=p.code,
                     phase="ALTERNATIVE", attempt=MAX_REPAIRS,
                     result="HOLD", code="REVIEW_REQUIRED",
                     route=ALTERNATIVES[p.code])
    return {
        "schema": SCHEMA, "task": TASK, "run_id": run_id,
        "mode": "SYNTHETIC_OFFLINE", "commit": commit,
        "passed": sorted(passed), "held": sorted(held),
        "alternative_routes": alternates, "log_file": name,
        "field_accepted": False, "worker_started": False,
        "task_completed": False,
        "recommendation": "QUALIFIED_HOST_GATE_REQUIRED" if not held
                          else "REVIEW_ALTERNATIVE_METHOD",
    }

def fixture_demo(root: Path, *, commit: str = "0"*40) -> dict:
    """One integrated dry run with a real failure, repair, and blocked fallback."""
    grant = {"valid": False}
    checkpoint = {"valid": False}
    def repair_grant_fixture() -> None:
        grant["valid"] = True
    probes = (
        Probe("GRANT", lambda: grant["valid"], repair_grant_fixture),
        Probe("CHECKPOINT", lambda: checkpoint["valid"]),
        Probe("SEQUENTIAL_RESOURCE", lambda: True),
    )
    return run_cycle(root, probes, commit=commit)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=Path, required=True)
    ap.add_argument("--commit", default="0"*40)
    ns = ap.parse_args()
    try:
        print(json.dumps(fixture_demo(ns.stage, commit=ns.commit), sort_keys=True))
    except StageRefusal as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc),
                          "task": TASK, "field_accepted": False}, sort_keys=True))
        sys.exit(2)
