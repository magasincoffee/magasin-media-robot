# -*- coding: utf-8 -*-
"""SAYDI low-impact runtime policy checks; no VieNeu/Whisper weights loaded."""
import ctypes
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT=Path(r"C:\SAYDI")
CONTROL=ROOT/"control"
NARR=ROOT/"narration_director_v1"
sys.path.insert(0,str(CONTROL))
import control_commands

class SingleCorePolicyTests(unittest.TestCase):
    def test_controller_python_path_valid(self):
        self.assertTrue(control_commands.CONTROL_PY.is_file())
        self.assertEqual(control_commands.OWNER_CPU_THREADS,1)
        self.assertEqual(control_commands.OWNER_MIN_GB,2.3)

    def test_all_heavy_scripts_one_cpu(self):
        specs=[
            ("chapter2_v5_qc_guarded.py", "if not kernel.SetProcessAffinityMask(handle, 0x1)"),
            ("saydi_review_qc.py", "if not k.SetProcessAffinityMask(h,1)"),
            ("saydi_quality_improve.py", "if not k.SetProcessAffinityMask(h,1)"),
            ("qc_local_segments.py", "mask = 0x1"),
        ]
        for name,marker in specs:
            text=(NARR/name).read_text(encoding="utf-8")
            with self.subTest(script=name):
                self.assertIn(marker,text)
                self.assertNotIn('cpu_threads=2',text)
                if name=="qc_local_segments.py":
                    self.assertIn("cpu_threads=1",text)
                    self.assertIn('os.environ["OPENBLAS_NUM_THREADS"] = "1"',text)
                else:
                    self.assertTrue(
                      'os.environ[key] = "1"' in text or
                      'os.environ[key]="1"' in text or
                      'os.environ[name]="1"' in text
                    )

    def test_affinity_actual_one_logical_cpu(self):
        # Run in a subprocess so its CPU affinity cannot affect the operator or this test.
        for mod,method in [
          ("chapter2_v5_qc_guarded","cap_cpu"),
          ("saydi_review_qc","limit_cpu"),
          ("saydi_quality_improve","cpu_cap"),
        ]:
            probe=(
              "import ctypes,sys;sys.path.insert(0,r'C:\\SAYDI\\narration_director_v1');"
              f"import {mod} as m;m.{method}();"
              "k=ctypes.windll.kernel32;k.GetCurrentProcess.restype=ctypes.c_void_p;"
              "k.GetProcessAffinityMask.argtypes=(ctypes.c_void_p,"
              "ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t));"
              "k.GetProcessAffinityMask.restype=ctypes.c_bool;"
              "current=k.GetCurrentProcess();"
              "process=ctypes.c_size_t(0);system=ctypes.c_size_t(0);"
              "assert k.GetProcessAffinityMask(current,ctypes.byref(process),ctypes.byref(system));"
              "print('MASK',process.value);"
              "assert process.value==1,process.value"
            )
            result=subprocess.run([str(control_commands.CONTROL_PY),"-c",probe],
                                  stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                  text=True,timeout=18,check=False)
            with self.subTest(module=mod):
                self.assertEqual(result.returncode,0,
                   f"stdout={result.stdout[-300:]} stderr={result.stderr[-500:]}")

if __name__=="__main__":
    unittest.main(verbosity=2)
