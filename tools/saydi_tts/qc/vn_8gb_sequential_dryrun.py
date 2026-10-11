"""A complete TWO-PHASE synthetic VieNeu->Whisper sequence, with zero model load.

The only purpose is to verify control-plane phase barriers using synthetic
inputs; it CANNOT start a real worker, change Owner STOP, or write checkpoint.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import dataclass

try:
    from vn_8gb_controller_bridge import evaluate_existing_job
except ImportError:
    from .vn_8gb_controller_bridge import evaluate_existing_job

STEPS = ("VIENEU_CHECK", "TTS_SYNTHETIC_DONE", "UNLOAD_BARRIER",
         "WHISPER_CHECK", "ASR_SYNTHETIC_DONE", "REVIEW_ONLY")

def synthetic_clean_snapshot() -> dict:
    return {
        "schema": "saydi-vn-8gb-h4-telemetry-v1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "host": "DESKTOP-H4A16IL", "physical_ram_gib": 7.88,
        "cpu_logical_threads": 4, "ram_samples_gib": [3.4, 3.35, 3.3, 3.38, 3.42],
        "disk_c_free_gib": 4.0, "disk_d_free_gib": 50.0, "temp_drive": "D:",
        "heavy_workers": [], "owner_stop_latch": "ON",
        "checkpoint_ownership": "VERIFIED", "worker_mutex_state": "FREE",
    }

def dry_run(tts_snapshot: dict, asr_snapshot: dict, *, unload_verified: bool) -> dict:
    """Simulation inputs only. No real TTS/ASR/owner authorization imported."""
    events = ["VIENEU_CHECK"]
    tts = evaluate_existing_job(
        {"action":"resume","state":"QUEUED","chapter":999,"id":"synthetic"},
        tts_snapshot, authenticated_owner_start=True,
        trusted_generation_witness=True, internal_tts_to_asr_barrier_qualified=True,
    )
    if tts["decision"] != "ELIGIBLE_FOR_EXISTING_AUTHORIZED_CHECKS":
        return _hold(events,"TTS_HOLD",tts["reasons"])
    events.append("TTS_SYNTHETIC_DONE")
    events.append("UNLOAD_BARRIER")
    if not unload_verified:
        return _hold(events,"UNLOAD_UNVERIFIED",["TTS_MODEL_UNLOAD_NOT_PROVEN"])
    if asr_snapshot.get("heavy_workers"):
        return _hold(events,"UNLOAD_UNVERIFIED",["HEAVY_WORKER_STILL_PRESENT"])
    events.append("WHISPER_CHECK")
    asr=evaluate_existing_job(
        {"action":"recheck","state":"QUEUED","chapter":999,"id":"synthetic"},
        asr_snapshot, authenticated_owner_start=True,
        trusted_generation_witness=True,
    )
    if asr["decision"] != "ELIGIBLE_FOR_EXISTING_AUTHORIZED_CHECKS":
        return _hold(events,"ASR_HOLD",asr["reasons"])
    events.extend(("ASR_SYNTHETIC_DONE","REVIEW_ONLY"))
    return {
        "status":"SYNTHETIC_REVIEW_SEQUENCE_PASS", "trace":events,
        "real_vieneu_loaded":False,"real_whisper_loaded":False,
        "production_started":False,"owner_approval_inferred":False,
        "audio_generated":False,"checkpoint_changed":False,
    }

def _hold(events:list[str],reason:str,details:list[str])->dict:
    return {
        "status":"HOLD", "halt_at":reason,"details":details,"trace":events,
        "real_vieneu_loaded":False,"real_whisper_loaded":False,
        "production_started":False,"owner_approval_inferred":False,
        "audio_generated":False,"checkpoint_changed":False,
    }

def main()->int:
    baseline=synthetic_clean_snapshot()
    result=dry_run(baseline,dict(baseline),unload_verified=True)
    print(json.dumps(result,sort_keys=True))
    return 0 if result["status"]=="SYNTHETIC_REVIEW_SEQUENCE_PASS" else 21

if __name__=="__main__":
    raise SystemExit(main())
