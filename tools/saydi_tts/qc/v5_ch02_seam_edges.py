"""Read-only acoustic seam diagnostics for SAYDI V5 Chapter 2.

Reports *potential* edge discontinuities for nearest real chunk joins to user marks.
Measurements never prove an audible click and never trigger automatic repair.
Uses only original PCM WAV metadata and <=24ms of samples at each clip edge.
"""
from __future__ import annotations
import argparse
import array
import hashlib
import json
import math
import wave
from pathlib import Path
from audit_v5_chapter2 import MARKS,timeline

EDGE_MS=24

def pcm16_edge(path,tail=False,ms=EDGE_MS):
    with wave.open(str(path),"rb") as f:
        if (f.getsampwidth(),f.getnchannels())!=(2,1):
            raise ValueError("UNSUPPORTED_WAV_FORMAT")
        rate=f.getframerate()
        n=max(1,round(rate*ms/1000))
        total=f.getnframes()
        if tail:f.setpos(max(0,total-n))
        raw=f.readframes(min(n,total))
    samples=array.array("h")
    samples.frombytes(raw[:len(raw)//2*2])
    if not samples:raise ValueError("EMPTY_WAV")
    norm=[float(s)/32768 for s in samples]
    return {
        "sample_rate":rate,
        "duration_ms":round(len(norm)*1000/rate,3),
        "first_sample":round(norm[0],6),
        "last_sample":round(norm[-1],6),
        "rms":round(math.sqrt(sum(v*v for v in norm)/len(norm)),6),
        "peak":round(max(abs(v) for v in norm),6),
    }

def edge_report(near,concat,items):
    ix=int(near["segment"])
    lines=concat.read_text(encoding="utf-8-sig").splitlines()
    paths=[Path(s[6:-1]) for s in lines]  # timeline() already validates paths
    if ix<0 or ix+1>=len(items):
        return {"status":"LAST_SEGMENT_HAS_NO_NEXT_WAV"}
    ending=pcm16_edge(paths[ix*2],tail=True)
    beginning=pcm16_edge(paths[(ix+1)*2])
    gap=int(near["gap_ms"])
    possible_edges=(abs(ending["last_sample"]),abs(beginning["first_sample"]))
    return {
        "wav_prev":paths[ix*2].name,"wav_next":paths[(ix+1)*2].name,
        "preceding_last_24ms":ending,"following_first_24ms":beginning,
        "configured_gap_ms":gap,
        "max_edge_endpoint_magnitude":round(max(possible_edges),6),
        "risk_indicator":"EDGE_NONZERO_REVIEW" if max(possible_edges)>.04 else "LOW_ENDPOINT_STEP",
        "verdict":"NOT_HUMAN_LISTEN_VERIFIED",
    }

def run(manifest,concat,audit,out):
    m=json.loads(manifest.read_text(encoding="utf8"))
    boundaries,total=timeline(m["segments"],concat)
    prior=json.loads(audit.read_text(encoding="utf8"))
    results=[]
    for clock,sec in MARKS.items():
        near=min(boundaries[:-1],key=lambda e:abs(e["time_s"]-sec))
        result={"clock":clock,"clock_s":sec,
                "nearest_valid_join_s":near["time_s"],
                "distance_s":round(abs(near["time_s"]-sec),3),
                "joining_segments":[near["segment"],near["segment"]+1]}
        result.update(edge_report(near,concat,m["segments"]))
        results.append(result)
    report={
        "schema":"SAYDI_V5_QC02_EDGE_DIAGNOSTIC_V1",
        "source_audio_sha256":prior.get("audio_sha256"),
        "examined":results,
        "conclusion":"NO_AUTOMATIC_AUDIBLE_CLICK_VERDICT",
        "production_changed":False,
        "repair_performed":False,
        "owner_listening_pending":True,
        "explanation":"The marks are approximate and not proven joins. Examines 24ms PCM endpoints around nearest actual join and silence gap, not final chapter MP3 timing under any post-assembly resampling."
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"report":str(out),"results":[{"clock":x["clock"],
      "join_s":x["nearest_valid_join_s"],"max_edge":x["max_edge_endpoint_magnitude"],
      "indicator":x["risk_indicator"]}for x in results]},ensure_ascii=True))
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for name in ("manifest","concat","audit","out"):parser.add_argument("--"+name,required=True,type=Path)
    a=parser.parse_args()
    run(a.manifest,a.concat,a.audit,a.out)
