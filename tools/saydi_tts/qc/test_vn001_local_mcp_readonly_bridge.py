"""No-network/no-robot synthetic tests for local MCP READ_ONLY bridge."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).with_name("vn001_local_mcp_readonly_bridge.py")
spec = importlib.util.spec_from_file_location("vn001_mcp_bridge", MODULE)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
REV = "a" * 40


def envelope(**updates):
    obj = {
        "schema": bridge.SCHEMA, "task_id": bridge.TASK,
        "target": "saydi", "action": "inventory_v5_readonly",
        "root_key": "chapter2", "scope": "audio", "mode": "metadata",
        "hash_offset": 0, "expected_metadata_sha256": None,
        "expected_main_sha": REV,
    }
    obj.update(updates)
    return obj


def authority(**updates):
    obj = {
        "verified_exact_main": True, "repository": bridge.REPOSITORY,
        "sot_path": bridge.SOT_PATH, "main_sha": REV,
        "active_task_id": bridge.TASK, "task_status": "IN_PROGRESS",
        "production_dispatch_authorized": False,
    }
    obj.update(updates)
    return obj


class Vn001McpTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "segment.wav").write_bytes(b"synthetic")
        (self.root / "checkpoint.json").write_text('{"test":true}', encoding="utf-8")
        self.roots = {"chapter2": {"path": str(self.root), "scope": "audio"}}

    def invoke(self, request=None, trusted=True, given_authority=None):
        with patch.object(bridge, "_is_h4", return_value=True), \\
             patch.object(bridge, "_root_is_allowed", return_value=True):
            return bridge.handle_inventory(
                envelope() if request is None else request,
                verified_sot=authority() if given_authority is None else given_authority,
                transport_authenticated=trusted,
                locally_approved_roots=self.roots,
            )

    def test_deny_by_default_no_auth_or_sot(self):
        actual = bridge.handle_inventory(envelope())
        self.assertEqual(actual["status"], "BLOCKED")
        self.assertEqual(actual["reason"], "MCP_TRANSPORT_NOT_AUTHENTICATED")
        self.assertFalse(actual["approved_to_dispatch"])
        self.assertFalse(actual["owner_stop_changed"])

    def test_rejected_without_trusted_main_authority(self):
        out = bridge.handle_inventory(envelope(), transport_authenticated=True)
        self.assertEqual(out["reason"], "SOT_MAIN_AUTHORITY_UNVERIFIED")

    def test_rejected_on_wrong_main_revision(self):
        out = self.invoke(given_authority=authority(main_sha="b"*40))
        self.assertEqual(out["reason"], "SOT_MAIN_AUTHORITY_UNVERIFIED")

    def test_rejected_if_someone_fakes_done_or_start(self):
        for claimed in (authority(task_status="DONE"),
                        authority(production_dispatch_authorized=True),
                        authority(active_task_id="SAYDI002-VN-002"),
                        authority(verified_exact_main=False)):
            with self.subTest(claimed=claimed):
                self.assertEqual(self.invoke(given_authority=claimed)["status"], "BLOCKED")

    def test_rejects_other_actions_and_cross_project(self):
        for change in ({"action": "execute_task"},
                       {"action": "render_qc"},
                       {"target": "supervisor"},
                       {"task_id": "SAYDI002-VN-002"},
                       {"root_key": "../secret"},
                       {"cmd": "powershell"}):
            with self.subTest(change=change):
                self.assertEqual(self.invoke(envelope(**change))["status"], "BLOCKED")

    def test_wrong_host_and_unapproved_roots_hold(self):
        with patch.object(bridge, "_is_h4", return_value=False):
            resp = bridge.handle_inventory(
                envelope(), verified_sot=authority(),
                transport_authenticated=True, locally_approved_roots=self.roots)
            self.assertEqual(resp["reason"], "WRONG_HOST")
        self.assertFalse(bridge._root_is_allowed(self.root))
        with patch.object(bridge, "_is_h4", return_value=True):
            resp = bridge.handle_inventory(
                envelope(), verified_sot=authority(),
                transport_authenticated=True, locally_approved_roots=self.roots)
            self.assertEqual(resp["reason"], "ROOT_OUTSIDE_APPROVED_SAYDI_TREE")

    def test_root_key_not_from_client_path(self):
        out = self.invoke(envelope(root_key="unknown"))
        self.assertEqual(out["reason"], "ROOT_BINDING_NOT_ALLOWLISTED")

    def test_readonly_metadata_receipt_no_private_file_names(self):
        before = [(p.name, p.stat().st_mtime_ns, p.read_bytes())
                  for p in self.root.iterdir()]
        out = self.invoke()
        after = [(p.name, p.stat().st_mtime_ns, p.read_bytes())
                 for p in self.root.iterdir()]
        self.assertEqual(before, after)
        self.assertEqual(out["status"], "READ_ONLY_RECEIPT_UNATTESTED")
        self.assertEqual(out["inventory"]["candidate_files"], 2)
        self.assertFalse(out["approved_to_start"])
        self.assertFalse(out["project_switch_allowed"])
        self.assertFalse(out["task_completed"])
        serialized = json.dumps(out)
        self.assertNotIn("segment.wav", serialized)
        self.assertNotIn(str(self.root), serialized)

    def test_paged_hash_must_include_previous_metadata_fingerprint(self):
        out = self.invoke(envelope(mode="hash", hash_offset=1))
        self.assertEqual(out["reason"], "PAGED_HASH_REQUIRES_FINGERPRINT")
        digest = self.invoke()["inventory"]["metadata_fingerprint_sha256"]
        valid = self.invoke(envelope(mode="hash", hash_offset=1,
                                     expected_metadata_sha256=digest))
        self.assertEqual(valid["status"], "READ_ONLY_RECEIPT_UNATTESTED")
        self.assertFalse(valid["inventory"]["complete_file_hash_inventory"])
        (self.root / "segment.wav").write_bytes(b"changed-test")
        drift = self.invoke(envelope(mode="hash", hash_offset=1,
                                     expected_metadata_sha256=digest))
        self.assertEqual(drift["status"], "BLOCKED")
        self.assertEqual(drift["reason"], "METADATA_FINGERPRINT_CHANGED_FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
