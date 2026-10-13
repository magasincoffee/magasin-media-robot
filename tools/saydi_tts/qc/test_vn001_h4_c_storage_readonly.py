"""Offline synthetic tests: file-content access and modifications are forbidden."""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).with_name("vn001_h4_c_storage_readonly.py")
spec = importlib.util.spec_from_file_location("vn001_storage", SCRIPT)
sut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sut)


class H4StorageAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "child").mkdir()
        (self.root / "child" / "segment.wav").write_bytes(b"synthetic-only")
        (self.root / "old.tmp").write_bytes(b"older-test")
        old = time.time() - 9 * 24 * 3600
        os.utime(self.root / "old.tmp", (old, old))
        (self.root / "private-manuscript.txt").write_bytes(b"none of this is real")
        self.now = time.time()

    def test_stats_without_reading_content_or_changing_anything(self):
        before = {str(x): (x.stat().st_size, x.stat().st_mtime_ns)
                  for x in self.root.rglob("*") if x.is_file()}
        with patch.object(Path, "open", side_effect=AssertionError("file bytes read")):
            result = sut.scan_scope(self.root, now=self.now)
        after = {str(x): (x.stat().st_size, x.stat().st_mtime_ns)
                 for x in self.root.rglob("*") if x.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result["file_count"], 3)
        self.assertEqual(result["older_than_7d_file_count"], 1)
        self.assertEqual(result["older_than_7d_logical_bytes"], len(b"older-test"))
        self.assertFalse(result["safe_to_delete_verified"])
        self.assertFalse(result["checkpoint_owner_verified"])
        text = json.dumps(result)
        self.assertNotIn("private-manuscript", text)
        self.assertNotIn(str(self.root), text)
        self.assertNotIn("segment.wav", text)

    def test_budget_fails_closed_not_partial_success(self):
        with self.assertRaisesRegex(sut.AuditHold, "FILE_BUDGET_EXCEEDED"):
            sut.scan_scope(self.root, max_files=2)
        with self.assertRaises(ValueError):
            sut.scan_scope(self.root, max_files=99999999)

    def test_depth_limit_fails_closed(self):
        (self.root / "child" / "deep").mkdir()
        with self.assertRaisesRegex(sut.AuditHold, "DEPTH_BUDGET_EXCEEDED"):
            sut.scan_scope(self.root, max_depth=1)

    def test_timeout_fails_closed(self):
        times = iter([1000, 1002])
        with self.assertRaisesRegex(sut.AuditHold, "TIME_BUDGET_EXCEEDED"):
            sut.scan_scope(self.root, monotonic=lambda: next(times), max_seconds=1)

    def test_reparse_or_symlink_excluded(self):
        link = self.root / "linked"
        try:
            link.symlink_to(self.root / "old.tmp")
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation requires platform permission")
        result = sut.scan_scope(self.root, now=self.now)
        self.assertEqual(result["file_count"], 3)
        self.assertGreaterEqual(result["skipped_reparse_entries"], 1)

    def test_root_symlink_is_rejected(self):
        alias = self.root.parent / (self.root.name + "-alias")
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation requires platform permission")
        self.addCleanup(alias.unlink)
        with self.assertRaisesRegex(sut.AuditHold, "ROOT_MISSING_OR_UNSAFE"):
            sut.scan_scope(alias)

    def test_wrong_host_never_inspects_paths(self):
        with patch.object(sut.platform, "node", return_value="DESKTOP-4K7IM13"), \
             patch.object(sut, "scan_scope", side_effect=AssertionError("must not scan")):
            r = sut.run_h4()
        self.assertEqual(r["status"], "BLOCKED")
        self.assertFalse(r["worker_started"])
        self.assertFalse(r["approved_to_dispatch"])
        self.assertFalse(r["safe_to_delete_verified"])

    def test_unreadable_roots_redacted_and_no_claim_of_success(self):
        with patch.object(sut, "_is_h4", return_value=True), \
             patch.dict(sut.SCOPES, {"user_temp": self.root / "missing",
                                     "saydi_output": self.root / "missing"}, clear=True):
            r = sut.run_h4()
        self.assertEqual(r["status"], "READ_ONLY_PARTIAL_UNATTESTED")
        self.assertEqual(r["scopes"]["user_temp"]["status"], "BLOCKED")
        self.assertNotIn(str(self.root), json.dumps(r))
        self.assertFalse(r["audio_sha_verified"])

    def test_no_cli_path_input_or_mutations_in_module(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("subprocess.run", "subprocess.Popen",
                          "shutil.rmtree", "os.remove(", "os.unlink(",
                          "os.rename(", "os.replace(", "os.makedirs(",
                          "Path.write_bytes", "Path.write_text", "urllib"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
