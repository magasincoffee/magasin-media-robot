"""SAYDI V5 QC01-05 read-only chapter evidence gates (opt-in, not production).

Reuses V5 manifest/concat/Whisper data and the existing V5 candidate/Owner ledger.
No TTS/ASR model loading, audio rewriting, UI/API/scheduler modification, or FINAL.
The report contains no private manuscript or transcript, only hashes and indices.
"""
from __future__ import annotations

import argparse
import collections
import difflib
import hashlib
import json
import math
import os
import re
import unicodedata
import wave
from pathlib import Path

SCHEMA = "saydi-v5-qc01-05-audit-v1"
MAX_ATTEMPTS = 2
_TOKEN = re.compile(r"[A-Za-zÀ-ỹĐđ]+|\d+", re.UNICODE)
_ACRONYM = re.compile(r"\b[A-Z]{2,}\b")

def read(path):
    result = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(result, dict):
        raise ValueError("INVALID_JSON_OBJECT")
    return result

def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def nfc_tokens(text):
    return [unicodedata.normalize("NFC", t).casefold() for t in _TOKEN.findall(text)]

def without_tone(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
                   if unicodedata.category(c) != "Mn").casefold()

def lexical_findings(expected, heard):
    a, b = nfc_tokens(expected), nfc_tokens(heard)
    edits = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        before, after = a[i1:i2], b[j1:j2]
        if tag == "replace" and len(before) == len(after) and all(
                without_tone(x) == without_tone(y) for x, y in zip(before, after)):
            cause = "VIETNAMESE_TONE_ASR_SUSPECT"
        else:
            cause = {"replace": "WORD_SUBSTITUTION_ASR_SUSPECT",
                     "delete": "WORD_OMISSION_ASR_SUSPECT",
                     "insert": "WORD_REPETITION_ASR_SUSPECT"}[tag]
        edits.append({"class": cause, "expected_count": len(before),
                      "heard_count": len(after)})
    return edits

def verified_concat(path, segment_count):
    rows = Path(path).read_text(encoding="utf-8-sig").splitlines()
    if len(rows) != 2 * segment_count:
        raise ValueError("CONCAT_COUNT_MISMATCH")
    paths = []
    for row in rows:
        if not re.fullmatch(r"file '[^']+'", row):
            raise ValueError("UNEXPECTED_CONCAT_SYNTAX")
        path = Path(row[6:-1])
        if not path.is_file():
            raise FileNotFoundError(str(path))
        paths.append(path)
    return paths

