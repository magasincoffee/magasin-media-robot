# -*- coding: utf-8 -*-
"""SAYDI Control commands: explicit local jobs, checkpoint-safe, queued on low RAM.

Never run a model from an HTTP handler. This coordinator owns one persistent
job request and launches a separate bounded process. Local API permits only
enumerated chapter/workflow actions. No FINAL approval action.
"""
from __future__ import annotations
import ctypes, json, os, secrets, subprocess, sys, threading, time
from pathlib import Path

HERE=Path(r"C:\SAYDI\control")
ROOT=Path(r"C:\SAYDI")
V5_ROOT=ROOT/"output"/"OWNER_APPROVED_NATURAL_V5"
D_ROOT=Path(r"D:\SAYDI\OWNER_APPROVED_NATURAL_V5")
SELECTED=HERE/"selected_chapter.json"
JOB=HERE/"control_job.json"
LOG=HERE/"job_controller.log"
PYTHON=ROOT/"VieNeu-TTS"/".venv"/"Scripts"/"python.exe"
CONTROL_PY=Path("C:/MAGASIN_MCP/.venv/Scripts/python.exe")
RECHECK_PYTHON=ROOT/"qc2"/".venv"/"Scripts"/"python.exe"
OWNER_MIN_GB=1.5
OWNER_CPU_THREADS=1
RUNTIME_ENV=("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS","RAYON_NUM_THREADS")
LOCK=threading.RLock()
ALLOWED={"select","resume","next","recheck","improve"}
COMPLETED={"DONE","FAILED","CANCELLED"}

def read(path):
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data,dict) else {}
    except (OSError,ValueError,UnicodeError):
        return {}

def persist(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".pending")
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(tmp,path)

