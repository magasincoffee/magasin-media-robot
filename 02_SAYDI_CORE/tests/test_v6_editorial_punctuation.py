"""V6: spoken text fidelity and natural pauses across Vietnamese punctuation."""
import unittest

from saydi_audiobook.editorial import (
    _pause_for_unit,
    compile_editorial_reading,
    editorial_manifest,
    split_for_editorial_reading,
)

class TestV6EditorialPunctuation(unittest.TestCase):
    SOURCE = "Chị dừng lại một chút, nhưng cậu bé vẫn đứng chờ ở cuối con đường."

    def test_comma_kept_when_splitting_long_sentence(self):
        units = split_for_editorial_reading(self.SOURCE, max_chars=45)
        self.assertEqual(units, [
            "Chị dừng lại một chút,",
            "nhưng cậu bé vẫn đứng chờ ở cuối con đường.",
        ])
        self.assertEqual(" ".join(units), self.SOURCE)

    def test_original_words_and_punctuation_stay_in_spoken_text(self):
        units = compile_editorial_reading(self.SOURCE, max_chars=45)
        self.assertEqual(" ".join(x.canonical_text for x in units), self.SOURCE)
        self.assertTrue(all(x.canonical_text == x.spoken_text for x in units))
        self.assertTrue(all(x.canonical_sha256 == x.spoken_sha256 for x in units))

    def test_pause_reads_question_mark_inside_closing_quote(self):
        self.assertEqual(_pause_for_unit("“Anh đã về chưa?”", "NARRATIVE"), 650)
        self.assertEqual(_pause_for_unit('“Anh đã về chưa?"', "NARRATIVE"), 650)
        self.assertEqual(_pause_for_unit("“Đừng đi!”", "NARRATIVE"), 550)
        self.assertEqual(_pause_for_unit("“Vậy thì…”", "NARRATIVE"), 800)

    def test_curly_single_quote_question_retains_own_pause(self):
        source = "‘Anh về chưa?’ Cô hỏi."
        units = compile_editorial_reading(source)
        self.assertEqual([u.spoken_text for u in units], ["‘Anh về chưa?’", "Cô hỏi."])
        self.assertGreaterEqual(units[0].pause_after_ms, 650)
        self.assertEqual(" ".join(u.spoken_text for u in units), source)

    def test_manifest_retains_comma_for_native_vieneu_prompt(self):
        manifest = editorial_manifest(self.SOURCE, max_chars=45)
        self.assertEqual(manifest["unit_count"], 2)
        self.assertEqual(manifest["segments"][0]["spoken_text"],
                         "Chị dừng lại một chút,")
        self.assertEqual(manifest["segments"][0]["tempo_factor"], 1.0)
        self.assertTrue(manifest["post_render_qc_required"])
        self.assertEqual(" ".join(x["spoken_text"] for x in manifest["segments"]),
                         self.SOURCE)

if __name__ == "__main__":
    unittest.main()
