# -*- coding: utf-8 -*-
"""SAYDI V5 process-tree guard tests. No media model or audio is loaded."""
import json
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,r"C:\SAYDI\narration_director_v1")
import chapter_v5_job
import chapter2_v5_qc_guarded as base

class ChapterProcessGuardTests(unittest.TestCase):
    def test_excludes_own_python_launcher_and_diagnostic_probe(self):
        processes=[
            {"ProcessId":1000,"ParentProcessId":900,"Name":"python.exe",
             "CommandLine":r'"C:\SAYDI\VieNeu-TTS\.venv\Scripts\python.exe" "C:\SAYDI\narration_director_v1\chapter_v5_job.py" --chapter 3'},
            {"ProcessId":900,"ParentProcessId":800,"Name":"python.exe",
             "CommandLine":r'"C:\SAYDI\VieNeu-TTS\.venv\Scripts\python.exe" "C:\SAYDI\narration_director_v1\chapter_v5_job.py" --chapter 3'},
            {"ProcessId":3000,"ParentProcessId":500,"Name":"python.exe",
             "CommandLine":r'"C:\SAYDI\qc2\.venv\Scripts\python.exe" "C:\SAYDI\narration_director_v1\qc_local_segments.py" --chapter 4'},
            {"ProcessId":4000,"ParentProcessId":500,"Name":"python.exe",
             "CommandLine":r'"C:\MAGASIN_MCP\.venv\Scripts\python.exe" -c "print(\'qc_local_segments.py\')"'},
        ]
        fake=subprocess.CompletedProcess(args=[],returncode=0,stdout=json.dumps(processes),stderr="")
        with patch.object(chapter_v5_job.os,"getpid",return_value=1000),\
             patch.object(chapter_v5_job.subprocess,"run",return_value=fake):
            result=chapter_v5_job.detect_external_heavy_jobs()
            self.assertEqual(len(result),1,result)
            self.assertEqual(result[0]["pid"],3000)
            self.assertEqual(result[0]["worker_script"],"qc_local_segments.py")

    def test_chapter3_outputs_correct_name_and_no_stale_blocker(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            with patch.object(base,"CHAPTER",3),patch.object(base,"WORK",work),\
                 patch.object(base,"STATUS_PATH",work/"job_status.json"),\
                 patch.object(base,"POINTER",work/"status_mirror.json"),\
                 patch.object(base,"free_ram_gb",return_value=3.1):
                base.status("PAUSED_RESOURCE",reason="OTHER_HEAVY_SAYDI_JOB_RUNNING",
                            blocking_jobs=[{"pid":990}])
                current=base.status("PREPARED",total=285,rendered=2)
                self.assertNotIn("blocking_jobs",current)
                self.assertNotIn("reason",current)
                def fake_assemble(items,chunks,destination,legacy):
                    Path(destination).write_bytes(b"synthetic-mp3-only-in-test")
                    return 155.2
                v5=SimpleNamespace(assemble=fake_assemble)
                with patch.object(base,"CHUNKS",work/"chunks"):
                    result=base.assemble({"segments":[{"index":0}]},v5,None)
                self.assertEqual(result.name,"CHUONG_03_OWNER_APPROVED_V5.REVIEW.mp3")
                self.assertFalse((work/"CHUONG_02_OWNER_APPROVED_V5.REVIEW.mp3").exists())

    def test_inventory_failure_blocks_new_render(self):
        fake=subprocess.CompletedProcess(args=[],returncode=1,stdout="",stderr="Temporary CIM failure")
        with patch.object(chapter_v5_job.subprocess,"run",return_value=fake):
            result=chapter_v5_job.detect_external_heavy_jobs()
        self.assertEqual(result[0]["pid"],-1)
        self.assertEqual(result[0]["reason"],"PROCESS_INVENTORY_UNAVAILABLE")

if __name__=="__main__":
    unittest.main(verbosity=2)
