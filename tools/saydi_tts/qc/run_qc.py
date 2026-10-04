from __future__ import annotations
import argparse,hashlib,json,math,os,re,time,urllib.request
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

def _sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as fh:
        for block in iter(lambda:fh.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def _pitch_variation(a,sr):
    # Coarse local F0 variation detector. It is intentionally provider-neutral
    # and used as a QC signal, not as a phonetic truth source.
    frame=max(256,int(sr*.05)); hop=max(128,int(sr*.05))
    min_lag=max(1,int(sr/350)); max_lag=max(min_lag+1,int(sr/70))
    f0=[]
    for start in range(0,max(0,len(a)-frame+1),hop):
        x=np.asarray(a[start:start+frame],dtype=np.float64)
        rms=math.sqrt(float(np.mean(x*x))+1e-12)
        if 20*math.log10(max(rms,1e-12))<-38: continue
        x=x-float(np.mean(x)); x*=np.hanning(len(x))
        nfft=1
        while nfft < len(x)*2: nfft*=2
        spec=np.fft.rfft(x,n=nfft); ac=np.fft.irfft(spec*np.conj(spec),n=nfft)[:len(x)]
        if ac[0]<=1e-12: continue
        hi=min(max_lag,len(ac)-1)
        if hi<=min_lag: continue
        lag=min_lag+int(np.argmax(ac[min_lag:hi+1]))
        confidence=float(ac[lag]/ac[0])
        if confidence<.25: continue
        hz=sr/lag
        if 70<=hz<=350: f0.append(float(hz))
    if len(f0)<4: return None
    arr=np.asarray(f0,dtype=np.float64); med=float(np.median(arr))
    semi=12*np.log2(arr/med)
    return float(np.std(semi))

def metrics(p):
    a,sr=sf.read(str(p),dtype="float32",always_2d=False)
    if getattr(a,"ndim",1)>1: a=a.mean(axis=1)
    if len(a)==0: raise RuntimeError("empty")
    dur=len(a)/sr; peak=float(np.max(np.abs(a))); rms=math.sqrt(float(np.mean(a*a))+1e-12)
    clip=float(np.mean(np.abs(a)>=0.995)); thr=10**(-45/20); active=np.flatnonzero(np.abs(a)>thr)
    if active.size:
        lead=active[0]/sr; trail=(len(a)-1-active[-1])/sr
    else: lead=trail=dur
    frame=max(1,int(sr*.02)); longest=cur=0; silent=0; frame_db=[]
    frame_count=len(a)//frame
    for i in range(frame_count):
        x=a[i*frame:(i+1)*frame]; db=20*math.log10(max(math.sqrt(float(np.mean(x*x))+1e-12),1e-12))
        frame_db.append(db)
        if db<-45:
            silent+=1; cur+=1; longest=max(longest,cur)
        else:
            cur=0
    active_db=[x for x in frame_db if x>=-45]
    return {"duration_sec":dur,"peak":peak,"rms_dbfs":20*math.log10(max(rms,1e-12)),"clipping_ratio":clip,
            "leading_silence_sec":lead,"trailing_silence_sec":trail,"longest_silence_sec":longest*.02,
            "pause_ratio":(silent/frame_count if frame_count else 1.0),
            "energy_variation_db":(float(np.std(active_db)) if len(active_db)>=2 else 0.0),
            "pitch_variation_semitones":_pitch_variation(a,sr),
            "audio_sha256":_sha256(p)}

def ev(t,sev,idx,s,e,score=None,**d):
    return {"event_type":t,"severity":sev,"chunk_index":idx,"time_start_sec":round(s,2),"time_end_sec":round(e,2),
            "score":None if score is None else round(float(score),4),"details":d}

def check(model,job,attempt):
    out=Path(job["output_file_name"]); cdir=out.parent/"chunks"; events=[]; observations=[]; repair=set(); cur=0.0; prevtrail=0.0
    rows=chunks(job["id"])
    chapter=int(job.get("chapter_number") or 0)
    total=len(rows)
    started=time.time()
    progress_path=QC/"qc_progress.json"
    print(f"[QC] Chapter {chapter}: START | {total} chunks | attempt={attempt}", flush=True)
    for pos,c in enumerate(rows, start=1):
        idx=int(c["chunk_index"]); text=str(c.get("text_content") or ""); wav=cdir/f"{idx:06d}.wav"
        chunk_started=time.time()
        elapsed=chunk_started-started
        avg=(elapsed/(pos-1)) if pos>1 else 0.0
        eta=avg*(total-pos+1)
        print(f"[QC] Chapter {chapter} | chunk {pos}/{total} (id={idx}) | ASR starting | elapsed={elapsed/60:.1f}m | ETA~{eta/60:.1f}m", flush=True)
        progress_path.write_text(json.dumps({
            "chapter":chapter,"chunk_position":pos,"chunk_index":idx,"total_chunks":total,
            "attempt":attempt,"stage":"asr","elapsed_sec":round(elapsed,1),"eta_sec":round(eta,1),
            "updated_at":time.strftime("%Y-%m-%d %H:%M:%S")
        },ensure_ascii=False,indent=2),encoding="utf-8")
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
            segs,info=model.transcribe(str(wav),language="vi",beam_size=5,vad_filter=True,
                                       condition_on_previous_text=False,word_timestamps=True)
            segs=list(segs)
            heard=" ".join(z.text.strip() for z in segs if z.text.strip()); q=sim(text,heard)
            words=[w for z in segs for w in (getattr(z,"words",None) or []) if getattr(w,"word","").strip()]
            probs=[float(w.probability) for w in words if getattr(w,"probability",None) is not None]
            min_conf=min(probs) if probs else None
            mean_conf=(sum(probs)/len(probs)) if probs else None
            unclear=[w.word.strip() for w in words
                     if getattr(w,"probability",None) is not None and float(w.probability)<.60]
            word_count=len(words) if words else len(norm(heard).split())
            speaking_rate=(word_count/max(m["duration_sec"]/60.0,1e-6)) if word_count else 0.0
            obs={"chunk_index":idx,"audio_sha256":m["audio_sha256"],"attempt":attempt,
                 "asr_similarity":round(q,4),
                 "min_word_confidence":None if min_conf is None else round(min_conf,4),
                 "mean_word_confidence":None if mean_conf is None else round(mean_conf,4),
                 "unclear_tokens":unclear[:20],
                 "speaking_rate_wpm":round(speaking_rate,2),
                 "pause_ratio":round(m["pause_ratio"],4),
                 "pitch_variation_semitones":None if m["pitch_variation_semitones"] is None else round(m["pitch_variation_semitones"],4),
                 "energy_variation_db":round(m["energy_variation_db"],4),
                 "clipping_ratio":round(m["clipping_ratio"],6),
                 "duration_sec":round(m["duration_sec"],3)}
            observations.append(obs)
            took=time.time()-chunk_started
            print(f"[QC] Chapter {chapter} | chunk {pos}/{total} DONE | similarity={q:.3f} | "
                  f"word_min={min_conf if min_conf is not None else 'n/a'} | wpm={speaking_rate:.1f} | "
                  f"pause={m['pause_ratio']:.3f} | pitch_var={m['pitch_variation_semitones'] if m['pitch_variation_semitones'] is not None else 'n/a'} | {took:.1f}s", flush=True)
            if q<.55: events.append(ev("asr_mismatch","error",idx,s,e,q,expected=text[:160],heard=heard[:160]))
            elif q<.76: events.append(ev("asr_mismatch","warning",idx,s,e,q,expected=text[:160],heard=heard[:160]))
            if min_conf is not None and min_conf<.45:
                events.append(ev("pronunciation_clarity","warning",idx,s,e,min_conf,
                                 unclear_tokens=unclear[:20],mean_word_confidence=mean_conf))
            elif unclear:
                events.append(ev("pronunciation_clarity","warning",idx,s,e,min_conf,
                                 unclear_tokens=unclear[:20],mean_word_confidence=mean_conf))
        except Exception as x:
            print(f"[QC] Chapter {chapter} | chunk {pos}/{total} ASR ERROR: {x}", flush=True)
            events.append(ev("asr_mismatch","warning",idx,s,e,error=str(x)[:300]))
            observations.append({"chunk_index":idx,"audio_sha256":m["audio_sha256"],"attempt":attempt,
                                 "asr_error":str(x)[:180],"pause_ratio":round(m["pause_ratio"],4),
                                 "pitch_variation_semitones":m["pitch_variation_semitones"],
                                 "energy_variation_db":round(m["energy_variation_db"],4),
                                 "clipping_ratio":round(m["clipping_ratio"],6),
                                 "duration_sec":round(m["duration_sec"],3)})
    warn=sum(x["severity"]=="warning" for x in events); err=sum(x["severity"]=="error" for x in events)
    report={"source":"local_qc_v2","attempt":attempt,"chapter_number":job.get("chapter_number"),"checked_chunks":len(rows),
            "warnings":warn,"errors":err,"auto_repair_indices":sorted(repair),"asr_model":"small","audible_markers":False,
            "metric_schema":"pronunciation_prosody_v1","chunk_observations":observations}
    call("qc_report_batch",job_id=job["id"],qc_status="passed" if not warn and not err else "review",qc_report=report,events=events)
    print(f"[QC] Chapter {chapter}: DONE | warnings={warn} errors={err} | elapsed={(time.time()-started)/60:.1f}m", flush=True)
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
    p=argparse.ArgumentParser()
    p.add_argument("--book-id",required=True)
    p.add_argument("--max-chapter",type=int,default=5)
    p.add_argument("--observe-only",action="store_true",
                   help="Run QC and persist observations without deleting audio or requesting repair jobs.")
    a=p.parse_args()
    REPORTS.mkdir(parents=True,exist_ok=True); MODELS.mkdir(parents=True,exist_ok=True)
    print("[QC] Loading faster-whisper model: small / CPU int8 ...", flush=True)
    model=WhisperModel("small",device="cpu",compute_type="int8",download_root=str(MODELS),cpu_threads=max(2,min(8,os.cpu_count() or 4)))
    print("[QC] Model ready.", flush=True)
    jobs=call("book_jobs",book_id=a.book_id,max_chapter=a.max_chapter).get("jobs") or []
    jobs=[j for j in jobs if 1<=int(j.get("chapter_number") or 0)<=a.max_chapter]
    summary=[]
    for j in jobs:
        if j.get("status")!="completed": raise RuntimeError(f"chapter {j.get('chapter_number')} not complete")
        rep,repair=check(model,j,1)
        if repair and not a.observe_only:
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
        elif repair and a.observe_only:
            rep["observe_only"] = True
            rep["repair_suppressed"] = repair
        summary.append(rep)
    folder=REPORTS/a.book_id; folder.mkdir(parents=True,exist_ok=True)
    (folder/"qc_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# SAYDI QC Report",""]+[f"- Chương {x['chapter_number']}: warnings={x['warnings']} errors={x['errors']} repair={x['auto_repair_indices']}" for x in summary]
    (folder/"QC_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

if __name__=="__main__": main()
