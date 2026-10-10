"""SAYDI V5 QC-01/02 read-only audit. No render, no audio writes, no PASS assertion."""
import argparse, array, collections, hashlib, json, math, re, subprocess, wave
from pathlib import Path
MARKS={"00:16:33":993,"00:23:34":1414,"00:36:19":2179,"00:56:29":3389,"01:01:12":3672}
def wav_seconds(p):
    with wave.open(str(p),"rb") as f:return f.getnframes()/f.getframerate()
def timeline(items,concat):
    lines=concat.read_text(encoding="utf-8-sig").splitlines()
    if len(lines)!=2*len(items):raise ValueError("CONCAT_COUNT_MISMATCH")
    ts=0.0;boundaries=[]
    for j,item in enumerate(items):
        paths=[]
        for line in lines[j*2:j*2+2]:
            m=re.fullmatch(r"file '([^']+)'",line)
            if not m:raise ValueError("INVALID_CONCAT_ROW")
            paths.append(Path(m.group(1)))
        wav,gap=paths
        idx=int(item["index"])
        if wav.name!=f"{idx:06d}.wav" or not re.fullmatch(r"gap_\d+\.wav",gap.name):
            raise ValueError("CHUNK_GAP_ORDER_MISMATCH")
        ts+=wav_seconds(wav); gap_ms=int(gap.stem.split("_")[1])
        if abs(wav_seconds(gap)-gap_ms/1000)>.003:raise ValueError("GAP_DURATION_MISMATCH")
        boundaries.append({"segment":idx,"time_s":round(ts,3),"gap_ms":gap_ms,
            "heading":bool(item.get("heading")),
            "paragraph_change":j+1<len(items) and item.get("parent_line")!=items[j+1].get("parent_line"),
            "punctuation":str(item.get("canonical_text","")).rstrip()[-1:]})
        ts+=gap_ms/1000
    return boundaries,round(ts,3)
def measure(ffmpeg,mp3,t):
    start=max(0,t-1.3)
    p=subprocess.run([ffmpeg,"-hide_banner","-nostdin","-loglevel","error",
      "-ss",str(start),"-i",str(mp3),"-t","2.6","-ar","16000","-ac","1",
      "-f","f32le","pipe:1"],capture_output=True,timeout=25)
    if p.returncode:raise RuntimeError(p.stderr.decode("utf8","replace")[-400:])
    a=array.array("f");a.frombytes(p.stdout[:len(p.stdout)//4*4])
    if not a:raise RuntimeError("EMPTY_AUDIO_WINDOW")
    vals=[math.sqrt(sum(x*x for x in a[k:k+160])/160) for k in range(0,len(a)-159,160)]
    quiet=[];start_ix=None
    for i,v in enumerate(vals+[float("inf")]):
        if v<.0079 and start_ix is None:start_ix=i
        if v>=.0079 and start_ix is not None:
            if i-start_ix>=13:quiet.append({"start_s":round(start+start_ix*.01,2),"ms":(i-start_ix)*10})
            start_ix=None
    mx=max(range(1,len(a)),key=lambda i:abs(a[i]-a[i-1]))
    return {"jump_at_s":round(start+mx/16000,4),"max_sample_step":round(abs(a[mx]-a[mx-1]),5),
      "peak":round(max(abs(x) for x in a),4),"quiet_spans":quiet[:12],
      "interpretation":"AUTOMATED_METRIC_ONLY_NOT_LISTEN_CONFIRMED"}
def analyze(manifest,concat,mp3,ffmpeg):
    m=json.loads(manifest.read_text(encoding="utf8"))
    bounds,estimated=timeline(m["segments"],concat)
    counts=collections.Counter(x["gap_ms"] for x in bounds)
    checks=[]
    for label,seconds in MARKS.items():
        near=min(bounds,key=lambda x:abs(x["time_s"]-seconds))
        checks.append({"timestamp":label,"nearest_join":near,
          "offset_from_nearest_join_s":round(seconds-near["time_s"],3),
          "measured_audio":measure(ffmpeg,str(mp3),seconds),
          "verdict":"REVIEW_REQUIRED"})
    with mp3.open("rb") as f:dig=hashlib.file_digest(f,"sha256").hexdigest()
    return {"schema":"saydi-v5-ch02-qc01-qc02-readonly-audit-v1",
     "audio_sha256":dig,"duration_from_concat_s":estimated,"segment_count":len(bounds),
     "gaps_ms":dict(sorted(counts.items())),"suspected_marks":checks,
     "qc01":"BASELINE_ONLY","qc02":"BASELINE_ONLY",
     "required_next":"compare timecodes against verified join map and listen to 5 selected excerpts",
     "source_modified":False,"audio_modified":False,"human_pass":False}
def main():
    a=argparse.ArgumentParser()
    for name in ("manifest","concat","audio","ffmpeg","report"):a.add_argument("--"+name,required=True)
    v=a.parse_args()
    result=analyze(Path(v.manifest),Path(v.concat),Path(v.audio),v.ffmpeg)
    target=Path(v.report);target.parent.mkdir(parents=True,exist_ok=True)
    tmp=target.with_suffix(".tmp");tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8");tmp.replace(target)
    print(json.dumps({"report":str(target),"segments":result["segment_count"],
      "gaps_ms":result["gaps_ms"],"timeline_s":result["duration_from_concat_s"],
      "marks":[{"t":z["timestamp"],"closest_gap_ms":z["nearest_join"]["gap_ms"],
      "dist_s":z["offset_from_nearest_join_s"],"peak_step":z["measured_audio"]["max_sample_step"]}
      for z in result["suspected_marks"]]},ensure_ascii=True))
if __name__=="__main__":main()
