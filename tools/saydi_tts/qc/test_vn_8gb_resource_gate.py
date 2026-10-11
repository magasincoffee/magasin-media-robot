"""Offline tests: H4 cannot dispatch VieNeu/Whisper through this read-only gate."""
from __future__ import annotations
import importlib.util
import json
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SUT = Path(__file__).with_name("vn_8gb_resource_gate.py")
spec = importlib.util.spec_from_file_location("vn8gb_guard", SUT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)

def snap():
    return dict(
        schema="saydi-vn-8gb-h4-telemetry-v1",
        captured_at=datetime.now(timezone.utc).isoformat(),
        host="DESKTOP-H4A16IL",
        physical_ram_gib=7.88,
        cpu_logical_threads=4,
        ram_samples_gib=[3.25, 3.1, 3.0, 3.05, 3.2],
        disk_c_free_gib=4.5,
        disk_d_free_gib=54.0,
        temp_drive="D:",
        heavy_workers=[],
        owner_stop_latch="ON",
        checkpoint_ownership="VERIFIED",
        worker_mutex_state="FREE",
    )

class GuardTests(unittest.TestCase):
    def test_good_snapshot_is_still_never_authorized_to_start(self):
        for stage in ("TTS","ASR"):
            result=mod.evaluate(snap(),stage=stage)
            self.assertEqual(result["resource_assessment"],"ELIGIBLE_FOR_SEPARATE_AUTHORIZED_CHECK")
            self.assertFalse(result["approved_to_start"])
            self.assertFalse(result["approved_to_dispatch"])
            self.assertFalse(result["installed_in_production"])

    def test_missing_telemetry_schema_fails_closed(self):
        x=snap();x.pop("schema")
        r=mod.evaluate(x,stage="TTS")
        self.assertIn("TELEMETRY_SCHEMA_UNVERIFIED",r["reasons"])
        self.assertFalse(r["approved_to_dispatch"])

    def test_missing_capture_time_fails_closed(self):
        x=snap();x.pop("captured_at")
        self.assertIn("TELEMETRY_STALE_OR_UNVERIFIED",mod.evaluate(x,stage="ASR")["reasons"])

    def test_stale_capture_fails_closed(self):
        x=snap();x["captured_at"]=(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat()
        self.assertIn("TELEMETRY_STALE_OR_UNVERIFIED",mod.evaluate(x,stage="TTS")["reasons"])

    def test_future_capture_fails_closed(self):
        x=snap();x["captured_at"]=(datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat()
        self.assertIn("TELEMETRY_STALE_OR_UNVERIFIED",mod.evaluate(x,stage="ASR")["reasons"])

    def test_naive_capture_fails_closed(self):
        x=snap();x["captured_at"]=datetime.now().isoformat()
        self.assertIn("TELEMETRY_STALE_OR_UNVERIFIED",mod.evaluate(x,stage="TTS")["reasons"])

    def test_fresh_capture_is_still_not_owner_start_proof(self):
        r=mod.evaluate(snap(),stage="TTS")
        self.assertEqual(r["resource_assessment"],"ELIGIBLE_FOR_SEPARATE_AUTHORIZED_CHECK")
        self.assertFalse(r["approved_to_dispatch"])
        self.assertLessEqual(r["telemetry_age_seconds"],30)

    def test_missing_owner_latch_blocks(self):
        x=snap();x["owner_stop_latch"]="UNKNOWN"
        self.assertIn("OWNER_LATCH_UNVERIFIED_OR_STOPPED",mod.evaluate(x,stage="TTS")["reasons"])

    def test_owner_stop_blocks_even_with_ram(self):
        x=snap();x["owner_stop_latch"]="STOP"
        self.assertEqual(mod.evaluate(x,stage="ASR")["resource_assessment"],"HOLD")

    def test_wrong_host_blocks(self):
        x=snap();x["host"]="DESKTOP-4K7IM13"
        self.assertIn("WRONG_HOST",mod.evaluate(x,stage="TTS")["reasons"])

    def test_missing_checkpoint_ownership_blocks(self):
        x=snap();x["checkpoint_ownership"]="UNKNOWN"
        self.assertIn("CHECKPOINT_OWNERSHIP_UNVERIFIED",mod.evaluate(x,stage="ASR")["reasons"])

    def test_unknown_mutex_blocks(self):
        x=snap();x["worker_mutex_state"]="UNKNOWN"
        self.assertIn("WORKER_MUTEX_UNVERIFIED",mod.evaluate(x,stage="TTS")["reasons"])

    def test_one_weak_ram_sample_blocks(self):
        x=snap();x["ram_samples_gib"]=[2.8,2.7,2.49,2.8,2.7]
        self.assertIn("INSUFFICIENT_STABLE_RAM_ASR",mod.evaluate(x,stage="ASR")["reasons"])

    def test_tts_threshold_below_whisper_threshold(self):
        x=snap();x["ram_samples_gib"]=[2.21,2.12,2.22,2.14,2.16]
        self.assertNotIn("INSUFFICIENT_STABLE_RAM_TTS",mod.evaluate(x,stage="TTS")["reasons"])
        self.assertIn("INSUFFICIENT_STABLE_RAM_ASR",mod.evaluate(x,stage="ASR")["reasons"])

    def test_ram_not_5_samples_blocks(self):
        x=snap();x["ram_samples_gib"]=[5]
        self.assertIn("RAM_SAMPLES_MISSING_OR_INVALID",mod.evaluate(x,stage="TTS")["reasons"])

    def test_invalid_ram_none_blocks(self):
        x=snap();x["ram_samples_gib"]=[1,2,None,3,4]
        self.assertIn("RAM_SAMPLES_MISSING_OR_INVALID",mod.evaluate(x,stage="TTS")["reasons"])

    def test_missing_process_inventory_blocks(self):
        x=snap();x.pop("heavy_workers")
        self.assertIn("HEAVY_WORKER_INVENTORY_MISSING",mod.evaluate(x,stage="TTS")["reasons"])

    def test_asr_already_running_blocks_tts(self):
        x=snap();x["heavy_workers"]=[{"kind":"ASR","pid":9}]
        self.assertIn("HEAVY_WORKER_ALREADY_ACTIVE",mod.evaluate(x,stage="TTS")["reasons"])

    def test_tts_already_running_blocks_asr(self):
        x=snap();x["heavy_workers"]=[{"kind":"TTS","pid":12}]
        self.assertIn("HEAVY_WORKER_ALREADY_ACTIVE",mod.evaluate(x,stage="ASR")["reasons"])

    def test_concurrent_models_still_fail_closed(self):
        x=snap();x["heavy_workers"]=[{"kind":"TTS"},{"kind":"ASR"}]
        self.assertIn("CONCURRENT_TTS_ASR_DETECTED",mod.evaluate(x,stage="ASR")["reasons"])

    def test_wrapper_plus_asr_is_active_but_not_false_concurrent_tts(self):
        x=snap();x["heavy_workers"]=[{"kind":"WRAPPER","pid":17268},{"kind":"ASR","pid":15680}]
        r=mod.evaluate(x,stage="TTS")
        self.assertIn("HEAVY_WORKER_ALREADY_ACTIVE",r["reasons"])
        self.assertNotIn("CONCURRENT_TTS_ASR_DETECTED",r["reasons"])
        self.assertFalse(r["approved_to_start"])

    def test_unrecognized_heavy_process_blocks(self):
        x=snap();x["heavy_workers"]=[{"kind":"UNKNOWN","pid":1}]
        self.assertIn("UNIDENTIFIED_HEAVY_WORKER",mod.evaluate(x,stage="TTS")["reasons"])

    def test_low_c_storage_blocks_even_when_temp_is_d(self):
        x=snap();x["disk_c_free_gib"]=1.29
        self.assertIn("LOW_C_DRIVE_HEADROOM",mod.evaluate(x,stage="TTS")["reasons"])

    def test_low_c_temp_adds_warning(self):
        x=snap();x["disk_c_free_gib"]=1.29;x["temp_drive"]="C:"
        self.assertIn("TEMP_ON_LOW_SPACE_C_DRIVE",mod.evaluate(x,stage="ASR")["reasons"])

    def test_d_below_10_gib_blocks(self):
        x=snap();x["disk_d_free_gib"]=9.9
        self.assertIn("LOW_D_DRIVE_HEADROOM",mod.evaluate(x,stage="ASR")["reasons"])

    def test_invalid_stage_raises(self):
        with self.assertRaises(ValueError):
            mod.evaluate(snap(),stage="BOTH")

    def test_no_shell_or_provider_import_in_guard(self):
        import ast
        parsed=ast.parse(SUT.read_text(encoding="utf-8-sig"))
        imports={getattr(n,"module","") for n in ast.walk(parsed) if isinstance(n,ast.ImportFrom)}
        self.assertFalse(imports.intersection({"vieneu","whisper","psutil","subprocess","onnxruntime","supabase"}))

    def test_cli_bad_data_does_not_grant_permission(self):
        r=subprocess.run([sys.executable,str(SUT),"--input","-","--stage","TTS"],
                         input="invalid json",text=True,capture_output=True)
        self.assertEqual(r.returncode,21)
        self.assertFalse(json.loads(r.stdout)["approved_to_start"])

if __name__=="__main__":
    unittest.main(verbosity=2)
