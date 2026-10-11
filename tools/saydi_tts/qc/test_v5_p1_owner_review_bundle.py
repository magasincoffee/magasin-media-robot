"""Offline report bundle tests. Fake input metadata, no original book text."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from v5_p1_owner_review_bundle import build


def fixture():
    e={"schema":"saydi-v5-editorial-multiround-1", "chapter":3,
       "manifest_sha256":"a"*64,"status":"REVIEW","owner_final":False,
       "independent_review_status":"PENDING", "findings":[
           {"code":"SOURCE_PROVENANCE_UNVERIFIED", "index":None, "count":285},
           {"code":"POSSIBLE_BOUNDARY_REPEAT","index":1,"severity":"REVIEW",
            "private_original_text":"PRIVATE_DO_NOT_LEAK"}]}
    p={"schema":"saydi-v5-p1-repair-readiness-v1","chapter":3,
       "manifest_sha256":"a"*64,"source_sha256":"b"*64,
       "voice_reference_sha256":"c"*64,"owner_final":False,
       "p0_source_lineage_status":"PENDING_OR_INCOMPLETE",
       "state":"REVIEW_ONLY_NO_RUNTIME_PERMISSION", "worker_started":False,
       "automatic_promotion":False, "actions_exposed_for_inspection":0}
    q={"schema":"saydi-v5-qc01-05-audit-v1","final":False,"chapter":3,
       "qc04":{"issues":[{"index":1,"at_s":34.5,"checked_asr_status":"REVIEW"},
                         {"index":2,"at_s":43.0,"checked_asr_status":"PASS"}]}}
    w={"schema":"saydi-v5-p1-wav-candidate-gate-1","segment":1,
       "manifest_sha256":"a"*64,"source_sha256":"b"*64,
       "voice_reference_sha256":"c"*64,"owner_final":False,
       "approved_to_promote":False,"worker_started":False,
       "flags":["GAIN_CHANGE_REVIEW"]}
    return e,p,q,w


class ReviewBundleTests(unittest.TestCase):
    def test_bundle_never_marks_final(self):
        e,p,q,w=fixture(); r=build(e,p,q,[w])
        self.assertEqual(r["status"],"REVIEW_NOT_FINAL")
        self.assertFalse(r["dispatch_allowed"])
        self.assertFalse(r["owner_final"])
        self.assertEqual(r["exception_total"],4)
        self.assertEqual(r["exceptions"][1]["at_s"],34.5)

    def test_private_text_not_exported(self):
        e,p,q,w=fixture()
        self.assertNotIn("PRIVATE_DO_NOT_LEAK",json.dumps(build(e,p,q,[w])))

    def test_foreign_wav_manifest_rejected(self):
        e,p,q,w=fixture();w["manifest_sha256"]="d"*64
        with self.assertRaisesRegex(ValueError,"STALE_OR_UNSAFE_WAV"):
            build(e,p,q,[w])

    def test_wrong_source_sha_rejected(self):
        e,p,q,w=fixture();w["source_sha256"]="d"*64
        with self.assertRaisesRegex(ValueError,"STALE_OR_UNSAFE_WAV"):
            build(e,p,q,[w])

    def test_false_final_refused(self):
        e,p,q,w=fixture();e["owner_final"]=True
        with self.assertRaisesRegex(ValueError,"UNSAFE_EXTERNAL_REPORT_STATE"):
            build(e,p,q,[w])

    def test_fake_promotion_refused(self):
        e,p,q,w=fixture();w["approved_to_promote"]=True
        with self.assertRaisesRegex(ValueError,"STALE_OR_UNSAFE_WAV"):
            build(e,p,q,[w])

    def test_chapter_mismatch_refused(self):
        e,p,q,w=fixture();q["chapter"]=4
        with self.assertRaisesRegex(ValueError,"CHAPTER_REPORT_MISMATCH"):
            build(e,p,q)

    def test_manifest_mismatch_refused(self):
        e,p,q,w=fixture();e["manifest_sha256"]="d"*64
        with self.assertRaisesRegex(ValueError,"STALE_EDITORIAL_MANIFEST"):
            build(e,p,q)

    def test_unknown_word_in_code_refused(self):
        e,p,q,w=fixture();e["findings"][0]["code"]="PRIVATE WORD"
        with self.assertRaisesRegex(ValueError,"UNSAFE_FINDING_CODE"):
            build(e,p,q)

    def test_timecode_never_invented(self):
        e,p,q,w=fixture();r=build(e,p,q)
        self.assertIsNone(r["exceptions"][0]["at_s"])
        self.assertEqual(r["exceptions"][2]["at_s"],34.5)

    def test_limit_and_pagination(self):
        e,p,q,w=fixture()
        e["findings"]=[{"code":"SAMPLE_REVIEW","index":1} for _ in range(40)]
        first=build(e,p,q,max_exceptions=25)
        second=build(e,p,q,max_exceptions=25,exception_offset=25)
        self.assertEqual(first["exceptions_shown"],25)
        self.assertEqual(second["exceptions_shown"],16)
        self.assertEqual(second["exception_total"],41)
        self.assertEqual(second["exceptions_remaining"],0)

    def test_bad_limit_rejected(self):
        e,p,q,w=fixture()
        with self.assertRaisesRegex(ValueError,"INVALID_EXCEPTION_PAGE"):
            build(e,p,q,max_exceptions=200)

    def test_bad_wav_flag_rejected(self):
        e,p,q,w=fixture();w["flags"]=["Người phụ nữ"]
        with self.assertRaisesRegex(ValueError,"UNSAFE_WAV_FLAG"):
            build(e,p,q,[w])

    def test_cli_default_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); e,p,q,w=fixture()
            for path,val in (("e.json",e),("p.json",p),("q.json",q)):
                (d/path).write_text(json.dumps(val),encoding="utf-8")
            args=[sys.executable,str(Path(__file__).with_name("v5_p1_owner_review_bundle.py")),
                  "--editorial",str(d/"e.json"),"--repair-readiness",str(d/"p.json"),
                  "--qc01-05",str(d/"q.json"),"--output",str(d/"report.json")]
            run=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn("DISABLED_DEFAULT",run.stdout)
            self.assertFalse((d/"report.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
