"""QC04 Vietnamese phoneme/text ambiguity tests; no ASR model required."""
import unittest
from qc_v5_vietnamese_triage import detect,triage
class TriageTests(unittest.TestCase):
    def test_diacritics_are_ambiguous_not_certain_tts_error(self):
        r=detect("Mỗi khi hè về","mỗi khi he về")
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]["kind"],"DIACRITIC_AMBIGUOUS")
    def test_text_omission(self):
        r=detect("anh ấy đang đến đây","anh ấy đến đây")
        self.assertEqual(r[0]["kind"],"POSSIBLE_OMISSION")
    def test_extra_word(self):
        r=detect("tôi đi","tôi đi đi")
        self.assertEqual(r[0]["kind"],"POSSIBLE_EXTRA_OR_REPEAT")
    def test_substitution(self):
        r=detect("thử xem nhé","thử quay nhé")
        self.assertEqual(r[0]["kind"],"TOKEN_SUBSTITUTION")
    def test_candidate_row_review_and_no_auto_fix(self):
        m={"chapter_number":3,"segments":[{"index":0,"spoken_text":"Hè về."}]}
        q={"rows":[{"index":0,"expected":"Hè về.","heard":"he về","status":"REVIEW"}]}
        r=triage(m,q)
        self.assertEqual(r["counts_by_kind"]["DIACRITIC_AMBIGUOUS"],1)
        self.assertFalse(r["owner_final"])
        self.assertEqual(r["corrected_words"],0)
    def test_refuse_asr_source_drift(self):
        m={"chapter_number":3,"segments":[{"index":0,"spoken_text":"Nội dung đúng."}]}
        q={"rows":[{"index":0,"expected":"Nội dung khác.","heard":"Nội dung khác.","status":"PASS"}]}
        with self.assertRaisesRegex(ValueError,"ASR_EXPECTED_TEXT_DRIFT"):
            triage(m,q)
if __name__=="__main__":unittest.main(verbosity=2)
