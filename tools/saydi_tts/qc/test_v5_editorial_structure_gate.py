"""Offline synthetic regression for editorial structure and page furniture triage."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from v5_editorial_structure_gate import audit, save_new


def fixture(source=None):
    source = source if source is not None else (
        "Chương 4: Mở đầu.\nMột dòng của câu chuyện. Một ý nhỏ, người kể tiếp theo.\n"
        "Trang 12\nChú thích: ví dụ.\n"
    )
    manifest = {
        "chapter_number": 4,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "segments": [
            {"index":0,"canonical_text":"Chương 4: Mở đầu.",
             "heading":True,"parent_line":0,"parent_end":True,"pause_before_ms":0},
            {"index":1,"canonical_text":"Một dòng của câu chuyện.",
             "heading":False,"parent_line":1,"parent_end":False},
            {"index":2,"canonical_text":"Một ý nhỏ,",
             "heading":False,"parent_line":1,"parent_end":False},
            {"index":3,"canonical_text":"người kể tiếp theo.",
             "heading":False,"parent_line":1,"parent_end":True},
        ],
    }
    return source.encode("utf-8"), manifest


class EditorialStructureTests(unittest.TestCase):
    def setUp(self):
        self.source,self.manifest=fixture()
        self.msha="a"*64

    def run_gate(self, src=None, manifest=None):
        return audit(self.manifest if manifest is None else manifest,
                     self.source if src is None else src,self.msha)

    def test_heading_present_and_missing_prosody_approval(self):
        r=self.run_gate()
        self.assertEqual(r["heading_indices"],[0])
        self.assertEqual(r["heading_prosody_review_indices"],[0])
        self.assertFalse(r["new_heading_audio_verified"])
        self.assertFalse(r["owner_final"])

    def test_weak_clause_cut_detected_without_changing_words(self):
        r=self.run_gate()
        self.assertIn(2,r["same_parent_weak_split_indices"])
        self.assertTrue(r["all_original_text_preserved"])
        self.assertFalse(r["automatic_rerender_allowed"])

    def test_explicit_page_number_is_candidate_not_deleted(self):
        r=self.run_gate()
        candidates=r["source_page_and_annotation_candidates"]
        self.assertIn("EXPLICIT_PAGE_LABEL_CANDIDATE",[x["type"] for x in candidates])
        self.assertFalse(r["automatic_text_suppression_allowed"])
        self.assertTrue(all(not x["automatic_deletion_allowed"] for x in candidates))

    def test_translator_note_is_review_not_automatic_deletion(self):
        r=self.run_gate()
        self.assertIn("ANNOTATION_OR_TRANSLATOR_NOTE_REVIEW",
                      [x["type"] for x in r["source_page_and_annotation_candidates"]])
        self.assertFalse(r["automatic_text_suppression_allowed"])

    def test_standalone_numeric_line_requires_review(self):
        source,_=fixture("Bắt đầu.\n2024\nKết thúc.")
        m=copy.deepcopy(self.manifest)
        m["source_sha256"]=hashlib.sha256(source.encode()).hexdigest()
        r=self.run_gate(src=source.encode(),manifest=m)
        self.assertEqual(r["source_page_and_annotation_candidates"][0]["type"],
                         "AMBIGUOUS_STANDALONE_NUMBER_CANDIDATE")
        self.assertFalse(r["automatic_text_suppression_allowed"])

    def test_chapter_number_is_not_page_artifact(self):
        source=b"Chuong 12\nMot cau."
        m=copy.deepcopy(self.manifest)
        m["source_sha256"]=hashlib.sha256(source).hexdigest()
        r=self.run_gate(src=source,manifest=m)
        self.assertEqual(r["source_page_and_annotation_candidates"],[])

    def test_in_sentence_page_word_is_not_auto_removed(self):
        source="Nhân vật đang ở trang 12 của cuốn sách.".encode()
        m=copy.deepcopy(self.manifest)
        m["source_sha256"]=hashlib.sha256(source).hexdigest()
        r=self.run_gate(src=source,manifest=m)
        self.assertEqual(r["source_page_and_annotation_candidates"],[])

    def test_notes_number_marked_only_when_structural(self):
        source="Một chương.\n[12] chú giải ở đây.\n".encode("utf-8")
        m=copy.deepcopy(self.manifest)
        m["source_sha256"]=hashlib.sha256(source).hexdigest()
        r=self.run_gate(src=source,manifest=m)
        self.assertEqual(r["source_page_and_annotation_candidates"][0]["type"],
                         "FOOTNOTE_REFERENCE_REVIEW")

    def test_heading_prosody_metadata_suppresses_missing_style_warning_only(self):
        m=copy.deepcopy(self.manifest)
        m["segments"][0]["prosody_role"]="HEADING"
        r=self.run_gate(manifest=m)
        self.assertEqual(r["heading_prosody_review_indices"],[])
        self.assertEqual(r["headings"],1)
        self.assertFalse(r["new_heading_audio_verified"])

    def test_bad_source_sha_stops(self):
        m=copy.deepcopy(self.manifest)
        m["source_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"SOURCE_SHA256_MISMATCH"):
            self.run_gate(manifest=m)

    def test_noncanonical_segmentation_stops(self):
        m=copy.deepcopy(self.manifest)
        m["segments"][2]["index"]=7
        with self.assertRaisesRegex(ValueError,"BAD_SEGMENT_ORDER"):
            self.run_gate(manifest=m)

    def test_no_transcript_in_report(self):
        result=json.dumps(self.run_gate(),ensure_ascii=False)
        self.assertNotIn("Một dòng của câu",result)
        self.assertNotIn("Chương 4: Mở",result)
        self.assertNotIn("chú thích: ví dụ",result.casefold())

    def test_stage_new_file_and_refuse_production_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"review"/"metadata.json"
            r=self.run_gate()
            save_new(output,r)
            self.assertTrue(output.exists())
            with self.assertRaises(FileExistsError):
                save_new(output,r)
            with self.assertRaisesRegex(ValueError,"REFUSE_PRODUCTION_PATH"):
                save_new(Path(tmp)/"chunks"/"metadata.json",r)

    def test_cli_default_does_not_read_or_write_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            m=folder/"manifest.json"
            s=folder/"source.txt"
            dest=folder/"out.json"
            m.write_text(json.dumps(self.manifest),encoding="utf-8")
            s.write_bytes(self.source)
            script=Path(__file__).with_name("v5_editorial_structure_gate.py")
            call=subprocess.run([sys.executable,str(script),
                "--manifest",str(m),"--source-utf8",str(s),
                "--output",str(dest)],capture_output=True,text=True)
            self.assertEqual(call.returncode,0,call.stderr)
            self.assertIn("DISABLED_DEFAULT",call.stdout)
            self.assertFalse(dest.exists())


if __name__=="__main__":
    unittest.main(verbosity=2)
