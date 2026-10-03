from __future__ import annotations
import argparse,json,math,os,re,time,urllib.request
from difflib import SequenceMatcher
from pathlib import Path
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

ROOT=Path(r"C:\SAYDI"); CFG=json.loads((ROOT/"worker"/"config.json").read_text(encoding="utf-8"))
API=CFG["api_url"]; TOKEN=CFG["worker_token"]; QC=ROOT/"qc"; REPORTS=QC/"reports"; MODELS=QC/"models"

def call(action,**kw):
    data=json.dumps({"action":action,**kw},ensure_ascii=False).encode("utf-8")
    req=urllib.request.Request(API,data=data,headers={"Content-Type":"application/json","X-SAYDI-WORKER-TOKEN":TOKEN},method="POST")
    with urllib.request.urlopen(req,timeout=90) as r: out=json.loads(r.read().decode("utf-8"))
    if out.get("error"): raise RuntimeError(out["error"])
    return out

def chunks(job):
    out=[]; after=-1
    while True:
        rows=call("chunks",job_id=job,after_index=after,limit=20).get("chunks") or []
        if not rows: return out
        out+=rows; after=int(rows[-1]["chunk_index"])

def norm(s):
    return re.sub(r"\s+"," ",re.sub(r"[^\wÀ-ỹĐđ]+"," ",s.lower())).strip()

def sim(a,b):
    a,b=norm(a),norm(b)
    return SequenceMatcher(None,a,b).ratio() if a and b else 0.0

