from __future__ import annotations

import unittest

from saydi_audiobook.editorial import (
    compile_editorial_reading,
    editorial_manifest,
    split_for_editorial_reading,
)


class EditorialQATests(unittest.TestCase):
    def test_long_text_is_split_before_render_without_paraphrase(self):
        text = (
            "Khi đi ngang qua một công viên, có một người phụ nữ lớn tuổi đang dọn vệ sinh. "
            "Chị chợt nhìn thấy đoàn khất thực chúng tôi."
        )
        units = split_for_editorial_reading(text, max_chars=90)
        self.assertGreaterEqual(len(units), 2)
        joined = " ".join(units)
        self.assertIn("người phụ nữ", joined)
        self.assertIn("đoàn khất thực", joined)

    def test_must_check_phrase_requires_post_render_pronunciation_qc(self):
        plan = compile_editorial_reading(
            "Có một người phụ nữ lớn tuổi đang dọn vệ sinh.",
            must_check_phrases=["người phụ nữ"],
            emphasis_phrases=["người phụ nữ lớn tuổi"],
        )
        self.assertEqual(len(plan), 1)
        self.assertTrue(plan[0].pronunciation_qc_required)
        self.assertEqual(plan[0].must_check_phrases, ("người phụ nữ",))
        self.assertEqual(plan[0].emphasis_phrases, ("người phụ nữ lớn tuổi",))

    def test_pre_render_editorial_stage_never_waives_post_render_qc(self):
        manifest = editorial_manifest(
            "Giúp người khác cũng chính là giúp mình.",
            must_check_phrases=["giúp mình"],
        )
        self.assertTrue(manifest["post_render_qc_required"])
        self.assertEqual(manifest["unit_count"], 1)
        self.assertEqual(len(manifest["source_sha256"]), 64)

    def test_nfc_normalization_preserves_vietnamese_diacritics(self):
        plan = compile_editorial_reading(
            "Người phụ nữ đứng bên đường.",
            must_check_phrases=["phụ nữ"],
        )
        self.assertEqual(plan[0].canonical_text, "Người phụ nữ đứng bên đường.")
        self.assertIn("phụ nữ", plan[0].must_check_phrases)


if __name__ == "__main__":
    unittest.main()
