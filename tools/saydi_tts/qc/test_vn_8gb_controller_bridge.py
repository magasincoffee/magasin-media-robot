r"""Isolated no-worker tests for legacy SAYDI Control integration.

Never imports the actual C:\SAYDI control script or calls VieNeu/Whisper.
"""
from __future__ import annotations
import importlib.util
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).parent

def load(name):
    s=importlib.util.spec_from_file_location(name,HERE/(name+".py"))
    o=importlib.util.module_from_spec(s)
    assert s and s.loader
    s.loader.exec_module(o)
    return o

import sys
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))
import vn_8gb_controller_bridge as bridge
import vn_8gb_stage_controller_patch as patcher

def clean_snapshot():
    return {
        "schema":"saydi-vn-8gb-h4-telemetry-v1",
        "captured_at":datetime.now(timezone.utc).isoformat(),
        "host":"DESKTOP-H4A16IL", "physical_ram_gib":7.88,
        "cpu_logical_threads":4,"ram_samples_gib":[3.3,3.2,3.15,3.25,3.21],
        "disk_c_free_gib":5.0,"disk_d_free_gib":55.0,"temp_drive":"D:",
        "heavy_workers":[],"owner_stop_latch":"ON",
        "checkpoint_ownership":"VERIFIED","worker_mutex_state":"FREE",
    }

def clean_job(action="recheck"):
    return {"action":action,"state":"QUEUED","chapter":5,"id":"synthetic"}

CONTROL_SAMPLE = """
def execute_tick():
        if known_heavy():
            return 0
        free=free_ram()
        if free < 1.5:
            return 0
        job = dict()
        def worker():
            p=subprocess.Popen(argv,
                stdin=None)
""".lstrip()

import vn_8gb_sequential_dryrun as demo

class TwoPhaseTests(unittest.TestCase):
    def test_synthetic_two_phase_sequence_no_worker_started(self):
        x=demo.synthetic_clean_snapshot()
        result=demo.dry_run(x,dict(x),unload_verified=True)
        self.assertEqual(result["status"],"SYNTHETIC_REVIEW_SEQUENCE_PASS")
        self.assertEqual(result["trace"],list(demo.STEPS))
        self.assertFalse(result["production_started"])
        self.assertFalse(result["real_vieneu_loaded"])
        self.assertFalse(result["real_whisper_loaded"])

    def test_no_unload_barrier_refuses_asr(self):
        x=demo.synthetic_clean_snapshot()
        result=demo.dry_run(x,dict(x),unload_verified=False)
        self.assertEqual(result["status"],"HOLD")
        self.assertNotIn("WHISPER_CHECK",result["trace"])

    def test_active_tts_worker_refuses_asr(self):
        x=demo.synthetic_clean_snapshot()
        a=dict(x);a["heavy_workers"]=[{"kind":"TTS","pid":3}]
        result=demo.dry_run(x,a,unload_verified=True)
        self.assertEqual(result["status"],"HOLD")
        self.assertNotIn("ASR_SYNTHETIC_DONE",result["trace"])

    def test_no_disk_headroom_holds_before_synthesis(self):
        x=demo.synthetic_clean_snapshot();x["disk_c_free_gib"]=1.2
        result=demo.dry_run(x,dict(x),unload_verified=True)
        self.assertEqual(result["status"],"HOLD")
        self.assertEqual(result["halt_at"],"TTS_HOLD")
        self.assertFalse(result["audio_generated"])

