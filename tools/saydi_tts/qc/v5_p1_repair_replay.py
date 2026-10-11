"""Replay-safe metadata validation for the existing SAYDI V5 bounded repair loop.

Deterministically folds an append-only staging journal; it is not a worker,
checkpoint writer, repair scheduler or authority to accept a chapter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "saydi-v5-p1-repair-journal-review-1"
HEX = re.compile(r"[a-f0-9]{64}\Z")
EVENTS = {"CANDIDATE_STAGED", "QC_REJECTED", "QC_REVIEW_REQUIRED", "OWNER_SAMPLE_ACCEPTED"}


def sha(value: object) -> bool:
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def fold(manifest_sha: str, source_sha: str, voice_sha: str, events: list[dict]) -> dict:
    if not all(sha(v) for v in (manifest_sha, source_sha, voice_sha)):
        raise ValueError("CHAPTER_IDENTITY_INVALID")
    if not isinstance(events, list) or len(events) > 10000:
        raise ValueError("INVALID_OR_EXCESSIVE_JOURNAL")
    states: dict[int, dict] = {}
    seen: dict[str, str] = {}
    unique = 0
    replays = 0
    for ev in events:
        if not isinstance(ev, dict):
            raise ValueError("EVENT_NOT_OBJECT")
        required = ("event_id", "kind", "segment", "attempt",
                    "original_wav_sha256", "candidate_wav_sha256")
        if not all(key in ev for key in required):
            raise ValueError("EVENT_REQUIRED_FIELD_MISSING")
        if set(ev)-set(required)-{"sample_sha256"}:
            raise ValueError("EXTRANEOUS_EVENT_FIELDS")
        if not all(sha(ev.get(k)) for k in ("event_id", "original_wav_sha256",
                                              "candidate_wav_sha256")):
            raise ValueError("INVALID_EVENT_DIGEST")
        kind, idx, attempt = ev["kind"], ev["segment"], ev["attempt"]
        if kind not in EVENTS or type(idx) is not int or idx < 0 or type(attempt) is not int or attempt not in (1,2):
            raise ValueError("EVENT_TYPE_OR_SCOPE_INVALID")
        if kind == "OWNER_SAMPLE_ACCEPTED" and not sha(ev.get("sample_sha256")):
            raise ValueError("OWNER_SAMPLE_RECEIPT_MISSING")
        if kind != "OWNER_SAMPLE_ACCEPTED" and "sample_sha256" in ev:
            raise ValueError("UNSUPPORTED_SAMPLE_FOR_EVENT")
        payload_hash = hashlib.sha256(json.dumps(ev, sort_keys=True,
            separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
        event_id = ev["event_id"]
        if event_id in seen:
            if seen[event_id] != payload_hash:
                raise ValueError("EVENT_ID_REPLAY_CONFLICT")
            replays += 1
            continue
        previous = states.get(idx)
        if previous is None:
            previous = {"segment": idx, "attempts_used":0,
                        "phase":"NOT_STAGED", "original_wav_sha256":ev["original_wav_sha256"],
                        "candidate_wav_sha256":None, "candidates":[]}
            states[idx] = previous
        if ev["original_wav_sha256"] != previous["original_wav_sha256"]:
            raise ValueError("ORIGINAL_WAV_CHANGED_DURING_RETRY")
        if kind == "CANDIDATE_STAGED":
            if not (previous["phase"] in ("NOT_STAGED", "QC_REJECTED")
                    and previous["attempts_used"] < 2
                    and attempt == previous["attempts_used"]+1):
                raise ValueError("UNBOUNDED_OR_INVALID_REPAIR_ATTEMPT")
            if ev["candidate_wav_sha256"] in previous["candidates"]:
                raise ValueError("DUPLICATE_CANDIDATE_AUDIO")
            if ev["candidate_wav_sha256"] == previous["original_wav_sha256"]:
                raise ValueError("NO_ACTUAL_AUDIO_REPAIR")
            previous["phase"] = "CANDIDATE_STAGED"
            previous["attempts_used"] = attempt
            previous["candidate_wav_sha256"] = ev["candidate_wav_sha256"]
            previous["candidates"].append(ev["candidate_wav_sha256"])
        else:
            if previous["attempts_used"] != attempt or ev["candidate_wav_sha256"] != previous["candidate_wav_sha256"]:
                raise ValueError("QC_EVENT_WITH_STALE_CANDIDATE")
            if kind in ("QC_REJECTED", "QC_REVIEW_REQUIRED"):
                if previous["phase"] != "CANDIDATE_STAGED":
                    raise ValueError("QC_EVENT_OUT_OF_ORDER")
                previous["phase"] = kind
            else:
                if previous["phase"] != "QC_REVIEW_REQUIRED":
                    raise ValueError("OWNER_APPROVAL_WITHOUT_REVIEW")
                previous["phase"] = "SAMPLE_ACCEPTED_NOT_CHAPTER_FINAL"
        seen[event_id] = payload_hash
        unique += 1
    public = [dict(segment=idx, attempts_used=s["attempts_used"],
                   phase=s["phase"], attempts_remaining=2-s["attempts_used"],
                   original_wav_sha256=s["original_wav_sha256"],
                   candidate_wav_sha256=s["candidate_wav_sha256"])
              for idx,s in sorted(states.items())]
    return {"schema":SCHEMA,"manifest_sha256":manifest_sha,
            "source_sha256":source_sha,"voice_reference_sha256":voice_sha,
            "unique_event_count":unique,"exact_replay_count":replays,
            "segment_states":public,"status":"REVIEW_ONLY_NO_DISPATCH",
            "source_wav_modified":False,"worker_started":False,
            "repair_dispatched":False,"owner_final":False}


def main() -> int:
    p=argparse.ArgumentParser(description="SAYDI P1 dry-run event replay preflight")
    p.add_argument("--journal",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--enable-journal-review",action="store_true")
    args=p.parse_args()
    if not args.enable_journal_review:
        print("SAYDI_P1_JOURNAL_REVIEW_DISABLED_DEFAULT")
        return 0
    obj=json.loads(args.journal.read_text(encoding="utf-8-sig"))
    output=fold(obj["manifest_sha256"],obj["source_sha256"],
                obj["voice_reference_sha256"],obj["events"])
    if any(c.casefold() in {"chunks","stitch_cleaned","owner_approved_natural_v5"}
           for c in args.output.parts):
        raise ValueError("OUTPUT_IS_PRODUCTION_LOCATION")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(output,f,ensure_ascii=False,indent=2)
        f.write("\n")
    print(json.dumps({"status":output["status"],"events":output["unique_event_count"],
                      "replays":output["exact_replay_count"],"worker_started":False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
