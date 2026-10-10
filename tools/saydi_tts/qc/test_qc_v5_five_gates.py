"""Safe regressions for the opt-in five-stage SAYDI V5 evidence gate."""
import hashlib, json, subprocess, sys, tempfile, unittest, wave
from pathlib import Path
from qc_v5_five_gates import audit,sha
class FiveGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        def wav(name,secs=1.0):
            f=self.root/name
            with wave.open(str(f),"wb") as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
                w.writeframes(b"\0\0"*int(16000*secs))
            return f
        a=wav("000000.wav");b=wav("000001.wav")
        x=wav("gap_610.wav",.610)
        self.files=[a,x,b,x]
        self.concat=self.root/"concat.txt"
        self.concat.write_text("\n".join("file '"+str(f).replace("\\","/")+"'" for f in self.files)+"\n",encoding="utf8")
        self.manifest={"chapter_number":3,"segments":[
            {"index":0,"spoken_text":"Câu một.","canonical_text":"Câu một.","parent_end":False},
            {"index":1,"spoken_text":"VOC được đọc đúng.","canonical_text":"VOC được đọc đúng.","parent_end":False}]}
        self.qc={"rows":[
            {"index":0,"status":"PASS","expected":"Câu một.","asr_similarity":1.0},
            {"index":1,"status":"REVIEW","expected":"VOC được đọc đúng.","asr_similarity":.87}]}
        self.owner={"chapter":3,"qc02_issue":"AUDIBLE_TWO_VOICE_TONES_OWNER_CONFIRMED",
                    "qc02_join_after_segment":0,"qc02_join_before_segment":1,
                    "qc02_source_timestamp_seconds":20.4}
        self.mp3=self.root/"original.mp3";self.mp3.write_bytes(b"ORIGINAL")
        self.new=self.root/"new.mp3";self.new.write_bytes(b"REVIEW_OUTPUT")
        self.receipt={"chapter":3,"source_mp3":str(self.mp3),"source_mp3_sha256":sha(self.mp3),
                      "output_mp3":str(self.new),"output_sha256":sha(self.new),
                      "changed_spoken_segments":[1],"qc02_owner_sample_accepted":True,
                      "whole_chapter_owner_final":False}
    def test_owner_feedback_prevents_false_qc02_pass(self):
        x=audit(self.manifest,self.qc,self.concat,self.receipt,self.owner)
        self.assertEqual(x["qc"]["QC02_JOIN"]["reason_counts"]["OWNER_CONFIRMED_TONE_DISCONTINUITY_IN_ORIGINAL"],1)
        self.assertEqual(x["status"],"REVIEW")
        self.assertFalse(x["final_eligible"])
        self.assertEqual(x["repair_receipt"]["changed_spoken_segments"],[1])
    def test_cannot_pass_qc03_without_semantics(self):
        x=audit(self.manifest,self.qc,self.concat,self.receipt)
        self.assertEqual(x["qc"]["QC03_PROSODY"]["finding_count"],2)
        self.assertEqual(x["qc"]["QC04_PRONUNCIATION"]["reason_counts"]["ASR_REVIEW"],1)
    def test_hash_mismatch_blocks_repair(self):
        self.receipt["output_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"REVIEW_HASH_MISMATCH"):
            audit(self.manifest,self.qc,self.concat,self.receipt)
    def test_wrong_chapter_owner_rejected(self):
        self.owner["chapter"]=5
        with self.assertRaisesRegex(ValueError,"OWNER_FEEDBACK_WRONG_CHAPTER"):
            audit(self.manifest,self.qc,self.concat,self.receipt,self.owner)
    def test_missing_segment_coverage_fails_closed(self):
        self.qc["rows"].pop()
        with self.assertRaisesRegex(ValueError,"WHISPER_QC_INCOMPLETE"):
            audit(self.manifest,self.qc,self.concat)
    def test_candidate_asr_needs_matching_wav_sha(self):
        candidate=self.root/"new.wav"
        candidate.write_bytes(self.files[2].read_bytes())
        proposed={"rows":[{"index":1,"status":"PASS","expected":"VOC được đọc đúng.",
                           "asr_similarity":.95,"audio_sha256":"bad"}]}
        with self.assertRaisesRegex(ValueError,"CANDIDATE_ASR_HASH_MISMATCH"):
            audit(self.manifest,self.qc,self.concat,self.receipt,
                  candidate_qc=proposed,candidate_wav=candidate)
        proposed["rows"][0]["audio_sha256"]=sha(candidate)
        result=audit(self.manifest,self.qc,self.concat,self.receipt,
                     candidate_qc=proposed,candidate_wav=candidate)
        self.assertEqual(result["qc"]["QC04_PRONUNCIATION"]["reason_counts"].get("ASR_REVIEW",0),0)
        self.assertFalse(result["final_eligible"])
    def test_cli_default_disabled(self):
        program=Path(__file__).with_name("qc_v5_five_gates.py")
        out=self.root/"should_not_exist.json"
        p=subprocess.run([sys.executable,str(program),"--manifest","missing",
            "--qc","missing","--concat","missing","--report",str(out)],
            capture_output=True,text=True,timeout=12)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("DISABLED_DEFAULT",p.stdout)
        self.assertFalse(out.exists())
if __name__=="__main__":unittest.main(verbosity=2)
