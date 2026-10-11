r"""Stage-only patch generator for existing SAYDI Control — NEVER installs live.

Copies the exact hash-pinned existing controller to a new D: staging file,
inserting a fail-closed resource check before subprocess dispatch.
No writing to C:\SAYDI, Windows Scheduler, Supabase or Owner STOP state.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "saydi-vn8gb-stage-controller-v1"
SOURCE_FILE_NAME = "control_commands.py"
REQUIRED_ANCHORS = (
    "def execute_tick():",
    "        if known_heavy():",
    "        free=free_ram()",
    "            p=subprocess.Popen(argv,",
)
HOOK = """        # VN8GB_STAGED_ONLY_GUARD: NOT authenticated to launch live workers
        from vn_8gb_controller_bridge import staged_guard_before_dispatch
        vn8gb_preflight = staged_guard_before_dispatch(job)
        if vn8gb_preflight["decision"] != "ELIGIBLE_FOR_EXISTING_AUTHORIZED_CHECKS":
            job.update(
                state="QUEUED_RESOURCE",
                detail="VN8GB_HOLD:" + ",".join(vn8gb_preflight["reasons"][:4]),
            )
            persist(JOB, job)
            return 0
"""

def build_staged_source(original: str) -> str:
    if "VN8GB_STAGED_ONLY_GUARD" in original:
        raise ValueError("ALREADY_PATCHED_REFUSE_DUPLICATE")
    for needle in REQUIRED_ANCHORS:
        if original.count(needle) != 1:
            raise ValueError("EXACT_ANCHOR_MISMATCH")
    target = "        free=free_ram()"
    result = original.replace(target, HOOK + target, 1)
    compile(result, SOURCE_FILE_NAME, "exec")
    return result

def stage(source: Path, destination: Path, expected_source_sha256: str) -> dict:
    if source.name.lower() != SOURCE_FILE_NAME:
        raise ValueError("WRONG_SOURCE_SCRIPT")
    if not expected_source_sha256 or len(expected_source_sha256) != 64:
        raise ValueError("MISSING_EXACT_SOURCE_SHA")
    # Allow only staging location; no capability to patch C: installed script.
    staging_root = Path(r"D:\SAYDI\QC_STAGING")
    if destination == source or str(destination).lower().startswith("c:\\"):
        raise ValueError("PRODUCTION_TARGET_FORBIDDEN")
    if not str(destination).lower().startswith(str(staging_root).lower() + "\\"):
        raise ValueError("NOT_IN_APPROVED_D_STAGING_ROOT")
    if destination.exists():
        raise FileExistsError("EXCLUSIVE_DESTINATION_REQUIRED")
    raw = source.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual.lower() != expected_source_sha256.lower():
        raise ValueError("SOURCE_SHA_CHANGED_REFUSE_PATCH")
    original = raw.decode("utf-8-sig")
    staged = build_staged_source(original)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as dest:
        dest.write(staged)
    return {
        "schema": SCHEMA,
        "source_sha256": actual,
        "staged_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "staged_only": True,
        "production_modified": False,
        "worker_started": False,
    }

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--dest",required=True,type=Path)
    p.add_argument("--expected-source-sha256",required=True)
    args=p.parse_args()
    try:
        result=stage(args.source,args.dest,args.expected_source_sha256)
    except (OSError,UnicodeError,ValueError):
        print(json.dumps({"schema":SCHEMA,"status":"HOLD","production_modified":False}))
        return 21
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
