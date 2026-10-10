"""Read-only SAYDI QC Control status contract tests."""
import unittest
from qc_v5_control_status import summarize
class StatusTests(unittest.TestCase):
    def setUp(self):
        self.five={"chapter":3,"final_eligible":False,"findings_count":2,
          "qc":{name:{"status":"REVIEW","finding_count":2} for name in (
            "QC01_PAUSE","QC02_JOIN","QC03_PROSODY","QC04_PRONUNCIATION","QC05_POST_REPAIR")}}
        self.semantic={"chapter":3,"segments":[{},{}],"scene_groups_by_parent_line":1}
        self.pronunciation={"chapter":3,"review_segments":1,"counts_by_kind":{"DIACRITIC_AMBIGUOUS":1}}
        self.plan={"chapter":3,"automatic_execution":False,"targets":[{"segment":1}],"max_attempts_per_segment":2}
    def test_never_promote_final(self):
        x=summarize(self.five,self.semantic,self.pronunciation,self.plan)
        self.assertFalse(x["final"])
        self.assertFalse(x["feature_enabled_in_production"])
        self.assertEqual(x["qc05"]["proposed_bounded_repairs"],1)
    def test_mixed_chapters_rejected(self):
        self.semantic["chapter"]=5
        with self.assertRaisesRegex(ValueError,"MIXED_CHAPTER"):
            summarize(self.five,self.semantic,self.pronunciation,self.plan)
    def test_reject_automatic_job_execution(self):
        self.plan["automatic_execution"]=True
        with self.assertRaisesRegex(ValueError,"UNSAFE_QC_STATE"):
            summarize(self.five,self.semantic,self.pronunciation,self.plan)
if __name__=="__main__":unittest.main(verbosity=2)
