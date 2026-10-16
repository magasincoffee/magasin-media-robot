import sys
from pathlib import Path
import unittest

DEPLOY = Path(__file__).resolve().parent
SRC = DEPLOY / "prepare_v6_audition.py"
FIXTURE = DEPLOY.parents[2] / "02_SAYDI_CORE" / "fixtures" / "v6_original_5min_vi.txt"
sys.path.insert(0, str(DEPLOY))
from prepare_v6_audition import prepare_text, MAX_CHARS

class AuditionSourceSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_text = FIXTURE.read_text(encoding="utf-8")

    def test_public_original_five_minute_estimate(self):
        plan = prepare_text(self.original_text)
        self.assertGreaterEqual(plan["estimated_minutes_not_measured"], 5)
        self.assertLessEqual(plan["estimated_minutes_not_measured"], 10)
        self.assertTrue(plan["natural_speed_only"])
        self.assertFalse(plan["new_audio_generated"])
        self.assertFalse(plan["saydi_owner_start_verified"])
        self.assertFalse(plan["h4_changed"])
        self.assertGreater(plan["segment_count"], 20)
        self.assertEqual([c["index"] for c in plan["segments"]],list(range(plan["segment_count"])))

    def test_no_truncated_segmentation(self):
        plan = prepare_text(self.original_text)
        self.assertTrue(all(0 < c["character_count"] <= MAX_CHARS for c in plan["segments"]))

    def test_no_fake_short_sample(self):
        with self.assertRaisesRegex(ValueError, "SAMPLE_LENGTH_OUT_OF_RANGE"):
            prepare_text("Một đoạn rất ngắn.")

    def test_no_nul_byte(self):
        with self.assertRaisesRegex(ValueError, "INVALID_SAMPLE_TEXT"):
            prepare_text(self.original_text + "\x00")

    def test_no_engine_or_side_effect_imports(self):
        body = SRC.read_text(encoding="utf-8")
        for forbidden in ("from vieneu import", "Vieneu(", "subprocess.run",
                          "Start-Process", "os.system(", "shutil.rmtree(",
                          "write_bytes(", ".write_text("):
            self.assertNotIn(forbidden, body)

if __name__ == "__main__":
    unittest.main()