def metrics(p):
    a,sr=sf.read(str(p),dtype="float32",always_2d=False)
    if getattr(a,"ndim",1)>1: a=a.mean(axis=1)
    if len(a)==0: raise RuntimeError("empty")
    dur=len(a)/sr; peak=float(np.max(np.abs(a))); rms=math.sqrt(float(np.mean(a*a))+1e-12)
    clip=float(np.mean(np.abs(a)>=0.995)); thr=10**(-45/20); active=np.flatnonzero(np.abs(a)>thr)
    if active.size:
        lead=active[0]/sr; trail=(len(a)-1-active[-1])/sr
    else: lead=trail=dur
    frame=max(1,int(sr*.02)); longest=cur=0
    for i in range(len(a)//frame):
        x=a[i*frame:(i+1)*frame]; db=20*math.log10(max(math.sqrt(float(np.mean(x*x))+1e-12),1e-12))
        if db<-45: cur+=1; longest=max(longest,cur)
        else: cur=0
    return {"duration_sec":dur,"peak":peak,"rms_dbfs":20*math.log10(max(rms,1e-12)),"clipping_ratio":clip,
            "leading_silence_sec":lead,"trailing_silence_sec":trail,"longest_silence_sec":longest*.02}

def ev(t,sev,idx,s,e,score=None,**d):
    return {"event_type":t,"severity":sev,"chunk_index":idx,"time_start_sec":round(s,2),"time_end_sec":round(e,2),
            "score":None if score is None else round(float(score),4),"details":d}

def check(model,job,attempt):
    out=Path(job["output_file_name"]); cdir=out.parent/"chunks"; events=[]; repair=set(); cur=0.0; prevtrail=0.0
    rows=chunks(job["id"])
    for c in rows:
        idx=int(c["chunk_index"]); text=str(c.get("text_content") or ""); wav=cdir/f"{idx:06d}.wav"
        if not wav.exists() or wav.stat().st_size<1024:
            events.append(ev("missing_audio","error",idx,cur,cur)); repair.add(idx); continue
        try: m=metrics(wav)
        except Exception as x:
            events.append(ev("decode","error",idx,cur,cur,error=str(x))); repair.add(idx); continue
        s=cur; e=cur+m["duration_sec"]; cur=e
        if m["rms_dbfs"]<-48: events.append(ev("acoustic","error",idx,s,e,m["rms_dbfs"],reason="near_zero")); repair.add(idx)
        if m["clipping_ratio"]>.02: events.append(ev("clipping","error",idx,s,e,m["clipping_ratio"])); repair.add(idx)
        elif m["clipping_ratio"]>.002: events.append(ev("clipping","warning",idx,s,e,m["clipping_ratio"]))
        if len(text)>500 and m["duration_sec"]<8: events.append(ev("duration","error",idx,s,e,m["duration_sec"])); repair.add(idx)
        if m["longest_silence_sec"]>2.2: events.append(ev("silence","warning",idx,s,e,m["longest_silence_sec"]))
        gap=prevtrail+m["leading_silence_sec"] if idx>0 else 0
        if gap>1.2: events.append(ev("join_discontinuity","error",idx,s,s+gap,gap))
        elif gap>.65: events.append(ev("join_discontinuity","warning",idx,s,s+gap,gap))
        prevtrail=m["trailing_silence_sec"]
        try:
            segs,info=model.transcribe(str(wav),language="vi",beam_size=5,vad_filter=True,condition_on_previous_text=False)
            heard=" ".join(z.text.strip() for z in segs if z.text.strip()); q=sim(text,heard)
            if q<.55: events.append(ev("asr_mismatch","error",idx,s,e,q,expected=text[:160],heard=heard[:160]))
            elif q<.76: events.append(ev("asr_mismatch","warning",idx,s,e,q,expected=text[:160],heard=heard[:160]))
        except Exception as x: events.append(ev("asr_mismatch","warning",idx,s,e,error=str(x)[:300]))
    warn=sum(x["severity"]=="warning" for x in events); err=sum(x["severity"]=="error" for x in events)
    report={"source":"local_qc_v1","attempt":attempt,"chapter_number":job.get("chapter_number"),"checked_chunks":len(rows),
            "warnings":warn,"errors":err,"auto_repair_indices":sorted(repair),"asr_model":"small","audible_markers":False}
    call("qc_report_batch",job_id=job["id"],qc_status="passed" if not warn and not err else "review",qc_report=report,events=events)
    return report,sorted(repair)

def wait_done(book,jobid,limit=7200):
    end=time.time()+limit
    while time.time()<end:
        js=call("book_jobs",book_id=book,max_chapter=999).get("jobs") or []
        j=next((x for x in js if x["id"]==jobid),None)
        if j and j.get("status")=="completed" and j.get("output_file_name"): return j
        if j and j.get("status")=="failed": raise RuntimeError(j.get("error") or "repair failed")
        time.sleep(15)
    raise TimeoutError(jobid)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--book-id",required=True); p.add_argument("--max-chapter",type=int,default=5); a=p.parse_args()
    REPORTS.mkdir(parents=True,exist_ok=True); MODELS.mkdir(parents=True,exist_ok=True)
    model=WhisperModel("small",device="cpu",compute_type="int8",download_root=str(MODELS),cpu_threads=max(2,min(8,os.cpu_count() or 4)))
    jobs=call("book_jobs",book_id=a.book_id,max_chapter=a.max_chapter).get("jobs") or []
    jobs=[j for j in jobs if 1<=int(j.get("chapter_number") or 0)<=a.max_chapter]
    summary=[]
    for j in jobs:
        if j.get("status")!="completed": raise RuntimeError(f"chapter {j.get('chapter_number')} not complete")
        rep,repair=check(model,j,1)
        if repair:
            out=Path(j["output_file_name"]); cdir=out.parent/"chunks"
            for idx in repair:
                w=cdir/f"{idx:06d}.wav"
                if w.exists(): w.unlink()
            # Keep the last complete chapter MP3 available while repair runs.
            # The worker will overwrite/rebuild it after the repaired chunks finish.
            call("repair_chunks",job_id=j["id"],chunk_indices=repair)
            j=wait_done(a.book_id,j["id"]); rep,again=check(model,j,2)
            if again:
                rep["repair_exhausted"]=again
                call("qc_report_batch",job_id=j["id"],qc_status="failed",qc_report=rep,events=[])
        summary.append(rep)
    folder=REPORTS/a.book_id; folder.mkdir(parents=True,exist_ok=True)
    (folder/"qc_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# SAYDI QC Report",""]+[f"- Chương {x['chapter_number']}: warnings={x['warnings']} errors={x['errors']} repair={x['auto_repair_indices']}" for x in summary]
    (folder/"QC_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

if __name__=="__main__": main()
