"""Synthetic PCM WAV test fixture suite; no private audio used."""
from __future__ import annotations

import io
import json
import math
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

from v5_p1_wav_candidate_gate import SCHEMA, digest, inspect


def wav(amplitude=8000, frames=8000, sample_rate=16000, compressed=False):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        samples = [int(amplitude * math.sin(2*math.pi*440*i/sample_rate))
                   for i in range(frames)]
        w.writeframes(b"".join(struct.pack("<h", s) for s in samples))
    return buffer.getvalue()


def fixture():
    original = wav(8000)
    candidate = wav(8100)
    receipt = {"schema": SCHEMA, "segment": 10, "attempts_used": 1,
               "manifest_sha256": "a"*64, "source_sha256": "b"*64,
               "voice_reference_sha256": "c"*64,
               "tts_text_fingerprint": "d"*64,
               "original_wav_sha256": digest(original),
               "candidate_wav_sha256": digest(candidate)}
    return original, candidate, receipt


class WavCandidateTests(unittest.TestCase):
    def test_happy_path_is_still_review_only(self):
        a,b,r = fixture()
        out=inspect(a,b,r)
        self.assertEqual(out["status"], "REVIEW_NO_PROMOTION")
        self.assertEqual(out["attempts_remaining"], 1)
        self.assertIn("NEIGHBOR_WAV_EVIDENCE_INCOMPLETE",out["flags"])
        self.assertFalse(out["approved_to_dispatch"])
        self.assertFalse(out["owner_final"])

    def test_neighbors_present_hash_and_codec(self):
        a,b,r=fixture()
        r.update(left_wav_sha256=digest(a),right_wav_sha256=digest(a))
        out=inspect(a,b,r,left=a,right=a)
        self.assertEqual(len(out["neighbor_checks"]),2)
        self.assertNotIn("NEIGHBOR_WAV_EVIDENCE_INCOMPLETE",out["flags"])
        self.assertFalse(out["approved_to_promote"])

    def test_baseline_sha_mismatch(self):
        a,b,r=fixture()
        r["original_wav_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"STALE_ORIGINAL_WAV_SHA"):
            inspect(a,b,r)

    def test_candidate_sha_mismatch(self):
        a,b,r=fixture()
        r["candidate_wav_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"STALE_CANDIDATE_WAV_SHA"):
            inspect(a,b,r)

    def test_same_audio_is_not_new_repair(self):
        a,b,r=fixture()
        r["candidate_wav_sha256"]=digest(a)
        with self.assertRaisesRegex(ValueError,"CANDIDATE_IDENTICAL_TO_BASELINE"):
            inspect(a,a,r)

    def test_too_many_attempts_rejected(self):
        a,b,r=fixture()
        r["attempts_used"]=2
        with self.assertRaisesRegex(ValueError,"INVALID_SEGMENT_OR_ATTEMPT_BUDGET"):
            inspect(a,b,r)

    def test_silent_candidate_flagged(self):
        a,b,r=fixture()
        b=wav(0)
        r["candidate_wav_sha256"]=digest(b)
        self.assertIn("NEAR_SILENT_CANDIDATE",inspect(a,b,r)["flags"])

    def test_clipped_candidate_flagged(self):
        a,b,r=fixture()
        b=wav(32767)
        r["candidate_wav_sha256"]=digest(b)
        self.assertIn("POSSIBLE_CLIPPING",inspect(a,b,r)["flags"])

    def test_short_and_changed_duration(self):
        a,b,r=fixture()
        b=wav(8100,frames=400)
        r["candidate_wav_sha256"]=digest(b)
        out=inspect(a,b,r)
        self.assertIn("CANDIDATE_TOO_SHORT",out["flags"])
        self.assertIn("DURATION_CHANGE_REVIEW",out["flags"])

    def test_different_sample_rate_refused(self):
        a,b,r=fixture()
        b=wav(8100,sample_rate=24000)
        r["candidate_wav_sha256"]=digest(b)
        with self.assertRaisesRegex(ValueError,"WAV_CODEC_MISMATCH"):
            inspect(a,b,r)

    def test_truncated_wav_refused(self):
        a,b,r=fixture()
        b=b[:400]
        r["candidate_wav_sha256"]=digest(b)
        with self.assertRaisesRegex(ValueError,"TRUNCATED_WAV_PAYLOAD"):
            inspect(a,b,r)

    def test_neighbor_sha_mismatch(self):
        a,b,r=fixture()
        r["left_wav_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"NEIGHBOR_SHA_MISMATCH"):
            inspect(a,b,r,left=a)

    def test_claimed_neighbor_without_bytes_refused(self):
        a,b,r=fixture()
        r["left_wav_sha256"]=digest(a)
        with self.assertRaisesRegex(ValueError,"CLAIMED_NEIGHBOR_WITHOUT_BYTES"):
            inspect(a,b,r)

    def test_malformed_receipt_rejected(self):
        a,b,r=fixture()
        r["manifest_sha256"]="invalid"
        with self.assertRaisesRegex(ValueError,"REQUIRED_SHA_MISSING"):
            inspect(a,b,r)

    def test_report_never_contains_manuscript(self):
        a,b,r=fixture()
        report=json.dumps(inspect(a,b,r),ensure_ascii=False)
        self.assertNotIn("Người phụ nữ",report)
        self.assertNotIn("Mỗi khi hè",report)

    def test_cli_default_off_and_no_write(self):
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)
            a,b,r=fixture()
            for name,data in (("a.wav",a),("b.wav",b)):
                (f/name).write_bytes(data)
            (f/"receipt.json").write_text(json.dumps(r),encoding="utf-8")
            args=[sys.executable,str(Path(__file__).with_name("v5_p1_wav_candidate_gate.py")),
                  "--original",str(f/"a.wav"),"--candidate",str(f/"b.wav"),
                  "--receipt",str(f/"receipt.json"),"--output",str(f/"gate.json")]
            p=subprocess.run(args,text=True,capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn("DISABLED_DEFAULT",p.stdout)
            self.assertFalse((f/"gate.json").exists())

    def test_cli_optin_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)
            a,b,r=fixture()
            (f/"a.wav").write_bytes(a)
            (f/"b.wav").write_bytes(b)
            (f/"receipt.json").write_text(json.dumps(r),encoding="utf-8")
            args=[sys.executable,str(Path(__file__).with_name("v5_p1_wav_candidate_gate.py")),
                  "--original",str(f/"a.wav"),"--candidate",str(f/"b.wav"),
                  "--receipt",str(f/"receipt.json"),"--output",str(f/"gate.json"),
                  "--enable-wav-candidate-inspection"]
            ok=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(ok.returncode,0,ok.stderr)
            second=subprocess.run(args,capture_output=True,text=True)
            self.assertNotEqual(second.returncode,0)
            self.assertFalse(json.loads((f/"gate.json").read_text())["owner_final"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
