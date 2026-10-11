"""Synthetic safety/unit tests for original background audio during headings."""
import array
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from v5_title_music_staging import (
    musical_intro, quiet_bed_over_heading, write_pcm, pcm_of,
    create_ab, MAX_MUSIC_PEAK, MAX_MUSIC_RMS, MAX_BED_PEAK, MUSIC_MS, SR,
)


class MusicalHeadingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.e=self.root/"E_STAGE"
        wavs=self.e/"review_wavs"
        wavs.mkdir(parents=True)
        self.manifest={"chapter_number":4,"segments":[
            {"index":0,"heading":True,"canonical_text":"Chương bốn"},
            {"index":1,"heading":False,"canonical_text":"Nội dung bình thường"},
            {"index":2,"heading":True,"canonical_text":"Tiêu đề phụ"},
        ]}
        self.mpath=self.root/"manifest.json"
        self.mpath.write_text(json.dumps(self.manifest),encoding="utf8")
        # Real 48k PCM samples but mock encoding to avoid dependence on FFmpeg.
        samples=array.array("h", [
            int(1200 * __import__("math").sin(2*__import__("math").pi*280*i/SR))
            for i in range(48000)])
        for i in range(3):
            write_pcm(wavs/f"{i:06d}.wav",samples.tobytes())
        write_pcm(wavs/"gap_365.wav",b"\0\0"*17520)
        items=[]
        for i in range(3):
            items.append("file '"+str((wavs/f"{i:06d}.wav").resolve()).replace("\\","/")+"'")
            if i!=2:
                items.append("file '"+str((wavs/"gap_365.wav").resolve()).replace("\\","/")+"'")
        (self.e/"review_concat.txt").write_text("\n".join(items)+"\n",encoding="utf8")
        original=self.e/"CHAPTER_STAGING_NOT_FINAL.REVIEW.mp3"
        original.write_bytes(b"private-synthetic-E-audio")
        receipt={"schema":"saydi-v5-staging-review-assembly-v1",
                 "chapter":4,"manifest_sha256":hashlib.sha256(self.mpath.read_bytes()).hexdigest(),
                 "mp3_sha256":hashlib.sha256(original.read_bytes()).hexdigest(),
                 "chapter_final":False,"production_modified":False,
                 "included_voice_wavs":3,"heading_indices":[0,2]}
        (self.e/"REVIEW_RECEIPT.json").write_text(json.dumps(receipt),encoding="utf8")

    def test_original_musical_intro_length_and_peak(self):
        pcm,meta=musical_intro()
        self.assertEqual(len(pcm), MUSIC_MS*SR//1000*2)
        self.assertLess(meta["peak"],MAX_MUSIC_PEAK)
        self.assertLess(meta["rms"],MAX_MUSIC_RMS)
        self.assertGreater(meta["peak"],.020)

    def test_heading_bed_is_bounded(self):
        original=pcm_of(self.e/"review_wavs"/"000000.wav")
        after,metric=quiet_bed_over_heading(original)
        self.assertEqual(len(after),len(original)*2)
        self.assertLess(metric["bed_peak"],MAX_BED_PEAK)
        self.assertTrue(metric["ducked_during_voice"])
        self.assertNotEqual(after,original.tobytes())

    def test_bed_fades_out_and_retains_voice_shape(self):
        original=pcm_of(self.e/"review_wavs"/"000000.wav")
        mixed,metric=quiet_bed_over_heading(original)
        result=array.array("h");result.frombytes(mixed)
        self.assertEqual(result[0],original[0])
        self.assertEqual(result[-1],original[-1])
        self.assertLessEqual(max(map(abs,result)),32767)

    def test_stage_and_original_cannot_be_overwritten(self):
        with self.assertRaisesRegex(ValueError,"REFUSE_E_STAGE_MUTATION"):
            create_ab(self.mpath,self.e,self.e/"subdir",0,2)
        with self.assertRaisesRegex(ValueError,"REFUSE_PRODUCTION_PATH"):
            create_ab(self.mpath,self.e,self.root/"chunks"/"review",0,2)

    def test_audio_identity_cannot_be_spoofed(self):
        path=self.e/"CHAPTER_STAGING_NOT_FINAL.REVIEW.mp3"
        path.write_bytes(b"tamper")
        with self.assertRaisesRegex(ValueError,"E_STAGE_AUDIO_HASH_MISMATCH"):
            create_ab(self.mpath,self.e,self.root/"AB",0,2)
        self.assertFalse((self.root/"AB").exists())

    def test_rejects_selection_without_heading(self):
        with self.assertRaisesRegex(ValueError,"NO_HEADINGS_SELECTED"):
            create_ab(self.mpath,self.e,self.root/"AB",1,1)

    def test_rejects_empty_window(self):
        with self.assertRaisesRegex(ValueError,"INVALID_SELECTION"):
            create_ab(self.mpath,self.e,self.root/"AB",0,0)

    def test_end_to_end_title_only_background_with_mock_ffmpeg(self):
        def run(args,**kwargs):
            if args[0]=="ffmpeg":
                Path(args[-1]).write_bytes(b"synthetic-mp3-"+Path(args[-1]).name.encode())
                return subprocess.CompletedProcess(args,0)
            if args[0]=="ffprobe":
                return subprocess.CompletedProcess(args,0,
                    stdout="14.2\n" if "G_SOFT_BACKGROUND" in str(args[-1]) else "12.2\n")
            raise AssertionError("Unknown command")
        out=self.root/"G_STAGING"
        with patch("v5_title_music_staging.subprocess.run",side_effect=run):
            r=create_ab(self.mpath,self.e,out,0,3)
        self.assertEqual(r["heading_indices"],[0,2])
        self.assertTrue(r["music_only_before_and_during_heading"])
        self.assertFalse(r["production_modified"])
        self.assertFalse(r["owner_approved"])
        self.assertFalse(r["chapter_final"])
        self.assertEqual(len(r["files"]),2)
        # Only the 2 heading voice WAVs mixed; narration voice WAV untouched.
        self.assertEqual(len(list((out/"mixed_heading_wavs").glob("*.wav"))),2)
        self.assertNotIn("Nội dung bình thường",json.dumps(r,ensure_ascii=False))
        contents=(out/"G_SOFT_BACKGROUND.concat.txt").read_text()
        self.assertEqual(contents.count("original_soft_music_intro.wav"),2)
        self.assertEqual(contents.count("lead_silence_160ms.wav"),2)
        control=(out/"E_NO_BACKGROUND.concat.txt").read_text()
        self.assertNotIn("original_soft_music_intro.wav",control)
        self.assertEqual((self.e/"CHAPTER_STAGING_NOT_FINAL.REVIEW.mp3").read_bytes(),
                         b"private-synthetic-E-audio")
        with patch("v5_title_music_staging.subprocess.run",side_effect=run):
            with self.assertRaises(FileExistsError):
                create_ab(self.mpath,self.e,out,0,3)

    def test_cli_off_by_default(self):
        out=self.root/"NO_STAGE"
        script=Path(__file__).with_name("v5_title_music_staging.py")
        p=subprocess.run([sys.executable,str(script),"--manifest",str(self.mpath),
                          "--e-stage-dir",str(self.e),"--out-dir",str(out),
                          "--count","2"],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("DISABLED_DEFAULT",p.stdout)
        self.assertFalse(out.exists())

    def test_output_wav_format(self):
        pcm,stats=musical_intro()
        path=self.root/"music.wav"
        write_pcm(path,pcm)
        with wave.open(str(path),"rb") as f:
            self.assertEqual((f.getnchannels(),f.getsampwidth(),f.getframerate()),
                             (1,2,48000))
        with self.assertRaises(FileExistsError):
            write_pcm(path,pcm)


if __name__=="__main__":
    unittest.main(verbosity=2)
