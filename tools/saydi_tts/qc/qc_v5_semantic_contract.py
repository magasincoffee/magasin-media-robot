"""SAYDI QC03 provider-neutral narration context and directive gate.

Prepares hierarchical context from immutable manifest; validates optional
semantic director suggestions. No local/cloud model is invoked by this tool,
no pitch/atempo control, no source rewrite or audio modifications.
"""
import argparse,hashlib,json,os
from collections import defaultdict
from pathlib import Path
ROLES={"CHAPTER_TITLE","SECTION_HEADING","NARRATOR_BODY","DIALOGUE","QUOTE",
       "LIST_ITEM","REFLECTIVE","EXPLANATORY","EMPHATIC","TRANSITION"}
EMOTIONS={"neutral","reflective","warmth","joy","tension","sadness","concern","excitement"}
def txt_hash(s):return hashlib.sha256(s.encode("utf8")).hexdigest()
def context(manifest):
    items=manifest["segments"]
    chapter=manifest["chapter_number"]
    groups=defaultdict(list)
    for obj in items:
        idx=int(obj["index"])
        groups[int(obj.get("parent_line",idx))].append(idx)
    parents=list(groups)
    rows=[]
    for i,item in enumerate(items):
        idx=int(item["index"]);canonical=str(item.get("canonical_text",""))
        spoken=str(item.get("spoken_text") or canonical)
        if item.get("tts_text_sha256") is None:
            raise ValueError("IMMUTABLE_SPOKEN_HASH_MISSING")
        parent=int(item.get("parent_line",idx))
        neighbors=[items[j].get("canonical_text","") for j in (i-1,i+1) if 0<=j<len(items)]
        rows.append({"index":idx,"parent_line":parent,
            "is_heading":bool(item.get("heading")),
            "source_text_sha256":txt_hash(canonical),
            "tts_text_sha256":item["tts_text_sha256"],
            "context_digest_sha256":txt_hash("\n".join(neighbors)),
            "role":"NEEDS_SEMANTIC_ANALYSIS","emotion":"unknown","confidence":0,
            "directive_status":"REVIEW","text_change_allowed":False})
    return {"schema":"saydi-v5-qc03-directive-contract-1","chapter":chapter,
        "book_source_sha256":manifest.get("source_sha256"),
        "voice_reference_sha256":manifest.get("reference_sha256"),
        "scene_groups_by_parent_line":len(parents),
        "segments":rows,"auto_tts_instruction":False,
        "note":"Only structural context pointers and hashes. No emotion model or narration override was run."}
def verify(snapshot,proposals):
    base={int(x["index"]):x for x in snapshot["segments"]}
    incoming=proposals.get("directives",[])
    if not isinstance(incoming,list):raise ValueError("DIRECTIVE_ARRAY_REQUIRED")
    seen=set();issues=[];accepted=[]
    for proposal in incoming:
        idx=int(proposal["index"])
        if idx in seen or idx not in base:raise ValueError("DIRECTIVE_SCOPE_INVALID")
        seen.add(idx);original=base[idx]
        for key in ("tts_text_sha256","source_text_sha256"):
            if proposal.get(key)!=original[key]:raise ValueError("TEXT_FINGERPRINT_CHANGED")
        role=proposal.get("role");emotion=proposal.get("emotion")
        confidence=float(proposal.get("confidence",0))
        intensity=float(proposal.get("emotion_intensity",0))
        pause=int(proposal.get("pause_after_ms",-1))
        if role not in ROLES or emotion not in EMOTIONS or not 0<=confidence<=1 or not 0<=intensity<=1 or not 0<=pause<=1200:
            raise ValueError("UNSUPPORTED_DIRECTIVE")
        if confidence<.80:
            issues.append({"index":idx,"code":"LOW_SEMANTIC_CONFIDENCE"})
        accepted.append({"index":idx,"parent_line":original["parent_line"],
            "role":role,"emotion":emotion,"confidence":confidence,
            "emotion_intensity":intensity,"pause_after_ms":pause,
            "status":"REVIEW" if confidence<.80 else "SCHEMA_VALID_ONLY"})
    seenmap={int(x["index"]):x for x in accepted}
    for i in sorted(seenmap):
        if i-1 not in seenmap:continue
        prev=seenmap[i-1];curr=seenmap[i]
        if prev["parent_line"]==curr["parent_line"] and abs(prev["emotion_intensity"]-curr["emotion_intensity"])>.35:
            issues.append({"index":i,"code":"EMOTION_TRANSITION_ABRUPT"})
    missing=len(base)-len(seenmap)
    if missing:issues.append({"index":None,"code":"UNANNOTATED_SEGMENTS","count":missing})
    return {"schema":"saydi-v5-qc03-validated-directives-1",
        "chapter":snapshot["chapter"],"annotated":len(seenmap),
        "missing":missing,"exceptions":issues,
        "status":"REVIEW" if issues else "SCHEMA_VALID_NEEDS_LISTENING",
        "production_changed":False,"voice_reference_unchanged":True,
        "source_text_unchanged":True,"pace_tempo_override":False,
        "owner_final":False}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    ap.add_argument("--director-proposals",type=Path)
    ap.add_argument("--enable-experimental-qc03",action="store_true")
    a=ap.parse_args()
    if not a.enable_experimental_qc03:
        print("QC03_CONTEXT_DISABLED_DEFAULT");return 0
    m=json.loads(a.manifest.read_text(encoding="utf-8-sig"))
    c=context(m)
    r=verify(c,json.loads(a.director_proposals.read_text(encoding="utf8"))) if a.director_proposals else c
    a.out.parent.mkdir(parents=True,exist_ok=True)
    temp=a.out.with_suffix(".pending")
    temp.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    os.replace(temp,a.out)
    print(json.dumps({"chapter":r["chapter"],"segments":len(c["segments"]),
                      "context_groups":c["scene_groups_by_parent_line"],
                      "out":str(a.out),"owner_final":False}))
if __name__=="__main__":raise SystemExit(main())
