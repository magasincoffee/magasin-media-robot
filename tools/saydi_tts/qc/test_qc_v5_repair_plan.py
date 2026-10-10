"""Bounded repair proposal tests: no worker, no auto-promotion."""
import copy, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from qc_v5_repair_plan import build
class RepairPlanTests(unittest.TestCase):
    def setUp(self):
        self.manifest={"chapter_number":3,"source_sha256":"src","reference_sha256":"ref",
          "segments":[{"index":i,"tts_text_sha256":f"text{i}","reference_fingerprint":"ref"} for i in range(4)]}
        self.baseline={"rows":[{"index":i,"asr_similarity":s} for i,s in enumerate((.92,.51,.42,.76))]}
        self.report={"chapter":3,"status":"REVIEW","final_eligible":False,"segments_checked":4,
          "findings":[{"segment":i,"code":"ASR_REVIEW"} for i in (1,2,3)],
          "repair_receipt":{"changed_spoken_segments":[2]},
          "candidate_asr_replacement":{"index":2,"asr_status":"PASS"}}
    def test_prefer_low_score_but_protect_owner_candidate(self):
        q=build(self.report,self.manifest,self.baseline,{},3)
        self.assertEqual([x["segment"] for x in q["targets"]],[1,3])
        self.assertFalse(q["automatic_execution"])
        self.assertFalse(q["promotion_allowed"])
    def test_bounded_attempt_ledger(self):
        q=build(self.report,self.manifest,self.baseline,{"1":2,"3":1},8)
        self.assertEqual([x["segment"] for x in q["targets"]],[3])
        self.assertEqual(q["targets"][0]["remaining_attempts"],1)
        self.assertIn("MAX_TWO_ATTEMPTS",{x["reason"] for x in q["preserved"]})
    def test_reject_false_final(self):
        self.report["final_eligible"]=True
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_RELEASE_STATE"):
            build(self.report,self.manifest,self.baseline)
    def test_refuse_unbounded_queue(self):
        with self.assertRaisesRegex(ValueError,"TOO_MANY_TARGETS"):
            build(self.report,self.manifest,self.baseline,max_targets=99)
    def test_default_plan_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"out.json"
            module=Path(__file__).with_name("qc_v5_repair_plan.py")
            r=subprocess.run([sys.executable,str(module),"--qc-report","missing",
              "--manifest","missing","--baseline-qc","missing","--output",str(out)],
              text=True,capture_output=True,timeout=15)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertFalse(out.exists())
            self.assertIn("DISABLED_DEFAULT",r.stdout)
if __name__=="__main__":unittest.main(verbosity=2)