class BridgeTests(unittest.TestCase):
    def test_resource_green_never_dispatches_itself(self):
        o=bridge.evaluate_existing_job(
            clean_job(),clean_snapshot(),
            authenticated_owner_start=True,
            trusted_generation_witness=True)
        self.assertEqual(o["decision"],"ELIGIBLE_FOR_EXISTING_AUTHORIZED_CHECKS")
        self.assertFalse(o["approved_to_start"])
        self.assertFalse(o["approved_to_dispatch"])

    def test_legacy_job_json_cannot_claim_authenticated_owner(self):
        j=clean_job();j["is_owner"]=True;j["authenticated"]=True
        result=bridge.evaluate_existing_job(j,clean_snapshot())
        self.assertEqual(result["decision"],"HOLD")
        self.assertIn("OWNER_START_WITNESS_UNVERIFIED",result["reasons"])

    def test_stale_field_snapshot_cannot_be_reused_for_dispatch(self):
        x=clean_snapshot();x["captured_at"]="2026-01-01T00:00:00+00:00"
        r=bridge.evaluate_existing_job(clean_job(),x,authenticated_owner_start=True,
                                       trusted_generation_witness=True)
        self.assertIn("TELEMETRY_STALE_OR_UNVERIFIED",r["reasons"])
        self.assertEqual(r["decision"],"HOLD")
        self.assertFalse(r["approved_to_dispatch"])

    def test_wrong_host(self):
        x=clean_snapshot();x["host"]="DESKTOP-4K7IM13"
        o=bridge.evaluate_existing_job(clean_job(),x,authenticated_owner_start=True,trusted_generation_witness=True)
        self.assertIn("WRONG_HOST",o["reasons"])

    def test_low_c_disk(self):
        x=clean_snapshot();x["disk_c_free_gib"]=1.25
        o=bridge.evaluate_existing_job(clean_job(),x,authenticated_owner_start=True,trusted_generation_witness=True)
        self.assertEqual(o["decision"],"HOLD")
        self.assertIn("LOW_C_DRIVE_HEADROOM",o["reasons"])

    def test_asr_and_tts_concurrency_blocks(self):
        x=clean_snapshot();x["heavy_workers"]=[{"kind":"TTS","pid":12}]
        o=bridge.evaluate_existing_job(clean_job("recheck"),x,
            authenticated_owner_start=True,trusted_generation_witness=True)
        self.assertIn("HEAVY_WORKER_ALREADY_ACTIVE",o["reasons"])

    def test_resume_composite_needs_internal_barrier(self):
        o=bridge.evaluate_existing_job(clean_job("resume"),clean_snapshot(),
            authenticated_owner_start=True,trusted_generation_witness=True)
        self.assertIn("LEGACY_COMPOSITE_PHASE_BARRIER_UNVERIFIED",o["reasons"])

    def test_explicitly_verified_composite_can_proceed_only_to_other_checks(self):
        o=bridge.evaluate_existing_job(clean_job("resume"),clean_snapshot(),
            authenticated_owner_start=True,trusted_generation_witness=True,
            internal_tts_to_asr_barrier_qualified=True)
        self.assertEqual(o["decision"],"ELIGIBLE_FOR_EXISTING_AUTHORIZED_CHECKS")
        self.assertFalse(o["approved_to_dispatch"])

    def test_legacy_improve_composite_stays_blocked(self):
        o=bridge.evaluate_existing_job(clean_job("improve"),clean_snapshot(),
            authenticated_owner_start=True,trusted_generation_witness=True,
            internal_tts_to_asr_barrier_qualified=True)
        self.assertEqual(o["decision"],"HOLD")
        self.assertIn("ACTION_NOT_QUALIFIED_FOR_SEQUENTIAL_ADMISSION",o["reasons"])

    def test_running_job_not_reenqueued(self):
        job=clean_job();job["state"]="RUNNING"
        o=bridge.evaluate_existing_job(job,clean_snapshot(),
            authenticated_owner_start=True,trusted_generation_witness=True)
        self.assertIn("JOB_STATE_NOT_QUEUED",o["reasons"])

    def test_snapshot_unavailable_fails_closed(self):
        o=bridge.evaluate_existing_job(clean_job(),None,
            authenticated_owner_start=True,trusted_generation_witness=True)
        self.assertIn("RESOURCE_SNAPSHOT_UNAVAILABLE",o["reasons"])

    def test_readonly_collector_missing_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(bridge.read_only_h4_snapshot(Path(d)/"missing.ps1"))

    def test_staged_guard_unknown_owner_still_holds(self):
        with patch.object(bridge,"read_only_h4_snapshot",return_value=clean_snapshot()):
            r=bridge.staged_guard_before_dispatch(clean_job("recheck"))
        self.assertEqual(r["decision"],"HOLD")
        self.assertFalse(r["approved_to_start"])

    def test_hook_inserted_before_resource_and_popen(self):
        s=patcher.build_staged_source(CONTROL_SAMPLE)
        self.assertEqual(s.count("VN8GB_STAGED_ONLY_GUARD"),1)
        self.assertLess(s.index("VN8GB_STAGED_ONLY_GUARD"),s.index("free=free_ram()"))
        self.assertLess(s.index("VN8GB_STAGED_ONLY_GUARD"),s.index("subprocess.Popen"))
        compile(s,"fake_controller.py","exec")

    def test_duplicate_patch_rejected(self):
        s=patcher.build_staged_source(CONTROL_SAMPLE)
        with self.assertRaisesRegex(ValueError,"ALREADY_PATCHED"):
            patcher.build_staged_source(s)

    def test_changed_local_controller_anchor_rejected(self):
        with self.assertRaisesRegex(ValueError,"EXACT_ANCHOR"):
            patcher.build_staged_source(CONTROL_SAMPLE.replace("free=free_ram()","free=0"))

    def test_live_c_path_never_writable(self):
        with self.assertRaisesRegex(ValueError,"PRODUCTION_TARGET_FORBIDDEN"):
            patcher.stage(Path("control_commands.py"),Path(r"C:\SAYDI\control\control_commands.py"),"0"*64)

    def test_sha_mismatch_refuses_stage(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_SHA_CHANGED"):
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/"control_commands.py";p.write_text(CONTROL_SAMPLE,encoding="utf-8")
                patcher.stage(p,Path(r"D:\SAYDI\QC_STAGING\test-new.py"),"0"*64)

if __name__=="__main__":
    unittest.main(verbosity=2)
