"""Offline P1 repair readiness gates: never dispatch, change WAV or approve FINAL."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from v5_p1_repair_readiness import prepare, checksum

M="f"*64
A="a"*64
B="b"*64
C="c"*64
D="d"*64

def setup():
    manifest={"chapter_number":3,"source_sha256":A,"reference_sha256":B,
              "segments":[{"index":0,"canonical_text":"Mỗi khi hè về.",
                           "tts_text_sha256":D},
                          {"index":1,"canonical_text":"Người phụ nữ.",
                           "tts_text_sha256":C}]}
    audit={"schema":"saydi-v5-qc01-05-audit-v1","final":False,"chapter":3,
           "segment_count":2,"review_mp3_sha256":A,
           "qc04":{"issues":[{"index":0,"checked_audio_sha256":B},
                             {"index":1,"checked_audio_sha256":C}]}}
    wl={"schema":"saydi-v5-bounded-qc-worklist-v1","chapter":3,
        "source_review_audio_sha256":A,"status":"REVIEW_NOT_FINAL",
        "no_autonomous_tts_started":True,"no_auto_final":True,
        "integration_status":"DRAFT_SOT_GATE_NOT_PRODUCTION",
        "confirmed_action_total":1,
        "confirmed_actions":[{"segment":0,"code":"OWNER_CONFIRMED_TONE_DRIFT",
                              "original_audio_sha256":B,"attempts_used":1,
                              "remaining_attempts":1,
                              "action":"STAGE_ONE_V5_SEGMENT_CANDIDATE",
                              "auto_run":False,"owner_acceptance_after":True}]}
    lineage={"schema":"saydi-v5-source-lineage-1",
             "manifest_hash_method":"RAW_MANIFEST_BYTES",
             "manifest_sha256":M,"source_sha256":A,
             "lexical_equivalence":"PASS","punctuation_equivalence":"PASS",
             "verified_source_span_count":2,
             "source_spans":[{"index":0},{"index":1}]}
    return manifest,audit,wl,lineage

class RepairReadinessTests(unittest.TestCase):
    def run_case(self,change=None):
        m,a,w,l=setup()
        if change:change(m,a,w,l)
        return prepare(m,a,w,M,l)

    def test_strict_dryrun_no_worker_even_with_source_lineage(self):
        r=self.run_case()
        self.assertEqual(r["p0_source_lineage_status"],"LEXICAL_AND_PUNCTUATION_SCREEN_PASS")
        self.assertEqual(r["state"],"REVIEW_ONLY_NO_RUNTIME_PERMISSION")
        self.assertEqual(r["intents"][0]["attempts_remaining"],1)
        self.assertFalse(r["intents"][0]["approved_to_dispatch"])
        self.assertFalse(r["intents"][0]["approved_to_promote"])
        self.assertFalse(r["worker_started"])
        self.assertFalse(r["owner_final"])

    def test_without_p0_lineage_stays_pending(self):
        m,a,w,_=setup()
        r=prepare(m,a,w,M,None)
        self.assertEqual(r["p0_source_lineage_status"],"PENDING_OR_INCOMPLETE")
        self.assertIn("P0_SOURCE_FIDELITY_NOT_PROVEN",r["intents"][0]["reasons_not_executable"])

    def test_stale_lineage_rejected(self):
        def mutate(m,a,w,l):l["manifest_sha256"]=D
        with self.assertRaisesRegex(ValueError,"STALE_P0_SOURCE_LINEAGE"):
            self.run_case(mutate)

    def test_changed_review_mp3_sha_rejected(self):
        def mutate(m,a,w,l):w["source_review_audio_sha256"]=D
        with self.assertRaisesRegex(ValueError,"STALE_CHAPTER_REVIEW_AUDIO"):
            self.run_case(mutate)

    def test_changed_chunk_audio_sha_rejected(self):
        def mutate(m,a,w,l):w["confirmed_actions"][0]["original_audio_sha256"]=D
        with self.assertRaisesRegex(ValueError,"OWNER_EVENT_AUDIO_SHA_MISMATCH"):
            self.run_case(mutate)

    def test_more_than_two_retries_rejected(self):
        def mutate(m,a,w,l):
            w["confirmed_actions"][0]["attempts_used"]=2
            w["confirmed_actions"][0]["remaining_attempts"]=0
        with self.assertRaisesRegex(ValueError,"RETRY_BUDGET_VIOLATION"):
            self.run_case(mutate)

    def test_attempt_ledger_must_be_exact(self):
        def mutate(m,a,w,l):w["confirmed_actions"][0]["remaining_attempts"]=2
        with self.assertRaisesRegex(ValueError,"RETRY_BUDGET_VIOLATION"):
            self.run_case(mutate)

    def test_auto_run_not_authorized(self):
        def mutate(m,a,w,l):w["confirmed_actions"][0]["auto_run"]=True
        with self.assertRaisesRegex(ValueError,"UNSAFE_REPAIR_ACTION"):
            self.run_case(mutate)

    def test_production_promoted_worklist_refused(self):
        def mutate(m,a,w,l):w["integration_status"]="PRODUCTION_ENABLED"
        with self.assertRaisesRegex(ValueError,"UNSAFE_WORKLIST_PRODUCTION_STATE"):
            self.run_case(mutate)

    def test_tampered_tts_hash_rejected(self):
        def mutate(m,a,w,l):m["segments"][0]["tts_text_sha256"]="corrupt"
        with self.assertRaisesRegex(ValueError,"IMMUTABLE_TTS_FINGERPRINT_MISSING"):
            self.run_case(mutate)

    def test_duplicate_segment_refused(self):
        def mutate(m,a,w,l):
            w["confirmed_actions"].append(dict(w["confirmed_actions"][0]))
            w["confirmed_action_total"]=2
        with self.assertRaisesRegex(ValueError,"ACTION_NOT_IN_AUDIT_OR_DUPLICATE"):
            self.run_case(mutate)

    def test_qc04_invalid_audio_digest_rejected(self):
        def mutate(m,a,w,l):a["qc04"]["issues"][0]["checked_audio_sha256"]="not_sha"
        with self.assertRaisesRegex(ValueError,"QC04_AUDIO_PROVENANCE_INVALID"):
            self.run_case(mutate)

    def test_changed_chapter_refused(self):
        def mutate(m,a,w,l):w["chapter"]=2
        with self.assertRaisesRegex(ValueError,"CHAPTER_MISMATCH"):
            self.run_case(mutate)

    def test_zero_actions_is_safe(self):
        m,a,w,l=setup()
        w["confirmed_action_total"]=0
        w["confirmed_actions"]=[]
        r=prepare(m,a,w,M,l)
        self.assertEqual(r["actions_exposed_for_inspection"],0)
        self.assertEqual(r["state"],"REVIEW_ONLY_NO_RUNTIME_PERMISSION")

    def test_legacy_lineage_cannot_mark_p0_pass(self):
        m,a,w,l=setup()
        l["punctuation_equivalence"]="REVIEW"
        r=prepare(m,a,w,M,l)
        self.assertEqual(r["p0_source_lineage_status"],"PENDING_OR_INCOMPLETE")

    def test_cli_disabled_creates_no_files(self):
        with tempfile.TemporaryDirectory() as root:
            d=Path(root);m=d/"manifest.json";a=d/"audit.json";w=d/"worklist.json";out=d/"out.json"
            mm,aa,ww,_=setup()
            for path,obj in ((m,mm),(a,aa),(w,ww)):
                path.write_text(json.dumps(obj),encoding="utf-8")
            script=Path(__file__).with_name("v5_p1_repair_readiness.py")
            p=subprocess.run([sys.executable,str(script),"--manifest",str(m),
                "--audit",str(a),"--worklist",str(w),"--output",str(out)],
                text=True,capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn("OFF_BY_DEFAULT",p.stdout)
            self.assertFalse(out.exists())

if __name__=="__main__":
    unittest.main(verbosity=2)
