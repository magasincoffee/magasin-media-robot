from __future__ import annotations
import argparse, hashlib, json, re, sys, os, ctypes
from difflib import SequenceMatcher
from pathlib import Path

# Owner safety policy: cap offline Vietnamese ASR to two logical CPUs.
# Keep this before heavy numerical libraries / Whisper model initialization.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

def limit_qc_resources() -> None:
    if sys.platform != "win32":
        return
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetProcessAffinityMask.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
    kernel.SetPriorityClass.argtypes = (ctypes.c_void_p, ctypes.c_uint)
    current = kernel.GetCurrentProcess()
    logical = os.cpu_count() or 4
    mask = 0x1  # one logical CPU for stable long-running local QC
    if not kernel.SetProcessAffinityMask(current, mask):
        print("[QC] WARNING: CPU affinity limit could not be applied", flush=True)
    kernel.SetPriorityClass(current, 0x00004000)  # BELOW_NORMAL_PRIORITY_CLASS
    print(f"[QC] RESOURCE_LIMIT logical_cpu_affinity={mask} threads=1 priority=below-normal", flush=True)

limit_qc_resources()

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
sys.path.insert(0, r"C:\SAYDI\qc")
from saydi_audiobook.pronunciation import vietnamese_integer_spoken_form

def norm(value: str) -> str:
    value = re.sub(r"(?<!\w)\d{1,6}(?!\w)", lambda m: vietnamese_integer_spoken_form(m.group(0)) or m.group(0), value)
    return re.sub(r"\s+", " ", re.sub(r"[^\wÀ-ỹĐđ]+", " ", value.lower())).strip()

def similarity(a: str, b: str) -> float:
    aa, bb = norm(a), norm(b)
    return SequenceMatcher(None, aa, bb, autojunk=False).ratio() if aa and bb else 0.0

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def thresholds(word_count: int) -> tuple[float,float]:
    if word_count <= 4:
        return 0.78, 0.72
    if word_count <= 11:
        return 0.90, 0.80
    return 0.94, 0.84

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True)
    p.add_argument("--chunk-dir",required=True)
    p.add_argument("--report",required=True)
    p.add_argument("--indices",default="")
    args=p.parse_args()

    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    items=manifest["segments"]
    wanted=None
    if args.indices.strip():
        wanted={int(x) for x in args.indices.split(",") if x.strip()}

    model=WhisperModel(
        "small",device="cpu",compute_type="int8",
        download_root=r"C:\SAYDI\qc\models",cpu_threads=1
    )
    rows=[]; flagged=[]
    for item in items:
        idx=int(item["index"])
        if wanted is not None and idx not in wanted:
            continue
        wav=Path(args.chunk_dir)/f"{idx:06d}.wav"
        if not wav.exists() or wav.stat().st_size < 1024:
            rows.append({"index":idx,"status":"FAIL","reason":["missing_audio"]})
            flagged.append(idx)
            continue

        # The final audiobook always places a breath/pause around a segment.
        # Add the same acoustic context for ASR QC so the first syllable is not
        # penalized merely because the isolated WAV starts at sample zero.
        audio, sample_rate = sf.read(str(wav), dtype="float32", always_2d=False)
        if getattr(audio, "ndim", 1) > 1:
            audio = audio.mean(axis=1)
        pad = np.zeros(int(sample_rate * 0.25), dtype=np.float32)
        padded_path = Path(args.report).parent / f".qc_padded_{idx:06d}.wav"
        sf.write(str(padded_path), np.concatenate([pad, audio, pad]), sample_rate, subtype="PCM_16")
        try:
            segments,_=model.transcribe(
                str(padded_path),language="vi",beam_size=5,
                word_timestamps=True,vad_filter=True
            )
        finally:
            padded_path.unlink(missing_ok=True)
        heard=[]; probs=[]
        for seg in segments:
            heard.append(seg.text.strip())
            for word in (seg.words or []):
                if word.probability is not None:
                    probs.append(float(word.probability))
        heard_text=" ".join(x for x in heard if x)
        expected=str(item.get("spoken_text") or item["canonical_text"])
        score=similarity(expected,heard_text)
        word_count=max(1,len(norm(expected).split()))
        sim_min, conf_min=thresholds(word_count)
        mean_conf=(sum(probs)/len(probs)) if probs else 0.0
        min_conf=min(probs) if probs else 0.0
        reasons=[]
        if score < sim_min: reasons.append("asr_similarity")
        if mean_conf < conf_min: reasons.append("mean_word_confidence")
        status="PASS" if not reasons else "REVIEW"
        if reasons: flagged.append(idx)
        rows.append({
            "index":idx,"status":status,"word_count":word_count,
            "asr_similarity":round(score,4),
            "mean_word_confidence":round(mean_conf,4),
            "min_word_confidence":round(min_conf,4),
            "expected":expected,"heard":heard_text,
            "audio_sha256":sha256(wav),"reasons":reasons,
        })
        print(f"[QC] {idx+1}/{len(items)} {status} sim={score:.3f} conf={mean_conf:.3f}",flush=True)

    report={
        "schema_version":"saydi-local-segment-qc-v1",
        "checked":len(rows),"flagged_indices":sorted(set(flagged)),
        "pass":not flagged,"rows":rows,
    }
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"checked":len(rows),"flagged":sorted(set(flagged)),"pass":not flagged},ensure_ascii=False),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
