# -*- coding: utf-8 -*-
"""One bounded V5 quality repair round. Original WAV and QC remain immutable."""
from __future__ import annotations
import argparse, ctypes, gc, hashlib, importlib.util, json, os, shutil, subprocess, sys, time
from pathlib import Path
for name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[name]="1"
ROOT=Path(r"C:\SAYDI")
C_BASE=ROOT/"output"/"OWNER_APPROVED_NATURAL_V5"
D_BASE=Path(r"D:\SAYDI\OWNER_APPROVED_NATURAL_V5")
V5=ROOT/"narration_director_v1"/"render_owner_approved_v5.py"
QC=ROOT/"narration_director_v1"/"qc_local_segments.py"
QC_PY=ROOT/"qc2"/".venv"/"Scripts"/"python.exe"

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))
def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(tmp,path)
def sha(path):
    with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def ram():
    class M(ctypes.Structure):
        _fields_=[("sz",ctypes.c_ulong),("load",ctypes.c_ulong),("total",ctypes.c_ulonglong),
                  ("free",ctypes.c_ulonglong),("page",ctypes.c_ulonglong),("pageFree",ctypes.c_ulonglong),
                  ("virtual",ctypes.c_ulonglong),("virtualFree",ctypes.c_ulonglong),
                  ("extended",ctypes.c_ulonglong)]
    x=M();x.sz=ctypes.sizeof(x)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(x))
    return x.free/(1024**3)
def cpu_cap():
    k=ctypes.windll.kernel32;k.GetCurrentProcess.restype=ctypes.c_void_p
    k.SetProcessAffinityMask.argtypes=(ctypes.c_void_p,ctypes.c_size_t)
    k.SetPriorityClass.argtypes=(ctypes.c_void_p,ctypes.c_uint)
    h=k.GetCurrentProcess()
    if not k.SetProcessAffinityMask(h,1):raise RuntimeError("TTS_CPU_CAP_FAILURE")
    k.SetPriorityClass(h,0x4000)

