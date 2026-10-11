"""Offline tests for soft title bell and immutable E/F A/B preview."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v5_title_cue_staging import (
    BEFORE_TITLE_GAP_MS, CUE_MS, MAX_CUE_PEAK, MAX_CUE_RMS,
    create_review, make_playlists, soft_bell_pcm, verify_stage, write_wave_new,
)


class TitleCueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.stage = self.root / "safe_E"
        self.stage.mkdir()
        self.wavs = self.stage/"review_wavs"
        self.wavs.mkdir()
        self.manifest = {"chapter_number": 4, "segments": [
            {"index": 0, "heading": True, "canonical_text": "Tên Chương."},
            {"index": 1, "heading": False, "canonical_text": "Nội dung tiếp."},
            {"index": 2, "heading": True, "canonical_text": "Tiêu đề mới."},
        ]}
        self.mpath = self.root/"manifest.json"
        self.mpath.write_text(json.dumps(self.manifest), encoding="utf-8")
        wavebytes, _ = soft_bell_pcm()
        for idx in range(3):
            write_wave_new(self.wavs/f"{idx:06d}.wav", wavebytes)
        write_wave_new(self.wavs/"gap_300.wav", b"\0\0"*14400)
        original_lines = []
        for idx in range(3):
            original_lines.append("file '"+(self.wavs/f"{idx:06d}.wav").resolve().as_posix()+"'")
            if idx < 2:
                original_lines.append("file '"+(self.wavs/"gap_300.wav").resolve().as_posix()+"'")
        (self.stage/"review_concat.txt").write_text("\n".join(original_lines)+"\n",encoding="utf-8")
        mp3 = self.stage/"CHAPTER_STAGING_NOT_FINAL.REVIEW.mp3"
        mp3.write_bytes(b"synthetic-E-mp3")
        receipt = {"schema": "saydi-v5-staging-review-assembly-v1",
                   "chapter": 4,
                   "manifest_sha256": hashlib.sha256(self.mpath.read_bytes()).hexdigest(),
                   "mp3_sha256": hashlib.sha256(mp3.read_bytes()).hexdigest(),
                   "chapter_final": False, "production_modified": False,
                   "included_voice_wavs": 3,
                   "heading_indices": [0,2],
                   "excluded_page_artifact_indices": []}
        (self.stage/"REVIEW_RECEIPT.json").write_text(json.dumps(receipt),encoding="utf-8")

    def test_cue_is_short_and_gentle(self):
        pcm, metrics = soft_bell_pcm()
        self.assertEqual(len(pcm), CUE_MS * 48 * 2)
        self.assertLessEqual(metrics["peak_linear"], MAX_CUE_PEAK)
        self.assertLessEqual(metrics["rms_linear"], MAX_CUE_RMS)
        self.assertEqual(metrics["lead_silence_ms"], BEFORE_TITLE_GAP_MS)

    def test_stage_source_is_hash_bound(self):
        receipt, pairs=verify_stage(self.mpath.read_bytes(),self.stage)
        self.assertEqual([x[0] for x in pairs],[0,1,2])
        self.assertEqual(receipt["heading_indices"],[0,2])

    def test_tampered_mp3_refused(self):
        (self.stage/"CHAPTER_STAGING_NOT_FINAL.REVIEW.mp3").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError,"E_STAGE_AUDIO_HASH_MISMATCH"):
            verify_stage(self.mpath.read_bytes(),self.stage)

    def test_tampered_manifest_refused(self):
        wrong = self.mpath.read_bytes()+b" "
        with self.assertRaisesRegex(ValueError,"E_STAGE_MANIFEST_SHA_MISMATCH"):
            verify_stage(wrong,self.stage)

    def test_tampered_title_list_refused(self):
        p=self.stage/"REVIEW_RECEIPT.json";data=json.loads(p.read_text());data["heading_indices"]=[0]
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,"HEADING_RECEIPT_MISMATCH"):
            verify_stage(self.mpath.read_bytes(),self.stage)

    def test_untrusted_voice_path_refused(self):
        p=self.stage/"review_concat.txt";lines=p.read_text().splitlines()
        lines[0]="file '"+str(self.root/"elsewhere"/"000000.wav")+"'"
        p.write_text("\n".join(lines)+"\n")
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_VOICE_PATH_OR_ORDER"):
            verify_stage(self.mpath.read_bytes(),self.stage)

    def test_only_title_positions_get_cue(self):
        _,pairs=verify_stage(self.mpath.read_bytes(),self.stage)
        a,b,titles=make_playlists(pairs,{0,2},{0,1,2},
                                 self.root/"bell.wav",self.root/"lead.wav")
        self.assertEqual(titles,[0,2])
        self.assertEqual(a.count("file '"),5)
        self.assertEqual(b.count("bell.wav"),2)
        self.assertEqual(b.count("lead.wav"),2)
        for idx in range(3):
            self.assertEqual(a.count(f"{idx:06d}.wav"),1)
            self.assertEqual(b.count(f"{idx:06d}.wav"),1)
        self.assertEqual(a.count("gap_300.wav"),2)
        self.assertEqual(b.count("gap_300.wav"),2)

    def test_preview_without_title_rejected(self):
        _,pairs=verify_stage(self.mpath.read_bytes(),self.stage)
        with self.assertRaisesRegex(ValueError,"SELECTED_WINDOW_HAS_NO_HEADING"):
            make_playlists(pairs,{0,2},{1},self.root/"bell.wav",self.root/"lead.wav")

    def test_output_in_original_stage_refused(self):
        with self.assertRaisesRegex(ValueError,"OUTPUT_MUST_NOT_MODIFY_E_STAGE"):
            create_review(self.mpath,self.stage,self.stage/"prohibited",0,2)

    def test_production_output_path_refused(self):
        with self.assertRaisesRegex(ValueError,"REFUSE_UNSAFE_STAGING_DESTINATION"):
            create_review(self.mpath,self.stage,self.root/"chunks"/"review",0,2)

    def test_cli_defaults_to_no_execution(self):
        out=self.root/"untouched"
        script=Path(__file__).with_name("v5_title_cue_staging.py")
        p=subprocess.run([sys.executable,str(script),"--manifest",str(self.mpath),
            "--e-stage-dir",str(self.stage),"--out-dir",str(out)],
            capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("DISABLED_DEFAULT",p.stdout)
        self.assertFalse(out.exists())

    def test_synthetic_end_to_end_no_real_ffmpeg_required(self):
        out=self.root/"AB"
        def mocked_subprocess(cmd, **kwargs):
            if cmd[0]=="ffmpeg":
                Path(cmd[-1]).write_bytes(b"synthetic-output-"+Path(cmd[-1]).name.encode())
                return subprocess.CompletedProcess(cmd,0)
            if cmd[0]=="ffprobe":
                file=str(cmd[-1])
                return subprocess.CompletedProcess(cmd,0,
                    stdout="11.74\n" if "F_TITLE_CUE" in file else "10.26\n")
            raise AssertionError(cmd)
        with patch("v5_title_cue_staging.subprocess.run",side_effect=mocked_subprocess):
            result=create_review(self.mpath,self.stage,out,0,3)
        self.assertEqual(result["title_indices"],[0,2])
        self.assertTrue(result["no_sfx_under_speech"])
        self.assertEqual(len(result["files"]),2)
        self.assertFalse(result["production_modified"])
        self.assertFalse(result["chapter_final"])
        self.assertFalse(result["owner_approved"])
        self.assertEqual((self.stage/"CHAPTER_STAGING_NOT_FINAL.REVIEW.mp3").read_bytes(),
                         b"synthetic-E-mp3")
        self.assertNotIn("Tên Chương",json.dumps(result,ensure_ascii=False))
        with patch("v5_title_cue_staging.subprocess.run",side_effect=mocked_subprocess):
            with self.assertRaises(FileExistsError):
                create_review(self.mpath,self.stage,out,0,3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
