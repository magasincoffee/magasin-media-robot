"""QA: bounded worklist never infers audible PASS or retries ASR alone."""
import unittest
from v5_qc_bounded_worklist import create_worklist

HASH="a"*64
def report():
    return {"schema":"saydi-v5-qc01-05-audit-v1","chapter":3,"final":False,
      "review_mp3_sha256":"b"*64,"segment_count":285,
      "qc01":{"owner_approved_scope":"SAMPLE_ONLY"},
      "qc02":{"approved_sample_not_entire_chapter":True,"flag_count":0},
      "qc03":{"candidate_total":1,"semantic_candidates":[{"index":2,"at_s":5,
               "suggested_delivery":"DIALOGUE_POSSIBLE"}]},
      "qc04":{"checked_asr_review_count":115,"issues":[{"index":146,"at_s":785.6,
        "checked_audio_sha256":HASH,"asr_issue_classes":[],
        "checked_asr_status":"PASS"},
        {"index":147,"at_s":790,"checked_audio_sha256":"c"*64,
        "asr_issue_classes":[{"class":"VIETNAMESE_TONE_ASR_SUSPECT"}],
        "checked_asr_status":"REVIEW"}]}}

class WorklistTests(unittest.TestCase):
    def test_asr_only_never_autorender(self):
        x=create_worklist(report())
        self.assertEqual(x["confirmed_action_total"],0)
        self.assertGreater(x["owner_review_total"],0)
        self.assertTrue(x["no_autonomous_tts_started"])
        self.assertEqual(x["status"],"REVIEW_NOT_FINAL")
    def test_owner_resolved_sample_not_entire_chapter(self):
        evt={"index":146,"code":"OWNER_CONFIRMED_TONE_DRIFT",
             "audio_sha256":HASH,"resolved":True,"approved_sample_sha256":"f"*64}
        x=create_worklist(report(),owner_events=[evt])
        self.assertEqual(len(x["resolved_sample_events"]),1)
        self.assertFalse(x["resolved_sample_events"][0]["whole_chapter_accepted"])
        self.assertEqual(x["confirmed_action_total"],0)
    def test_bounded_queue_and_exhaustion(self):
        evt={"index":147,"code":"OWNER_CONFIRMED_WRONG_WORD",
             "audio_sha256":"c"*64}
        q=create_worklist(report(),{"147":1},[evt])
        self.assertEqual(q["confirmed_action_total"],1)
        self.assertEqual(q["confirmed_actions"][0]["remaining_attempts"],1)
        self.assertFalse(q["confirmed_actions"][0]["auto_run"])
        q=create_worklist(report(),{"147":2},[evt])
        self.assertEqual(q["confirmed_action_total"],0)
        self.assertEqual(q["blocked_after_retry"][0]["reason"],"MAX_2_ATTEMPTS_EXHAUSTED")
    def test_stale_or_malformed_confirmation_fail_closed(self):
        e={"index":146,"code":"OWNER_CONFIRMED_TONE_DRIFT","audio_sha256":"0"*64}
        with self.assertRaisesRegex(ValueError,"STALE_OR_UNTRACKED"):
            create_worklist(report(),owner_events=[e])
        e["audio_sha256"]=HASH;e["code"]="UNKNOWN"
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_QC_DEFECT"):
            create_worklist(report(),owner_events=[e])
    def test_budget_validation(self):
        with self.assertRaises(ValueError):
            create_worklist(report(),max_auto=0)
        with self.assertRaises(ValueError):
            create_worklist(report(),max_owner=100)

if __name__=="__main__":
    unittest.main(verbosity=2)
