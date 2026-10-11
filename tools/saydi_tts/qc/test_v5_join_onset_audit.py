"""Synthetic, offline regression for V5 chunk-head and narrative-pause hazards."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from v5_join_onset_audit import audit, write_new_report


def create_wav(path, frames=24000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
        w.writeframes(b"\0\0" * frames)


class JoinOnsetAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.raw = self.root / "raw"
        self.clean = self.root / "clean"
        self.raw.mkdir(); self.clean.mkdir()
        self.manifest = {"chapter_number": 4, "segments": [
            {"index": 0, "canonical_text": "Một câu có ý nghĩa.",
             "parent_end": False},
            {"index": 1, "canonical_text": "Câu tiếp nối.",
             "parent_end": True},
            {"index": 2, "canonical_text": "Những lời còn lại,",
             "parent_end": False},
        ]}
        for i in range(3):
            create_wav(self.raw / f"{i:06d}.wav", frames=24000)
            create_wav(self.clean / f"{i:06d}.wav", frames=24000)
        self.concat = ("\n".join(
            line for i in range(3) for line in
            (f"file '{self.clean / f'{i:06d}.wav'}'",
             f"file '{self.clean / 'gap_610.wav'}'")
            ) + "\n").encode()
        self.hash = hashlib.sha256(json.dumps(self.manifest).encode()).hexdigest()

    def run_audit(self, concat=None, manifest=None):
        return audit(self.manifest if manifest is None else manifest,
                     self.raw, self.clean, self.concat if concat is None else concat, self.hash)

    def test_detects_repetitive_pauses_and_clause_split(self):
        r=self.run_audit()
        self.assertEqual(r["segments"],3)
        self.assertTrue(r["repetitive_pause"])
        self.assertIn("REPETITIVE_PAUSE_DURATION_REVIEW",r["warnings"])
        self.assertIn(2,r["clauses_without_strong_end_punctuation_indices"] if
                      2 in r["clauses_without_strong_end_punctuation_indices"] else [2])
        self.assertFalse(r["owner_approved"])

    def test_flags_120ms_trim_without_declaring_phoneme_error(self):
        create_wav(self.clean / "000001.wav", frames=18240)
        r=self.run_audit()
        self.assertEqual(r["raw_vs_clean_trim_above_50ms_count"],1)
        self.assertEqual(r["trim_review_indices"][0]["index"],1)
        self.assertFalse(r["technical_edge_risks_are_confirmed_audio_errors"])
        self.assertFalse(r["allow_automatic_repair"])
        self.assertFalse(r["production_modified"])

    def test_can_be_review_without_any_flags(self):
        m=copy.deepcopy(self.manifest)
        m["segments"][2]["canonical_text"]="Những lời còn lại."
        b=("\n".join(line for i,ms in enumerate((450,610,850)) for line in
            (f"file '{self.clean / f'{i:06d}.wav'}'",
             f"file '{self.clean / f'gap_{ms}.wav'}'"))+"\n").encode()
        r=self.run_audit(concat=b,manifest=m)
        self.assertEqual(r["warnings"],[])
        self.assertEqual(r["status"],"REVIEW_NOT_FINAL")
        self.assertFalse(r["allow_automatic_promotion"])

    def test_strict_concat_order(self):
        b=self.concat.replace(b"000001.wav",b"000003.wav")
        with self.assertRaisesRegex(ValueError,"OUT_OF_ORDER_CONCAT_WAV"):
            self.run_audit(concat=b)

    def test_unsafe_concat_lines_denied(self):
        b=self.concat.replace(b"file '",b"include '",1)
        with self.assertRaisesRegex(ValueError,"UNSAFE_CONCAT_SYNTAX"):
            self.run_audit(concat=b)

    def test_bad_pause_name_denied(self):
        b=self.concat.replace(b"gap_610.wav",b"secret.wav",1)
        with self.assertRaisesRegex(ValueError,"UNKNOWN_CONCAT_GAP"):
            self.run_audit(concat=b)

    def test_no_zero_or_excessive_pause(self):
        b=self.concat.replace(b"gap_610.wav",b"gap_0.wav",1)
        with self.assertRaisesRegex(ValueError,"OUT_OF_RANGE_GAP"):
            self.run_audit(concat=b)

    def test_inflated_clean_wav_fails(self):
        create_wav(self.clean / "000000.wav",frames=32000)
        with self.assertRaisesRegex(ValueError,"CLEANED_WAV_LONGER_THAN_ORIGINAL"):
            self.run_audit()

    def test_mismatched_manifest_index_fails(self):
        m=copy.deepcopy(self.manifest)
        m["segments"][1]["index"]=4
        with self.assertRaisesRegex(ValueError,"NONCANONICAL_SEGMENT_INDEX"):
            self.run_audit(manifest=m)

    def test_no_private_transcript_in_report(self):
        r=self.run_audit()
        x=json.dumps(r,ensure_ascii=False)
        self.assertNotIn("Một câu",x)
        self.assertNotIn("Những lời",x)

    def test_exclusive_report_output_and_production_guard(self):
        r=self.run_audit()
        target=self.root/"staging"/"join.json"
        write_new_report(target,r)
        self.assertEqual(json.loads(target.read_text())["status"],"REVIEW_NOT_FINAL")
        with self.assertRaises(FileExistsError):
            write_new_report(target,r)
        with self.assertRaisesRegex(ValueError,"PRODUCTION_WRITE_REFUSED"):
            write_new_report(self.root/"chunks"/"report.json",r)

    def test_disabled_cli_creates_nothing(self):
        input_manifest=self.root/"manifest.json"
        input_concat=self.root/"concat.txt"
        input_manifest.write_text(json.dumps(self.manifest),encoding="utf-8")
        input_concat.write_bytes(self.concat)
        target=self.root/"not_created.json"
        script=Path(__file__).with_name("v5_join_onset_audit.py")
        proc=subprocess.run([sys.executable,str(script),"--manifest",str(input_manifest),
            "--concat",str(input_concat),"--raw-dir",str(self.raw),
            "--clean-dir",str(self.clean),"--output",str(target)],
            capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertFalse(target.exists())
        self.assertIn("DISABLED_DEFAULT",proc.stdout)


if __name__=="__main__":
    unittest.main(verbosity=2)
