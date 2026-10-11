"""Offline QC pre-render safety fixtures; no models, private text or WAV used."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from v5_editorial_multiround import digest, inspect, write_report
from v5_source_lineage import audit as source_audit, utf8_sha


MANIFEST_SHA = "b" * 64


def unit(index, canonical, spoken=None, parent_line=None, original=None):
    actual = spoken if spoken is not None else canonical
    result = {"index": index, "canonical_text": canonical,
              "spoken_text": actual, "parent_line": index if parent_line is None else parent_line,
              "tts_text_sha256": digest(actual)}
    if original is not None:
        result["original_text"] = original
    return result


def codes(report):
    return {f["code"] for f in report["findings"]}


class V5EditorialMultiroundTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {"chapter_number": 2, "segments": [
            unit(0, "Mỗi khi hè về.", original="Mỗi khi hè về."),
            unit(1, "Người phụ nữ bước tới.", original="Người phụ nữ bước tới."),
            unit(2, "Tôi nghe thấy tiếng mưa.", original="Tôi nghe thấy tiếng mưa."),
        ]}

    def run_check(self, manifest=None, reviewers=None, legacy=None):
        return inspect(self.manifest if manifest is None else manifest,
                       MANIFEST_SHA, reviewers, legacy)

    def test_clean_source_still_requires_independent_review(self):
        r = self.run_check()
        self.assertEqual(r["status"], "REVIEW")
        self.assertEqual(r["source_text_verified_segments"], 3)
        self.assertEqual(codes(r), {"INDEPENDENT_REVIEW_PENDING"})
        self.assertFalse(r["production_changed"])
        self.assertFalse(r["owner_final"])

    def test_tone_cannot_be_silently_rewritten(self):
        m = copy.deepcopy(self.manifest)
        m["segments"][0] = unit(0, "Mỗi khi hè về.", "Mỗi khi he về.",
                                original="Mỗi khi hè về.")
        r = self.run_check(m)
        self.assertIn("CANONICAL_SPOKEN_TOKEN_DIFF", codes(r))
        self.assertEqual(m["segments"][0]["canonical_text"], "Mỗi khi hè về.")
        self.assertEqual(r["status"], "REVIEW")

    def test_original_source_token_mismatch_requires_review(self):
        m = copy.deepcopy(self.manifest)
        m["segments"][1]["original_text"] = "Người phu nữ bước tới."
        r = self.run_check(m)
        self.assertIn("SOURCE_CANONICAL_TOKEN_DIFF", codes(r))

    def test_bad_spoken_hash_blocks(self):
        m = copy.deepcopy(self.manifest)
        m["segments"][0]["tts_text_sha256"] = "a" * 64
        m["segments"][0]["tts_text_hash_scheme"] = "sha256_utf8_spoken_v1"
        r = self.run_check(m)
        self.assertEqual(r["status"], "BLOCKED")
        self.assertIn("TTS_TEXT_HASH_DRIFT", codes(r))

    def test_legacy_v5_opaque_fingerprint_is_not_a_false_block(self):
        m = copy.deepcopy(self.manifest)
        m["segments"][0]["tts_text_sha256"] = "a" * 64
        r = self.run_check(m)
        self.assertEqual(r["status"], "REVIEW")
        self.assertEqual(r["legacy_opaque_tts_hash_count"], 3)
        self.assertNotIn("TTS_TEXT_HASH_DRIFT", codes(r))

    def test_structural_gap_blocks(self):
        m = copy.deepcopy(self.manifest)
        m["segments"][1]["index"] = 3
        r = self.run_check(m)
        self.assertIn("INVALID_INDEX_ORDER", codes(r))
        self.assertEqual(r["status"], "BLOCKED")

    def test_repeated_clause_boundary_review_not_autodelete(self):
        m = {"segments": [
            unit(0, "Người phụ nữ,", parent_line=7),
            unit(1, "phụ nữ bước tới.", parent_line=7),
        ]}
        r = self.run_check(m)
        self.assertIn("CLAUSE_CUT_WITHIN_PARENT", codes(r))
        self.assertFalse(r["auto_repair"])
        self.assertEqual(len(m["segments"]), 2)

    def test_replacement_character_flagged(self):
        m = copy.deepcopy(self.manifest)
        m["segments"][0] = unit(0, "Mỗi khi h\ufffd về.")
        r = self.run_check(m)
        self.assertIn("REPLACEMENT_CHARACTER", codes(r))

    def test_missing_canonical_blocks(self):
        m = {"segments": [unit(0, "", "")]}
        r = self.run_check(m)
        self.assertIn("EMPTY_CANONICAL", codes(r))
        self.assertEqual(r["status"], "BLOCKED")

    def test_unverified_provenance_never_claims_source_fidelity(self):
        m = {"segments": [unit(0, "Một ngày đẹp trời.")]}
        r = self.run_check(m)
        self.assertEqual(r["source_text_verified_segments"], 0)
        self.assertIn("SOURCE_PROVENANCE_UNVERIFIED", codes(r))
        self.assertEqual(r["missing_source_provenance_count"], 1)
        self.assertEqual(len([f for f in r["findings"] if f["code"] == "SOURCE_PROVENANCE_UNVERIFIED"]), 1)

    def test_verified_lineage_closes_unknown_source_span_count_only(self):
        m = copy.deepcopy(self.manifest)
        for segment in m["segments"]:
            segment.pop("original_text", None)
        source = "Mỗi khi hè về. Người phụ nữ bước tới. Tôi nghe thấy tiếng mưa."
        m["source_sha256"] = utf8_sha(source)
        lineage = source_audit(m, source.encode("utf-8"),
                               manifest_sha256=MANIFEST_SHA)
        report = inspect(m, MANIFEST_SHA, source_lineage=lineage)
        self.assertEqual(report["source_text_verified_segments"], 3)
        self.assertEqual(report["missing_source_provenance_count"], 0)
        self.assertEqual(report["source_lineage"],
                         "SHA_BOUND_LEXICAL_EQUIVALENCE_PASS")
        self.assertNotIn("SOURCE_PROVENANCE_UNVERIFIED", codes(report))
        self.assertEqual(report["status"], "REVIEW")
        self.assertFalse(report["independent_semantics_verified"]
                         if "independent_semantics_verified" in report else False)

    def test_source_punctuation_divergence_never_becomes_auto_pass(self):
        m = copy.deepcopy(self.manifest)
        original = "Mỗi khi hè về, Người phụ nữ bước tới. Tôi nghe thấy tiếng mưa."
        m["source_sha256"] = utf8_sha(original)
        lineage = source_audit(m, original.encode("utf-8"),
                               manifest_sha256=MANIFEST_SHA)
        self.assertEqual(lineage["lexical_equivalence"], "PASS")
        self.assertEqual(lineage["punctuation_equivalence"], "REVIEW")
        result = inspect(m, MANIFEST_SHA, source_lineage=lineage)
        self.assertIn("SOURCE_PUNCTUATION_REVIEW", codes(result))
        self.assertEqual(result["status"], "REVIEW")
        self.assertFalse(result["owner_final"])

    def test_stale_lineage_manifest_sha_cannot_authorize_source_span(self):
        m = copy.deepcopy(self.manifest)
        source = "Mỗi khi hè về. Người phụ nữ bước tới. Tôi nghe thấy tiếng mưa."
        m["source_sha256"] = utf8_sha(source)
        lineage = source_audit(m, source.encode("utf-8"),
                               manifest_sha256="c" * 64)
        with self.assertRaisesRegex(ValueError, "STALE_OR_UNBOUND_SOURCE_LINEAGE"):
            inspect(m, MANIFEST_SHA, source_lineage=lineage)

    def test_incomplete_source_lineage_keeps_review_open(self):
        m = copy.deepcopy(self.manifest)
        source = "Mỗi khi hè về. Người phụ nữ đi tới. Tôi nghe thấy tiếng mưa."
        m["source_sha256"] = utf8_sha(source)
        lineage = source_audit(m, source.encode("utf-8"),
                               manifest_sha256=MANIFEST_SHA)
        report = inspect(m, MANIFEST_SHA, source_lineage=lineage)
        self.assertEqual(report["source_lineage"], "REVIEW_UNVERIFIED")
        self.assertIn("SOURCE_LINEAGE_INCOMPLETE_OR_CHANGED", codes(report))
        self.assertEqual(report["status"], "REVIEW")

    def test_distinct_external_review_receipts_do_not_certify_final(self):
        reviewers = {"manifest_sha256": MANIFEST_SHA, "validators": [
            {"validator_id": "local-spelling-check", "manifest_sha256": MANIFEST_SHA, "status": "PASS"},
            {"validator_id": "independent-editor", "manifest_sha256": MANIFEST_SHA, "status": "PASS"}]}
        r = self.run_check(reviewers=reviewers)
        self.assertEqual(r["independent_review_status"],
                         "RECEIPTS_PRESENT_NOT_PROOF_OF_SEMANTIC_CORRECTNESS")
        self.assertNotIn("INDEPENDENT_REVIEW_PENDING", codes(r))
        self.assertEqual(r["status"], "REVIEW")
        self.assertFalse(r["owner_final"])

    def test_legacy_editorial_audit_reports_unresolved_paraphrase_risk(self):
        m = copy.deepcopy(self.manifest)
        m["source_sha256"] = "1" * 64
        m["reference_sha256"] = "2" * 64
        legacy = {"source_sha256": "1" * 64, "reference_sha256": "2" * 64,
                  "segments": 3, "word_integrity": "PASS",
                  "legacy_paraphrase_suspects": 60, "v5_spoken_text_diff": False,
                  "canonical_source_utf8": True}
        report = self.run_check(m, legacy=legacy)
        self.assertIn("LEGACY_PARAPHRASE_REVIEW", codes(report))
        self.assertEqual(report["legacy_editorial_audit"]["legacy_paraphrase_suspects"], 60)
        self.assertEqual(report["status"], "REVIEW")
        self.assertFalse(report["owner_final"])

    def test_legacy_editorial_audit_must_match_source_and_voice(self):
        m = copy.deepcopy(self.manifest)
        m["source_sha256"] = "1" * 64
        m["reference_sha256"] = "2" * 64
        legacy = {"source_sha256": "3" * 64, "reference_sha256": "2" * 64,
                  "segments": 3, "word_integrity": "PASS",
                  "legacy_paraphrase_suspects": 0, "v5_spoken_text_diff": False,
                  "canonical_source_utf8": True}
        report = self.run_check(m, legacy=legacy)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("LEGACY_AUDIT_BINDING_MISMATCH", codes(report))

    def test_editing_suggestion_cannot_silently_replace_spoken_tokens(self):
        m = copy.deepcopy(self.manifest)
        m["segments"][1]["editorial_text"] = "Người phu nữ bước tới."
        report = self.run_check(m)
        self.assertIn("EDITORIAL_SPOKEN_TOKEN_DIFF", codes(report))

    def test_duplicate_reviewers_rejected(self):
        reviewers = {"manifest_sha256": MANIFEST_SHA, "validators": [
            {"validator_id": "same", "manifest_sha256": MANIFEST_SHA, "status": "PASS"},
            {"validator_id": "same", "manifest_sha256": MANIFEST_SHA, "status": "PASS"}]}
        with self.assertRaisesRegex(ValueError, "REVIEWER_NOT_DISTINCT"):
            self.run_check(reviewers=reviewers)

    def test_stale_review_rejected(self):
        with self.assertRaisesRegex(ValueError, "STALE_EDITORIAL"):
            self.run_check(reviewers={"manifest_sha256": "x" * 64, "validators": []})

    def test_report_does_not_export_private_text(self):
        report = json.dumps(self.run_check(), ensure_ascii=False)
        self.assertNotIn("Người phụ nữ", report)
        self.assertNotIn("Mỗi khi hè về", report)

    def test_report_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "review.json"
            report = self.run_check()
            write_report(file, report)
            self.assertEqual(json.loads(file.read_text(encoding="utf-8"))["owner_final"], False)
            with self.assertRaises(FileExistsError):
                write_report(file, report)

    def test_cli_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            m = Path(directory) / "manifest.json"
            o = Path(directory) / "output.json"
            m.write_text(json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")
            script = Path(__file__).with_name("v5_editorial_multiround.py")
            p = subprocess.run([sys.executable, str(script), "--manifest", str(m),
                                "--report", str(o)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("DISABLED_DEFAULT", p.stdout)
            self.assertFalse(o.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
