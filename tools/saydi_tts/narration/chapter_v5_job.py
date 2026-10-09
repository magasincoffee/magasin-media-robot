# -*- coding: utf-8 -*-
"""Run a source-faithful V5 chapter 2..11 with the existing checkpointed pipeline.

Keeps Chapter 2's existing production logic but patches its chapter-specific
runtime paths before calling run(). Never uses V4 output as completed V5 work.
"""
from __future__ import annotations
import argparse
import importlib.util
import os
import sys
from pathlib import Path

RUNNER=Path(r"C:\SAYDI\narration_director_v1\chapter2_v5_qc_guarded.py")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--chapter",type=int,required=True)
    p.add_argument("--prepare-only",action="store_true")
    a=p.parse_args()
    if a.chapter not in range(2,12):
        p.error("Only chapter 2 to chapter 11 can use the V5 chapter pipeline")
    if not RUNNER.exists():
        raise RuntimeError("Chapter 2 V5 base runner not installed")
    spec=importlib.util.spec_from_file_location("v5_base_chapter",str(RUNNER))
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    work=Path(r"D:\SAYDI\OWNER_APPROVED_NATURAL_V5")/f"Chuong_{a.chapter:02d}"
    mod.CHAPTER=a.chapter
    mod.WORK=work
    mod.CHUNKS=work/"chunks"
    mod.QC_BATCHES=work/"qc_batches"
    mod.STATUS_PATH=work/"job_status.json"
    mod.POINTER=Path(r"C:\SAYDI\output\OWNER_APPROVED_NATURAL_V5")/f"CH{a.chapter:02d}_V5_STATUS.json"
    mod.RUN_LOG=work/"job.log"
    mod.WIN_MUTEX=rf"Local\SAYDI_OWNER_V5_CH{a.chapter:02d}_EXCLUSIVE"
    # Avoid misleading fixed Chapter 2 flag messages and skip only our own pid.
    old_heavy=mod.active_heavy_jobs
    def detect_all_jobs():
        import subprocess
        cmd=("$ErrorActionPreference='SilentlyContinue';"
             "Get-CimInstance Win32_Process | Where-Object {"
             "$_.Name -match 'python.exe|pythonw.exe' -and $_.CommandLine -match "
             "'chapter_v5_job.py|chapter2_v5_qc_guarded.py|qc_local_segments.py|"
             "repair_chapter1_owner_v5_r2.py|render_owner_approved_v5.py|"
             "render_business_natural_v4.py|saydi_quality_improve.py' } | "
             "Select-Object -ExpandProperty ProcessId")
        r=subprocess.run(["powershell.exe","-NoProfile","-Command",cmd],
                         capture_output=True,text=True,timeout=15)
        return [{"pid":int(x.strip())} for x in r.stdout.splitlines()
                if x.strip().isdigit() and int(x.strip())!=os.getpid()]
    mod.active_heavy_jobs=detect_all_jobs
    return mod.run(a.prepare_only)

if __name__=="__main__":
    raise SystemExit(main())
