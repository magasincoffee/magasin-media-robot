"""Synthetic GitHub-main authority tests, no external network or H4."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
QC = Path(__file__).resolve().parent
SOT = ROOT / "00_PROJECT" / "SOURCE_OF_TRUTH.md"


def module_at(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, QC / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


auth = module_at("vn001_sot_auth", "vn001_local_mcp_authority.py")
bridge = module_at("vn001_mcp_bridge", "vn001_local_mcp_readonly_bridge.py")
REV = "a" * 40


def fake_github(*, before=REV, after=REV, content=None, wrong_blob=False):
    actual = SOT.read_bytes() if content is None else content
    blob = hashlib.sha1(b"blob " + str(len(actual)).encode() + b"\0" + actual).hexdigest()
    payload = {
        "type": "file",
        "encoding": "base64",
        "path": auth.SOT_PATH,
        "sha": "b" * 40 if wrong_blob else blob,
        "content": base64.b64encode(actual).decode(),
    }
    state = {"reads": 0, "contents": 0}
    def getter(url):
        if url == auth.API + "/commits/main":
            state["reads"] += 1
            return {"sha": before if state["reads"] == 1 else after}
        if url == auth.API + "/contents/" + auth.SOT_PATH + "?ref=" + REV:
            state["contents"] += 1
            return payload
        raise AssertionError("wrong host/path")
    getter.state = state
    return getter


def request(**updates):
    obj = {
        "schema": bridge.SCHEMA, "task_id": bridge.TASK,
        "target": "saydi", "action": "inventory_v5_readonly",
        "root_key": "chapter2", "scope": "audio", "mode": "metadata",
        "hash_offset": 0, "expected_metadata_sha256": None,
        "expected_main_sha": REV,
    }
    obj.update(updates)
    return obj


class FreshAuthorityTests(unittest.TestCase):
    def test_real_sot_fixture_matches_exact_authority(self):
        get = fake_github()
        proof = auth.verify_current_main(expected_sha=REV, fetch_json=get)
        self.assertTrue(proof["verified_exact_main"])
        self.assertEqual(proof["active_task_id"], "SAYDI002-VN-001")
        self.assertEqual(proof["main_sha"], REV)
        self.assertEqual(get.state, {"reads": 2, "contents": 1})
        self.assertFalse(proof["production_dispatch_authorized"])
        self.assertFalse(proof["owner_start_verified"])

    def test_old_revision_fails_before_file_read(self):
        get = fake_github(before="b" * 40)
        with self.assertRaisesRegex(auth.VerificationHold, "MAIN_SHA_CHANGED"):
            auth.verify_current_main(expected_sha=REV, fetch_json=get)
        self.assertEqual(get.state["contents"], 0)

    def test_main_changes_mid_verification(self):
        with self.assertRaisesRegex(auth.VerificationHold, "MAIN_DIVERGED"):
            auth.verify_current_main(expected_sha=REV,
                                     fetch_json=fake_github(after="b" * 40))

    def test_tampered_blob_cannot_be_used(self):
        with self.assertRaisesRegex(auth.VerificationHold, "SOT_BLOB_HASH_MISMATCH"):
            auth.verify_current_main(expected_sha=REV, fetch_json=fake_github(wrong_blob=True))

    def test_missing_active_task_fails(self):
        altered = SOT.read_bytes().replace(
            b"| **SAYDI002-VN-001** | **IN_PROGRESS / active** |",
            b"| **SAYDI002-VN-001** | **DONE / closed** |",
            1,
        )
        self.assertNotEqual(altered, SOT.read_bytes())
        with self.assertRaisesRegex(auth.VerificationHold, "SOT_TASK_NOT_IN_PROGRESS"):
            auth.verify_current_main(expected_sha=REV, fetch_json=fake_github(content=altered))

    def test_no_network_unless_explicit_trusted_sot_transport(self):
        with self.assertRaisesRegex(auth.VerificationHold, "EXPECTED_MAIN_SHA_INVALID"):
            auth.verify_current_main(expected_sha="a" * 39, fetch_json=fake_github())

    def test_request_cannot_supply_verified_sot_proof(self):
        with self.assertRaises(TypeError):
            bridge.handle_inventory(request(), verified_sot={"verified_exact_main": True})

    def test_public_entrypoint_requires_auth_and_correct_machine(self):
        get = fake_github()
        denied = bridge.handle_inventory(request(), trusted_fetch_json=get)
        self.assertEqual(denied["reason"], "MCP_TRANSPORT_NOT_AUTHENTICATED")
        self.assertEqual(get.state["reads"], 0)
        with patch.object(bridge, "_is_h4", return_value=False):
            denied = bridge.handle_inventory(
                request(), transport_authenticated=True, trusted_fetch_json=get
            )
        self.assertEqual(denied["status"], "BLOCKED")
        self.assertFalse(denied["approved_to_start"])
        self.assertEqual(get.state["reads"], 0)

    def test_public_entrypoint_live_authority_then_readonly_local_inventory(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "segment.wav").write_bytes(b"synthetic-audio")
        roots = {"chapter2": {"path": str(root), "scope": "audio"}}
        get = fake_github()
        with (patch.object(bridge, "_is_h4", return_value=True),
              patch.object(bridge, "_root_is_allowed", return_value=True)):
            result = bridge.handle_inventory(
                request(), transport_authenticated=True, trusted_fetch_json=get,
                locally_approved_roots=roots,
            )
        self.assertEqual(result["status"], "READ_ONLY_RECEIPT_UNATTESTED")
        self.assertEqual(result["inventory"]["candidate_files"], 1)
        self.assertFalse(result["approved_to_dispatch"])
        self.assertFalse(result["owner_stop_changed"])
        self.assertFalse(result["task_completed"])
        self.assertEqual(get.state, {"reads": 2, "contents": 1})
        self.assertNotIn(str(root), json.dumps(result))

    def test_public_rejects_conflicting_revision_without_file_reads(self):
        get = fake_github(before="b" * 40)
        with patch.object(bridge, "_is_h4", return_value=True):
            result = bridge.handle_inventory(
                request(), transport_authenticated=True, trusted_fetch_json=get,
                locally_approved_roots={},
            )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "SOT_MAIN_AUTHORITY_UNVERIFIED")
        self.assertEqual(get.state["contents"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
