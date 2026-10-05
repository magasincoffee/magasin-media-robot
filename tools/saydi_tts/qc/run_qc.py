from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import time
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

from saydi_audiobook.repair import build_targeted_pronunciation_repair
from saydi_audiobook.prosody import evaluate_prosody_metrics, get_prosody_envelope


ROOT = Path(r"C:\SAYDI")
CFG = json.loads((ROOT / "worker" / "config.json").read_text(encoding="utf-8"))
API = CFG["api_url"]
TOKEN = CFG["worker_token"]
QC = ROOT / "qc"
REPORTS = QC / "reports"
MODELS = QC / "models"


def call(action, **kw):
    data = json.dumps({"action": action, **kw}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API,
        data=data,
        headers={"Content-Type": "application/json", "X-SAYDI-WORKER-TOKEN": TOKEN},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        out = json.loads(response.read().decode("utf-8"))
    if out.get("error"):
        raise RuntimeError(out["error"])
    return out


def chunks(job_id):
    out = []
    after = -1
    while True:
        rows = call("chunks", job_id=job_id, after_index=after, limit=20).get("chunks") or []
        if not rows:
            return out
        out += rows
        after = int(rows[-1]["chunk_index"])


def norm(value):
    return re.sub(r"\s+", " ", re.sub(r"[^\wÀ-ỹĐđ]+", " ", value.lower())).strip()


def sim(a, b):
    a, b = norm(a), norm(b)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pitch_variation(audio, sample_rate):
    frame = max(256, int(sample_rate * 0.05))
    hop = max(128, int(sample_rate * 0.05))
    min_lag = max(1, int(sample_rate / 350))
    max_lag = max(min_lag + 1, int(sample_rate / 70))
    f0 = []
    for start in range(0, max(0, len(audio) - frame + 1), hop):
        segment = np.asarray(audio[start : start + frame], dtype=np.float64)
        rms = math.sqrt(float(np.mean(segment * segment)) + 1e-12)
        if 20 * math.log10(max(rms, 1e-12)) < -38:
            continue
        segment = segment - float(np.mean(segment))
        segment *= np.hanning(len(segment))
        nfft = 1
        while nfft < len(segment) * 2:
            nfft *= 2
        spec = np.fft.rfft(segment, n=nfft)
        ac = np.fft.irfft(spec * np.conj(spec), n=nfft)[: len(segment)]
        if ac[0] <= 1e-12:
            continue
        hi = min(max_lag, len(ac) - 1)
        if hi <= min_lag:
            continue
        lag = min_lag + int(np.argmax(ac[min_lag : hi + 1]))
        confidence = float(ac[lag] / ac[0])
        if confidence < 0.25:
            continue
        hz = sample_rate / lag
        if 70 <= hz <= 350:
            f0.append(float(hz))
    if len(f0) < 4:
        return None
    arr = np.asarray(f0, dtype=np.float64)
    median = float(np.median(arr))
    semitones = 12 * np.log2(arr / median)
    return float(np.std(semitones))


def metrics(path):
    audio, sample_rate = sf.read(str(path), dtype="float32", always_2d=False)
    if getattr(audio, "ndim", 1) > 1:
        audio = audio.mean(axis=1)
    if len(audio) == 0:
        raise RuntimeError("empty")
    duration = len(audio) / sample_rate
    peak = float(np.max(np.abs(audio)))
    rms = math.sqrt(float(np.mean(audio * audio)) + 1e-12)
    clipping = float(np.mean(np.abs(audio) >= 0.995))
    threshold = 10 ** (-45 / 20)
    active = np.flatnonzero(np.abs(audio) > threshold)
    if active.size:
        lead = active[0] / sample_rate
        trail = (len(audio) - 1 - active[-1]) / sample_rate
    else:
        lead = trail = duration

    frame = max(1, int(sample_rate * 0.02))
    longest = cur = silent = 0
    frame_db = []
    frame_count = len(audio) // frame
    for i in range(frame_count):
        segment = audio[i * frame : (i + 1) * frame]
        db = 20 * math.log10(
            max(math.sqrt(float(np.mean(segment * segment)) + 1e-12), 1e-12)
        )
        frame_db.append(db)
        if db < -45:
            silent += 1
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0

    active_db = [value for value in frame_db if value >= -45]
    return {
        "duration_sec": duration,
        "peak": peak,
        "rms_dbfs": 20 * math.log10(max(rms, 1e-12)),
        "clipping_ratio": clipping,
        "leading_silence_sec": lead,
        "trailing_silence_sec": trail,
        "longest_silence_sec": longest * 0.02,
        "pause_ratio": (silent / frame_count if frame_count else 1.0),
        "energy_variation_db": (float(np.std(active_db)) if len(active_db) >= 2 else 0.0),
        "pitch_variation_semitones": _pitch_variation(audio, sample_rate),
        "audio_sha256": _sha256(path),
    }


def ev(event_type, severity, idx, start, end, score=None, **details):
    return {
        "event_type": event_type,
        "severity": severity,
        "chunk_index": idx,
        "time_start_sec": round(start, 2),
        "time_end_sec": round(end, 2),
        "score": None if score is None else round(float(score), 4),
        "details": details,
    }


def _repair_batch_id(job_id, attempt, indices, pronunciation_plans):
    payload = {
        "job_id": job_id,
        "attempt": attempt,
        "indices": sorted(indices),
        "pronunciation": {
            str(idx): {
                "audio": plan.source_audio_sha256,
                "spoken": plan.spoken_text,
                "lexicon": plan.lexicon_version,
            }
            for idx, plan in sorted(pronunciation_plans.items())
            if idx in indices
        },
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "qc004-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _stage_wavs(chunk_dir, indices):
    staged = {}
    for idx in indices:
        wav = chunk_dir / f"{idx:06d}.wav"
        if not wav.exists():
            continue
        backup = chunk_dir / f"{idx:06d}.wav.qc004.bak"
        if backup.exists():
            backup.unlink()
        wav.replace(backup)
        staged[idx] = backup
    return staged


def _restore_staged(chunk_dir, staged):
    for idx, backup in staged.items():
        if not backup.exists():
            continue
        wav = chunk_dir / f"{idx:06d}.wav"
        if wav.exists():
            wav.unlink()
        backup.replace(wav)


def _discard_staged(staged):
    for backup in staged.values():
        if backup.exists():
            backup.unlink()


def check(model, job, attempt, *, prosody_profile_key, only_chunks=None, replace_chunk_indices=None):
    out = Path(job["output_file_name"])
    chunk_dir = out.parent / "chunks"
    events = []
    observations = []
    technical_repair = set()
    pronunciation_plans = {}
    current_time = 0.0
    previous_trail = 0.0

    rows = chunks(job["id"])
    if only_chunks is not None:
        selected = set(only_chunks)
        rows = [row for row in rows if int(row["chunk_index"]) in selected]

    chapter = int(job.get("chapter_number") or 0)
    total = len(rows)
    started = time.time()
    progress_path = QC / "qc_progress.json"
    print(f"[QC] Chapter {chapter}: START | {total} chunks | attempt={attempt}", flush=True)

    for pos, chunk in enumerate(rows, start=1):
        idx = int(chunk["chunk_index"])
        render_text = str(chunk.get("text_content") or "")
        canonical_text = str(chunk.get("canonical_text_content") or render_text)
        override_applied = bool(chunk.get("spoken_override_applied"))
        wav = chunk_dir / f"{idx:06d}.wav"

        chunk_started = time.time()
        elapsed = chunk_started - started
        average = (elapsed / (pos - 1)) if pos > 1 else 0.0
        eta = average * (total - pos + 1)
        print(
            f"[QC] Chapter {chapter} | chunk {pos}/{total} (id={idx}) | ASR starting | "
            f"elapsed={elapsed/60:.1f}m | ETA~{eta/60:.1f}m",
            flush=True,
        )
        progress_path.write_text(
            json.dumps(
                {
                    "chapter": chapter,
                    "chunk_position": pos,
                    "chunk_index": idx,
                    "total_chunks": total,
                    "attempt": attempt,
                    "stage": "asr",
                    "elapsed_sec": round(elapsed, 1),
                    "eta_sec": round(eta, 1),
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        if not wav.exists() or wav.stat().st_size < 1024:
            events.append(ev("missing_audio", "error", idx, current_time, current_time))
            technical_repair.add(idx)
            continue

        try:
            measurement = metrics(wav)
        except Exception as exc:
            events.append(
                ev("decode", "error", idx, current_time, current_time, error=str(exc))
            )
            technical_repair.add(idx)
            continue

        start_time = current_time
        end_time = current_time + measurement["duration_sec"]
        current_time = end_time

        if measurement["rms_dbfs"] < -48:
            events.append(
                ev(
                    "acoustic",
                    "error",
                    idx,
                    start_time,
                    end_time,
                    measurement["rms_dbfs"],
                    reason="near_zero",
                )
            )
            technical_repair.add(idx)

        if measurement["clipping_ratio"] > 0.02:
            events.append(
                ev(
                    "clipping",
                    "error",
                    idx,
                    start_time,
                    end_time,
                    measurement["clipping_ratio"],
                )
            )
            technical_repair.add(idx)
        elif measurement["clipping_ratio"] > 0.002:
            events.append(
                ev(
                    "clipping",
                    "warning",
                    idx,
                    start_time,
                    end_time,
                    measurement["clipping_ratio"],
                )
            )

        if len(render_text) > 500 and measurement["duration_sec"] < 8:
            events.append(
                ev(
                    "duration",
                    "error",
                    idx,
                    start_time,
                    end_time,
                    measurement["duration_sec"],
                )
            )
            technical_repair.add(idx)

        if measurement["longest_silence_sec"] > 2.2:
            events.append(
                ev(
                    "silence",
                    "warning",
                    idx,
                    start_time,
                    end_time,
                    measurement["longest_silence_sec"],
                )
            )

        gap = previous_trail + measurement["leading_silence_sec"] if idx > 0 else 0
        if gap > 1.2:
            events.append(ev("join_discontinuity", "error", idx, start_time, start_time + gap, gap))
        elif gap > 0.65:
            events.append(
                ev("join_discontinuity", "warning", idx, start_time, start_time + gap, gap)
            )
        previous_trail = measurement["trailing_silence_sec"]

        try:
            segments, _info = model.transcribe(
                str(wav),
                language="vi",
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=False,
                word_timestamps=True,
            )
            segments = list(segments)
            heard = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
            similarity = sim(render_text, heard)
            canonical_similarity = sim(canonical_text, heard)
            words = [
                word
                for segment in segments
                for word in (getattr(segment, "words", None) or [])
                if getattr(word, "word", "").strip()
            ]
            probabilities = [
                float(word.probability)
                for word in words
                if getattr(word, "probability", None) is not None
            ]
            min_conf = min(probabilities) if probabilities else None
            mean_conf = sum(probabilities) / len(probabilities) if probabilities else None
            unclear = [
                word.word.strip()
                for word in words
                if getattr(word, "probability", None) is not None
                and float(word.probability) < 0.60
            ]
            word_count = len(words) if words else len(norm(heard).split())
            speaking_rate = (
                word_count / max(measurement["duration_sec"] / 60.0, 1e-6)
                if word_count
                else 0.0
            )
            prosody_evaluation = evaluate_prosody_metrics(
                profile_key=prosody_profile_key,
                speaking_rate_wpm=speaking_rate,
                pause_ratio=measurement["pause_ratio"],
                pitch_variation_semitones=measurement["pitch_variation_semitones"],
                energy_variation_db=measurement["energy_variation_db"],
            )
            if prosody_evaluation.reasons:
                events.append(
                    ev(
                        "prosody_style_mismatch",
                        "warning",
                        idx,
                        start_time,
                        end_time,
                        None,
                        profile_key=prosody_evaluation.profile_key,
                        profile_fingerprint=prosody_evaluation.profile_fingerprint,
                        reasons=list(prosody_evaluation.reasons),
                        measured=prosody_evaluation.measured,
                    )
                )

            pronunciation_plan = None
            if not override_applied:
                pronunciation_plan = build_targeted_pronunciation_repair(
                    chunk_index=idx,
                    canonical_text=canonical_text,
                    heard_text=heard,
                    source_audio_sha256=measurement["audio_sha256"],
                )
                if pronunciation_plan is not None:
                    pronunciation_plans[idx] = pronunciation_plan
                    events.append(
                        ev(
                            "pronunciation_repair_candidate",
                            "info",
                            idx,
                            start_time,
                            end_time,
                            similarity,
                            lexicon_version=pronunciation_plan.lexicon_version,
                            expected_suspect_tokens=list(
                                pronunciation_plan.expected_suspect_tokens
                            ),
                            applied_overrides=[
                                {
                                    "key": item.key,
                                    "category": item.category,
                                    "source_text": item.source_text,
                                    "spoken_text": item.spoken_text,
                                }
                                for item in pronunciation_plan.applied_overrides
                            ],
                            source_audio_sha256=measurement["audio_sha256"],
                        )
                    )

            observation = {
                "chunk_index": idx,
                "audio_sha256": measurement["audio_sha256"],
                "attempt": attempt,
                "asr_similarity": round(similarity, 4),
                "canonical_asr_similarity": round(canonical_similarity, 4),
                "min_word_confidence": None
                if min_conf is None
                else round(min_conf, 4),
                "mean_word_confidence": None
                if mean_conf is None
                else round(mean_conf, 4),
                "unclear_tokens": unclear[:20],
                "speaking_rate_wpm": round(speaking_rate, 2),
                "pause_ratio": round(measurement["pause_ratio"], 4),
                "pitch_variation_semitones": None
                if measurement["pitch_variation_semitones"] is None
                else round(measurement["pitch_variation_semitones"], 4),
                "energy_variation_db": round(measurement["energy_variation_db"], 4),
                "clipping_ratio": round(measurement["clipping_ratio"], 6),
                "duration_sec": round(measurement["duration_sec"], 3),
                "spoken_override_applied": override_applied,
                "qc_repair_attempts": int(chunk.get("qc_repair_attempts") or 0),
                "pronunciation_repair_candidate": pronunciation_plan is not None,
                "prosody_profile_key": prosody_evaluation.profile_key,
                "prosody_profile_fingerprint": prosody_evaluation.profile_fingerprint,
                "prosody_status": prosody_evaluation.status,
                "prosody_reasons": list(prosody_evaluation.reasons),
            }
            observations.append(observation)

            took = time.time() - chunk_started
            print(
                f"[QC] Chapter {chapter} | chunk {pos}/{total} DONE | "
                f"similarity={similarity:.3f} | canonical_similarity={canonical_similarity:.3f} | "
                f"word_min={min_conf if min_conf is not None else 'n/a'} | "
                f"wpm={speaking_rate:.1f} | pause={measurement['pause_ratio']:.3f} | "
                f"pitch_var={measurement['pitch_variation_semitones'] if measurement['pitch_variation_semitones'] is not None else 'n/a'} | "
                f"profile={prosody_evaluation.profile_key} | prosody={prosody_evaluation.status} | "
                f"override={'yes' if override_applied else 'no'} | {took:.1f}s",
                flush=True,
            )

            if similarity < 0.55:
                events.append(
                    ev(
                        "asr_mismatch",
                        "error",
                        idx,
                        start_time,
                        end_time,
                        similarity,
                        expected=render_text[:160],
                        heard=heard[:160],
                    )
                )
            elif similarity < 0.76:
                events.append(
                    ev(
                        "asr_mismatch",
                        "warning",
                        idx,
                        start_time,
                        end_time,
                        similarity,
                        expected=render_text[:160],
                        heard=heard[:160],
                    )
                )

            if min_conf is not None and min_conf < 0.45:
                events.append(
                    ev(
                        "pronunciation_clarity",
                        "warning",
                        idx,
                        start_time,
                        end_time,
                        min_conf,
                        unclear_tokens=unclear[:20],
                        mean_word_confidence=mean_conf,
                    )
                )
            elif unclear:
                events.append(
                    ev(
                        "pronunciation_clarity",
                        "warning",
                        idx,
                        start_time,
                        end_time,
                        min_conf,
                        unclear_tokens=unclear[:20],
                        mean_word_confidence=mean_conf,
                    )
                )

        except Exception as exc:
            print(
                f"[QC] Chapter {chapter} | chunk {pos}/{total} ASR ERROR: {exc}",
                flush=True,
            )
            events.append(
                ev("asr_mismatch", "warning", idx, start_time, end_time, error=str(exc)[:300])
            )
            observations.append(
                {
                    "chunk_index": idx,
                    "audio_sha256": measurement["audio_sha256"],
                    "attempt": attempt,
                    "asr_error": str(exc)[:180],
                    "pause_ratio": round(measurement["pause_ratio"], 4),
                    "pitch_variation_semitones": measurement[
                        "pitch_variation_semitones"
                    ],
                    "energy_variation_db": round(
                        measurement["energy_variation_db"], 4
                    ),
                    "clipping_ratio": round(measurement["clipping_ratio"], 6),
                    "duration_sec": round(measurement["duration_sec"], 3),
                    "spoken_override_applied": override_applied,
                    "qc_repair_attempts": int(chunk.get("qc_repair_attempts") or 0),
                }
            )

    warnings = sum(item["severity"] == "warning" for item in events)
    errors = sum(item["severity"] == "error" for item in events)
    active_envelope = get_prosody_envelope(prosody_profile_key)
    report = {
        "source": "local_qc_v4",
        "attempt": attempt,
        "prosody_profile_key": active_envelope.profile_key,
        "prosody_profile_fingerprint": active_envelope.fingerprint,
        "prosody_profile_version": active_envelope.version,
        "chapter_number": job.get("chapter_number"),
        "checked_chunks": len(rows),
        "warnings": warnings,
        "errors": errors,
        "auto_repair_indices": sorted(technical_repair),
        "pronunciation_repair_indices": sorted(pronunciation_plans),
        "asr_model": "small",
        "audible_markers": False,
        "metric_schema": "pronunciation_prosody_v2",
        "chunk_observations": observations,
    }
    kwargs = {
        "job_id": job["id"],
        "qc_status": "passed" if not warnings and not errors else "review",
        "qc_report": report,
        "events": events,
    }
    if replace_chunk_indices:
        kwargs["replace_chunk_indices"] = sorted(set(replace_chunk_indices))
    call("qc_report_batch", **kwargs)

    print(
        f"[QC] Chapter {chapter}: DONE | warnings={warnings} errors={errors} | "
        f"technical_repair={sorted(technical_repair)} | "
        f"pronunciation_repair={sorted(pronunciation_plans)} | "
        f"elapsed={(time.time()-started)/60:.1f}m",
        flush=True,
    )
    return report, sorted(technical_repair), pronunciation_plans


def wait_done(book_id, job_id, limit=7200):
    end = time.time() + limit
    while time.time() < end:
        jobs = call("book_jobs", book_id=book_id, max_chapter=999).get("jobs") or []
        job = next((item for item in jobs if item["id"] == job_id), None)
        if job and job.get("status") == "completed" and job.get("output_file_name"):
            return job
        if job and job.get("status") == "failed":
            raise RuntimeError(job.get("error") or "repair failed")
        time.sleep(15)
    raise TimeoutError(job_id)


def execute_targeted_repair(job, technical, pronunciation_plans, *, attempt):
    requested = sorted(set(technical) | set(pronunciation_plans))
    if not requested:
        return [], []

    eligibility = call(
        "repair_eligibility",
        job_id=job["id"],
        chunk_indices=requested,
    )
    eligible = sorted(set(eligibility.get("eligible_indices") or []))
    exhausted = sorted(set(eligibility.get("exhausted_indices") or []))
    if exhausted:
        print(
            f"[QC] repair budget exhausted before queue: {exhausted}",
            flush=True,
        )
    if not eligible:
        return [], exhausted

    out = Path(job["output_file_name"])
    chunk_dir = out.parent / "chunks"
    staged = _stage_wavs(chunk_dir, eligible)

    spoken_overrides = []
    eligible_plans = {
        idx: plan for idx, plan in pronunciation_plans.items() if idx in eligible
    }
    for idx, plan in sorted(eligible_plans.items()):
        spoken_overrides.append(
            {
                "chunk_index": idx,
                "spoken_text": plan.spoken_text,
                "meta": plan.meta(),
            }
        )

    request_id = _repair_batch_id(
        job["id"],
        attempt,
        eligible,
        eligible_plans,
    )

    try:
        response = call(
            "repair_chunks",
            job_id=job["id"],
            chunk_indices=eligible,
            repair_request_id=request_id,
            spoken_overrides=spoken_overrides,
        )
    except Exception:
        _restore_staged(chunk_dir, staged)
        raise

    queued = sorted(set(response.get("repaired_indices") or []))
    rejected = sorted(set(eligible) - set(queued))
    if rejected:
        for idx in rejected:
            backup = staged.get(idx)
            if backup and backup.exists():
                wav = chunk_dir / f"{idx:06d}.wav"
                if wav.exists():
                    wav.unlink()
                backup.replace(wav)

    if not queued:
        return [], sorted(set(exhausted) | set(response.get("exhausted_indices") or []))

    print(
        f"[QC] queued targeted repair | chunks={queued} | request={request_id}",
        flush=True,
    )

    try:
        updated_job = wait_done(job["book_id"], job["id"])
    except Exception:
        _restore_staged(chunk_dir, {idx: path for idx, path in staged.items() if idx in queued})
        raise

    _discard_staged({idx: path for idx, path in staged.items() if idx in queued})
    exhausted = sorted(
        set(exhausted) | set(response.get("exhausted_indices") or [])
    )
    return queued, exhausted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-id", required=True)
    parser.add_argument("--max-chapter", type=int, default=5)
    parser.add_argument(
        "--observe-only",
        action="store_true",
        help="Run QC and persist observations without deleting audio or requesting repair jobs.",
    )
    parser.add_argument(
        "--disable-pronunciation-repair",
        action="store_true",
        help="Keep technical repair enabled but do not apply safe lexicon/spoken-form pronunciation repair.",
    )
    parser.add_argument(
        "--only-chunk",
        action="append",
        type=int,
        default=[],
        help="Field/debug mode: QC only the selected chunk index. Repeat as needed.",
    )
    parser.add_argument(
        "--narration-profile",
        choices=("BUSINESS_CLEAR", "STORY_NARRATIVE", "GENERAL_CLEAR"),
        default="GENERAL_CLEAR",
        help="Active profile envelope used by prosody/style QC.",
    )
    args = parser.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)

    print("[QC] Loading faster-whisper model: small / CPU int8 ...", flush=True)
    model = WhisperModel(
        "small",
        device="cpu",
        compute_type="int8",
        download_root=str(MODELS),
        cpu_threads=max(2, min(8, os.cpu_count() or 4)),
    )
    print("[QC] Model ready.", flush=True)

    jobs = call(
        "book_jobs",
        book_id=args.book_id,
        max_chapter=args.max_chapter,
    ).get("jobs") or []
    jobs = [
        job
        for job in jobs
        if 1 <= int(job.get("chapter_number") or 0) <= args.max_chapter
    ]

    only_chunks = set(args.only_chunk) if args.only_chunk else None
    summary = []

    for job in jobs:
        if job.get("status") != "completed":
            raise RuntimeError(f"chapter {job.get('chapter_number')} not complete")

        report, technical, pronunciation_plans = check(
            model,
            job,
            1,
            prosody_profile_key=args.narration_profile,
            only_chunks=only_chunks,
        )

        if args.disable_pronunciation_repair:
            pronunciation_plans = {}

        requested = sorted(set(technical) | set(pronunciation_plans))

        if requested and args.observe_only:
            report["observe_only"] = True
            report["repair_suppressed"] = requested
        elif requested:
            queued, exhausted = execute_targeted_repair(
                job,
                technical,
                pronunciation_plans,
                attempt=1,
            )
            report["queued_repair_indices"] = queued
            report["repair_exhausted_before_queue"] = exhausted

            if queued:
                refreshed = wait_done(args.book_id, job["id"])
                second_report, second_technical, second_pronunciation = check(
                    model,
                    refreshed,
                    2,
                    prosody_profile_key=args.narration_profile,
                    only_chunks=set(queued),
                    replace_chunk_indices=queued,
                )
                remaining = sorted(
                    set(second_technical) | set(second_pronunciation)
                )
                second_report["repair_exhausted"] = remaining
                if remaining:
                    call(
                        "qc_report_batch",
                        job_id=refreshed["id"],
                        qc_status="review",
                        qc_report=second_report,
                        events=[
                            ev(
                                "repair_exhausted",
                                "warning",
                                idx,
                                0,
                                0,
                                reason="bounded_retry_or_persistent_defect",
                            )
                            for idx in remaining
                        ],
                        replace_chunk_indices=remaining,
                    )
                report["post_repair"] = second_report

        summary.append(report)

    folder = REPORTS / args.book_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "qc_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = ["# SAYDI QC Report", ""]
    for item in summary:
        lines.append(
            f"- Chương {item['chapter_number']}: warnings={item['warnings']} "
            f"errors={item['errors']} technical={item['auto_repair_indices']} "
            f"pronunciation={item.get('pronunciation_repair_indices', [])}"
        )
    (folder / "QC_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
