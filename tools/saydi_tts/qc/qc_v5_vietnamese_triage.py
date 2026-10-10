"""SAYDI QC04: source-safe Vietnamese word/diacritic ASR *triage*.

Never declares a mispronunciation solely from Whisper. Produces local,
timecode/segment-addressed REVIEW candidates; never changes text or WAVs.
"""
from __future__ import annotations
import argparse, difflib, hashlib, json, os, re, unicodedata
from collections import Counter
from pathlib import Path
def words(text):
    normalized=unicodedata.normalize("NFC",str(text)).casefold()
    return re.findall(r"[^\W_]+",normalized,flags=re.UNICODE)
def strip_tones(word):
    v=unicodedata.normalize("NFD",word)
    v="".join(ch for ch in v if unicodedata.category(ch)!="Mn")
    return v.replace("đ","d").replace("Đ","D")
def detect(expected,heard):
    e,h=words(expected),words(heard)
    op=difflib.SequenceMatcher(None,e,h,autojunk=False)
    outcomes=[]
    for tag,i,j,a,b in op.get_opcodes():
        if tag=="equal":continue
        left=e[i:j];right=h[a:b]
        if tag=="replace" and len(left)==len(right):
            for x,y in zip(left,right):
                kind="DIACRITIC_AMBIGUOUS" if strip_tones(x)==strip_tones(y) else "TOKEN_SUBSTITUTION"
                outcomes.append({"kind":kind,"position":i,"expected_hash":hashlib.sha256(x.encode()).hexdigest()[:16],
                                 "observed_hash":hashlib.sha256(y.encode()).hexdigest()[:16]})
        else:
            outcomes.append({"kind":{"delete":"POSSIBLE_OMISSION","insert":"POSSIBLE_EXTRA_OR_REPEAT","replace":"PHRASE_MISMATCH"}[tag],
                             "position":i,"expected_token_count":len(left),"recognized_token_count":len(right)})
    return outcomes
def triage(manifest,qc,candidate=None):
    segments=manifest["segments"];base={int(r["index"]):r for r in qc["rows"]}
    if len(base)!=len(segments):raise ValueError("ASR_COVERAGE_INCOMPLETE")
    replacements={}
    if candidate:
        if len(candidate.get("rows",[]))!=1:raise ValueError("CANDIDATE_COUNT_UNEXPECTED")
        row=candidate["rows"][0];idx=int(row["index"])
        if idx not in base:raise ValueError("CANDIDATE_NOT_IN_CHAPTER")
        replacements[idx]=row
    alerts=[];counts=Counter()
    for segment in segments:
        idx=int(segment["index"]);row=replacements.get(idx,base[idx])
        expected=str(segment.get("spoken_text") or segment.get("canonical_text",""))
        if words(expected)!=words(row.get("expected","")):
            raise ValueError(f"ASR_EXPECTED_TEXT_DRIFT_{idx}")
        differences=detect(expected,row.get("heard",""))
        codes=sorted({f["kind"] for f in differences})
        if row.get("status")!="PASS" or differences:
            counts.update(codes)
            alerts.append({"segment":idx,"asr_status":row.get("status"),
                 "asr_similarity":row.get("asr_similarity"),
                 "kinds":codes,"details":differences[:15],
                 "classification":"REVIEW_ASR_AMBIGUITY_NOT_PROVEN_MISPRONUNCIATION"})
    return {"schema":"saydi-qc04-vi-language-triage-v1",
        "chapter":manifest.get("chapter_number"),
        "segments_checked":len(segments),
        "candidate_row_used":next(iter(replacements),None),
        "counts_by_kind":dict(counts),"review_segments":len(alerts),
        "alerts":alerts,"owner_final":False,"corrected_words":0,
        "source_immutable":True,"production_modified":False,
        "note":"Whisper errors or diacritic differences must be listened to and checked against source before any targeted re-render."}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--qc",type=Path,required=True)
    p.add_argument("--candidate-qc",type=Path)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--enable-experimental-qc04",action="store_true")
    args=p.parse_args()
    if not args.enable_experimental_qc04:
        print("QC04_DIAGNOSTIC_DISABLED_DEFAULT");return 0
    obj=lambda f:json.loads(f.read_text(encoding="utf-8-sig"))
    result=triage(obj(args.manifest),obj(args.qc),obj(args.candidate_qc) if args.candidate_qc else None)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    tmp=args.report.with_suffix(".pending")
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    os.replace(tmp,args.report)
    print(json.dumps({"report":str(args.report),"counts":result["counts_by_kind"],
                      "segments":result["review_segments"],"final":False}))
    return 0
if __name__=="__main__":raise SystemExit(main())
