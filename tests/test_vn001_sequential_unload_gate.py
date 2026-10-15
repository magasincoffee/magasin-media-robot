"""Synthetic no-model/no-checkpoint regression for SAYDI VN-001 unload policy."""
import dataclasses
import importlib.util
from pathlib import Path
import sys
import unittest

MODULE = Path(__file__).resolve().parents[1] / "tools" / "saydi_tts" / "qc" / "vn001_sequential_unload_gate.py"
spec = importlib.util.spec_from_file_location("vn001_sequential_unload_gate", MODULE)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def healthy():
    return mod.SimulatedTransition(
        tts_generation="opaque-owner-gen-1", asr_generation="opaque-owner-gen-1",
        tts_observed_ms=10000, asr_observed_ms=10002, current_ms=10003,
        owner_start_attested=True, owner_stop=False,
        checkpoint_owner_attested=True, source_voice_model_attested=True,
        tts_shutdown_ack=True, tts_object_released=True,
        tts_process_reaped=True, tts_mutex_released=True, tts_model_unloaded=True,
        active_tts_workers=0, active_asr_workers=0, other_heavy_workers=0,
        cpu_threads=1, free_ram_gib=1.25, proposed_ram_floor_gib=1.0,
        free_c_gib=2.1, free_d_gib=50.0,
    )


class TestSequentialUnload(unittest.TestCase):
    def check_block(self, reason, **changes):
        receipt = mod.assess_offline_handoff(dataclasses.replace(healthy(), **changes))
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertIn(reason, receipt["reason_codes"])
        self.assertFalse(receipt["approved_to_start"])
        self.assertFalse(receipt["approved_to_dispatch"])
        self.assertFalse(receipt["worker_started"])
        self.assertFalse(receipt["production_modified"])

    def test_synthetic_positive_never_production_authorization(self):
        receipt = mod.assess_offline_handoff(healthy())
        self.assertEqual(receipt["status"], "SIMULATED_HANDOFF_READY_UNATTESTED")
        for name in ("approved_to_start", "approved_to_dispatch", "production_modified",
                     "owner_attestation_verified_in_field", "protected_checkpoint_verified_in_field",
                     "model_unload_verified_in_field", "worker_started", "task_completed"):
            self.assertIs(receipt[name], False)

    def test_owner_stop(self): self.check_block("OWNER_STOP_ACTIVE_OR_UNKNOWN", owner_stop=True)
    def test_no_start_generation(self): self.check_block("OWNER_START_NOT_ATTESTED", owner_start_attested=False)
    def test_changed_generation(self): self.check_block("GENERATION_UNVERIFIED_OR_CHANGED", asr_generation="another")
    def test_stale_snapshot(self): self.check_block("TRANSITION_STALE_OR_OUT_OF_ORDER", current_ms=17000)
    def test_out_of_order(self): self.check_block("TRANSITION_STALE_OR_OUT_OF_ORDER", asr_observed_ms=9990)
    def test_missing_checkpoint(self): self.check_block("CHECKPOINT_OWNERSHIP_UNVERIFIED", checkpoint_owner_attested=False)
    def test_missing_source_voice(self): self.check_block("SOURCE_VOICE_MODEL_UNVERIFIED", source_voice_model_attested=False)
    def test_no_shutdown_ack(self): self.check_block("VIENEU_SHUTDOWN_NOT_ACKED", tts_shutdown_ack=False)
    def test_object_live(self): self.check_block("VIENEU_OBJECT_STILL_REFERENCED", tts_object_released=False)
    def test_tts_process_alive(self): self.check_block("VIENEU_PROCESS_NOT_REAPED", tts_process_reaped=False)
    def test_mutex_held(self): self.check_block("VIENEU_MUTEX_NOT_RELEASED", tts_mutex_released=False)
    def test_model_loaded(self): self.check_block("VIENEU_MODEL_UNLOAD_NOT_PROVEN", tts_model_unloaded=False)
    def test_heavy_overlap(self): self.check_block("HEAVY_WORKER_COUNT_INVALID", other_heavy_workers=1)
    def test_asr_already_running(self): self.check_block("ASR_WORKER_COUNT_INVALID", active_asr_workers=1)
    def test_tts_still_running(self): self.check_block("TTS_WORKER_COUNT_INVALID", active_tts_workers=1)
    def test_wrong_threads(self): self.check_block("THREAD_LIMIT_NOT_ONE", cpu_threads=2)
    def test_invalid_boolean_is_not_authority(self): self.check_block("OWNER_START_NOT_ATTESTED", owner_start_attested=1)
    def test_insufficient_ram(self): self.check_block("RAM_BELOW_PROPOSED_FLOOR", free_ram_gib=0.95)
    def test_too_low_proposed_floor(self): self.check_block("RAM_BELOW_PROPOSED_FLOOR", proposed_ram_floor_gib=0.7)
    def test_insufficient_disk(self): self.check_block("DISK_BELOW_PROPOSED_FLOOR", free_c_gib=1.0)
    def test_invalid_ram(self): self.check_block("RESOURCE_MEASUREMENT_INVALID", free_ram_gib=float("nan"))
    def test_negative_worker_count(self): self.check_block("TTS_WORKER_COUNT_INVALID", active_tts_workers=-1)
    def test_missing_monotonic_time(self): self.check_block("INVALID_MONOTONIC_TIMESTAMPS", tts_observed_ms=None)
    def test_wrong_input(self):
        with self.assertRaises(TypeError): mod.assess_offline_handoff({"owner_start_attested": True})


if __name__ == "__main__":
    unittest.main()
