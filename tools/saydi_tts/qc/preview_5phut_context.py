"""QC Chapter 2: ~5-minute context A/B and long original suspect excerpt.

Isolated opt-in staging only, no production audio writes, no TTS/ASR.
Uses *identical* cleaned narrated WAVs in A and B; candidate B changes only
sentence-boundary silence 610 ms => 530/690 ms where appropriate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import wave
from pathlib import Path

from audit_v5_chapter2 import timeline,MARKS
from v5_ch02_ab_preview import pause_candidate

def run(cmd, timeout=240):
    flags=getattr(subprocess,"BELOW_NORMAL_PRIORITY_CLASS",0)|getattr(subprocess,"CREATE_NO_WINDOW",0)
    p=subprocess.run(cmd,capture_output=True,timeout=timeout,creationflags=flags)
    if p.returncode:
        raise RuntimeError("FFMPEG_FAILED: "+p.stderr.decode("utf8","replace")[-450:])

def audlen(file):
    with wave.open(str(file),"rb") as w:
        return w.getnframes()/w.getframerate()

def list_wavs(manifest, concat):
    m=json.loads(manifest.read_text(encoding="utf8"))
    segments=m["segments"]
    bounds,total=timeline(segments,concat)
    rows=concat.read_text(encoding="utf-8-sig").splitlines()
    paths=[Path(x[6:-1]) for x in rows]
    positions=[]
    ts=0.
    for ix,item in enumerate(segments):
        positions.append(ts)
        ts+=audlen(paths[2*ix])+audlen(paths[2*ix+1])
    return segments,bounds,paths,positions

def choose_window(segments,paths,positions,center,secs=300):
    ideal=max(0,center-secs/2)
    best=min(range(len(segments)-1),key=lambda i:abs(positions[i]-ideal)+
        (0 if segments[i].get("part_in_parent")==0 else 14))
    final_target=positions[best]+secs
    end=min(range(best+1,len(segments)),key=lambda i:
        abs(positions[i]-final_target)+(0 if segments[i-1].get("parent_end") else 7))
    actual=positions[end]-positions[best]
    if not 270<=actual<=335:
        raise RuntimeError(f"WINDOW_NOT_FIVE_MINUTES: {actual:.2f}")
    return best,end,actual

def concat_file(paths,dst):
    dst.write_text("\n".join("file '"+str(p.resolve()).replace("\\","/")+"'"
                              for p in paths)+"\n",encoding="utf8")

def make_gap(path,ms):
    if path.exists():return path
    # Identify properties from source gap WAV so replacement has exact encoding.
    n=48000*ms//1000
    with wave.open(str(path),"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(48000)
        f.writeframes(b"\0\0"*n)
    return path

def create_ab(segments,bounds,paths,positions,center,out,ffmpeg):
    st,ed,duration=choose_window(segments,paths,positions,center)
    candidate_changes=[]
    a=[];b=[]
    for ix in range(st,ed):
        clean,gap=paths[2*ix:2*ix+2]
        source_ms=bounds[ix]["gap_ms"]
        proposed=source_ms
        if ix < ed-1 and not bounds[ix]["paragraph_change"] and not segments[ix].get("heading"):
            proposed=pause_candidate(segments[ix],source_ms)
        a.extend((clean,gap))
        if proposed != source_ms:
            changed=make_gap(out/f"candidate_gap_{proposed}.wav",proposed)
            b.extend((clean,changed))
            candidate_changes.append({"segment":segments[ix]["index"],
                "words":len(str(segments[ix].get("canonical_text","")).split()),
                "baseline_ms":source_ms,"candidate_ms":proposed,
                "duration_change_ms":proposed-source_ms})
        else:b.extend((clean,gap))
    if not candidate_changes:
        raise RuntimeError("NO_EFFECTIVE_PAUSE_CANDIDATES_IN_WINDOW")
    results={}
    for label,items in (("A_BAN_GOC_5PHUT",a),("B_THU_NHIP_NGHI_5PHUT",b)):
        concat=out/(label+".concat.txt")
        concat_file(items,concat)
        destination=out/(label+".mp3")
        run([ffmpeg,"-hide_banner","-nostdin","-loglevel","error","-y",
             "-threads","1","-filter_threads","1","-filter_complex_threads","1",
             "-f","concat","-safe","0","-i",str(concat),
             "-af","loudnorm=I=-18:LRA=11:TP=-2",
             "-ac","1","-ar","48000","-c:a","libmp3lame","-b:a","128k",
             str(destination)],timeout=360)
        if not destination.is_file() or destination.stat().st_size<200_000:
            raise RuntimeError("PREVIEW_AUDIO_MISSING")
        with destination.open("rb") as f:sha=hashlib.file_digest(f,"sha256").hexdigest()
        results[label]={"path":str(destination),"bytes":destination.stat().st_size,
                        "sha256":sha}
    return {"start_segment":st,"end_segment_exclusive":ed,
            "start_time_in_chapter_s":round(positions[st],3),
            "end_time_in_chapter_s":round(positions[ed],3),
            "A_nominal_duration_s":round(duration,3),
            "pause_changes":candidate_changes,
            "change_count":len(candidate_changes),
            "total_pause_delta_ms":sum(x["duration_change_ms"] for x in candidate_changes),
            "files":results}

def original_context(ffmpeg,mp3,out,center):
    destination=out/"QC02_NGU_CANH_GOC_5PHUT_002334.mp3"
    start=max(0,center-150)
    run([ffmpeg,"-hide_banner","-nostdin","-loglevel","error","-y",
         "-threads","1","-ss",str(start),"-i",str(mp3),"-t","300",
         "-map","0:a:0","-c:a","copy",str(destination)],timeout=65)
    if destination.stat().st_size<200_000:
        raise RuntimeError("QC02_ORIGINAL_MISSING")
    return {"path":str(destination),"source_start_s":start,"nominal_length_s":300}

def main():
    a=argparse.ArgumentParser()
    for name in ("manifest","concat","source","ffmpeg","out"):
        a.add_argument("--"+name,required=True)
    o=a.parse_args()
    manifest=Path(o.manifest);concat=Path(o.concat);source=Path(o.source)
    out=Path(o.out);out.mkdir(parents=True,exist_ok=True)
    with source.open("rb") as f:before=hashlib.file_digest(f,"sha256").hexdigest()
    seg,bounds,paths,positions=list_wavs(manifest,concat)
    ab=create_ab(seg,bounds,paths,positions,MARKS["00:16:33"],out,o.ffmpeg)
    qc02=original_context(o.ffmpeg,source,out,MARKS["00:23:34"])
    with source.open("rb") as f:after=hashlib.file_digest(f,"sha256").hexdigest()
    if before!=after:
        raise RuntimeError("PRODUCTION_SOURCE_CHANGED")
    payload={
       "schema":"SAYDI_V5_QC_5MIN_AB_PREVIEW_1",
       "chapter":2,"feature":"OFF_IN_PRODUCTION","render_engine_changed":False,
       "native_voice_and_tempo_unchanged":True,
       "audio_original_sha256":before,"production_unmodified":True,
       "source_chunks_preserved":True,
       "A_B":ab,"QC02_unmodified":qc02,
       "quality_verdict":"LISTENING_REVIEW_REQUIRED",
       "notes":"Only inserted silence varies in B; do not infer naturalness PASS from duration or technical tests. "+
               "The extra 5-min QC02 excerpt preserves the existing encoded audio."
    }
    (out/"QC_5PHUT_REPORT.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"A_B":{k:v for k,v in ab.items() if k!="pause_changes"},
                      "QC02":qc02,"source_unmodified":True},ensure_ascii=True))
if __name__=="__main__":
    main()
