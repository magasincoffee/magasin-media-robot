"""Offline negative and positive tests: never use H4 production data."""
from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import time
import unittest
from contextlib import redirect_stdout
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

    def test_only_root_metadata_without_file_content_reads_or_mutation(self):
        before = {(str(x), x.stat().st_size, x.stat().st_mtime_ns)
                  for x in self.root.rglob("*") if x.is_file()}
        with patch.object(Path, "open", side_effect=AssertionError("bytes must not be read")):
            result = sut.scan_scope(self.root, now=self.now)
        after = {(str(x), x.stat().st_size, x.stat().st_mtime_ns)
                 for x in self.root.rglob("*") if x.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result["file_count"], 2)  # child WAV intentionally NOT scanned
        self.assertEqual(result["skipped_subdirectory_count"], 1)
        self.assertEqual(result["status"], "READ_ONLY_METADATA_PARTIAL_SKIPPED")
        self.assertFalse(result["complete_tree_inventory"])
        self.assertEqual(result["older_than_7d_file_count"], 1)
        self.assertEqual(result["older_than_7d_logical_bytes"], len(b"older-test"))
        self.assertFalse(result["safe_to_delete_verified"])
        self.assertFalse(result["checkpoint_owner_verified"])
        dump = json.dumps(result)
        for sensitive in ("private-manuscript", "segment.wav", str(self.root)):
            self.assertNotIn(sensitive, dump)

    def test_single_level_fixture_without_children_is_complete_only_for_that_level(self):
        shallow = self.root / "child"
        r = sut.scan_scope(shallow)
        self.assertEqual(r["file_count"], 1)
        self.assertEqual(r["skipped_subdirectory_count"], 0)
        self.assertTrue(r["complete_tree_inventory"])
        self.assertEqual(r["status"], "READ_ONLY_METADATA_TOP_LEVEL_COMPLETE")

    def test_no_directory_queue_even_if_child_can_be_replaced_with_junction(self):
        original = sut.os.scandir
        targets = []
        def bounded(path):
            targets.append(str(path))
            if Path(path) != self.root:
                raise AssertionError("nested scan: TOCTOU reparse escape")
            return original(path)
        with patch.object(sut.os, "scandir", side_effect=bounded):
            r = sut.scan_scope(self.root)
        self.assertEqual(targets, [str(self.root)])
        self.assertEqual(r["skipped_subdirectory_count"], 1)
        self.assertFalse(r["complete_tree_inventory"])

    def test_file_budget_fail_closed(self):
        with self.assertRaisesRegex(sut.AuditHold, "FILE_BUDGET_EXCEEDED"):
            sut.scan_scope(self.root, max_files=1)
        for bad in (0, True, 30001):
            with self.assertRaises(ValueError):
                sut.scan_scope(self.root, max_files=bad)

    def test_timeout_fail_closed(self):
        samples = iter([1000, 1002])
        with self.assertRaisesRegex(sut.AuditHold, "TIME_BUDGET_EXCEEDED"):
            sut.scan_scope(self.root, monotonic=lambda: next(samples), max_seconds=1)

    def test_symlink_skipped_and_incompleteness_visible(self):
        try:
            (self.root / "linked").symlink_to(self.root / "old.tmp")
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable on this hosted Windows runner")
        r = sut.scan_scope(self.root, now=self.now)
        self.assertEqual(r["file_count"], 2)
        self.assertGreaterEqual(r["skipped_reparse_entries"], 1)
        self.assertEqual(r["status"], "READ_ONLY_METADATA_PARTIAL_SKIPPED")
        self.assertFalse(r["complete_tree_inventory"])

    def test_root_symlink_rejected_without_following(self):
        alias = self.root.parent / (self.root.name + "-alias")
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable on hosted Windows runner")
        self.addCleanup(alias.unlink)
        with self.assertRaisesRegex(sut.AuditHold, "ROOT_MISSING_OR_UNSAFE"):
            sut.scan_scope(alias)

    def test_p1_real_h4_gate_precedes_even_root_metadata(self):
        with patch.object(sut, "_is_h4", return_value=True), \
             patch.object(Path, "is_dir", side_effect=AssertionError("root touched")), \
             patch.object(sut.os, "scandir", side_effect=AssertionError("scan touched")):
            with self.assertRaisesRegex(sut.AuditHold, "LIVE_H4_SCAN_NOT_AUTHORIZED"):
                sut.scan_scope(self.root)

    def test_p1_no_direct_executable_path_even_with_a_fake_correct_host(self):
        with patch.object(sut, "_is_h4", return_value=True), \
             patch.object(sut, "scan_scope", side_effect=AssertionError("scan touched")):
            receipt = sut.run_h4()
            stream = io.StringIO()
            with redirect_stdout(stream):
                status = sut.main()
        self.assertEqual(status, 21)
        self.assertEqual(json.loads(stream.getvalue()), receipt)
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertEqual(receipt["scopes"], {})
        self.assertFalse(receipt["approved_to_dispatch"])
        self.assertFalse(receipt["approved_to_start"])
        self.assertFalse(receipt["task_completed"])

    def test_wrong_host_also_blocks_direct_executable(self):
        with patch.object(sut.platform, "node", return_value="DESKTOP-4K7IM13"):
            r = sut.run_h4()
        self.assertEqual(r["status"], "BLOCKED")
        self.assertFalse(r["worker_started"])

    def test_missing_root_fails_without_claiming_inventory(self):
        with self.assertRaisesRegex(sut.AuditHold, "ROOT_MISSING_OR_UNSAFE"):
            sut.scan_scope(self.root / "nonexistent-root")

    def test_unreadable_root_fails_closed_without_leaking_path(self):
        with patch.object(Path, "is_dir", side_effect=PermissionError("PRIVATE_ROOT")):
            with self.assertRaises(sut.AuditHold) as error:
                sut.scan_scope(self.root)
        self.assertEqual(str(error.exception), "ROOT_METADATA_UNREADABLE")
        self.assertNotIn("PRIVATE_ROOT", str(error.exception))

    def test_root_reparse_attribute_is_rejected_before_enumeration(self):
        with patch.object(sut, "_reparse", return_value=True), \
             patch.object(sut.os, "scandir", side_effect=AssertionError("opened root")):
            with self.assertRaisesRegex(sut.AuditHold, "ROOT_REPARSE_REJECTED"):
                sut.scan_scope(self.root)

    def test_directory_enumeration_permission_error_is_sanitized(self):
        with patch.object(sut.os, "scandir", side_effect=PermissionError("PRIVATE_FOLDER")):
            with self.assertRaises(sut.AuditHold) as error:
                sut.scan_scope(self.root)
        self.assertEqual(str(error.exception), "DIRECTORY_UNREADABLE_NO_COMPLETE_CLAIM")
        self.assertNotIn("PRIVATE_FOLDER", str(error.exception))

    def test_child_entry_metadata_error_is_sanitized(self):
        class BadEntry:
            def is_symlink(self):
                return False

            def stat(self, *, follow_symlinks=True):
                raise PermissionError("PRIVATE_FILE_NAME")

        class FakeScan:
            def __enter__(self):
                return iter([BadEntry()])

            def __exit__(self, exc_type, exc_value, traceback):
                return False

        with patch.object(sut.os, "scandir", return_value=FakeScan()):
            with self.assertRaises(sut.AuditHold) as error:
                sut.scan_scope(self.root)
        self.assertEqual(str(error.exception), "ENTRY_METADATA_UNREADABLE")
        self.assertNotIn("PRIVATE_FILE_NAME", str(error.exception))

    def test_time_budget_out_of_range_fails_closed(self):
        for bad in (0, 26, True, 1.5, "25"):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    sut.scan_scope(self.root, max_seconds=bad)

    def test_entry_budget_and_partial_report_cannot_approve_cleanup(self):
        receipt = sut.scan_scope(self.root, now=self.now)
        self.assertFalse(receipt["complete_tree_inventory"])
        self.assertFalse(receipt["safe_to_delete_verified"])
        self.assertFalse(receipt["checkpoint_owner_verified"])
        self.assertNotIn("approved_to_dispatch", receipt)
        blocked = sut.run_h4()
        self.assertEqual(blocked["status"], "BLOCKED")
        self.assertFalse(blocked["approved_to_start"])
        self.assertFalse(blocked["approved_to_dispatch"])
        self.assertFalse(blocked["safe_to_delete_verified"])
        self.assertFalse(blocked["task_completed"])

    def test_no_unsafe_mutation_or_network_in_source(self):
        code = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("subprocess.run", "subprocess.Popen",
                          "shutil.rmtree", "os.remove(", "os.unlink(",
                          "os.rename(", "os.replace(", "os.makedirs(",
                          "Path.write_bytes", "Path.write_text", "urllib",
                          "os.walk(", "os.fwalk(", "stack.append("):
            self.assertNotIn(forbidden, code)
        self.assertIn('"LIVE_H4_SCAN_NOT_AUTHORIZED"', code)
        self.assertIn("return 21", code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
