"""Isolated Chapter 3 V5 five-minute QC01 A/B and QC02 reference.

Imports previously field-tested read-only utility functions. Never changes
audio production, narrator speed or chapter job. Feature remains OFF.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path
from preview_5phut_context import list_wavs, choose_window, create_ab
from v5_ch02_seam_edges import pcm16_edge

def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

def stream_copy_reference(ffmpeg,original,out,start):
    dst=out/"QC02_CHUONG_03_GOC_5PHUT.mp3"
    command=[ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-y",
             "-threads","1","-ss",f"{start:.3f}","-i",str(original),
             "-t","300","-map","0:a:0","-c:a","copy",str(dst)]
    process=subprocess.run(command,capture_output=True,timeout=60)
    if process.returncode or not dst.is_file() or dst.stat().st_size<2_000_000:
        raise RuntimeError("QC02_CONTEXT_EXTRACTION_FAILED: "+
                           process.stderr.decode("utf8","replace")[-260:])
    return {"path":str(dst),"source_start_s":round(start,3),
            "nominal_duration_s":300,"sha256":digest(dst)}

def examine_clean_joins(paths,bounds,start,end):
    rows=[]
    for i in range(start,end-1):
        tail=pcm16_edge(paths[2*i],tail=True)
        head=pcm16_edge(paths[2*(i+1)],tail=False)
        mag=max(abs(tail["last_sample"]),abs(head["first_sample"]))
        rows.append({"segment_join_after":i,"source_gap_ms":bounds[i]["gap_ms"],
                     "wav_tail":tail["last_sample"],"wav_head":head["first_sample"],
                     "endpoint_risk":"REVIEW" if mag>.04 else "LOW",
                     "audible_click_verified":False})
    return rows

def build(manifest,concat,source,ffmpeg,out,center):
    out.mkdir(parents=True,exist_ok=True)
    before=digest(source)
    items,bounds,paths,positions=list_wavs(manifest,concat)
    if len(items)<10:
        raise RuntimeError("UNEXPECTED_CHAPTER_SEGMENT_COUNT")
    st,ed,approx=choose_window(items,paths,positions,center,300)
    if not 270<=approx<=335:
        raise RuntimeError("FIVE_MINUTE_WINDOW_NOT_AVAILABLE")
    ab=create_ab(items,bounds,paths,positions,center,out,ffmpeg)
    if ab["start_segment"]!=st or ab["end_segment_exclusive"]!=ed:
        raise RuntimeError("A_B_WINDOW_CHANGED_UNEXPECTEDLY")
    ref=stream_copy_reference(ffmpeg,source,out,positions[st])
    edges=examine_clean_joins(paths,bounds,st,ed)
    if digest(source)!=before:
        raise RuntimeError("PRODUCTION_MP3_MODIFIED")
    report={"schema":"SAYDI_CH03_V5_QC01_QC02_FIVE_MINUTE_REVIEW_V1",
        "source_chapter":3,"source_mp3":str(source),
        "source_original_sha256":before,
        "qc01":{
            "A_B":ab,
            "comparison_rule":"IDENTICAL_SPOKEN_WAV_REFERENCES_GAP_ONLY",
            "listening_acceptance":"PENDING_OWNER",
            "no_atempo":True,
        },
        "qc02":{
            "original_context":ref,
            "join_edges_count":len(edges),
            "endpoint_flags":sum(x["endpoint_risk"]=="REVIEW" for x in edges),
            "checked_wav_join_edges":edges,
            "audible_faults_confirmed":0,
            "interpretation":"Technical endpoint screening only. No automatic seam repair.",
            "listening_acceptance":"PENDING_OWNER",
        },
        "production_changed":False,"feature_enabled_in_robot":False,
        "engine_changed":False,"audio_final":False}
    target=out/"CH03_QC01_QC02_5PHUT_REPORT.json"
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"output":str(out),"audio":{k:v["path"] for k,v in ab["files"].items()},
        "reference":ref["path"],"segments":f"{st}-{ed-1}",
        "estimated_duration_s":round(approx,3),
        "silences_changed":ab["change_count"],"total_pause_delta_ms":ab["total_pause_delta_ms"],
        "qc02_joins_checked":len(edges),"qc02_endpoints_flagged":report["qc02"]["endpoint_flags"],
        "source_mp3_unchanged":True,"owner_listening_pass":False},ensure_ascii=True))
    return report

def main():
    p=argparse.ArgumentParser()
    for x in ("manifest","concat","source","ffmpeg","out"):p.add_argument("--"+x,required=True)
    p.add_argument("--center-seconds",type=float,default=750)
    args=p.parse_args()
    build(Path(args.manifest),Path(args.concat),Path(args.source),
          args.ffmpeg,Path(args.out),args.center_seconds)

if __name__=="__main__":
    main()
