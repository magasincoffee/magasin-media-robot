# -*- coding: utf-8 -*-
"""Synthetic safety tests; no VieNeu, Whisper or private chapter source imported."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import chapter2_v5_qc_guarded as ch2

class SafeChapter2Tests(unittest.TestCase):
    def test_resource_probe_available(self):
        self.assertGreater(ch2.free_ram_gb(), 0)
        self.assertGreater(ch2.free_disk_gb(), 1)

    def test_resource_status_is_atomic_and_marks_not_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(ch2, "WORK", root), patch.object(ch2, "STATUS_PATH", root/"job_status.json"), \
                 patch.object(ch2, "POINTER", root/"shared"/"status.json"):
                ch2.status("QUEUED_RESOURCE", chapter=2, total=640, rendered=0,
                           reason="RAM_BELOW_SAFETY_GATE", min_start_ram_gb=2.3)
                data=json.loads((root/"job_status.json").read_text(encoding="utf-8"))
                self.assertEqual(data["stage"], "QUEUED_RESOURCE")
                self.assertFalse(data["final"])
                self.assertFalse(data["owner_approved"])
                self.assertEqual(data["rendered"], 0)
                self.assertEqual(data["total"], 640)
                self.assertEqual(json.loads((root/"shared"/"status.json").read_text(encoding="utf-8"))["stage"], "QUEUED_RESOURCE")

    def test_mutex_refuses_second_worker(self):
        first=ch2.lock()
        self.assertIsNotNone(first)
        try:
            second=ch2.lock()
            self.assertIsNone(second, "Second concurrent Chapter 2 worker must not acquire mutex")
        finally:
            ch2.unlock(first)

if __name__ == "__main__":
    unittest.main(verbosity=2)
