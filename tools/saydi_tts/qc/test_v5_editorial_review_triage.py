"""Offline tests with synthetic Vietnamese text. No audio, model or network."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from v5_editorial_review_triage import diff_types, triage, sha


def fixture():
    return {
        "chapter_number": 3,
        "source_sha256": "a" * 64,
        "reference_sha256": "b" * 64,
        "segments": [
            {"index": 0, "canonical_text": "Mỗi khi hè về.",
             "spoken_text": "Mỗi khi hè về.",
             "origin_spoken_text_v4": "Mỗi khi he về.", "parent_line": 1},
            {"index": 1, "canonical_text": "Người phụ nữ bước tới.",
             "spoken_text": "Người phụ nữ bước tới.",
             "origin_spoken_text_v4": "Người phụ nữ đi tới.", "parent_line": 2},
            {"index": 2, "canonical_text": "Trời đổ mưa.",
             "spoken_text": "Trời đổ mưa.", "parent_line": 3},
        ],
    }


class EditorialReviewTriageTests(unittest.TestCase):
    def report(self, m=None, old=None):
        return triage(fixture() if m is None else m, "c" * 64, old)

    def test_diacritic_drift_from_v4_is_review_only(self):
        result = self.report()
        self.assertEqual(result["status"], "REVIEW")
        self.assertFalse(result["auto_repair"])
        self.assertIn("POSSIBLE_VIETNAMESE_DIACRITIC_DRIFT", result["review_queue"][0]["codes"])

    def test_word_substitution_classification(self):
        self.assertEqual(diff_types("người phụ nữ đi tới", "người phụ nữ bước tới"),
                         {"POSSIBLE_WORD_REPLACEMENT"})

    def test_missing_added_or_reordered_tokens(self):
        self.assertIn("POSSIBLE_MISSING_WORDS", diff_types("tôi vẫn ở đây", "tôi ở đây"))
        self.assertIn("POSSIBLE_ADDED_WORDS", diff_types("tôi ở đây", "tôi vẫn ở đây"))
        self.assertEqual(diff_types("tôi đứng đây", "đây tôi đứng"), {"POSSIBLE_WORD_REORDER"})

    def test_old_v4_is_not_treated_as_authoritative_manuscript(self):
        result = self.report()
        self.assertFalse(result["source_semantic_approval"])
        self.assertFalse(result["owner_final"])
        self.assertFalse(result["audio_pronunciation_verified"])

    def test_legacy_60_is_aggregate_not_60_issues(self):
        old = {"source_sha256": "a"*64, "reference_sha256": "b"*64,
               "segments": 3, "legacy_paraphrase_suspects": 60}
        r = self.report(old=old)
        self.assertEqual(r["legacy_audit_status"], "BOUND_AGGREGATE_ONLY")
        self.assertEqual(r["legacy_paraphrase_suspect_count"], 60)
        self.assertEqual(r["potentially_affected_segments"], 2)
        self.assertTrue(r["legacy_count_does_not_identify_segments"])

    def test_stale_legacy_audit_fails(self):
        with self.assertRaisesRegex(ValueError, "STALE_LEGACY_AUDIT"):
            self.report(old={"source_sha256": "f"*64})

    def test_authored_repetition_is_not_automatically_removed(self):
        m = {"segments": [{"index": 0, "canonical_text": "Tôi tôi vẫn ở đây."}]}
        r = self.report(m=m)
        self.assertEqual(r["potentially_affected_segments"], 0)
        self.assertFalse(r["auto_repair"])

    def test_noncanonical_index_fails(self):
        m = fixture()
        m["segments"][1]["index"] = 19
        with self.assertRaisesRegex(ValueError, "INVALID_SEGMENT_ORDER"):
            self.report(m)

    def test_canonical_spoken_mismatch_flagged(self):
        m = fixture()
        m["segments"][2]["spoken_text"] = "Trời đổ mua."
        r = self.report(m)
        self.assertIn("SPOKEN_POSSIBLE_VIETNAMESE_DIACRITIC_DRIFT",
                      r["review_queue"][-1]["codes"])

    def test_parent_clause_boundary_flagged(self):
        m = fixture()
        m["segments"][0]["canonical_text"] = "Mỗi khi hè về,"
        m["segments"][1]["parent_line"] = 1
        r = self.report(m)
        self.assertIn("POSSIBLE_CLAUSE_CUT", r["review_queue"][1]["codes"])

    def test_bounded_owner_review_queue(self):
        m = {"segments": [
            {"index": i, "canonical_text": "Từ gốc.", "origin_spoken_text_v4": "Từ khác."}
            for i in range(50)
        ]}
        r = self.report(m)
        self.assertEqual(r["potentially_affected_segments"], 50)
        self.assertEqual(len(r["review_queue"]), 25)
        self.assertEqual(r["review_items_not_shown"], 25)

    def test_private_text_never_output(self):
        report = json.dumps(self.report(), ensure_ascii=False)
        self.assertNotIn("người phụ nữ", report.casefold())
        self.assertNotIn("Mỗi khi hè", report)

    def test_opt_in_required_and_no_report_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            manifest = d / "manifest.json"
            output = d / "result.json"
            manifest.write_text(json.dumps(fixture(), ensure_ascii=False), encoding="utf-8")
            script = Path(__file__).with_name("v5_editorial_review_triage.py")
            p = subprocess.run([sys.executable, str(script), "--manifest", str(manifest),
                                "--output", str(output)], text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("DISABLED_DEFAULT", p.stdout)
            self.assertFalse(output.exists())

    def test_cli_opt_in_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            manifest = d / "manifest.json"
            output = d / "result.json"
            manifest.write_text(json.dumps(fixture(), ensure_ascii=False), encoding="utf-8")
            script = Path(__file__).with_name("v5_editorial_review_triage.py")
            args = [sys.executable, str(script), "--manifest", str(manifest),
                    "--output", str(output), "--enable-experimental-triage"]
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertFalse(json.loads(output.read_text(encoding="utf-8"))["owner_final"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
