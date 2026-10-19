# -*- coding: utf-8 -*-
"""SAYDI activity timeline regression cases: stale log vs actual queued job."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import activity_monitor

class ActivityTests(unittest.TestCase):
    def test_old_audio_log_cannot_hide_current_waiting_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            guardian=folder/"job_guardian.log"
            guardian.write_text("[2026-10-10 10:42:00] TICK_END=0\n")
            controller=folder/"job_controller.log"
            controller.write_text("[2026-10-08 22:40:00] old completed\n")
            jobfile=folder/"control_job.json"
            job={"id":"task01","action":"improve","chapter":2,"state":"QUEUED_RESOURCE",
                 "queued_at":"2026-10-10 10:40:34","last_check_at":"2026-10-10 10:42:03",
                 "free_ram_gb":0.68,"attempts":0}
            jobfile.write_text(json.dumps(job))
            now=datetime.now().astimezone()
            result=activity_monitor.summarize(
                job,jobfile,guardian,controller,None,2,0.85,[],now=now)
            self.assertEqual(result["category"],"waiting")
            self.assertIn("CHỜ RAM",result["headline"])
            self.assertNotIn("running",result["headline"].lower())
            self.assertIsNone(result["last_processing_started"])
            self.assertTrue(result["events"])
            self.assertEqual(result["events"][0]["kind"],"heartbeat")
            self.assertTrue(any(e["kind"]=="check" for e in result["events"]))
            self.assertTrue(any("Đã nhận lệnh" in e["text"] for e in result["events"]))
            self.assertFalse(any("Completed QC previously" in e["text"] for e in result["events"]))

    def test_heartbeat_stale_is_not_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            result=activity_monitor.summarize({},
                     folder/"none.json",folder/"missing_guardian.log",
                     folder/"missing_control.log",None,1,3.0,[])
            self.assertFalse(result["scheduler_healthy"])
            self.assertEqual(result["category"],"error")
            self.assertIn("MẤT NHỊP",result["headline"])

    def test_actual_heavy_process_has_priority_over_waiting_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)
            result=activity_monitor.summarize(
               {"action":"improve","chapter":2,"state":"QUEUED_RESOURCE"},
               f/"job.json",f/"guardian.log",f/"controller.log",None,2,0.8,
               [{"kind":"repair","pid":4321}])
            self.assertEqual(result["category"],"running")
            self.assertIn("TIẾN TRÌNH ÂM THANH",result["headline"])

if __name__=="__main__":
    unittest.main(verbosity=2)
