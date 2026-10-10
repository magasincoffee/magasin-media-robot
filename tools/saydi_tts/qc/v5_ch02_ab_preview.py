"""Opt-in QC-01/02 listening previews for SAYDI V5, never production.

Uses existing cleaned WAVs, punctuation boundaries and FFmpeg. No TTS/ASR,
no tempo adjustment, no replacement of approved files, no automatic PASS.
"""
from __future__ import annotations
import argparse,json,subprocess,wave
from pathlib import Path
from audit_v5_chapter2 import MARKS,timeline

def pause_candidate(item,existing):
    """Bounded 80ms proposal for a *listening preview*, not semantic acceptance."""
    text=str(item.get("canonical_text","")).strip()
    words=len(text.split())
    if existing != 610 or not text.endswith((".",".”",'.\"')):
        return existing
    if words<=10:return 530
    if words>=22:return 690
    return existing

def choose(items,bounds,time_s,exclude=()):
    possible=[]
    for item,edge in zip(items,bounds):
        if edge["segment"] in exclude:continue
        proposed=pause_candidate(item,edge["gap_ms"])
        if proposed!=edge["gap_ms"]:
            possible.append((abs(edge["time_s"]-time_s),item,edge,proposed))
    if not possible:raise RuntimeError("NO_APPROPRIATE_REVIEW_SEGMENT")
    return min(possible,key=lambda x:x[0])

def encode_pair(ffmpeg,concat_wavs,folder,item,edge,new_gap_ms,output):
    j=int(item["index"])
    old=concat_wavs[j*2]
    next_wav=concat_wavs[(j+1)*2]
    if not old.is_file() or not next_wav.is_file():raise FileNotFoundError("PREPARED_WAV_MISSING")
    gap=folder/("preview_gap_"+str(new_gap_ms)+".wav")
    if not gap.exists():
        with wave.open(str(gap),"wb") as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(48000)
            f.writeframes(b"\x00\x00"*round(48000*new_gap_ms/1000))
    filelist=folder/(output.stem+".concat.txt")
    filelist.write_text("\n".join("file '"+str(p.resolve()).replace("\\","/")+"'"
                            for p in (old,gap,next_wav))+"\n",encoding="utf8")
    cmd=[ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-y",
         "-threads","1","-filter_threads","1","-f","concat","-safe","0",
         "-i",str(filelist),"-af","loudnorm=I=-18:LRA=11:TP=-2",
         "-ar","48000","-ac","1","-c:a","libmp3lame","-b:a","128k",str(output)]
    result=subprocess.run(cmd,capture_output=True,timeout=65)
    if result.returncode or not output.is_file():
        raise RuntimeError("PAIR_ENCODE_FAIL: "+result.stderr.decode("utf8","replace")[-260:])
    return str(output)

def excerpt(ffmpeg,master,sec,out):
    cmd=[ffmpeg,"-hide_banner","-nostdin","-loglevel","error","-y",
         "-threads","1","-ss",str(max(0,sec-4.0)),"-i",str(master),"-t","8",
         "-ar","48000","-ac","1","-c:a","libmp3lame","-b:a","128k",str(out)]
    res=subprocess.run(cmd,capture_output=True,timeout=35)
    if res.returncode or not out.is_file():raise RuntimeError("EXCERPT_FAIL")
    return str(out)

def build(manifest,concat,audio,ffmpeg,out):
    out.mkdir(parents=True,exist_ok=True)
    m=json.loads(manifest.read_text(encoding="utf8")); items=m["segments"]
    bounds,_=timeline(items,concat)
    lines=concat.read_text(encoding="utf8").splitlines()
    paths=[Path(line[6:-1]) for line in lines]  # validated by timeline()
    trials=[];excluded=set()
    for key in ("00:16:33","00:36:19"):
        sec=MARKS[key]
        dist,item,edge,proposal=choose(items,bounds,sec,excluded)
        excluded.add(edge["segment"])
        base_name="qc01_"+key.replace(":","")+"_seg"+str(edge["segment"])
        baseline=out/(base_name+"_A_original_gap.mp3")
        changed=out/(base_name+"_B_proposed_gap.mp3")
        encode_pair(ffmpeg,paths,out,item,edge,edge["gap_ms"],baseline)
        encode_pair(ffmpeg,paths,out,item,edge,proposal,changed)
        trials.append({"near_mark":key,"selected_segment":edge["segment"],
            "source_join_s":edge["time_s"],"distance_from_requested_s":round(dist,2),
            "baseline_pause_ms":edge["gap_ms"],"proposed_pause_ms":proposal,
            "spoken_words":len(str(item["canonical_text"]).split()),
            "original":str(baseline),"candidate":str(changed),
            "status":"PREVIEW_ONLY_NEEDS_OWNER_LISTENING"})
    excerpts=[]
    for key,sec in MARKS.items():
        name=out/("qc02_suspect_"+key.replace(":","")+"_ORIGINAL.mp3")
        excerpt(ffmpeg,audio,sec,name)
        excerpts.append({"requested":key,"source_audio_excerpt":str(name),
                         "status":"NEEDS_LISTENING_NO_REPAIR_APPLIED"})
    data={"schema":"saydi-v5-qc01-qc02-preview-1","qc01_trials":trials,
          "qc02_reference_excerpts":excerpts,"feature_flag":"OFF_IN_PRODUCTION",
          "baseline_and_production_unchanged":True,
          "owner_pass":False,
          "note":"A/B previews use two existing clean WAVs. No TTS, atempo or chapter rebuild. "
                 "Amplitude anomaly is not a confirmed audible artifact."}
    target=out/"preview_report.json"
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    return data
def main():
    ap=argparse.ArgumentParser()
    for name in ("manifest","concat","audio","ffmpeg","out"):ap.add_argument("--"+name,required=True)
    a=ap.parse_args()
    d=build(Path(a.manifest),Path(a.concat),Path(a.audio),a.ffmpeg,Path(a.out))
    print(json.dumps({"qc01":d["qc01_trials"],"qc02":d["qc02_reference_excerpts"],
          "production_changed":False},ensure_ascii=True))
if __name__=="__main__":main()
