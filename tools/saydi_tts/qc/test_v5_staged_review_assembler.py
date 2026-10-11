"""Safe offline regression for the staging-only SAYDI V5 review assembler."""
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
from unittest.mock import patch

from v5_staged_review_assembler import (
    page_artifacts, segment_plan, bounded_heading_gain, safe_out_dir,
    render, write_wav_new,
)


def fixture():
    return {
        "chapter_number": 4,
        "source_sha256": "e"*64,
        "segments": [
            {"index": 0, "canonical_text": "Chương bốn.",
             "heading": True, "parent_line": 0, "parent_end": True},
            {"index": 1, "canonical_text": "69",
             "heading": False, "parent_line": 1, "part_in_parent": 2,
             "parent_end": True},
            {"index": 2, "canonical_text": "Một tiêu đề khác.",
             "heading": True, "parent_line": 2, "parent_end": True},
            {"index": 3, "canonical_text": "Đây là lời kể.",
             "heading": False, "parent_line": 3, "parent_end": True},
            {"index": 4, "canonical_text": "80",
             "heading": False, "parent_line": 3, "part_in_parent": 3,
             "parent_end": True},
        ],
    }


def noise():
    rng=random.Random(38)
    return array.array("h", (rng.randrange(-2000,2001) for _ in range(25000))).tobytes()


