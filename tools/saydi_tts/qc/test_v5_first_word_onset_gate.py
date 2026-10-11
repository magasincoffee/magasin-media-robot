"""Synthetic unit tests for native-WAV first-word preservation, no real audio."""
import array
import copy
import hashlib
import json
import random
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

from v5_first_word_onset_gate import (
    inspect_pair, audit, pcm_data, save_new, sha,
)


def synthetic_pcm(seed=42, frames=24000):
    rng = random.Random(seed)
    result = array.array("h", (rng.randrange(-15000, 15001) for _ in range(frames)))
    return result.tobytes()


def fadestart(blob, frames=576):
    arr = array.array("h"); arr.frombytes(blob)
    for i in range(min(frames, len(arr))):
        arr[i] = int(arr[i] * i / frames)
    return arr.tobytes()


def wav(path, content, rate=48000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(content)


class FirstWordOnsetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.raw = self.root/"raw"; self.raw.mkdir()
        self.cleaned = self.root/"cleaned"; self.cleaned.mkdir()
        self.orig = synthetic_pcm()
        self.manifest = {"chapter_number": 4, "segments": [
            {"index": 0, "canonical_text": "Một ngày nọ."},
            {"index": 1, "canonical_text": "Người phụ nữ bước tới."},
        ]}
        for i in range(2):
            wav(self.raw/f"{i:06d}.wav", self.orig)
            wav(self.cleaned/f"{i:06d}.wav", self.orig)

    def test_unmodified_pcm_has_no_trim_or_fade(self):
        result = inspect_pair(self.orig, self.orig)
        self.assertEqual(result["verified_leading_trim_ms"], 0)
        self.assertEqual(result["verified_trailing_trim_ms"], 0)
        self.assertFalse(result["onset_attenuation_review"])
        self.assertFalse(result["phoneme_or_half_word_loss_proven"])

    def test_fade_of_first_12ms_is_distinguished_from_trim(self):
        result = inspect_pair(self.orig, fadestart(self.orig))
        self.assertEqual(result["verified_leading_trim_ms"], 0)
        self.assertTrue(result["onset_attenuation_review"])
        self.assertTrue(result["first12ms_energy_ratio"] < .8)
        self.assertFalse(result["phoneme_or_half_word_loss_proven"])

    def test_actual_head_and_tail_trim_are_separate(self):
        cleaned = self.orig[4800*2:len(self.orig)-1440*2]
        result = inspect_pair(self.orig, cleaned)
        self.assertAlmostEqual(result["verified_leading_trim_ms"], 100)
        self.assertAlmostEqual(result["verified_trailing_trim_ms"], 30)
        self.assertTrue(result["leading_trim_over50ms"])

    def test_tail_only_trim_is_not_reported_as_head(self):
        clean = self.orig[:len(self.orig)-7200*2]
        result = inspect_pair(self.orig, clean)
        self.assertEqual(result["verified_leading_trim_ms"], 0)
        self.assertAlmostEqual(result["verified_trailing_trim_ms"], 150)
        self.assertFalse(result["leading_trim_over50ms"])

    def test_unrelated_audio_cannot_pass_alignment(self):
        wrong = synthetic_pcm(seed=11)
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_PCM_ALIGNMENT"):
            inspect_pair(self.orig, wrong)

    def test_unexpected_format_is_refused(self):
        bad = self.root/"bad.wav"
        wav(bad, self.orig, rate=16000)
        with self.assertRaisesRegex(ValueError, "WAV_FORMAT_NOT_MONO_48K_PCM16"):
            pcm_data(bad)

    def test_all_audit_flags_never_authorize_release(self):
        wav(self.cleaned/"000000.wav", fadestart(self.orig))
        wav(self.cleaned/"000001.wav", self.orig[:len(self.orig)-7200*2])
        res = audit(self.manifest,self.raw,self.cleaned,sha(b"synthetic"))
        self.assertEqual(res["segments_scanned"],2)
        self.assertEqual(res["verified_wav_heads_trim_over50ms"],0)
        self.assertEqual(res["verified_wav_tails_trim_over50ms"],1)
        self.assertEqual(res["processed_initial_12ms_attenuated_segments"],1)
        self.assertFalse(res["word_pronunciation_verified"])
        self.assertFalse(res["user_reported_word_loss_fixed"])
        self.assertFalse(res["automatic_worker_start_allowed"])
        self.assertFalse(res["automatic_promotion_allowed"])
        self.assertFalse(res["owner_final"])

    def test_wrong_manifest_order_fails(self):
        modified=copy.deepcopy(self.manifest)
        modified["segments"][1]["index"]=5
        with self.assertRaisesRegex(ValueError,"OUT_OF_ORDER_MANIFEST"):
            audit(modified,self.raw,self.cleaned,sha(b"synthetic"))

    def test_missing_wav_fails(self):
        (self.cleaned/"000001.wav").unlink()
        with self.assertRaisesRegex(ValueError,"WAV_NOT_READABLE"):
            audit(self.manifest,self.raw,self.cleaned,sha(b"synthetic"))

    def test_no_private_words_in_metadata(self):
        res=audit(self.manifest,self.raw,self.cleaned,sha(b"synthetic"))
        out=json.dumps(res,ensure_ascii=False)
        self.assertNotIn("Người phụ nữ",out)
        self.assertNotIn("Một ngày",out)

    def test_output_is_new_and_refuses_production(self):
        res=audit(self.manifest,self.raw,self.cleaned,sha(b"synthetic"))
        path=self.root/"staging"/"report.json"
        save_new(path,res)
        self.assertEqual(json.loads(path.read_text())["status"],"REVIEW_ONLY_NO_VOICE_APPROVAL")
        with self.assertRaises(FileExistsError):
            save_new(path,res)
        with self.assertRaisesRegex(ValueError,"REFUSE_PRODUCTION_OUTPUT"):
            save_new(self.root/"chunks"/"report.json",res)

    def test_cli_off_by_default(self):
        p=self.root/"manifest.json";p.write_text(json.dumps(self.manifest),encoding="utf-8")
        out=self.root/"report_should_not_exist.json"
        script=Path(__file__).with_name("v5_first_word_onset_gate.py")
        cmd=[sys.executable,str(script),"--manifest",str(p),
             "--raw-dir",str(self.raw),"--clean-dir",str(self.cleaned),
             "--output",str(out)]
        result=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("OFF_BY_DEFAULT",result.stdout)
        self.assertFalse(out.exists())


if __name__=="__main__":
    unittest.main(verbosity=2)
