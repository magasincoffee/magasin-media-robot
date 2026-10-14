"""Synthetic-only GitHub Issue screening, no network, files or H4 worker."""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

path = Path(__file__).with_name("vn001_github_relay_preflight.py")
spec = importlib.util.spec_from_file_location("vn001_relay_preflight", path)
sut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sut)
SHA = "a" * 40


def request(**overrides):
    body = {
        "schema": sut.SCHEMA, "task_id": sut.TASK,
        "target": "saydi", "action": "inventory_v5_readonly",
        "scope": "audio", "root_key": "chapter2",
        "mode": "metadata", "expected_main_sha": SHA,
    }
    body.update(overrides)
    return body


def issue(**overrides):
    record = {
        "id": 999891, "number": 345, "repository_url": sut.REPO_API,
        "html_url": "https://github.com/magasincoffee/magasin-media-robot/issues/345",
        "state": "open",
        "user": {"id": sut.OWNER_ACCOUNT_ID, "login": sut.OWNER_LOGIN, "type": "User"},
        "body": json.dumps(request(), sort_keys=True),
    }
    record.update(overrides)
    return record


class RelayUntrustedTests(unittest.TestCase):
    def check_hold(self, inp, reason, sha=SHA):
        result = sut.inspect_untrusted_issue(inp, expected_main_sha=sha)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], reason)
        self.assertFalse(result["request_shape_valid"])
        self.assertFalse(result["approved_to_dispatch"])
        self.assertFalse(result["can_read_v5"])

    def test_valid_shape_is_never_execution_authority(self):
        result = sut.inspect_untrusted_issue(issue(), expected_main_sha=SHA)
        self.assertEqual(result["status"], "PREFLIGHT_SHAPE_ONLY_UNATTESTED")
        self.assertTrue(result["request_shape_valid"])
        for field in ("github_identity_authenticated", "owner_issue_approval_verified",
                      "replay_and_stop_verified", "sot_main_verified",
                      "h4_mcp_transport_qualified", "can_read_v5",
                      "approved_to_dispatch", "approved_to_start",
                      "task_completed", "production_modified"):
            self.assertFalse(result[field], field)
        self.assertNotIn("chapter2", json.dumps(result))

    def test_reject_foreign_repo_wrong_owner_and_spoofed_id(self):
        self.check_hold(issue(repository_url="https://api.github.com/repos/other/repo"),
                        "ISSUE_REPOSITORY_INVALID")
        other = issue()
        other["user"]["id"] = 111
        self.check_hold(other, "ISSUE_CLAIMED_OWNER_MISMATCH")
        other = issue()
        other["user"]["id"] = True
        self.check_hold(other, "ISSUE_CLAIMED_OWNER_MISMATCH")
        other = issue()
        other["user"]["login"] = "unknown"
        self.check_hold(other, "ISSUE_CLAIMED_OWNER_MISMATCH")

    def test_reject_issue_crosslink_and_pr(self):
        self.check_hold(issue(state="closed"), "ISSUE_NOT_OPEN_REQUEST")
        self.check_hold(issue(pull_request={}), "ISSUE_NOT_OPEN_REQUEST")
        self.check_hold(issue(number=346), "ISSUE_URL_NUMBER_MISMATCH")
        self.check_hold(issue(html_url="https://evil.example.com/issues/345"),
                        "ISSUE_URL_INVALID")
        self.check_hold(issue(id=0), "ISSUE_NOT_OPEN_REQUEST")
        self.check_hold(issue(number=True), "ISSUE_NOT_OPEN_REQUEST")

    def test_reject_extra_script_private_path_and_wrong_task(self):
        for body in (
            request(cmd="powershell"), request(action="execute_task"),
            request(action="render_qc"), request(task_id="SAYDI002-VN-002"),
            request(root_key="../secret"), request(root_key=r"C:\SAYDI"),
            request(scope="production"), request(mode="hash"),
            request(expected_main_sha="b" * 40), request(target="supervisor"),
        ):
            with self.subTest(body=body):
                expected = ("ISSUE_REQUEST_FIELDS_INVALID" if "cmd" in body
                            else "ISSUE_REQUEST_NOT_ALLOWLISTED")
                self.check_hold(issue(body=json.dumps(body)), expected)

    def test_malformed_or_oversized_body_blocks_without_leakage(self):
        self.check_hold(issue(body="not-json secret-token-123"), "ISSUE_BODY_INVALID")
        self.check_hold(issue(body=chr(0xD800)), "ISSUE_BODY_INVALID")
        self.check_hold(issue(body=chr(0xDFFF)), "ISSUE_BODY_INVALID")
        self.check_hold(issue(body="x" * (sut.MAX_BODY_BYTES + 1)),
                        "ISSUE_BODY_INVALID")
        self.check_hold(issue(body="[]"), "ISSUE_REQUEST_FIELDS_INVALID")
        self.check_hold(issue(body=json.dumps(request(scope=["audio"]))),
                        "ISSUE_REQUEST_NOT_ALLOWLISTED")

    def test_duplicate_json_keys_fail_closed(self):
        ordinary = json.dumps(request())
        duplicated = ordinary.replace('"scope": "audio"', '"scope": "audio", "scope": "audio"')
        self.assertNotEqual(ordinary, duplicated)
        self.check_hold(issue(body=duplicated), "ISSUE_BODY_INVALID")

    def test_missing_main_and_missing_fields(self):
        self.check_hold(issue(), "MAIN_COMMIT_UNVERIFIED", sha="wrong")
        req = request()
        del req["root_key"]
        self.check_hold(issue(body=json.dumps(req)), "ISSUE_REQUEST_FIELDS_INVALID")
        self.check_hold(None, "ISSUE_REPOSITORY_INVALID")

    def test_forged_issue_snapshot_never_authorized(self):
        fake = issue()
        fake["approved_to_dispatch"] = True
        fake["user"]["login"] = sut.OWNER_LOGIN
        result = sut.inspect_untrusted_issue(fake, expected_main_sha=SHA)
        self.assertTrue(result["request_shape_valid"])
        self.assertFalse(result["approved_to_dispatch"])
        self.assertFalse(result["github_identity_authenticated"])
        self.assertFalse(result["owner_issue_approval_verified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