def log(message):
    with LOG.open("a",encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

def free_ram():
    class M(ctypes.Structure):
        _fields_=[("length",ctypes.c_ulong),("load",ctypes.c_ulong),
                  ("total",ctypes.c_ulonglong),("available",ctypes.c_ulonglong),
                  ("page",ctypes.c_ulonglong),("pagefree",ctypes.c_ulonglong),
                  ("virtual",ctypes.c_ulonglong),("virtualfree",ctypes.c_ulonglong),
                  ("extended",ctypes.c_ulonglong)]
    m=M();m.length=ctypes.sizeof(m)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return round(m.available/1024**3,2)

def selected_chapter():
    c=read(SELECTED).get("chapter",1)
    return c if type(c) is int and 1<=c<=11 else 1

def validate_chapter(chapter):
    if type(chapter) is not int or not 1<=chapter<=11:
        raise ValueError("CHAPTER_MUST_BE_INTEGER_1_TO_11")
    return chapter

def base(ch):
    return V5_ROOT/"Chuong_01_R2" if ch==1 else D_ROOT/f"Chuong_{ch:02d}"

def qc_baseline(ch):
    folder=base(ch)
    return folder/("QC_SELECTED_R2.json" if ch==1 else "QC_AFTER_RENDER.json")

def chapter_data(ch):
    folder=base(ch)
    state=read(V5_ROOT/"Chuong_01"/"render_state.json") if ch==1 else read(folder/"job_status.json")
    report=read(qc_baseline(ch))
    quality=read(folder/"quality_v5"/"status.json")
    recheck=read(folder/"qc_recheck_v5"/"status.json")
    canonical=ROOT/"narration_director_v1"/"doanh_nghiep_tu_hanh_v4"/f"chapter_{ch:02d}_canonical.txt"
    if ch==1:
        r2=read(folder/"REVIEW_STATUS.json")
        total=int(state.get("total") or r2.get("segments") or 0)
        rendered=int(state.get("rendered") or total)
        checked=int(state.get("qc_checked") or total)
        phase=("REVIEW_READY" if r2.get("status")=="FULL_R2_READY_FOR_OWNER_REVIEW"
               else state.get("status","UNKNOWN"))
        review=int(r2.get("basic_qc_review_remaining",0))
    else:
        total=int(state.get("total",0))
        rendered=int(state.get("rendered",0))
        checked=int(state.get("qc_checked",0))
        phase=state.get("stage","NOT_PREPARED")
        if state.get("reason")=="PREPARED_ONLY":
            phase="PREPARED_WAIT_OWNER"
        review=state.get("review_count")
    if report.get("rows"):
        review=sum(r.get("status")!="PASS" for r in report["rows"])
        if not checked:checked=int(report.get("checked",0))
    rounds=sorted(p for p in (folder/"quality_v5").glob("round_*")
                  if (p/"REVIEW_STATUS.json").exists())
    if rounds:
        q=read(rounds[-1]/"REVIEW_STATUS.json")
        review=q.get("remaining_basic_review",review)
        audio_available=Path(q.get("audio_path","")).exists()
    elif ch==1:
        audio_available=(folder/"CHUONG_01_V5_R2_SUA_LOI_NANG.REVIEW.mp3").exists()
    else:
        audio_available=(folder/f"CHUONG_{ch:02d}_OWNER_APPROVED_V5.REVIEW.mp3").exists()
    return {
        "chapter":ch,"source_available":canonical.exists(),
        "phase":phase,"total":total,"rendered":rendered,"qc_checked":checked,
        "review":review,"recheck":recheck.get("phase"),
        "quality":quality.get("phase"),
        "quality_review":quality.get("remaining_basic_review"),
        "can_resume":ch>=2 and canonical.exists() and phase!="REVIEW_READY",
        "can_recheck":bool(report.get("rows")),"can_improve":bool(report.get("rows")),
        "audio_available":audio_available,"is_final":False,
    }

def catalog():
    return [chapter_data(n) for n in range(1,12)]

def known_heavy():
    try:
        import psutil
        kinds=("chapter2_v5_qc_guarded.py","chapter_v5_job.py",
               "qc_local_segments.py","render_owner_approved_v5.py",
               "repair_chapter1_owner_v5_r2.py","saydi_review_qc.py",
               "saydi_quality_improve.py","render_business_natural_v4.py")
        found=[]
        for p in psutil.process_iter(["pid","name","cmdline"]):
            try:
                if (p.info.get("name") or "").lower() not in ("python.exe","pythonw.exe"):
                    continue
                argv=p.info.get("cmdline") or []
                script=next((Path(arg.strip('"')).name.lower() for arg in argv[1:]
                             if arg.strip('"').lower().endswith(".py")), "")
                if script in kinds:
                    found.append(int(p.pid))
            except (psutil.AccessDenied,psutil.NoSuchProcess):continue
        return found
    except ImportError:
        # Fail closed if process inventory unavailable.
        return [-1]

def job_status():
    return read(JOB)

def launch_tick():
    script=HERE/"control_commands.py"
    if not script.exists():raise RuntimeError("CONTROLLER_FILE_MISSING")
    if not CONTROL_PY.exists():raise RuntimeError("CONTROLLER_PYTHON_MISSING")
    out=HERE/"last_tick.log"
    out.parent.mkdir(parents=True,exist_ok=True)
    flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
    with out.open("ab") as f:
        proc=subprocess.Popen([str(CONTROL_PY),str(script),"--tick"],stdin=subprocess.DEVNULL,
                              stdout=f,stderr=subprocess.STDOUT,creationflags=flags,
                              close_fds=True)
    return proc.pid

def submit(action,chapter):
    if action not in ALLOWED:raise ValueError("UNSUPPORTED_ACTION")
    with LOCK:
        chapter=validate_chapter(chapter)
        current=job_status()
        if action=="select":
            persist(SELECTED,{"chapter":chapter,"updated":time.strftime("%Y-%m-%d %H:%M:%S")})
            return {"accepted":True,"action":"select","selected":chapter}
        if action=="next":
            if chapter>=11:raise ValueError("NO_CHAPTER_AFTER_11")
            chapter+=1
            action="resume"
        if action=="resume":
            if not chapter_data(chapter)["can_resume"]:
                raise ValueError("CHAPTER_READY_OR_SOURCE_MISSING")
        elif action in ("recheck","improve"):
            if not qc_baseline(chapter).exists():
                raise ValueError("CHAPTER_QC_BASELINE_NOT_FOUND")
        if current.get("state") not in (None,"DONE","FAILED","CANCELLED"):
            raise RuntimeError("ANOTHER_JOB_ALREADY_QUEUED_OR_RUNNING")
        job={"id":secrets.token_hex(10),"action":action,"chapter":chapter,
             "state":"QUEUED","queued_at":time.strftime("%Y-%m-%d %H:%M:%S"),
             "attempts":0,"final":False}
        persist(SELECTED,{"chapter":chapter,"updated":job["queued_at"]})
        persist(JOB,job)
        pid=launch_tick()
        log(f"QUEUED action={action} chapter={chapter} id={job['id']} tick_pid={pid}")
        return {"accepted":True,"job_id":job["id"],"action":action,
                "chapter":chapter,"state":"QUEUED"}

def exclusive_mutex():
    k=ctypes.windll.kernel32
    k.CreateMutexW.argtypes=(ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p)
    k.CreateMutexW.restype=ctypes.c_void_p
    handle=k.CreateMutexW(None,True,r"Local\SAYDI_CONTROL_EXCLUSIVE_JOB")
    if not handle:raise RuntimeError("CANNOT_CREATE_CONTROL_MUTEX")
    if k.GetLastError()==183:
        k.CloseHandle(ctypes.c_void_p(handle))
        return None
    return handle

def execute_tick():
    mutex=exclusive_mutex()
    if mutex is None:return 0
    k=ctypes.windll.kernel32
    try:
        job=job_status()
        if job.get("state") in COMPLETED or not job.get("action"):
            return 0
        chapter=validate_chapter(job.get("chapter"))
        job["last_check_at"]=time.strftime("%Y-%m-%d %H:%M:%S")
        job["last_check_free_ram_gb"]=free_ram()
        job["check_count"]=int(job.get("check_count") or 0)+1
        if known_heavy():
            job.update(state="WAIT_OTHER_WORKER",detail="Other SAYDI render/QC process is active.")
            persist(JOB,job)
            return 0
        free=free_ram()
        if free<OWNER_MIN_GB:
            job.update(state="QUEUED_RESOURCE",free_ram_gb=free,
                       detail=f"Requires at least {OWNER_MIN_GB:.1f} GB free RAM before expensive work.")
            persist(JOB,job)
            return 0
        action=job["action"]
        if action=="resume":
            argv=[str(PYTHON),str(ROOT/"narration_director_v1"/"chapter_v5_job.py"),
                  "--chapter",str(chapter)]
        elif action=="recheck":
            argv=[str(RECHECK_PYTHON),str(ROOT/"narration_director_v1"/"saydi_review_qc.py"),
                  "--chapter",str(chapter)]
        elif action=="improve":
            argv=[str(PYTHON),str(ROOT/"narration_director_v1"/"saydi_quality_improve.py"),
                  "--chapter",str(chapter),"--max-segments","8"]
        else:raise RuntimeError("INTERNAL_INVALID_ACTION")
        job.update(state="RUNNING",started_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                   attempts=int(job.get("attempts",0))+1,free_ram_gb=free,
                   cpu_threads=OWNER_CPU_THREADS,execution_mode="SEQUENTIAL_NATIVE_V5")
        persist(JOB,job)
        output=HERE/f"job_{job['id']}.log"
        flags=getattr(subprocess,"CREATE_NO_WINDOW",0)|getattr(subprocess,"BELOW_NORMAL_PRIORITY_CLASS",0)
        env=os.environ.copy()
        for key in RUNTIME_ENV:
            env[key]=str(OWNER_CPU_THREADS)
        env["TOKENIZERS_PARALLELISM"]="false"
        with output.open("ab") as f:
            p=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,
                               creationflags=flags,env=env)
            job["pid"]=p.pid
            persist(JOB,job)
            while True:
                try:
                    rc=p.wait(timeout=25)
                    break
                except subprocess.TimeoutExpired:
                    # Durable worker heartbeat while Task Scheduler owns the long-running tick.
                    job["last_check_at"]=time.strftime("%Y-%m-%d %H:%M:%S")
                    job["last_check_free_ram_gb"]=free_ram()
                    job["check_count"]=int(job.get("check_count") or 0)+1
                    persist(JOB,job)
        job["exit_code"]=rc
        job["finished_at"]=time.strftime("%Y-%m-%d %H:%M:%S")
        if rc:
            job["state"]="FAILED"
            job["detail"]="Worker exit code "+str(rc)+"; inspect local job log"
        else:
            if action=="resume":
                phase=chapter_data(chapter)["phase"]
            elif action=="recheck":
                phase=read(base(chapter)/"qc_recheck_v5"/"status.json").get("phase")
            else:
                phase=read(base(chapter)/"quality_v5"/"status.json").get("phase")
            job["worker_phase"]=phase
            if phase in ("PAUSED_RESOURCE","QUEUED_RESOURCE"):
                job["state"]="QUEUED_RESOURCE"
                job["detail"]="Saved checkpoint; waiting for more free RAM."
            elif phase in ("FAILED","QC_FAILED"):
                job["state"]="FAILED"
            elif phase=="REVIEW_READY":
                job["state"]="DONE"
                job["detail"]="Review audio/QC produced; FINAL still requires listening approval."
            else:
                job["state"]="QUEUED"
                job["detail"]="Additional checkpointed processing required."
        persist(JOB,job)
        log(f"JOB id={job['id']} action={action} ch={chapter} state={job['state']} rc={rc}")
        return 0
    finally:
        k.ReleaseMutex(ctypes.c_void_p(mutex))
        k.CloseHandle(ctypes.c_void_p(mutex))

if __name__=="__main__":
    raise SystemExit(execute_tick() if "--tick" in sys.argv else 2)
