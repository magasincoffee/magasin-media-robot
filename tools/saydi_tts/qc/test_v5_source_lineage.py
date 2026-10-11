"""Offline source lineage tests. Public synthetic Vietnamese fixtures only."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from v5_source_lineage import audit, utf8_sha, save_new_report


def fixture():
    text = "Mỗi khi hè về, người phụ nữ bước tới. Trời đổ mưa."
    segments = [
        {"index": 0, "canonical_text": "Mỗi khi hè về,",
         "spoken_text": "Mỗi khi hè về,", "editorial_text": "Mỗi khi hè về,"},
        {"index": 1, "canonical_text": "người phụ nữ bước tới.",
         "spoken_text": "người phụ nữ bước tới."},
        {"index": 2, "canonical_text": "Trời đổ mưa.",
         "spoken_text": "Trời đổ mưa."},
    ]
    return text.encode("utf-8"), {
        "source_sha256": utf8_sha(text),
        "reference_sha256": "a" * 64,
        "chapter_number": 3,
        "segments": segments,
    }


class SourceLineageTests(unittest.TestCase):
    def setUp(self):
        self.source, self.manifest = fixture()

    def test_exact_chain_provenance_for_every_chunk(self):
        result = audit(self.manifest, self.source)
        self.assertEqual(result["lexical_equivalence"], "PASS")
        self.assertEqual(result["verified_source_span_count"], 3)
        self.assertEqual([(x["source_word_start"], x["source_word_end_exclusive"])
                          for x in result["source_spans"]], [(0, 4), (4, 9), (9, 12)])
        self.assertEqual(result["status"], "REVIEW")
        self.assertFalse(result["owner_final"])

    def test_reordering_never_grants_provenance(self):
        changed = copy.deepcopy(self.manifest)
        changed["segments"][0]["canonical_text"], changed["segments"][1]["canonical_text"] = (
            changed["segments"][1]["canonical_text"], changed["segments"][0]["canonical_text"])
        report = audit(changed, self.source)
        self.assertEqual(report["lexical_equivalence"], "REVIEW")
        self.assertEqual(report["verified_source_span_count"], 0)
        self.assertIsNotNone(report["first_mismatch_source_word_offset"])

    def test_deletion_cannot_be_marked_correct(self):
        modified = copy.deepcopy(self.manifest)
        modified["segments"][1]["canonical_text"] = "người phụ nữ tới."
        report = audit(modified, self.source)
        self.assertEqual(report["lexical_equivalence"], "REVIEW")
        self.assertNotEqual(report["source_token_count"], report["canonical_token_count"])
        self.assertEqual(report["source_spans"], [])

    def test_silent_accent_loss_is_review(self):
        changed = copy.deepcopy(self.manifest)
        changed["segments"][0]["canonical_text"] = "Mỗi khi he về,"
        report = audit(changed, self.source)
        self.assertEqual(report["lexical_equivalence"], "REVIEW")

    def test_spoken_mutation_is_reported_but_never_repaired(self):
        changed = copy.deepcopy(self.manifest)
        changed["segments"][0]["spoken_text"] = "Mỗi khi he về,"
        report = audit(changed, self.source)
        self.assertEqual(report["lexical_equivalence"], "PASS")
        self.assertIn("SPOKEN_CANONICAL_TOKEN_MISMATCH",
                      {x["code"] for x in report["findings"]})
        self.assertFalse(report["production_modified"])
        self.assertFalse(report["auto_render"])

    def test_duplicate_words_from_original_are_not_removed(self):
        text = "Tôi tôi vẫn ở đây."
        source = text.encode()
        m = {"source_sha256": utf8_sha(text), "segments": [
            {"index": 0, "canonical_text": "Tôi"},
            {"index": 1, "canonical_text": "tôi vẫn ở đây."},
        ]}
        report = audit(m, source)
        self.assertEqual(report["lexical_equivalence"], "PASS")
        self.assertEqual(len(report["source_spans"]), 2)

    def test_punctuation_drift_is_review_even_when_words_match(self):
        changed = copy.deepcopy(self.manifest)
        changed["segments"][0]["canonical_text"] = "Mỗi khi hè về"
        result = audit(changed, self.source)
        self.assertEqual(result["lexical_equivalence"], "PASS")
        self.assertEqual(result["punctuation_equivalence"], "REVIEW")
        self.assertIn("PUNCTUATION_ORDER_OR_COUNT_DIFF",
                      {x["code"] for x in result["findings"]})
        self.assertFalse(result["owner_final"])

    def test_wrong_source_hash_fails_closed(self):
        changed = copy.deepcopy(self.manifest)
        changed["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_SHA256_MISMATCH"):
            audit(changed, self.source)

    def test_bom_and_nfc_normalization_supported_when_sha_bound(self):
        text = "Mỗi khi hè về."
        raw = b"\xef\xbb\xbf" + text.encode("utf-8")
        m = {"source_sha256": utf8_sha(text), "segments": [
            {"index": 0, "canonical_text": text}]}
        r = audit(m, raw)
        self.assertEqual(r["source_hash_method"], "NFC_UTF8")
        self.assertEqual(r["lexical_equivalence"], "PASS")

    def test_legacy_60_suspects_remain_explicit_review(self):
        previous = {
            "source_sha256": self.manifest["source_sha256"],
            "reference_sha256": self.manifest["reference_sha256"],
            "segments": 3,
            "legacy_paraphrase_suspects": 60,
        }
        r = audit(self.manifest, self.source, previous)
        self.assertEqual(r["legacy_paraphrase_suspects"], 60)
        self.assertIn("LEGACY_PARAPHRASE_SUSPECTS", [f["code"] for f in r["findings"]])
        self.assertEqual(r["status"], "REVIEW")

    def test_stale_legacy_qa_refused(self):
        with self.assertRaisesRegex(ValueError, "STALE_LEGACY_AUDIT"):
            audit(self.manifest, self.source, {"source_sha256": "f" * 64})

    def test_private_text_not_present_in_report(self):
        report = json.dumps(audit(self.manifest, self.source), ensure_ascii=False)
        self.assertNotIn("người phụ nữ", report)
        self.assertNotIn("Mỗi khi hè về", report)

    def test_report_written_new_only_never_production(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "staging" / "lineage.json"
            report = audit(self.manifest, self.source)
            save_new_report(output, report)
            with self.assertRaises(FileExistsError):
                save_new_report(output, report)
            with self.assertRaisesRegex(ValueError, "NO_REPORT_IN_PRODUCTION"):
                save_new_report(Path(tmp)/"chunks"/"lineage.json", report)

    def test_cli_off_by_default_creates_no_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            m = folder/"manifest.json"
            s = folder/"source.txt"
            o = folder/"result.json"
            m.write_text(json.dumps(self.manifest), encoding="utf-8")
            s.write_bytes(self.source)
            script = Path(__file__).with_name("v5_source_lineage.py")
            p = subprocess.run([sys.executable, str(script),
                                "--manifest", str(m), "--source-utf8", str(s),
                                "--out", str(o)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("OFF_BY_DEFAULT", p.stdout)
            self.assertFalse(o.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
