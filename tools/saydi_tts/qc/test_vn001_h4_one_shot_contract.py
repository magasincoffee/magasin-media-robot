"""Pure synthetic H4 STOP/Owner/replay contract tests; NEVER access H4 files."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

p = Path(__file__).with_name("vn001_h4_one_shot_contract.py")
spec = importlib.util.spec_from_file_location("saydi_vn001_contract", p)
sut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sut)
SHA = "a" * 40
GEN = "c" * 64
NONCE = hashlib.sha256(("1" * 32).encode("ascii")).hexdigest()


def fixtures():
    owner = {
        "schema": sut.OWNER_SCHEMA, "task_id": sut.TASK,
        "status": "OWNER_INTENT_MATCHED_NON_EXECUTABLE",
        "issue_number": 42, "issue_id": 789123,
        "approval_comment_id": 567890,
        "issue_body_sha256": "b" * 64,
        "approval_nonce_sha256": NONCE,
        "main_sha_observed": SHA, "owner_claims_match": True,
        "github_live_https_observed": True,
        "owner_one_shot_consumed": False,
        "owner_issue_approval_verified_for_h4": False,
        "h4_stop_generation_verified": False,
        "h4_root_identity_verified": False,
        "replay_guard_verified": False, "can_read_v5": False,
        "approved_to_dispatch": False, "approved_to_start": False,
        "worker_started": False, "task_completed": False,
        "production_modified": False,
    }
    stop = {
        "schema": sut.WITNESS_SCHEMA, "task_id": sut.TASK,
        "host": sut.HOST, "expected_main_sha": SHA,
        "stop_present_before": True, "stop_present_after": True,
        "autostart_disabled_before": True, "autostart_disabled_after": True,
        "owner_generation_before": GEN, "owner_generation_after": GEN,
        "worker_started": False, "production_modified": False,
    }
    ledger = {"schema": sut.LEDGER_SCHEMA, "records": []}
    return owner, stop, ledger


class TestOneShotContract(unittest.TestCase):
    def setUp(self):
        self.owner, self.stop, self.ledger = fixtures()

    def inspect(self, *, owner=None, stop=None, ledger=None, sha=SHA):
        return sut.inspect_one_shot_contract(
            expected_main_sha=sha,
            owner_intent=self.owner if owner is None else owner,
            stop_witness=self.stop if stop is None else stop,
            ledger_snapshot=self.ledger if ledger is None else ledger,
        )

    def assert_hold(self, code, **kwargs):
        result = self.inspect(**kwargs)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], code)
        self.assertFalse(result["can_read_v5"])

    def test_all_synthetic_gates_still_never_authorize_field_access(self):
        r = self.inspect()
        self.assertEqual(r["status"], "SYNTHETIC_CONTRACT_MATCHED_UNATTESTED")
        self.assertTrue(r["synthetic_contract_consistent"])
        for key in (
            "owner_issue_approval_verified_for_h4", "replay_guard_verified",
            "h4_stop_generation_verified", "h4_root_identity_verified",
            "real_v5_inventory_verified", "one_shot_consumed",
            "can_read_v5", "approved_to_dispatch", "approved_to_start",
            "worker_started", "task_completed", "production_modified",
        ):
            self.assertFalse(r[key], key)
        self.assertNotIn(NONCE, json.dumps(r))

    def test_refuse_bad_main_commit(self):
        self.assert_hold("EXPECTED_MAIN_SHA_INVALID", sha="main")
        o = dict(self.owner, main_sha_observed="d" * 40)
        self.assert_hold("OWNER_LIVE_INTENT_NOT_PROVEN", owner=o)

    def test_refuse_bogus_or_missing_owner_proof(self):
        for key, value in (
            ("owner_claims_match", False), ("github_live_https_observed", False),
            ("owner_issue_approval_verified_for_h4", True),
            ("owner_one_shot_consumed", True), ("replay_guard_verified", True),
            ("h4_stop_generation_verified", True), ("can_read_v5", True),
            ("approval_nonce_sha256", "secret"), ("approval_comment_id", 0),
            ("issue_number", True), ("worker_started", True),
            ("worker_started", None), ("task_completed", True),
            ("task_completed", "false"), ("production_modified", True),
        ):
            with self.subTest(key=key):
                o = copy.deepcopy(self.owner)
                o[key] = value
                self.assert_hold("OWNER_LIVE_INTENT_NOT_PROVEN", owner=o)
        for key in ("approval_nonce_sha256", "issue_body_sha256",
                    "owner_claims_match", "worker_started", "task_completed"):
            with self.subTest(missing=key):
                o = copy.deepcopy(self.owner)
                del o[key]
                self.assert_hold("OWNER_LIVE_INTENT_NOT_PROVEN", owner=o)

    def test_producer_owner_schema_never_tolerates_unexpected_fields(self):
        o = dict(self.owner, skip_worker_check=True)
        self.assert_hold("OWNER_LIVE_INTENT_NOT_PROVEN", owner=o)

    def test_stop_autostart_generation_and_host_fail_closed(self):
        for key, value in (
            ("host", "OTHER-PC"), ("stop_present_before", False),
            ("stop_present_after", False), ("autostart_disabled_before", False),
            ("autostart_disabled_after", False),
            ("owner_generation_before", "d" * 64),
            ("owner_generation_after", "no-generation"),
            ("worker_started", True), ("production_modified", True),
            ("stop_present_after", "true"),
        ):
            with self.subTest(key=key, value=value):
                witness = copy.deepcopy(self.stop)
                witness[key] = value
                self.assert_hold("H4_STOP_GENERATION_UNATTESTED", stop=witness)
        witness = copy.deepcopy(self.stop)
        del witness["owner_generation_after"]
        self.assert_hold("H4_STOP_GENERATION_UNATTESTED", stop=witness)

    def test_seen_reservation_consumption_and_hold_state_block_replay(self):
        for state in ("RESERVED", "CONSUMED", "HOLD"):
            ledger = {"schema": sut.LEDGER_SCHEMA,
                      "records": [{"nonce_sha256": NONCE, "state": state}]}
            with self.subTest(state=state):
                self.assert_hold("OWNER_ONE_SHOT_ALREADY_SEEN", ledger=ledger)

    def test_corrupt_duplicate_or_untrusted_ledger_blocks(self):
        self.assert_hold("REPLAY_LEDGER_UNTRUSTED", ledger={})
        self.assert_hold("REPLAY_LEDGER_UNTRUSTED",
                         ledger={"schema": sut.LEDGER_SCHEMA, "records": None})
        self.assert_hold("REPLAY_LEDGER_UNTRUSTED",
                         ledger={"schema": sut.LEDGER_SCHEMA,
                                 "records": [{"nonce_sha256": "bad", "state": "CONSUMED"}]})
        self.assert_hold("REPLAY_LEDGER_UNTRUSTED",
                         ledger={"schema": sut.LEDGER_SCHEMA,
                                 "records": [{"nonce_sha256": "e" * 64, "state": "RELEASED"}]})
        ledger = {"schema": sut.LEDGER_SCHEMA, "records": [
            {"nonce_sha256": "e" * 64, "state": "CONSUMED"},
            {"nonce_sha256": "e" * 64, "state": "RESERVED"},
        ]}
        self.assert_hold("REPLAY_LEDGER_DUPLICATE_RECORD", ledger=ledger)

    def test_other_nonce_in_fixture_does_not_grant_authority(self):
        ledger = {"schema": sut.LEDGER_SCHEMA, "records": [
            {"nonce_sha256": "e" * 64, "state": "CONSUMED"},
        ]}
        result = self.inspect(ledger=ledger)
        self.assertEqual(result["status"], "SYNTHETIC_CONTRACT_MATCHED_UNATTESTED")
        self.assertFalse(result["replay_guard_verified"])
        self.assertFalse(result["one_shot_consumed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
