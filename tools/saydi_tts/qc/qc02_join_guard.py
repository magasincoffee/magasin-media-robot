"""SAYDI V5 QC02 opt-in join/transient inspection (NO audio modification).

Computes boundary PCM16 metrics and 8-second decoded MP3 observations near
review timestamps. Flagging is not listening PASS or confirmed click.
"""
from __future__ import annotations
import argparse
import array
import hashlib
import json
import math
import os
import subprocess
import wave
from pathlib import Path

MARKS={"00:16:33":993.0,"00:23:34":1414.0,"00:36:19":2179.0,
       "00:56:29":3389.0,"01:01:12":3672.0}

def rms(v):
    return math.sqrt(sum(x*x for x in v)/max(1,len(v)))/32768.0

def chunk_edge(path,side):
    with wave.open(str(path),"rb") as w:
        if w.getsampwidth()!=2 or w.getnchannels()!=1:
            raise ValueError("EXPECTED_MONO_PCM16")
        sr=w.getframerate()
        frames=min(w.getnframes(),round(sr*.07))
        if side=="end":
            w.setpos(w.getnframes()-frames)
        raw=w.readframes(frames)
    a=array.array("h");a.frombytes(raw)
    if not a:raise RuntimeError("EMPTY_WAV_EDGE")
    f=min(len(a),round(sr*.03))
    edge=a[:f] if side=="start" else a[-f:]
    steps=[abs(edge[i]-edge[i-1])/32768 for i in range(1,len(edge))]
    return {"sample_rate":sr,"edge_rms":round(rms(edge),6),
            "outer_sample_abs":round(abs(a[0] if side=="start" else a[-1])/32768,6),
            "peak_step_30ms":round(max(steps,default=0),6),
            "duration_checked_ms":round(len(edge)/sr*1000,1)}

def join_map(manifest,concat):
    items=json.loads(Path(manifest).read_text(encoding="utf8"))["segments"]
    lines=Path(concat).read_text(encoding="utf-8-sig").splitlines()
    if len(lines)!=len(items)*2:raise ValueError("CONCAT_COUNT_MISMATCH")
    pairs=[]
    position=0.
    for ix,item in enumerate(items):
        wavline,gapline=lines[ix*2:ix*2+2]
        if not(wavline.startswith("file '") and gapline.startswith("file '")):
            raise ValueError("BAD_CONCAT_PATH_FORMAT")
        wav=Path(wavline[6:-1]);gap=Path(gapline[6:-1])
        if wav.name != f'{int(item["index"]):06d}.wav' or not gap.name.startswith("gap_"):
            raise ValueError("BAD_WAV_ORDER")
        with wave.open(str(wav),"rb") as w:seconds=w.getnframes()/w.getframerate()
        with wave.open(str(gap),"rb") as w:gap_s=w.getnframes()/w.getframerate()
        begin=position
        position+=seconds
        pairs.append((ix,begin,position,wav,gap_s))
        position+=gap_s
    return pairs,position

def inspect_candidate(j,items,boundary):
    ix,begin,end,wav,gap_sec=boundary
    close=chunk_edge(wav,"end")
    nxt=chunk_edge(items[ix+1][3],"start") if ix+1<len(items) else None
    # conservative flag: zero-edge fade already exists, and a pure acoustic click
    # should have a discontinuity at the actual edge, not just an intense consonant.
    high_edge=(close["outer_sample_abs"]>.025 or
               (nxt is not None and nxt["outer_sample_abs"]>.025))
    aggressive_step=max(close["peak_step_30ms"],
                        nxt["peak_step_30ms"] if nxt else 0)>.4
    label="TECHNICAL_EDGE_CANDIDATE" if high_edge and aggressive_step else "NO_CONFIRMED_EDGE_POP"
    return {"segment":j,"edge_at_seconds":round(end,4),
            "gap_ms":round(gap_sec*1000),"outgoing":close,
            "incoming":nxt,"technical_flag":label,
            "review_required":True}

def mp3_window_probe(ffmpeg,source,t):
    start=max(0.,t-4.)
    cmd=[ffmpeg,"-hide_banner","-nostdin","-loglevel","error","-threads","1",
         "-ss",str(start),"-i",str(source),"-t","8","-ar","16000","-ac","1",
         "-f","s16le","pipe:1"]
    flags=getattr(subprocess,"CREATE_NO_WINDOW",0)|getattr(subprocess,"BELOW_NORMAL_PRIORITY_CLASS",0)
    p=subprocess.run(cmd,capture_output=True,timeout=25,creationflags=flags)
    if p.returncode:raise RuntimeError("MP3_DECODE_FAILED")
    a=array.array("h");a.frombytes(p.stdout)
    if len(a)<16000:raise RuntimeError("MP3_DECODE_EMPTY")
    steps=sorted(((abs(a[i]-a[i-1])/32768,i) for i in range(1,len(a))),reverse=True)[:6]
    return {"start_s":round(start,2),"top_step_candidates":[
       {"at_s":round(start+i/16000,4),"step":round(v,5)} for v,i in steps],
       "note":"Acoustic impulse candidates only; voiced consonants may create equally large steps"}

def analyze(manifest,concat,mp3,ffmpeg):
    pairs,total=join_map(manifest,concat)
    result=[]
    for mark,t in MARKS.items():
        nearest=min(pairs,key=lambda r:abs(r[2]-t))
        nearby=[b for b in pairs if abs(b[2]-t)<=5.0]
        scan=[inspect_candidate(r[0],pairs,r) for r in nearby]
        result.append({"requested_mark":mark,"mark_seconds":t,
          "nearest_wav_end_s":round(nearest[2],3),
          "nearest_distance_seconds":round(abs(nearest[2]-t),3),
          "joins_in_5s_window":scan,
          "mp3_samples":mp3_window_probe(ffmpeg,mp3,t),
          "qc_status":"FLAGGED_FOR_OWNER_LISTENING",
          "automated_fix_applied":False})
    with Path(mp3).open("rb") as f:sha=hashlib.file_digest(f,"sha256").hexdigest()
    return {"schema":"SAYDI_V5_QC02_JOIN_GUARD_1","source_audio_sha256":sha,
      "source_audio":str(mp3),"source_duration_estimate_s":round(total,2),
      "segments":len(pairs),"reviewed_marks":result,
      "approved_reference":"Owner approves original QC02 5min narration style, not residual click artifacts",
      "manual_listening_required":True,"auto_approve":False,
      "production_audio_modified":False,"feature_default":"OFF"}

def main():
    p=argparse.ArgumentParser()
    for k in ("manifest","concat","audio","ffmpeg","report"):p.add_argument("--"+k,required=True)
    a=p.parse_args()
    output=analyze(a.manifest,a.concat,a.audio,a.ffmpeg)
    dest=Path(a.report)
    dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=dest.with_suffix(".pending.json")
    tmp.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    os.replace(tmp,dest)
    print(json.dumps({"report":str(dest),
      "marks":[{"time":x["requested_mark"],"nearby_edges":len(x["joins_in_5s_window"]),
      "technical_candidates":sum(y["technical_flag"]=="TECHNICAL_EDGE_CANDIDATE" for y in x["joins_in_5s_window"]),
      "seconds_to_nearest_end":x["nearest_distance_seconds"]} for x in output["reviewed_marks"]],
      "changed_production":False}))
if __name__=="__main__":main()
