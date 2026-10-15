"""Offline-only SAYDI002-VN-001 VieNeu -> Whisper transition policy simulation.

No worker, file, network, mutex or Owner lifecycle operations exist in this module.
Snapshots are synthetic and UNTRUSTED; even a passing result never authorizes a
real H4 scan, protected checkpoint read, VieNeu/Whisper launch, STOP change, or
production dispatch. The live handoff needs a separate trusted, reviewed host.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

SCHEMA = "saydi-vn001-sequential-unload-offline-v1"
TASK_ID = "SAYDI002-VN-001"
MAX_SNAPSHOT_AGE_MS = 5_000
MAX_TRANSITION_GAP_MS = 30_000


@dataclass(frozen=True)
class SimulatedTransition:
    tts_generation: str
    asr_generation: str
    tts_observed_ms: int
    asr_observed_ms: int
    current_ms: int
    owner_start_attested: bool
    owner_stop: bool
    checkpoint_owner_attested: bool
    source_voice_model_attested: bool
    tts_shutdown_ack: bool
    tts_object_released: bool
    tts_process_reaped: bool
    tts_mutex_released: bool
    tts_model_unloaded: bool
    active_tts_workers: int
    active_asr_workers: int
    other_heavy_workers: int
    cpu_threads: int
    free_ram_gib: float
    proposed_ram_floor_gib: float
    free_c_gib: float
    free_d_gib: float


def assess_offline_handoff(frame: SimulatedTransition) -> dict[str, object]:
    """Evaluate a FAKE handoff trace only; deliberately never grant START.

    1 GiB is a simulation hypothesis, NOT a validated VieNeu/Whisper floor.
    A future live host must independently authenticate Owner generation and
    checkpoint/model identities, measure resource stability, and recheck the
    entire barrier atomically at the moment of launching a real ASR worker.
    """
    if type(frame) is not SimulatedTransition:
        raise TypeError("SIMULATED_FRAME_REQUIRED")
    reasons: list[str] = []

    def require(value: bool, reason: str) -> None:
        if value is not True:
            reasons.append(reason)

    generation_ok = (
        type(frame.tts_generation) is str
        and 1 <= len(frame.tts_generation) <= 80
        and frame.tts_generation.isascii()
        and type(frame.asr_generation) is str
        and frame.tts_generation == frame.asr_generation
    )
    require(generation_ok, "GENERATION_UNVERIFIED_OR_CHANGED")

    timestamps_ok = all(type(x) is int and x >= 0 for x in (
        frame.tts_observed_ms, frame.asr_observed_ms, frame.current_ms
    ))
    if not timestamps_ok:
        reasons.append("INVALID_MONOTONIC_TIMESTAMPS")
    elif not (
        frame.tts_observed_ms <= frame.asr_observed_ms <= frame.current_ms
        and frame.current_ms - frame.asr_observed_ms <= MAX_SNAPSHOT_AGE_MS
        and frame.asr_observed_ms - frame.tts_observed_ms <= MAX_TRANSITION_GAP_MS
    ):
        reasons.append("TRANSITION_STALE_OR_OUT_OF_ORDER")

    require(frame.owner_start_attested, "OWNER_START_NOT_ATTESTED")
    if frame.owner_stop is not False:
        reasons.append("OWNER_STOP_ACTIVE_OR_UNKNOWN")
    require(frame.checkpoint_owner_attested, "CHECKPOINT_OWNERSHIP_UNVERIFIED")
    require(frame.source_voice_model_attested, "SOURCE_VOICE_MODEL_UNVERIFIED")
    for field, code in (
        (frame.tts_shutdown_ack, "VIENEU_SHUTDOWN_NOT_ACKED"),
        (frame.tts_object_released, "VIENEU_OBJECT_STILL_REFERENCED"),
        (frame.tts_process_reaped, "VIENEU_PROCESS_NOT_REAPED"),
        (frame.tts_mutex_released, "VIENEU_MUTEX_NOT_RELEASED"),
        (frame.tts_model_unloaded, "VIENEU_MODEL_UNLOAD_NOT_PROVEN"),
    ):
        require(field, code)

    for number, code in (
        (frame.active_tts_workers, "TTS_WORKER_COUNT_INVALID"),
        (frame.active_asr_workers, "ASR_WORKER_COUNT_INVALID"),
        (frame.other_heavy_workers, "HEAVY_WORKER_COUNT_INVALID"),
    ):
        if type(number) is not int or number != 0:
            reasons.append(code)
    if type(frame.cpu_threads) is not int or frame.cpu_threads != 1:
        reasons.append("THREAD_LIMIT_NOT_ONE")
    measurements = (frame.free_ram_gib, frame.proposed_ram_floor_gib,
                    frame.free_c_gib, frame.free_d_gib)
    if any(type(x) not in (float, int) or not isfinite(x) or x < 0 for x in measurements):
        reasons.append("RESOURCE_MEASUREMENT_INVALID")
    else:
        # Offline hypothesis parameters only; no production configuration changed.
        if frame.proposed_ram_floor_gib < 1.0 or frame.free_ram_gib < frame.proposed_ram_floor_gib:
            reasons.append("RAM_BELOW_PROPOSED_FLOOR")
        if frame.free_c_gib < 2.0 or frame.free_d_gib < 10.0:
            reasons.append("DISK_BELOW_PROPOSED_FLOOR")

    return {
        "schema": SCHEMA,
        "task_id": TASK_ID,
        "status": "SIMULATED_HANDOFF_READY_UNATTESTED" if not reasons else "BLOCKED",
        "reason_codes": reasons,
        "simulation_only": True,
        "owner_attestation_verified_in_field": False,
        "model_unload_verified_in_field": False,
        "protected_checkpoint_verified_in_field": False,
        "approved_to_start": False,
        "approved_to_dispatch": False,
        "production_modified": False,
        "worker_started": False,
        "task_completed": False,
    }
