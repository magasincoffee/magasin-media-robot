"""Regression guard for SAYDI opt-in five-minute QC A/B (no media models).

Runs synthetic unit cases in CI; real MP3/hash checks only when local
SAYDI_QC5_DIR and SAYDI_QC5_SOURCE are explicitly provided.
"""
import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from preview_5phut_context import choose_window

class QcFiveMinuteTests(unittest.TestCase):
    def test_window_selection_falls_in_five_minute_band(self):
        segments=[{"index":i,"part_in_parent":0,"parent_end":True} for i in range(55)]
        positions=[i*10.0 for i in range(55)]
        start,end,duration=choose_window(segments,[],positions,270,300)
        self.assertTrue(270<=duration<=335)
        self.assertTrue(start<end)

    def test_window_refuses_too_short_source(self):
        segments=[{"index":i,"part_in_parent":0} for i in range(4)]
        positions=[i*12.0 for i in range(4)]
        with self.assertRaisesRegex(RuntimeError,"WINDOW_NOT_FIVE_MINUTES"):
            choose_window(segments,[],positions,10,300)

    def test_actual_preview_speech_sources_unchanged_and_bounded(self):
        root=os.environ.get("SAYDI_QC5_DIR")
        source=os.environ.get("SAYDI_QC5_SOURCE")
        if not root or not source:self.skipTest("field assets not on this machine")
        root=Path(root);source=Path(source)
        report=json.loads((root/"QC_5PHUT_REPORT.json").read_text(encoding="utf8"))
        with source.open("rb") as f:sha=hashlib.file_digest(f,"sha256").hexdigest()
        self.assertEqual(sha,report["audio_original_sha256"])
        self.assertTrue(report["production_unmodified"])
        self.assertEqual(report["feature"],"OFF_IN_PRODUCTION")
        pair=report["A_B"]
        self.assertTrue(270<=pair["A_nominal_duration_s"]<=335)
        self.assertEqual(pair["change_count"],len(pair["pause_changes"]))
        self.assertLessEqual(abs(pair["total_pause_delta_ms"]),80*len(pair["pause_changes"]))
        lines=[]
        for label in ("A_BAN_GOC_5PHUT","B_THU_NHIP_NGHI_5PHUT"):
            f=root/(label+".concat.txt")
            rows=f.read_text(encoding="utf8").splitlines()
            self.assertEqual(len(rows)%2,0)
            lines.append(rows)
            mp3=root/(label+".mp3")
            with mp3.open("rb") as h:audiohash=hashlib.file_digest(h,"sha256").hexdigest()
            self.assertEqual(audiohash,pair["files"][label]["sha256"])
        a,b=lines
        self.assertEqual(len(a),len(b))
        self.assertEqual(a[::2],b[::2],"A/B MUST USE IDENTICAL SPOKEN WAVS")
        changes=sum(x!=y for x,y in zip(a[1::2],b[1::2]))
        self.assertEqual(changes,pair["change_count"])
        self.assertGreater(changes,0)
        self.assertTrue((root/"QC02_NGU_CANH_GOC_5PHUT_002334.mp3").is_file())

    def test_field_duration_and_native_tempo(self):
        root=os.environ.get("SAYDI_QC5_DIR")
        probe=os.environ.get("SAYDI_QC5_FFPROBE")
        if not root or not probe:self.skipTest("FFprobe or field assets not provided")
        root=Path(root)
        report=json.loads((root/"QC_5PHUT_REPORT.json").read_text(encoding="utf8"))
        def length(path):
            o=subprocess.run([probe,"-v","error","-show_entries","format=duration",
                "-of","default=noprint_wrappers=1:nokey=1",str(path)],
                capture_output=True,text=True,timeout=20,check=True)
            return float(o.stdout.strip())
        da=length(root/"A_BAN_GOC_5PHUT.mp3")
        db=length(root/"B_THU_NHIP_NGHI_5PHUT.mp3")
        dc=length(root/"QC02_NGU_CANH_GOC_5PHUT_002334.mp3")
        self.assertLess(abs((db-da)*1000-report["A_B"]["total_pause_delta_ms"]),65)
        self.assertTrue(270<da<335 and 270<db<335 and 298<dc<302)

if __name__=="__main__":
    unittest.main(verbosity=2)
