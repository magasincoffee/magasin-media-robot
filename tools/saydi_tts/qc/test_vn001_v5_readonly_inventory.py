"""Synthetic offline tests; never require V5 assets or contact H4."""
from __future__ import annotations

import importlib.util
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SUT = Path(__file__).with_name("vn001_v5_readonly_inventory.py")
spec = importlib.util.spec_from_file_location("vn001_inventory", SUT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "chapterA").mkdir()
        (self.root / "chapterA" / "segment.wav").write_bytes(b"not-real-audio")
        (self.root / "chapterA" / "review.mp3").write_bytes(b"not-real-mp3")
        (self.root / "progress.json").write_text('{"synthetic":true}', encoding="utf-8")
        (self.root / "private_manuscript.txt").write_text("synthetic only", encoding="utf-8")

    def test_metadata_mode_is_read_only_and_redacts_paths(self):
        before = {(p.name, p.stat().st_size, p.stat().st_mtime_ns)
                  for p in self.root.rglob("*") if p.is_file()}
        r = mod.inventory(self.root, scope="audio")
        after = {(p.name, p.stat().st_size, p.stat().st_mtime_ns)
                 for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(r["candidate_files"], 3)
        self.assertEqual(r["kinds"], {"audio": 2, "checkpoint": 1})
        self.assertEqual(r["hashed_files"], 0)
        self.assertFalse(r["complete_file_hash_inventory"])
        self.assertFalse(r["owner_latch_verified"])
        self.assertFalse(r["checkpoint_ownership_verified"])
        self.assertFalse(r["approved_to_start"])
        output = str(r)
        self.assertNotIn("private_manuscript", output)
        self.assertNotIn("segment.wav", output)
        self.assertNotIn(str(self.root), output)

    def test_full_small_hashes_are_exact_and_deterministic(self):
        a = mod.inventory(self.root, scope="narrator", mode="hash")
        b = mod.inventory(self.root, scope="narrator", mode="hash")
        self.assertEqual(a["individual_hashes"], b["individual_hashes"])
        self.assertEqual(a["hashed_files"], 3)
        self.assertTrue(a["complete_file_hash_inventory"])
        hashes = {x["sha256"] for x in a["individual_hashes"]}
        self.assertIn(hashlib.sha256(b"not-real-audio").hexdigest(), hashes)
        self.assertNotIn("segment.wav", str(a))
        self.assertFalse(a["approved_to_dispatch"])

    def test_modified_asset_changes_digest(self):
        a = mod.inventory(self.root, scope="audio", mode="hash")
        (self.root / "chapterA" / "segment.wav").write_bytes(b"changed synthetic")
        b = mod.inventory(self.root, scope="audio", mode="hash")
        self.assertNotEqual(a["individual_hashes"], b["individual_hashes"])

    def test_hash_budget_is_honest_about_partial_evidence(self):
        a = mod.inventory(self.root, scope="audio", mode="hash", max_hash_files=1)
        self.assertEqual(a["hashed_files"], 1)
        self.assertEqual(a["unhashed_files"], 2)
        self.assertFalse(a["complete_file_hash_inventory"])

    def test_zero_hash_byte_budget_marks_partial(self):
        a = mod.inventory(self.root, scope="audio", mode="hash", max_hash_bytes=0)
        self.assertEqual(a["hashed_files"], 0)
        self.assertEqual(a["unhashed_files"], 3)

    def test_scan_limit_fails_closed(self):
        with self.assertRaisesRegex(mod.InventoryHold, "SCAN_LIMIT_EXCEEDED"):
            mod.inventory(self.root, scope="audio", max_scan=2)

    def test_disallows_unbounded_read_settings(self):
        with self.assertRaises(ValueError):
            mod.inventory(self.root, scope="audio", max_hash_bytes=2**31)

    def test_nonexistent_root_is_hold(self):
        with self.assertRaisesRegex(mod.InventoryHold, "ROOT_NOT_LOCAL_DIRECTORY"):
            mod.inventory(self.root / "missing", scope="audio")

    def test_symlink_is_not_followed(self):
        link = self.root / "chapterA" / "outside.wav"
        try:
            link.symlink_to(self.root / "progress.json")
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        a = mod.inventory(self.root, scope="audio")
        self.assertEqual(a["candidate_files"], 3)

    def test_cli_wrong_host_has_no_auth_bypass(self):
        with patch.object(mod.platform, "node", return_value="DESKTOP-4K7IM13"):
            with patch("sys.stdout") as out:
                status = mod.main(["--root", str(self.root), "--scope", "audio"])
            self.assertEqual(status, 21)
            self.assertTrue(out.write.called)


if __name__ == "__main__":
    unittest.main(verbosity=2)