class StagedReviewAssemblerTests(unittest.TestCase):
    def setUp(self):
        self.manifest=fixture()
        self.selected=list(range(5))

    def test_page_numbers_at_end_and_before_title_are_candidates(self):
        self.assertEqual(page_artifacts(self.manifest), [1,4])

    def test_content_number_stays_spoken(self):
        m=copy.deepcopy(self.manifest)
        m["segments"][1]["parent_end"]=False
        self.assertEqual(page_artifacts(m),[4])
        with self.assertRaisesRegex(ValueError,"UNVERIFIED_PAGE_ARTIFACT_EXCLUSION"):
            segment_plan(m,self.selected,[1,4])

    def test_four_digit_year_never_page_candidate(self):
        m=copy.deepcopy(self.manifest)
        m["segments"][1]["canonical_text"]="2024"
        self.assertEqual(page_artifacts(m),[4])

    def test_heading_numbers_not_removed(self):
        m=copy.deepcopy(self.manifest)
        m["segments"][1]["heading"]=True
        self.assertEqual(page_artifacts(m),[4])

    def test_short_content_number_inside_prose_not_removed(self):
        m=copy.deepcopy(self.manifest)
        m["segments"][1]["canonical_text"]="Có 69 người"
        self.assertEqual(page_artifacts(m),[4])

    def test_plan_skips_confirmed_page_voice_and_preserves_titles(self):
        plan=segment_plan(self.manifest,self.selected,[1,4])
        self.assertEqual([s["index"] for s in plan],[0,2,3])
        self.assertEqual([s["index"] for s in plan if s["heading"]],[0,2])
        self.assertEqual([s["pause_after_ms"] for s in plan],[1150,1150,0])

    def test_unapproved_skip_blocked(self):
        with self.assertRaisesRegex(ValueError,"UNVERIFIED_PAGE_ARTIFACT_EXCLUSION"):
            segment_plan(self.manifest,self.selected,[3])

    def test_duplicate_and_outside_selection_blocked(self):
        with self.assertRaisesRegex(ValueError,"UNVERIFIED_PAGE_ARTIFACT_EXCLUSION"):
            segment_plan(self.manifest,self.selected,[1,1])
        with self.assertRaisesRegex(ValueError,"SKIPPED_SEGMENT_NOT_IN_SELECTED_RANGE"):
            segment_plan(self.manifest,[0,1,2],[4])

    def test_entirely_skipped_section_is_refused(self):
        with self.assertRaisesRegex(ValueError,"NO_PLAYABLE_SEGMENTS"):
            segment_plan(self.manifest,[4],[4])

    def test_heading_gain_never_clips(self):
        samples=array.array("h", [1000,-1000,22000,-22000]*1000)
        converted,level=bounded_heading_gain(samples.tobytes(),True)
        decoded=array.array("h");decoded.frombytes(converted)
        self.assertLessEqual(max(decoded),32767)
        self.assertGreaterEqual(min(decoded),-32768)
        self.assertGreater(level,1.0)

    def test_regular_voice_samples_unchanged(self):
        input_pcm=noise()
        converted,level=bounded_heading_gain(input_pcm,False)
        self.assertEqual(converted,input_pcm)
        self.assertEqual(level,1.0)

    def test_wave_written_exclusively(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/"test.wav"
            write_wav_new(dest,noise())
            with wave.open(str(dest),"rb") as w:
                self.assertEqual(w.getframerate(),48000)
                self.assertEqual(w.getnchannels(),1)
            with self.assertRaises(FileExistsError):
                write_wav_new(dest,noise())

    def test_source_and_production_paths_forbidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"source"
            root.mkdir()
            with self.assertRaisesRegex(ValueError,"NO_WRITES_UNDER_AUDIO_SOURCE_DIR"):
                safe_out_dir(root/"test",root)
            with self.assertRaisesRegex(ValueError,"REFUSE_PRODUCTION_PATH"):
                safe_out_dir(Path(tmp)/"chunks"/"review",root)

    def test_full_synthetic_assembly_is_staging_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            origin=base/"private_input"
            raw=origin/"chunks";raw.mkdir(parents=True)
            cleaned=origin/"stitch_cleaned";cleaned.mkdir()
            data=noise()
            for i in range(5):
                write_wav_new(raw/f"{i:06d}.wav",data)
                write_wav_new(cleaned/f"{i:06d}.wav",data)
            private_sha=hashlib.sha256((raw/"000001.wav").read_bytes()).hexdigest()
            out=base/"staging_result"
            def mock_command(args, **kwargs):
                if args[0]=="ffmpeg":
                    Path(args[-1]).write_bytes(b"synthetic fake mp3")
                    return subprocess.CompletedProcess(args,0)
                if args[0]=="ffprobe":
                    return subprocess.CompletedProcess(args,0,stdout="12.5\n")
                raise AssertionError("Unexpected command")
            with patch("v5_staged_review_assembler.subprocess.run",side_effect=mock_command):
                report=render(json.dumps(self.manifest).encode(),origin,out,self.selected,[1,4])
            self.assertEqual(report["excluded_page_artifact_indices"],[1,4])
            self.assertEqual(report["included_voice_wavs"],3)
            self.assertEqual(report["heading_indices"],[0,2])
            self.assertEqual(report["status"],"STAGING_LISTENING_ONLY")
            self.assertFalse(report["chapter_final"])
            self.assertFalse(report["production_modified"])
            self.assertFalse(report["native_word_pronunciation_verified"])
            self.assertEqual(
                hashlib.sha256((raw/"000001.wav").read_bytes()).hexdigest(),
                private_sha)
            self.assertNotIn("Một tiêu đề khác",json.dumps(report,ensure_ascii=False))
            with patch("v5_staged_review_assembler.subprocess.run",side_effect=mock_command):
                with self.assertRaises(FileExistsError):
                    render(json.dumps(self.manifest).encode(),origin,out,self.selected,[1,4])

    def test_cli_does_not_write_without_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); m=base/"manifest.json"
            m.write_text(json.dumps(self.manifest),encoding="utf8")
            out=base/"not_created"
            script=Path(__file__).with_name("v5_staged_review_assembler.py")
            p=subprocess.run([sys.executable,str(script),"--manifest",str(m),
                              "--source-dir",str(base),"--out-dir",str(out)],
                             capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn("DISABLED_DEFAULT",p.stdout)
            self.assertFalse(out.exists())


if __name__=="__main__":
    unittest.main(verbosity=2)