def locate(chapter):
    base=(C_BASE/"Chuong_01_R2") if chapter==1 else (D_BASE/f"Chuong_{chapter:02d}")
    manifest=base/"manifest.json"
    qfile=base/("QC_SELECTED_R2.json" if chapter==1 else "QC_AFTER_RENDER.json")
    if not manifest.exists() or not qfile.exists():raise RuntimeError("CHAPTER_NOT_QC_READY")
    return base,manifest,qfile

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--chapter",type=int,required=True)
    p.add_argument("--max-segments",type=int,default=8)
    args=p.parse_args()
    ch=args.chapter
    if ch not in range(1,12) or not 1<=args.max_segments<=12:raise ValueError("INVALID_SCOPE")
    cpu_cap()
    origin,manifestfile,qcfile=locate(ch)
    job=origin/"quality_v5"
    job.mkdir(parents=True,exist_ok=True)
    state=job/"status.json"
    def status(phase,**kw):
        save(state,{"chapter":ch,"phase":phase,"updated":time.strftime("%Y-%m-%d %H:%M:%S"),
                    "final":False,"owner_approved":False,**kw})
    if ram()<2.3:
        status("PAUSED_RESOURCE",reason="RAM_BELOW_2_3_GB",free_gb=round(ram(),2))
        return 0
    v5spec=importlib.util.spec_from_file_location("v5_owner",str(V5))
    v5=importlib.util.module_from_spec(v5spec);v5spec.loader.exec_module(v5)
    fingerprint=v5.reference_verified()
    master=read(manifestfile)
    if master.get("reference_sha256")!=fingerprint:raise RuntimeError("VOICE_REFERENCE_FINGERPRINT_CHANGED")
    rounds=sorted([p for p in job.glob("round_*") if (p/"qc_selected.json").exists()])
    baseline=rounds[-1] if rounds else origin
    actual_qc=(baseline/"qc_selected.json") if rounds else qcfile
    original=read(actual_qc)
    by_idx={int(x["index"]):x for x in original["rows"]}
    ledger_file=job/"attempt_ledger.json"
    ledger=read(ledger_file) if ledger_file.exists() else {}
    # Same basic algorithm for Ch1 and Ch2+: never rerender any known PASS segment.
    candidates=sorted([r for r in by_idx.values() if r["status"]!="PASS"],
                      key=lambda x:(float(x.get("asr_similarity",1)),int(x["index"])))
    choices=[int(r["index"]) for r in candidates if int(ledger.get(str(r["index"]),0))<2][:args.max_segments]
    if not choices:
        status("REVIEW_READY",reason="NO_SAFE_REPAIR_CANDIDATES",
               unresolved=sum(r["status"]!="PASS" for r in by_idx.values()))
        return 0
    item_map={int(x["index"]):x for x in master["segments"]}
    selected=job/"candidates"
    selected.mkdir(exist_ok=True)
    status("RENDERING_CANDIDATES",selected=choices,completed=0,total=len(choices))
    import soundfile as sf
    def valid_cached(idx):
        item=item_map[idx]
        key=hashlib.sha256((item["tts_text_sha256"]+"|V5_AUTOREPAIR_067").encode()).hexdigest()
        wav=selected/f"{idx:06d}.wav"
        marker=selected/f"{idx:06d}.key"
        return (wav.exists() and wav.stat().st_size>1024 and marker.exists()
                and marker.read_text().strip()==key)
    missing=[idx for idx in choices if not valid_cached(idx)]
    tts=None
    if missing:
        from vieneu import Vieneu
        tts=Vieneu(backend="onnx",precision="fp32")
        tts.add_voice(v5.VOICE,str(v5.REF),denoise=False,save=False,
                      description="Owner-approved V5 native audio; no atempo",gender="male")
    try:
        for j,idx in enumerate(choices):
            item=item_map[idx]
            dest=selected/f"{idx:06d}.wav"
            token=selected/f"{idx:06d}.key"
            key=hashlib.sha256((item["tts_text_sha256"]+"|V5_AUTOREPAIR_067").encode()).hexdigest()
            if not (dest.exists() and dest.stat().st_size>1024 and token.exists() and token.read_text().strip()==key):
                if ram()<.70:
                    status("PAUSED_RESOURCE",reason="RAM_DURING_VIENEU",completed=j,
                           selected=choices,total=len(choices))
                    return 0
                candidate=tts.infer(item["spoken_text"],voice=v5.VOICE,max_chars=320,
                                     temperature=.67,top_k=22,top_p=.90)
                tmp=dest.with_suffix(".partial.wav")
                tts.save(candidate,str(tmp))
                if sf.info(str(tmp)).duration<.25:raise RuntimeError(f"BAD_CANDIDATE_{idx}")
                os.replace(tmp,dest)
                token.write_text(key+"\n",encoding="utf-8")
            status("RENDERING_CANDIDATES",selected=choices,completed=j+1,total=len(choices))
    finally:
        if tts is not None:
            try:tts.close()
            except Exception:pass
            del tts
        gc.collect()
    if ram()<2.3:
        status("PAUSED_RESOURCE",reason="RAM_BEFORE_ASR",selected=choices,completed=len(choices),
               free_gb=round(ram(),2))
        return 0
    report=job/"candidate_qc.json"
    status("QC_TARGETED",selected=choices,completed=len(choices),total=len(choices))
    cached=None
    if report.exists():
        try:
            previous=read(report)["rows"]
            if ({int(x["index"]) for x in previous}==set(choices)
                and all(sha(selected/f'{int(x["index"]):06d}.wav')==x["audio_sha256"] for x in previous)):
                cached=previous
        except (KeyError,ValueError,OSError):
            cached=None
    if cached is None:
        with (job/"qc_console.log").open("w",encoding="utf-8") as out:
            process=subprocess.Popen([str(QC_PY),str(QC),"--manifest",str(manifestfile),
                 "--chunk-dir",str(selected),"--report",str(report),
                 "--indices",",".join(str(i) for i in choices)],stdout=out,stderr=subprocess.STDOUT)
            low_ram_ticks=0
            while process.poll() is None:
                time.sleep(3)
                low_ram_ticks=(low_ram_ticks+1) if ram()<.30 else 0
                if low_ram_ticks>=3:
                    process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
                    status("PAUSED_RESOURCE",reason="ASR_RAM_CRITICAL",selected=choices)
                    return 0
        if process.returncode:
            raise RuntimeError(f"QC_FAILED_{process.returncode}")
        checked=read(report)["rows"]
    else:
        checked=cached
    for row in checked:
        if sha(selected/f'{int(row["index"]):06d}.wav')!=row["audio_sha256"]:
            raise RuntimeError("CANDIDATE_QC_HASH_MISMATCH")
    audio_input=baseline/"chunks"
    for idx,r in by_idx.items():
        if sha(audio_input/f"{idx:06d}.wav")!=r["audio_sha256"]:
            raise RuntimeError(f"ORIGINAL_AUDIO_QC_HASH_MISMATCH_{idx}")
    # Accepted alternatives are staged in separate directory. Original audio is never overwritten.
    round_no=1 + len(rounds)
    while (job/f"round_{round_no:02d}").exists():round_no+=1
    target=job/f"round_{round_no:02d}"
    chunks=target/"chunks";chunks.mkdir(parents=True,exist_ok=False)
    for idx in by_idx:
        src=audio_input/f"{idx:06d}.wav";dst=chunks/src.name
        os.link(src,dst)  # source and destination always on the same volume
    improved=[]
    for row in checked:
        idx=int(row["index"]);old=by_idx[idx]
        new_sim=float(row.get("asr_similarity",0))
        old_sim=float(old.get("asr_similarity",0))
        new_conf=float(row.get("mean_word_confidence",0))
        old_conf=float(old.get("mean_word_confidence",0))
        good=(new_sim>=old_sim+.025 and new_conf>=old_conf-.08
              and (new_sim>=.78 or old_sim<.55))
        if good:
            dst=chunks/f"{idx:06d}.wav";tmp=dst.with_suffix(".replacement")
            shutil.copyfile(selected/dst.name,tmp);os.replace(tmp,dst)
            by_idx[idx]=row
            improved.append(idx)
        ledger[str(idx)]=int(ledger.get(str(idx),0))+1
    for idx,row in by_idx.items():
        if sha(chunks/f"{idx:06d}.wav")!=row["audio_sha256"]:
            raise RuntimeError("OUTPUT_QC_HASH_MISMATCH")
    save(ledger_file,ledger)
    status("ASSEMBLING_MP3",selected=choices,improved=improved)
    oldmod=v5.load_legacy_segmenter()
    output=target/f"CHUONG_{ch:02d}_OWNER_V5_QUALITY_R{round_no:02d}.REVIEW.mp3"
    duration=v5.assemble(master["segments"],chunks,output,oldmod)
    review=sum(x["status"]!="PASS" for x in by_idx.values())
    save(target/"qc_selected.json",{"rows":[by_idx[i] for i in sorted(by_idx)],"checked":len(by_idx),
         "flagged_indices":[i for i,r in sorted(by_idx.items()) if r["status"]!="PASS"],
         "human_listening_required":True})
    save(target/"REVIEW_STATUS.json",{"chapter":ch,"final":False,"owner_approved":False,
         "duration_sec":round(duration,2),"audio_path":str(output),"audio_sha256":sha(output),
         "original_basic_review":len(candidates),"remaining_basic_review":review,
         "candidates":choices,"improved":improved,
         "note":"ASR improvement alone cannot certify natural pronunciation."})
    status("REVIEW_READY",round=round_no,audio_path=str(output),
           remaining_basic_review=review,candidates=choices,improved=improved)
    print(f"CH{ch:02d} R{round_no:02d} chosen={len(improved)}/{len(choices)} review={review}; FINAL=False",flush=True)
    return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception as err:
        print(f"[SAYDI-QUALITY] {type(err).__name__}: {err}",file=sys.stderr,flush=True)
        raise
