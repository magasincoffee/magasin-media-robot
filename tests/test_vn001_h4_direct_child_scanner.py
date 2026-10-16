"""Windows synthetic-only filesystem tests; never access real SAYDI directories."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest

P=Path(__file__).resolve().parents[1]/"tools/saydi_tts/qc/vn001_h4_direct_child_scanner.py"
spec=importlib.util.spec_from_file_location("vn001_direct_child",P)
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m
spec.loader.exec_module(m)


@unittest.skipUnless(os.name=="nt","Windows handle tests require Windows")
class WindowsStageScanner(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)/"synthetic_v5"
        self.root.mkdir()

    def test_direct_metadata_only_no_private_paths_or_content(self):
        (self.root/"test_manifest.json").write_text('{"private":"NEVER_EMIT"}',encoding="utf-8")
        (self.root/"clip.wav").write_bytes(b"synthetic_pcm_not_private")
        result=m.inspect_direct_metadata(self.root)
        self.assertEqual(result["status"],"DIRECT_CHILD_METADATA_PARTIAL_UNATTESTED")
        self.assertEqual(result["candidate_files"],2)
        self.assertFalse(result["complete_v5_inventory"])
        self.assertFalse(result["content_sha_verified"])
        self.assertFalse(result["field_accepted"])
        self.assertFalse(result["approved_to_start"])
        self.assertNotIn("test_manifest",str(result))
        self.assertNotIn("NEVER_EMIT",str(result))
        self.assertNotIn(str(self.root),str(result))

    def test_nested_subdir_not_traversed_and_declared_partial(self):
        folder=self.root/"skip_dir"
        folder.mkdir()
        (folder/"protected.wav").write_bytes(b"simulated")
        report=m.inspect_direct_metadata(self.root)
        self.assertEqual(report["status"],"DIRECT_CHILD_METADATA_PARTIAL_UNATTESTED")
        self.assertEqual(report["candidate_files"],0)
        self.assertTrue(report["skipped_child_directories"])
        self.assertFalse(report["complete_v5_inventory"])

    def test_large_scan_fail_closed(self):
        for i in range(3):
            (self.root/f"file{i}.wav").write_bytes(b"x")
        report=m.inspect_direct_metadata(self.root,max_children=2)
        self.assertEqual(report["status"],"BLOCKED")
        self.assertEqual(report["reason"],"SCAN_LIMIT_EXCEEDED")
        self.assertNotIn("candidate_files",report)

    def test_unknown_suffix_declared_partial(self):
        (self.root/"private.txt").write_text("fixture only")
        report=m.inspect_direct_metadata(self.root)
        self.assertEqual(report["candidate_files"],0)
        self.assertTrue(report["skipped_other_files"])
        self.assertFalse(report["complete_v5_inventory"])

    def test_filesystem_root_reparse_rejected(self):
        target=self.root/"actual"
        target.mkdir()
        link=self.root.parent/"junc_link"
        try:
            os.symlink(target,link,target_is_directory=True)
        except (OSError,NotImplementedError) as exc:
            self.skipTest("symlink privilege unavailable: "+type(exc).__name__)
        report=m.inspect_direct_metadata(link)
        self.assertEqual(report["status"],"BLOCKED")
        self.assertEqual(report["reason"],"REPARSE_REJECTED")
        self.assertNotIn("candidate_files",report)

    def test_real_windows_junction_as_root_rejected(self):
        import subprocess
        target=self.root/"real_dir"
        target.mkdir()
        link=self.root.parent/"junction_root"
        proc=subprocess.run(["cmd","/c","mklink","/J",str(link),str(target)],
                            capture_output=True,text=True,check=False)
        if proc.returncode != 0:
            self.skipTest("mklink /J unsupported on this runner")
        result=m.inspect_direct_metadata(link)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertEqual(result["reason"],"REPARSE_REJECTED")

    def test_real_windows_junction_inside_root_rejected(self):
        import subprocess
        target=self.root.parent/"outside_dir"
        target.mkdir()
        (target/"fixture.wav").write_bytes(b"synthetic")
        link=self.root/"junction_child"
        proc=subprocess.run(["cmd","/c","mklink","/J",str(link),str(target)],
                            capture_output=True,text=True,check=False)
        if proc.returncode != 0:
            self.skipTest("mklink /J unsupported on this runner")
        result=m.inspect_direct_metadata(self.root)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertEqual(result["reason"],"REPARSE_REJECTED")

    def test_direct_file_link_rejected(self):
        target=self.root/"fixture_audio.wav"
        target.write_bytes(b"x")
        link=self.root/"virtual.wav"
        try:
            os.symlink(target,link)
        except (OSError,NotImplementedError) as exc:
            self.skipTest("symlink privilege unavailable: "+type(exc).__name__)
        report=m.inspect_direct_metadata(self.root)
        self.assertEqual(report["status"],"BLOCKED")
        self.assertEqual(report["reason"],"REPARSE_REJECTED")

    def test_malformed_bound_blocks(self):
        self.assertEqual(m.inspect_direct_metadata(self.root,max_children=0)["status"],"BLOCKED")
        self.assertEqual(m.inspect_direct_metadata(self.root,max_children=True)["status"],"BLOCKED")

    def test_relative_root_blocks(self):
        res=m.inspect_direct_metadata(Path("synthetic_v5"))
        self.assertEqual(res["status"],"BLOCKED")
        self.assertEqual(res["reason"],"ROOT_NOT_WINDOWS_ABSOLUTE")


class CrossPlatformFailClosed(unittest.TestCase):
    def test_no_scope_widening(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.inspect_direct_metadata(Path(d),max_children=1001)
            self.assertEqual(r["status"],"BLOCKED")
            self.assertFalse(r["task_completed"])
            self.assertFalse(r["approved_to_start"])

    @unittest.skipIf(os.name=="nt","non-Windows gate")
    def test_linux_must_block(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.inspect_direct_metadata(Path(d))
            self.assertEqual(r["reason"],"WINDOWS_ONLY")
            self.assertNotIn("metadata_fingerprint_sha256",r)


if __name__=="__main__":
    unittest.main()
