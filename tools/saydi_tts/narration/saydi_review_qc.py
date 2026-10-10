# -*- coding: utf-8 -*-
"""Recheck ONLY flagged audio WAVs. Never change an accepted audio file or mark FINAL."""
from __future__ import annotations
import argparse, ctypes, hashlib, json, os, subprocess, sys, time
from pathlib import Path
for key in ("OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[key]="1"
ROOT=Path(r"C:\SAYDI")
BASE=ROOT/"output"/"OWNER_APPROVED_NATURAL_V5"
D_BASE=Path(r"D:\SAYDI\OWNER_APPROVED_NATURAL_V5")
QC_PY=ROOT/"qc2"/".venv"/"Scripts"/"python.exe"
QC_SCRIPT=ROOT/"narration_director_v1"/"qc_local_segments.py"

def hashfile(path):
    with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(tmp,path)

def free_ram():
    class M(ctypes.Structure):
        _fields_=[("length",ctypes.c_ulong),("load",ctypes.c_ulong),("total",ctypes.c_ulonglong),
                  ("available",ctypes.c_ulonglong),("page",ctypes.c_ulonglong),("page_free",ctypes.c_ulonglong),
                  ("virtual",ctypes.c_ulonglong),("virtual_free",ctypes.c_ulonglong),
                  ("extended",ctypes.c_ulonglong)]
    m=M();m.length=ctypes.sizeof(m)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.available/1024**3

def limit_cpu():
    k=ctypes.windll.kernel32;k.GetCurrentProcess.restype=ctypes.c_void_p
    k.SetProcessAffinityMask.argtypes=(ctypes.c_void_p,ctypes.c_size_t)
    k.SetPriorityClass.argtypes=(ctypes.c_void_p,ctypes.c_uint)
    h=k.GetCurrentProcess()
    if not k.SetProcessAffinityMask(h,1):raise RuntimeError("QC_CPU_LIMIT_FAILED")
    k.SetPriorityClass(h,0x4000)

def source(chapter):
    if chapter==1:
        folder=BASE/"Chuong_01_R2"
        qc=folder/"QC_SELECTED_R2.json"
    else:
        folder=D_BASE/f"Chuong_{chapter:02d}"
        qc=folder/"QC_AFTER_RENDER.json"
    return folder,qc

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--chapter",type=int,required=True)
    args=a.parse_args()
    chapter=args.chapter
    if chapter not in range(1,12):raise ValueError("INVALID_CHAPTER")
    folder,original_qc=source(chapter)
    if not original_qc.exists():
        raise RuntimeError("QC_BASELINE_NOT_AVAILABLE")
    baseline=json.loads(original_qc.read_text(encoding="utf-8"))
    rows={int(r["index"]):r for r in baseline["rows"]}
    flagged=[x for x in rows.values() if x["status"]!="PASS" or float(x.get("asr_similarity",0))<.985]
    indices=sorted({int(x["index"]) for x in flagged})
    chunks=folder/"chunks"
    for idx in indices:
        path=chunks/f"{idx:06d}.wav"
        if not path.exists() or hashfile(path)!=rows[idx]["audio_sha256"]:
            raise RuntimeError(f"BASELINE_WAV_HASH_MISMATCH_{idx}")
    target=folder/"qc_recheck_v5"
    target.mkdir(parents=True,exist_ok=True)
    state=target/"status.json"
    stamp=lambda:time.strftime("%Y-%m-%d %H:%M:%S")
    def record(phase,**data):
        write(state,{"chapter":chapter,"phase":phase,"updated":stamp(),"total":len(indices),
                     "completed":data.get("completed",0),"final":False,**data})
    if not indices:
        record("REVIEW_READY",completed=0,confirmed_pass=0,remaining=0)
        return 0
    limit_cpu()
    checked=[]
    batch_size=30
    for start in range(0,len(indices),batch_size):
        block=indices[start:start+batch_size]
        first,last=block[0],block[-1]
        report=target/f"qc_{first:04d}_{last:04d}.json"
        previous=None
        if report.exists():
            try:
                previous=json.loads(report.read_text(encoding="utf-8"))
                if {int(x["index"]) for x in previous["rows"]}!={int(x) for x in block}:
                    previous=None
                elif any(hashfile(chunks/f'{int(r["index"]):06d}.wav')!=r["audio_sha256"]
                         for r in previous["rows"]):
                    previous=None
            except (ValueError,KeyError,OSError):previous=None
        if previous is None:
            if free_ram()<2.3:
                record("PAUSED_RESOURCE",completed=len(checked),reason="RAM_BELOW_2_3_GB",
                       free_gb=round(free_ram(),2))
                return 0
            record("QC_RUNNING",completed=len(checked),batch=f"{first}-{last}")
            cmd=[str(QC_PY),str(QC_SCRIPT),"--manifest",str(folder/"manifest.json"),
                 "--chunk-dir",str(chunks),"--report",str(report),
                 "--indices",",".join(str(x) for x in block)]
            with (target/f"log_{first:04d}_{last:04d}.txt").open("w",encoding="utf-8") as f:
                p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT)
                while p.poll() is None:
                    time.sleep(4)
                    if free_ram()<.30:
                        p.terminate()
                        try:p.wait(timeout=12)
                        except subprocess.TimeoutExpired:p.kill();p.wait()
                        record("PAUSED_RESOURCE",completed=len(checked),reason="RAM_CRITICAL")
                        return 0
            if p.returncode:
                record("FAILED",completed=len(checked),reason=f"QC_EXIT_{p.returncode}")
                return int(p.returncode)
            previous=json.loads(report.read_text(encoding="utf-8"))
            if any(hashfile(chunks/f'{int(r["index"]):06d}.wav')!=r["audio_sha256"]
                   for r in previous["rows"]):
                raise RuntimeError("RECHECK_QC_HASH_MISMATCH")
        checked.extend(previous["rows"])
        record("QC_RUNNING",completed=len(checked))
    count=sum(x["status"]!="PASS" or float(x.get("asr_similarity",0))<.985 for x in checked)
    write(target/"qc_summary.json",{
        "chapter":chapter,"checked":len(checked),"remaining_asr_warnings":count,
        "flagged_original":len(indices),"final":False,"human_approved":False,
        "note":"Rechecking the same WAV does not automatically repair wrong pronunciation.",
        "rows":checked})
    record("REVIEW_READY",completed=len(checked),remaining=count)
    return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception as exc:
        print(f"[SAYDI-QC] {type(exc).__name__}: {exc}",file=sys.stderr,flush=True)
        raise
