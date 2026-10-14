"""SAYDI Owner Issue/comment proof: synthetic HTTPS snapshots only."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

path = Path(__file__).with_name("vn001_github_relay_owner_evidence.py")
spec = importlib.util.spec_from_file_location("vn001_owner_evidence", path)
sut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sut)
SHA = "a" * 40
I = 42
ID = 789123
COMMENT = 567890
ISSUE_URL = sut.API + "/issues/" + str(I)
COMMENT_URL = sut.API + "/issues/comments/" + str(COMMENT)
MAIN_URL = sut.API + "/git/ref/heads/main"


def snapshots():
    request = {
        "schema": "MAGASIN_SAYDI_VN001_GITHUB_RELAY_REQUEST_V1",
        "task_id": sut.TASK, "target": "saydi",
        "action": "inventory_v5_readonly", "root_key": "chapter2",
        "scope": "audio", "mode": "metadata", "expected_main_sha": SHA,
    }
    body = json.dumps(request, sort_keys=True)
    issue = {
        "id": ID, "number": I, "state": "open",
        "repository_url": sut.API, "html_url":
        "https://github.com/magasincoffee/magasin-media-robot/issues/" + str(I),
        "user": {"id": sut.OWNER_ACCOUNT_ID,
                 "login": sut.OWNER_LOGIN, "type": "User"},
        "body": body,
        "created_at": "2026-10-14T08:00:00Z",
        "updated_at": "2026-10-14T08:00:00Z",
    }
    approval = {
        "id": COMMENT,
        "issue_url": ISSUE_URL,
        "html_url": issue["html_url"] + "#issuecomment-" + str(COMMENT),
        "user": copy.deepcopy(issue["user"]),
        "created_at": "2026-10-14T08:05:00Z",
        "updated_at": "2026-10-14T08:05:00Z",
        "body": json.dumps({
            "schema": sut.APPROVAL_SCHEMA, "task_id": sut.TASK,
            "action": "inventory_v5_readonly", "issue_number": I,
            "issue_id": ID, "expected_main_sha": SHA,
            "issue_body_sha256": hashlib.sha256(body.encode()).hexdigest(),
            "one_shot_nonce": "1" * 32, "read_only_metadata_only": True,
        }, sort_keys=True),
    }
    return issue, approval


def read_fixture(issue, approval, *, tail_issue=None, tail_approval=None, tail_main=None):
    ordered = [
        (MAIN_URL, {"ref": "refs/heads/main", "object": {"type": "commit", "sha": SHA}}),
        (ISSUE_URL, issue),
        (COMMENT_URL, approval),
        (ISSUE_URL, copy.deepcopy(issue) if tail_issue is None else tail_issue),
        (COMMENT_URL, copy.deepcopy(approval) if tail_approval is None else tail_approval),
        (MAIN_URL, {"ref": "refs/heads/main", "object": {"type": "commit", "sha": SHA}}
         if tail_main is None else tail_main),
    ]
    calls = []

    def getter(url):
        index = len(calls)
        if index >= len(ordered) or ordered[index][0] != url:
            raise AssertionError("UNEXPECTED_NETWORK_ENDPOINT_OR_ORDER")
        calls.append(url)
        return copy.deepcopy(ordered[index][1])

    return getter, calls


class OwnerEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.issue, self.approval = snapshots()

    def check_hold(self, code, issue=None, approval=None,
                   tail_issue=None, tail_approval=None, tail_main=None):
        get, calls = read_fixture(
            self.issue if issue is None else issue,
            self.approval if approval is None else approval,
            tail_issue=tail_issue, tail_approval=tail_approval,
            tail_main=tail_main,
        )
        with self.assertRaisesRegex(sut.EvidenceHold, "^" + code + "$"):
            sut.observe_owner_readonly_intent(
                issue_number=I, approval_comment_id=COMMENT,
                expected_main_sha=SHA, fetch_json=get,
            )
        self.assertGreaterEqual(len(calls), 2)

    def test_consistent_owner_intent_never_authorizes_real_h4(self):
        getter, calls = read_fixture(self.issue, self.approval)
        result = sut.observe_owner_readonly_intent(
            issue_number=I, approval_comment_id=COMMENT,
            expected_main_sha=SHA, fetch_json=getter,
        )
        self.assertEqual(calls, [MAIN_URL, ISSUE_URL, COMMENT_URL,
                                 ISSUE_URL, COMMENT_URL, MAIN_URL])
        self.assertEqual(result["status"], "OWNER_INTENT_MATCHED_NON_EXECUTABLE")
        self.assertTrue(result["owner_claims_match"])
        self.assertEqual(result["issue_body_sha256"],
                         hashlib.sha256(self.issue["body"].encode()).hexdigest())
        for key in ("github_live_https_observed", "owner_one_shot_consumed",
                    "owner_issue_approval_verified_for_h4",
                    "h4_stop_generation_verified", "h4_root_identity_verified",
                    "replay_guard_verified", "can_read_v5",
                    "approved_to_dispatch", "approved_to_start",
                    "worker_started", "task_completed", "production_modified"):
            self.assertFalse(result[key], key)
        self.assertNotIn("chapter2", json.dumps(result))
        self.assertNotIn(self.issue["body"], json.dumps(result))

    def test_invalid_arguments_rejected_before_any_fetch(self):
        for invalid in (0, -1, True, "1", None, 2147483648):
            with self.subTest(issue_number=invalid):
                with self.assertRaisesRegex(sut.EvidenceHold, "ISSUE_APPROVAL_ARGUMENTS_INVALID"):
                    sut.observe_owner_readonly_intent(
                        issue_number=invalid, approval_comment_id=COMMENT,
                        expected_main_sha=SHA, fetch_json=lambda _: self.fail("network touched"),
                    )
        with self.assertRaisesRegex(sut.EvidenceHold, "ISSUE_APPROVAL_ARGUMENTS_INVALID"):
            sut.observe_owner_readonly_intent(issue_number=I, approval_comment_id=True,
                                               expected_main_sha=SHA)
        with self.assertRaisesRegex(sut.EvidenceHold, "ISSUE_APPROVAL_ARGUMENTS_INVALID"):
            sut.observe_owner_readonly_intent(issue_number=I, approval_comment_id=COMMENT,
                                               expected_main_sha="main")

    def test_issue_author_mismatch_and_edited_request(self):
        issue = copy.deepcopy(self.issue)
        issue["user"]["id"] = 1
        self.check_hold("ISSUE_PREFLIGHT_NOT_QUALIFIED", issue=issue)
        issue = copy.deepcopy(self.issue)
        issue["body"] = issue["body"].replace("chapter2", "../secret")
        self.check_hold("ISSUE_PREFLIGHT_NOT_QUALIFIED", issue=issue)
        changed = copy.deepcopy(self.issue)
        changed["body"] += " "
        self.check_hold("ISSUE_CHANGED_DURING_OBSERVATION", tail_issue=changed)

    def test_main_changes_mid_approval_observation(self):
        self.check_hold("GITHUB_MAIN_DRIFT", tail_main={
            "ref": "refs/heads/main", "object": {"type": "commit", "sha": "b" * 40}
        })
        self.check_hold("GITHUB_MAIN_DRIFT", tail_main={"sha": SHA})

    def test_approval_mutated_or_deleted_during_read_is_hold(self):
        modified = copy.deepcopy(self.approval)
        modified["body"] += " "
        self.check_hold("APPROVAL_CHANGED_DURING_OBSERVATION",
                        tail_approval=modified)
        modified = copy.deepcopy(self.approval)
        modified["updated_at"] = "2026-10-14T08:06:00Z"
        self.check_hold("APPROVAL_CHANGED_DURING_OBSERVATION",
                        tail_approval=modified)
        self.check_hold("APPROVAL_CHANGED_DURING_OBSERVATION",
                        tail_approval={"error": "not found"})
        self.check_hold("APPROVAL_API_SHAPE_INVALID",
                        tail_approval="GONE")

    def test_approval_must_have_independent_owner_and_issue_link(self):
        bad = copy.deepcopy(self.approval)
        bad["user"]["id"] = 1
        self.check_hold("APPROVAL_OWNER_OR_ISSUE_MISMATCH", approval=bad)
        bad = copy.deepcopy(self.approval)
        bad["issue_url"] = sut.API + "/issues/1"
        self.check_hold("APPROVAL_OWNER_OR_ISSUE_MISMATCH", approval=bad)
        bad = copy.deepcopy(self.approval)
        bad["html_url"] += "/edited"
        self.check_hold("APPROVAL_OWNER_OR_ISSUE_MISMATCH", approval=bad)
        bad = copy.deepcopy(self.approval)
        bad["id"] = True
        self.check_hold("APPROVAL_OWNER_OR_ISSUE_MISMATCH", approval=bad)

    def test_approval_cannot_be_edited_or_predate_request(self):
        for created, updated in (
            ("2026-10-14T07:59:00Z", "2026-10-14T07:59:00Z"),
            ("2026-10-14T08:05:00Z", "2026-10-14T08:06:00Z"),
            ("not-a-date", "not-a-date"),
        ):
            bad = copy.deepcopy(self.approval)
            bad["created_at"], bad["updated_at"] = created, updated
            error = ("GITHUB_TIMESTAMP_INVALID" if created == "not-a-date"
                     else "APPROVAL_TIMESTAMP_OR_EDIT_INVALID")
            self.check_hold(error, approval=bad)

    def test_approval_binds_hash_issue_id_main_nonce_and_readonly(self):
        for field, value in (
            ("issue_id", ID + 1), ("issue_id", True),
            ("issue_number", 1), ("expected_main_sha", "b" * 40),
            ("issue_body_sha256", "f" * 64), ("one_shot_nonce", "NO"),
            ("one_shot_nonce", "g" * 32), ("read_only_metadata_only", False),
            ("read_only_metadata_only", 1), ("action", "execute_task"),
            ("task_id", "SAYDI002-VN-002"),
        ):
            with self.subTest(field=field, value=value):
                bad = copy.deepcopy(self.approval)
                parsed = json.loads(bad["body"])
                parsed[field] = value
                bad["body"] = json.dumps(parsed)
                self.check_hold("APPROVAL_INTENT_NOT_BOUND", approval=bad)

    def test_duplicate_keys_and_oversize_approval_rejected(self):
        bad = copy.deepcopy(self.approval)
        bad["body"] = '{"schema": "x", "schema": "y"}'
        self.check_hold("APPROVAL_BODY_INVALID", approval=bad)
        bad = copy.deepcopy(self.approval)
        bad["body"] = "x" * 1025
        self.check_hold("APPROVAL_BODY_INVALID", approval=bad)
        bad = copy.deepcopy(self.approval)
        bad["body"] = chr(0xD800)
        self.check_hold("APPROVAL_BODY_INVALID", approval=bad)

    def test_no_ad_hoc_network_endpoint_accepted(self):
        with self.assertRaisesRegex(sut.EvidenceHold, "GITHUB_ENDPOINT_NOT_ALLOWED"):
            sut._read_live_json("https://evil.example.com/anything")
        with self.assertRaisesRegex(sut.EvidenceHold, "GITHUB_ENDPOINT_NOT_ALLOWED"):
            sut._read_live_json(sut.API + "/issues/1/comments")

    def test_api_unavailable_redacted_and_fails_closed(self):
        def fail(_):
            raise RuntimeError("PRIVATE-TOKEN-DO-NOT-PRINT")
        with self.assertRaises(sut.EvidenceHold) as err:
            sut.observe_owner_readonly_intent(
                issue_number=I, approval_comment_id=COMMENT,
                expected_main_sha=SHA, fetch_json=fail,
            )
        self.assertEqual(str(err.exception), "GITHUB_FETCH_UNAVAILABLE")
        self.assertNotIn("PRIVATE-TOKEN", str(err.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
