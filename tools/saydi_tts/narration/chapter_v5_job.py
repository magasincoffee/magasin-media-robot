# -*- coding: utf-8 -*-
"""Chapter 2–11 source-faithful SAYDI V5 rendering and sequential QC.

Runs the same checkpointed V5 pipeline with chapter-specific output roots.
A process-tree-aware guard prevents concurrent *external* SAYDI workers
without incorrectly treating this worker's Windows python.exe launcher as
another active render.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

ROOT=Path(r"C:\SAYDI")
RUNNER=ROOT/"narration_director_v1"/"chapter2_v5_qc_guarded.py"
HEAVY_SCRIPTS={
    "chapter_v5_job.py","chapter2_v5_qc_guarded.py",
    "qc_local_segments.py","render_owner_approved_v5.py",
    "repair_chapter1_owner_v5_r2.py","saydi_review_qc.py",
    "saydi_quality_improve.py","render_business_natural_v4.py",
}

def detect_external_heavy_jobs():
    """Read the Windows process tree, excluding ourselves and our Python launchers."""
    command=(
      "$ErrorActionPreference='Stop';"
      "Get-CimInstance Win32_Process | Where-Object {"
      "$_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe'"
      "} | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    )
    try:
        result=subprocess.run(["powershell.exe","-NoProfile","-Command",command],
                              capture_output=True,text=True,timeout=17,check=False)
        if result.returncode!=0 or not result.stdout.strip():
            return [{"pid":-1,"reason":"PROCESS_INVENTORY_UNAVAILABLE"}]
        parsed=json.loads(result.stdout)
        rows=parsed if isinstance(parsed,list) else [parsed]
        by_pid={int(x["ProcessId"]):x for x in rows if x.get("ProcessId") is not None}
    except (OSError,ValueError,subprocess.TimeoutExpired,KeyError):
        return [{"pid":-1,"reason":"PROCESS_INVENTORY_UNAVAILABLE"}]

    # On Windows a venv python.exe can spawn another python.exe with identical
    # command line. Its parent is *not* a different SAYDI job.
    ancestors=set()
    current=os.getpid()
    while current>0 and current not in ancestors:
        ancestors.add(current)
        process=by_pid.get(current)
        if process is None:
            break
        current=int(process.get("ParentProcessId") or 0)

    result=[]
    for pid,record in by_pid.items():
        if pid in ancestors:
            continue
        cmd=str(record.get("CommandLine") or "").lower()
        if not cmd or re.search(r"\s-(?:c|m)(?:\s|$)",cmd):
            # Python -c diagnostic probes and module launchers do not count
            # merely for mentioning the name of a real worker script.
            continue
        names=[name for name in HEAVY_SCRIPTS
               if re.search(r"(?:^|[\\/\s])"+re.escape(name)+r"(?=$|[\s\"])",cmd)]
        if names:
            result.append({"pid":pid,"parent_pid":record.get("ParentProcessId"),
                           "worker_script":names[0]})
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--chapter",type=int,required=True)
    parser.add_argument("--prepare-only",action="store_true")
    args=parser.parse_args()
    if args.chapter not in range(2,12):
        parser.error("Only chapters 2–11 have a V5 incremental chapter pipeline")
    if not RUNNER.is_file():
        raise RuntimeError("Base V5 chapter pipeline is not installed")
    spec=importlib.util.spec_from_file_location("saydi_v5_chapter_base",str(RUNNER))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    work=Path(r"D:\SAYDI\OWNER_APPROVED_NATURAL_V5")/f"Chuong_{args.chapter:02d}"
    module.CHAPTER=args.chapter
    module.WORK=work
    module.CHUNKS=work/"chunks"
    module.QC_BATCHES=work/"qc_batches"
    module.STATUS_PATH=work/"job_status.json"
    module.POINTER=ROOT/"output"/"OWNER_APPROVED_NATURAL_V5"/f"CH{args.chapter:02d}_V5_STATUS.json"
    module.RUN_LOG=work/"job.log"
    module.WIN_MUTEX=rf"Local\SAYDI_OWNER_V5_CH{args.chapter:02d}_EXCLUSIVE"
    module.active_heavy_jobs=detect_external_heavy_jobs
    return module.run(args.prepare_only)

if __name__=="__main__":
    raise SystemExit(main())
