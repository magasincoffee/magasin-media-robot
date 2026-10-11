"""Offline append-only repair replay fixtures, no models or actual checkpoints."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from v5_p1_repair_replay import fold

M="a"*64
S="b"*64
V="c"*64
ORIG="d"*64
W1="e"*64
W2="f"*64

def event(serial,kind,attempt=1,wav=W1,segment=11):
    o={"event_id":format(serial,"064x"),"kind":kind,
       "segment":segment,"attempt":attempt,
       "original_wav_sha256":ORIG,"candidate_wav_sha256":wav}
    if kind=="OWNER_SAMPLE_ACCEPTED":o["sample_sha256"]="1"*64
    return o

def check(events):
    return fold(M,S,V,events)

class ReplayTests(unittest.TestCase):
    def test_valid_one_staged_and_rejected(self):
        r=check([event(1,"CANDIDATE_STAGED"),event(2,"QC_REJECTED")])
        self.assertEqual(r["segment_states"][0]["attempts_used"],1)
        self.assertEqual(r["segment_states"][0]["phase"],"QC_REJECTED")
        self.assertFalse(r["repair_dispatched"])

    def test_valid_two_attempts_never_final(self):
        ev=[event(1,"CANDIDATE_STAGED"),event(2,"QC_REJECTED"),
            event(3,"CANDIDATE_STAGED",2,W2),event(4,"QC_REVIEW_REQUIRED",2,W2),
            event(5,"OWNER_SAMPLE_ACCEPTED",2,W2)]
        r=check(ev)
        self.assertEqual(r["segment_states"][0]["attempts_remaining"],0)
        self.assertEqual(r["segment_states"][0]["phase"],"SAMPLE_ACCEPTED_NOT_CHAPTER_FINAL")
        self.assertFalse(r["owner_final"])

    def test_duplicate_event_replay_is_idempotent(self):
        a=event(1,"CANDIDATE_STAGED")
        r=check([a,copy.deepcopy(a)])
        self.assertEqual(r["unique_event_count"],1)
        self.assertEqual(r["exact_replay_count"],1)
        self.assertEqual(r["segment_states"][0]["attempts_used"],1)

    def test_conflicting_event_id_rejected(self):
        a=event(1,"CANDIDATE_STAGED")
        b=event(1,"QC_REJECTED")
        with self.assertRaisesRegex(ValueError,"EVENT_ID_REPLAY_CONFLICT"):
            check([a,b])

    def test_attempt_two_without_one_refused(self):
        with self.assertRaisesRegex(ValueError,"UNBOUNDED_OR_INVALID_REPAIR_ATTEMPT"):
            check([event(1,"CANDIDATE_STAGED",2,W2)])

    def test_attempt_two_before_reject_refused(self):
        with self.assertRaisesRegex(ValueError,"UNBOUNDED_OR_INVALID_REPAIR_ATTEMPT"):
            check([event(1,"CANDIDATE_STAGED"),event(2,"CANDIDATE_STAGED",2,W2)])

    def test_third_attempt_impossible(self):
        with self.assertRaisesRegex(ValueError,"EVENT_TYPE_OR_SCOPE_INVALID"):
            check([event(1,"CANDIDATE_STAGED",3,W2)])

    def test_duplicate_candidate_audio_refused(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_CANDIDATE_AUDIO"):
            check([event(1,"CANDIDATE_STAGED"),event(2,"QC_REJECTED"),
                   event(3,"CANDIDATE_STAGED",2,W1)])

    def test_no_change_in_audio_refused(self):
        with self.assertRaisesRegex(ValueError,"NO_ACTUAL_AUDIO_REPAIR"):
            check([event(1,"CANDIDATE_STAGED",1,ORIG)])

    def test_stale_candidate_qc_refused(self):
        with self.assertRaisesRegex(ValueError,"QC_EVENT_WITH_STALE_CANDIDATE"):
            check([event(1,"CANDIDATE_STAGED"),event(2,"QC_REJECTED",1,W2)])

    def test_approval_without_review_refused(self):
        with self.assertRaisesRegex(ValueError,"OWNER_APPROVAL_WITHOUT_REVIEW"):
            check([event(1,"CANDIDATE_STAGED"),event(2,"OWNER_SAMPLE_ACCEPTED")])

    def test_duplicate_qc_result_refused(self):
        with self.assertRaisesRegex(ValueError,"QC_EVENT_OUT_OF_ORDER"):
            check([event(1,"CANDIDATE_STAGED"),event(2,"QC_REJECTED"),
                   event(3,"QC_REJECTED")])

    def test_missing_sample_receipt_refused(self):
        e=event(2,"OWNER_SAMPLE_ACCEPTED")
        del e["sample_sha256"]
        with self.assertRaisesRegex(ValueError,"OWNER_SAMPLE_RECEIPT_MISSING"):
            check([event(1,"CANDIDATE_STAGED"),event(3,"QC_REVIEW_REQUIRED"),e])

    def test_changed_original_hash_refused(self):
        e=event(2,"QC_REJECTED");e["original_wav_sha256"]="7"*64
        with self.assertRaisesRegex(ValueError,"ORIGINAL_WAV_CHANGED_DURING_RETRY"):
            check([event(1,"CANDIDATE_STAGED"),e])

    def test_bad_manifest_identity_refused(self):
        with self.assertRaisesRegex(ValueError,"CHAPTER_IDENTITY_INVALID"):
            fold("invalid",S,V,[])

    def test_unknown_event_key_refused(self):
        e=event(1,"CANDIDATE_STAGED");e["private_source_text"]="SECRET"
        with self.assertRaisesRegex(ValueError,"EXTRANEOUS_EVENT_FIELDS"):
            check([e])

    def test_different_segments_keep_independent_budgets(self):
        r=check([event(1,"CANDIDATE_STAGED"),event(2,"CANDIDATE_STAGED",1,W2,12)])
        self.assertEqual(len(r["segment_states"]),2)
        self.assertEqual([x["attempts_used"] for x in r["segment_states"]],[1,1])

    def test_cli_default_off_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            doc=path/"input.json";out=path/"out.json"
            doc.write_text(json.dumps({"manifest_sha256":M,"source_sha256":S,
                "voice_reference_sha256":V,"events":[event(1,"CANDIDATE_STAGED")]}))
            script=Path(__file__).with_name("v5_p1_repair_replay.py")
            p=subprocess.run([sys.executable,str(script),"--journal",str(doc),
                "--output",str(out)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertFalse(out.exists())
            self.assertIn("DISABLED_DEFAULT",p.stdout)

    def test_cli_optin_exclusive_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            doc=path/"input.json";out=path/"out.json"
            doc.write_text(json.dumps({"manifest_sha256":M,"source_sha256":S,
                "voice_reference_sha256":V,"events":[event(1,"CANDIDATE_STAGED")]}))
            script=Path(__file__).with_name("v5_p1_repair_replay.py")
            args=[sys.executable,str(script),"--journal",str(doc),
                "--output",str(out),"--enable-journal-review"]
            p=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0)
            self.assertFalse(json.loads(out.read_text())["owner_final"])

if __name__=="__main__":
    unittest.main(verbosity=2)
