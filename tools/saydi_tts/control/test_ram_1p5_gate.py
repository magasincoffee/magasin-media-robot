# -*- coding: utf-8 -*-
"""Low-memory 1.5 GB admission policy smoke; never load media weights."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(r"C:\SAYDI")
sys.path.insert(0,str(ROOT/"control"))
sys.path.insert(0,str(ROOT/"narration_director_v1"))
import control_commands as controller
import chapter2_v5_qc_guarded as chapter
import activity_monitor

class MemoryGateTests(unittest.TestCase):
    def test_threshold_shared_controller_pipeline(self):
        self.assertEqual(controller.OWNER_MIN_GB,1.5)
        self.assertEqual(chapter.MIN_START_RAM_GB,1.5)
        self.assertEqual(chapter.MIN_RUN_RAM_GB,0.70)
        self.assertEqual(controller.OWNER_CPU_THREADS,1)

    def test_qc_and_quality_match(self):
        quality=(ROOT/"narration_director_v1"/"saydi_quality_improve.py").read_text(encoding="utf-8")
        recheck=(ROOT/"narration_director_v1"/"saydi_review_qc.py").read_text(encoding="utf-8")
        self.assertEqual(quality.count("if ram()<1.5:"),2)
        self.assertIn("if free_ram()<1.5:",recheck)
        self.assertNotIn('RAM_BELOW_2_3_GB',quality+recheck)

    def test_report_wait_uses_new_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            (base/"job.json").write_text("{}")
            out=activity_monitor.summarize(
               {"state":"QUEUED_RESOURCE","chapter":3,"action":"resume","id":"request3",
                "last_check_free_ram_gb":1.27},
               base/"job.json",base/"guardian.log",base/"controller.log",
               None,3,1.27,[],min_start_ram_gb=controller.OWNER_MIN_GB)
            self.assertEqual(out["category"],"error")  # missing scheduler heartbeat is alerted
            events=" ".join(e["text"] for e in out["events"])
            self.assertIn("1.5 GB",events)
            self.assertNotIn("2,3 GB",events)
            self.assertIn("1.5 GB",out["explanation"])

    def test_chapter_checkpoint_always_reports_1_5(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with patch.object(chapter,"WORK",base),\
                 patch.object(chapter,"STATUS_PATH",base/"state.json"),\
                 patch.object(chapter,"POINTER",base/"pointer.json"):
                x=chapter.status("PAUSED_RESOURCE",reason="PREPARED_ONLY")
                self.assertEqual(x["min_start_ram_gb"],1.5)
                y=chapter.status("RENDERING",rendered=4,total=285)
                self.assertEqual(y["min_start_ram_gb"],1.5)
                self.assertNotIn("reason",y)

if __name__=="__main__":
    unittest.main(verbosity=2)
