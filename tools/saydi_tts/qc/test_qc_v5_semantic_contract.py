"""Provider-neutral QC03 semantic context validation tests."""
import unittest
from qc_v5_semantic_contract import context,verify
class Qc03Tests(unittest.TestCase):
    def setUp(self):
        self.m={"chapter_number":3,"source_sha256":"src","reference_sha256":"voice",
                "segments":[{"index":0,"parent_line":1,"canonical_text":"A.","spoken_text":"A.","tts_text_sha256":"a"},
                            {"index":1,"parent_line":1,"canonical_text":"B.","spoken_text":"B.","tts_text_sha256":"b"}]}
        self.snap=context(self.m)
    def directive(self,idx,confidence=.96,intensity=.15):
        s=self.snap["segments"][idx]
        return {"index":idx,"tts_text_sha256":s["tts_text_sha256"],
                "source_text_sha256":s["source_text_sha256"],
                "role":"NARRATOR_BODY","emotion":"neutral",
                "confidence":confidence,"emotion_intensity":intensity,
                "pause_after_ms":610}
    def test_unannotated_stays_review(self):
        r=verify(self.snap,{"directives":[]})
        self.assertEqual(r["missing"],2)
        self.assertEqual(r["status"],"REVIEW")
        self.assertFalse(r["owner_final"])
    def test_good_suggestions_only_validate_schema(self):
        r=verify(self.snap,{"directives":[self.directive(0),self.directive(1)]})
        self.assertEqual(r["status"],"SCHEMA_VALID_NEEDS_LISTENING")
        self.assertFalse(r["owner_final"])
        self.assertFalse(r["pace_tempo_override"])
    def test_reject_source_rewrite(self):
        p=self.directive(0);p["tts_text_sha256"]="tampered"
        with self.assertRaisesRegex(ValueError,"TEXT_FINGERPRINT_CHANGED"):
            verify(self.snap,{"directives":[p]})
    def test_emotional_jump_requires_review(self):
        r=verify(self.snap,{"directives":[self.directive(0,intensity=.1),
                                         self.directive(1,intensity=.9)]})
        self.assertIn("EMOTION_TRANSITION_ABRUPT",{x["code"] for x in r["exceptions"]})
    def test_low_confidence_is_review(self):
        r=verify(self.snap,{"directives":[self.directive(0,confidence=.40),self.directive(1)]})
        self.assertIn("LOW_SEMANTIC_CONFIDENCE",{x["code"] for x in r["exceptions"]})
    def test_forbidden_pause_rejected(self):
        q=self.directive(0);q["pause_after_ms"]=9000
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_DIRECTIVE"):
            verify(self.snap,{"directives":[q]})
if __name__=="__main__":unittest.main(verbosity=2)
