"""Synthetic QC01-05 tests, no private manuscript, TTS, ASR model or audio."""
import hashlib, json, tempfile, unittest, wave
from pathlib import Path
from v5_quality_gates_01_05 import audit, write_report, lexical_findings, beat_hint, sha, wav_detail

def make_wav(path, seconds=.1):
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
        f.writeframes(b"\0\0"*round(16000*seconds))
def save(path, obj):
    path.write_text(json.dumps(obj,ensure_ascii=False),encoding="utf8")
def concat(path, series):
    path.write_text("".join("file '"+str(p).replace("\\","/")+"'\n" for p in series),encoding="utf8")

class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir=Path(self.temp.name)
        self.source=self.dir/"source.mp3";self.source.write_bytes(b"BASELINE")
        self.review=self.dir/"candidate.mp3";self.review.write_bytes(b"REVIEW")
        self.chunk=self.dir/"chunks";self.chunk.mkdir()
        self.items=[];self.rows=[];self.pairs=[]
        for i,text in enumerate(("Mỗi khi hè về.","Tôi tự hỏi điều gì tiếp theo.",
                                  "Những người phụ nữ sẽ đến.")):
            orig=self.chunk/f"{i:06d}.wav";make_wav(orig)
            gap=self.dir/f"gap_{i}.wav";make_wav(gap,.61 if i!=2 else .90)
            self.pairs.extend([orig,gap])
            self.items.append({"index":i,"canonical_text":text,"spoken_text":text,
                               "parent_line":i,"heading":False,"tts_text_sha256":"a"*64})
            self.rows.append({"index":i,"audio_sha256":sha(orig),"status":"PASS",
                "expected":text,"heard":text,"asr_similarity":1})
        self.manifest=self.dir/"manifest.json"
        save(self.manifest,{"chapter_number":3,"segments":self.items})
        self.qc=self.dir/"qc.json";save(self.qc,{"rows":self.rows})
        self.oc=self.dir/"orig.concat";self.nc=self.dir/"candidate.concat"
        concat(self.oc,self.pairs);concat(self.nc,self.pairs)

    def call(self,**kw):
        return audit(self.manifest,self.qc,self.oc,self.nc,self.source,self.review,self.chunk,**kw)

    def test_no_changes_review_only(self):
        r=self.call()
        self.assertFalse(r["final"])
        self.assertEqual(r["qc01"]["changed_gap_count"],0)
        self.assertEqual(r["qc04"]["checked_asr_review_count"],0)
        self.assertEqual(r["qc05"]["speech_change_count"],0)
        self.assertTrue(r["qc05"]["prohibited_auto_final"])

    def test_pcm_energy_screen_is_measurement_not_emotion_pass(self):
        silence=self.chunk/"000000.wav"
        measured=wav_detail(silence)
        self.assertLess(measured["mid_rms_dbfs"],-100)
        report=self.call()
        self.assertEqual(report["qc03"]["status"],"REVIEW")
        self.assertEqual(report["qc03"]["energy_measurement"],"MIDDLE_0P5S_PCM_RMS_ONLY")

    def test_vietnamese_tone_routed_as_review(self):
        differences=lexical_findings("Mỗi khi hè về.","Mỗi khi he về.")
        self.assertEqual(differences[0]["class"],"VIETNAMESE_TONE_ASR_SUSPECT")
        self.assertEqual(beat_hint("Tôi tự hỏi điều gì tiếp theo.",False)[0],"REFLECTION_POSSIBLE")

    def test_changed_speech_requires_sha_bound_fresh_qc(self):
        newwav=self.dir/"000001_candidate.wav";make_wav(newwav,.21)
        pairs=self.pairs[:];pairs[2]=newwav;concat(self.nc,pairs)
        with self.assertRaisesRegex(ValueError,"MODIFIED_SPEECH_REQUIRES_NEW_ASR_HASH"):
            self.call()
        newqc=self.dir/"new.json"
        save(newqc,{"rows":[{"index":1,"audio_sha256":sha(newwav),"status":"REVIEW",
                             "asr_similarity":.90,"expected":"Tôi tự hỏi.","heard":"Tôi tự hỏi."}]})
        r=self.call(new_qc=newqc)
        self.assertEqual(r["qc05"]["changed_speech_indices"],[1])
        self.assertEqual(r["qc04"]["checked_asr_review_count"],1)

    def test_modified_file_invalidates_asr(self):
        (self.chunk/"000000.wav").write_bytes(b"CORRUPTED")
        with self.assertRaisesRegex(ValueError,"STALE_BASELINE_ASR_AT_0"):
            self.call()

    def test_receipt_must_match_source_and_changed_paths(self):
        gate=self.dir/"gate.json"
        save(gate,{"source_mp3_sha256":"0"*64,"output_sha256":sha(self.review),
                   "changed_spoken_segments":[],"changed_silence_after_segments":[]})
        with self.assertRaisesRegex(ValueError,"REVIEW_RECEIPT_SHA_MISMATCH"):
            self.call(repair_gate=gate)
        save(gate,{"source_mp3_sha256":sha(self.source),"output_sha256":sha(self.review),
                   "changed_spoken_segments":[1],"changed_silence_after_segments":[]})
        with self.assertRaisesRegex(ValueError,"REVIEW_DIFF_NOT_EQUAL_TO_RECEIPT"):
            self.call(repair_gate=gate)

    def test_stale_approved_sample_cannot_be_reused(self):
        approval=self.dir/"approved.mp3"
        approval.write_bytes(b"APPROVED_SAMPLE")
        gate=self.dir/"gate_sample.json"
        save(gate,{"source_mp3_sha256":sha(self.source),
                   "output_sha256":sha(self.review),
                   "changed_spoken_segments":[],"changed_silence_after_segments":[],
                   "approved_sample_mp3":str(approval),
                   "approved_sample_sha256":"f"*64})
        with self.assertRaisesRegex(ValueError,"STALE_APPROVED_SAMPLE_HASH"):
            self.call(repair_gate=gate)

    def test_owner_approval_must_be_tied_to_exact_review_mp3(self):
        approval=self.dir/"owner.json"
        save(approval,{"chapter_final_approved":True,"source_mp3_sha256":"0"*64})
        with self.assertRaisesRegex(ValueError,"STALE_OWNER_APPROVAL"):
            self.call(owner_acceptance=approval)

    def test_no_overwrite_or_production_report(self):
        output=self.dir/"out"/"report.json"
        write_report(output,self.call())
        with self.assertRaises(FileExistsError):write_report(output,self.call())
        with self.assertRaisesRegex(ValueError,"REPORT_IN_PRODUCTION"):
            write_report(self.dir/"owner_approved_natural_v5"/"report.json",self.call())

if __name__=="__main__":
    unittest.main(verbosity=2)