def wav_detail(path):
    with wave.open(str(path), "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError("PCM16_MONO_REQUIRED")
        frames, rate = w.getnframes(), w.getframerate()
        if rate <= 0 or frames <= 0:
            raise ValueError("BAD_WAV")
        edge_frames = min(frames, max(1, round(rate * .025)))
        beginning = w.readframes(edge_frames)
        w.setpos(frames-edge_frames)
        ending = w.readframes(edge_frames)
    import array
    first, last = array.array("h"), array.array("h")
    first.frombytes(beginning)
    last.frombytes(ending)
    return {"seconds": frames/rate, "rate": rate,
            "start_abs": abs(first[0])/32768,
            "end_abs": abs(last[-1])/32768,
            "start_rms": math.sqrt(sum(v*v for v in first)/len(first))/32768,
            "end_rms": math.sqrt(sum(v*v for v in last)/len(last))/32768}

def beat_hint(text, is_heading):
    """Only an auditable editorial *suggestion*. Never a claim about heard emotion."""
    if is_heading:
        return "HEADING", .95
    v = unicodedata.normalize("NFC", text).casefold()
    if any(k in v for k in ("sáng hôm sau", "ngày hôm sau", "đêm ấy", "trong khi đó")):
        return "SCENE_TRANSITION_POSSIBLE", .72
    if any(k in v for k in ("sợ hãi", "hoảng hốt", "căng thẳng", "giật mình")):
        return "TENSION_POSSIBLE", .75
    if any(k in v for k in ("nhớ lại", "suy nghĩ", "tôi tự hỏi", "hồi tưởng")):
        return "REFLECTION_POSSIBLE", .75
    if text.lstrip().startswith(("“", "\"", "—")):
        return "DIALOGUE_POSSIBLE", .68
    return "NARRATION", .55

def audit(manifest, baseline_qc, original_concat, review_concat,
          baseline_audio, review_audio, chunk_dir, repair_gate=None,
          new_qc=None, owner_acceptance=None, max_issues=50):
    m, q = read(manifest), read(baseline_qc)
    items = m["segments"]
    count = len(items)
    if not count or count > 10000:
        raise ValueError("INVALID_SEGMENT_COUNT")
    if [int(x["index"]) for x in items] != list(range(count)):
        raise ValueError("NON_CANONICAL_SEGMENT_SEQUENCE")
    rows = {int(x["index"]):x for x in q["rows"]}
    if set(rows) != set(range(count)):
        raise ValueError("INCOMPLETE_BASELINE_ASR")
    original = verified_concat(original_concat, count)
    changed = verified_concat(review_concat, count)
    source_hash, new_hash = sha(baseline_audio), sha(review_audio)
    gate = read(repair_gate) if repair_gate else {}
    if gate:
        if gate["source_mp3_sha256"] != source_hash or gate["output_sha256"] != new_hash:
            raise ValueError("REVIEW_RECEIPT_SHA_MISMATCH")
        if gate.get("approved_sample_mp3"):
            if sha(gate["approved_sample_mp3"]) != gate.get("approved_sample_sha256"):
                raise ValueError("STALE_APPROVED_SAMPLE_HASH")
    modified_speech = [i for i in range(count) if original[2*i].resolve() != changed[2*i].resolve()]
    modified_gaps = [i for i in range(count) if original[2*i+1].resolve() != changed[2*i+1].resolve()]
    if gate:
        if modified_speech != gate["changed_spoken_segments"] or modified_gaps != gate["changed_silence_after_segments"]:
            raise ValueError("REVIEW_DIFF_NOT_EQUAL_TO_RECEIPT")
    if len(modified_speech) > MAX_ATTEMPTS:
        raise ValueError("UNBOUNDED_SPEECH_REPAIR")
    candidate_rows = {int(r["index"]):r for r in read(new_qc)["rows"]} if new_qc else {}
    if any(i not in candidate_rows for i in modified_speech):
        raise ValueError("MODIFIED_SPEECH_REQUIRES_NEW_ASR_HASH")
    for i in range(count):
        baseline = Path(chunk_dir) / f"{i:06d}.wav"
        if sha(baseline) != rows[i]["audio_sha256"]:
            raise ValueError(f"STALE_BASELINE_ASR_AT_{i}")
    for i in modified_speech:
        if sha(changed[2*i]) != candidate_rows[i]["audio_sha256"]:
            raise ValueError(f"STALE_CHANGED_ASR_AT_{i}")

    now = 0.0
    timeline, lengths, gaps, edge_flags = [], [], [], []
    last_parent = None
    for i, item in enumerate(items):
        audio, silence = changed[2*i:2*i+2]
        md = wav_detail(audio)
        gap = wav_detail(silence)
        start, end = now, now + md["seconds"]
        current_gap_ms = round(gap["seconds"]*1000)
        suffix = item.get("canonical_text", "").rstrip()[-1:]
        changed_paragraph = last_parent is not None and item.get("parent_line") != last_parent
        timeline.append({"segment":i,"time_s":round(start,3),"end_s":round(end,3)})
        lengths.append(md["seconds"])
        gaps.append({"index":i,"gap_ms":current_gap_ms,"mark":suffix,
                     "heading":bool(item.get("heading")),
                     "changed":i in modified_gaps,
                     "new_paragraph":changed_paragraph})
        if i:
            prev = wav_detail(changed[2*(i-1)])
            endpoint = max(prev["end_abs"],md["start_abs"])
            if endpoint > .025:
                edge_flags.append({"join_after":i-1,"time_s":round(start,3),
                                   "indicator":"PCM_EDGE_RISK_NOT_AUDIBLE_PROOF"})
        last_parent = item.get("parent_line")
        now = end + gap["seconds"]
    distribution = dict(sorted(collections.Counter(x["gap_ms"] for x in gaps).items()))
    dominant = max(distribution.values())/count
    qc01 = {"status":"REVIEW","pause_distribution_ms":distribution,
            "most_common_gap_ratio":round(dominant,4),
            "changed_gap_count":len(modified_gaps),
            "changed_gap_indices":modified_gaps,
            "owner_approved_scope":"SAMPLE_ONLY" if gate and gate.get("qc02_owner_sample_accepted") else "NONE",
            "finding":"UNIFORM_RHYTHM_POTENTIAL_REVIEW" if dominant>.7 else "CONTEXTUAL_PAUSE_AUDIT_REQUIRED",
            "verified_voice_speed_unchanged":bool(gate.get("native_vieneu_tempo_unchanged"))}
    qc02 = {"status":"REVIEW","technical_endpoint_flags":edge_flags[:max_issues],
            "flag_count":len(edge_flags),"joins_checked":count-1,
            "timbre_continuity":"NOT_MEASURED_REQUIRES_LISTENING",
            "approved_sample_not_entire_chapter":bool(gate.get("qc02_owner_sample_accepted"))}
    editorial = []
    flagged = []
    for i,item in enumerate(items):
        hint,confidence=beat_hint(item.get("canonical_text",""),item.get("heading",False))
        if hint != "NARRATION" and confidence >=.68:
            editorial.append({"index":i,"at_s":timeline[i]["time_s"],
                              "suggested_delivery":hint,"confidence":confidence,
                              "accepted":False})
        lexical = lexical_findings(rows[i].get("expected",""), rows[i].get("heard",""))
        qrow = candidate_rows.get(i, rows[i])
        if qrow["status"]!="PASS" or lexical or _ACRONYM.search(item.get("canonical_text","")):
            entry={"index":i,"at_s":timeline[i]["time_s"],
                  "baseline_asr_status":rows[i]["status"],
                  "checked_asr_status":qrow["status"],
                  "checked_audio_sha256":qrow["audio_sha256"],
                  "asr_similarity":qrow.get("asr_similarity"),
                  "asr_issue_classes":lexical[:6],
                  "needs_human_pronunciation_check":True}
            if _ACRONYM.search(item.get("canonical_text","")):
                entry["special_term"]="ACRONYM_PRONUNCIATION_REVIEW"
            flagged.append(entry)
    qc03={"status":"REVIEW","semantic_candidates":editorial[:max_issues],
          "candidate_total":len(editorial),"emotion_ear_check":"MISSING",
          "no_tts_emotion_controls_invented":True}
    qc04={"status":"REVIEW","baseline_review_count":sum(x["status"]!="PASS" for x in rows.values()),
          "checked_asr_review_count":sum(candidate_rows.get(i,rows[i])["status"]!="PASS" for i in rows),
          "issues_total":len(flagged),"issues":flagged,
          "issues_preview":flagged[:max_issues],
          "automatic_asr_not_pronunciation_pass":True}
    owner=read(owner_acceptance) if owner_acceptance else {}
    if owner.get("chapter_final_approved") and owner.get("source_mp3_sha256")!=new_hash:
        raise ValueError("STALE_OWNER_APPROVAL_FOR_DIFFERENT_MP3")
    qc05={"status":"REVIEW","changed_speech_indices":modified_speech,
          "changed_gap_indices":modified_gaps,
          "speech_change_count":len(modified_speech),
          "bounded_attempt_limit":MAX_ATTEMPTS,
          "candidate_asr_hash_verified":True,
          "baseline_asr_hash_verified":True,
          "whole_chapter_owner_approved":bool(owner.get("chapter_final_approved", False)),
          "prohibited_auto_final":True,
          "rollback_source_mp3_sha256":source_hash,
          "repair_receipt_present":bool(gate)}
    return {"schema":SCHEMA,"chapter":m.get("chapter_number"),
        "status":"REVIEW","final":False,"production_modified":False,
        "original_mp3_sha256":source_hash,"review_mp3_sha256":new_hash,
        "review_duration_from_concat_s":round(now,3),"segment_count":count,
        "qc01":qc01,"qc02":qc02,"qc03":qc03,"qc04":qc04,"qc05":qc05,
        "summary":{"issues_found":len(flagged)+len(edge_flags),
                   "issues_repaired_production":0,
                   "issues_needing_review":len(flagged)+len(edge_flags),
                   "verdict":"INCOMPLETE_HUMAN_LISTENING_AND_LAYERED_QC",
                   "full_qc_final_not_claimed":True},
        "paths":{"review_mp3":str(review_audio)},
        "source_text_exported":False}

def write_report(path, data):
    path=Path(path)
    if path.exists():
        raise FileExistsError("NO_OVERWRITE_QC_RESULT")
    if any(part.lower() in ("owner_approved_natural_v5", "chunks", "stitch_cleaned") for part in path.parts):
        raise ValueError("REPORT_IN_PRODUCTION_TREE_NOT_ALLOWED")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp=path.with_suffix(".pending")
    if temp.exists():
        raise FileExistsError("PENDING_REPORT_EXISTS")
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    os.replace(temp,path)

def main():
    p=argparse.ArgumentParser()
    for name in ("manifest","baseline-qc","original-concat","review-concat",
                 "baseline-audio","review-audio","chunk-dir","report"):
        p.add_argument("--"+name,required=True)
    for name in ("repair-gate","new-qc","owner-acceptance"):
        p.add_argument("--"+name)
    p.add_argument("--opt-in",action="store_true")
    a=p.parse_args()
    if not a.opt_in:
        raise SystemExit("QC01-05_DISABLED_BY_DEFAULT: pass --opt-in to run read-only")
    r=audit(a.manifest,a.baseline_qc,a.original_concat,a.review_concat,
            a.baseline_audio,a.review_audio,a.chunk_dir,
            a.repair_gate,a.new_qc,a.owner_acceptance)
    write_report(a.report,r)
    print(json.dumps({"status":r["status"],"report":a.report,
        "qc01_changed_gaps":r["qc01"]["changed_gap_count"],
        "qc02_edge_flags":r["qc02"]["flag_count"],
        "qc03_semantic_reviews":r["qc03"]["candidate_total"],
        "qc04_asr_reviews":r["qc04"]["checked_asr_review_count"],
        "qc05_speech_changes":r["qc05"]["speech_change_count"],
        "whole_chapter_final":False},ensure_ascii=True))

if __name__=="__main__":
    main()
