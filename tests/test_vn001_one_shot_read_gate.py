"""Fixture-only safety tests for SAYDI002-VN-001 one-shot read gate."""
import dataclasses
import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / "tools" / "saydi_tts" / "qc" / "vn001_one_shot_read_gate.py"
spec = importlib.util.spec_from_file_location("vn001_one_shot_read_gate", PATH)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

def witness(**overrides):
    data = dict(issue_id=123, approval_id=456, nonce="a"*32,
                main_sha="b"*40, stop_generation="stop-1",
                root_key="fixture_audio", scope="audio",
                owner_verified=True, approval_verified=True,
                exact_main_verified=True, transport_verified=True,
                root_verified=True, stop_generation_verified=True,
                owner_stop_engaged=True)
    data.update(overrides)
    return m.TrustedWitness(**data)

def metadata(**overrides):
    d = {"schema": m.INVENTORY_SCHEMA, "scope": "audio", "mode": "metadata",
         "candidate_files": 2, "candidate_bytes": 120,
         "metadata_fingerprint_sha256": "c"*64,
         "individual_hashes": [], "hash_batch_offset": 0}
    d.update(overrides)
    return d

class TestOneShot(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = Path(tmp.name) / "journal.db"
        self.reads = 0
    def run_gate(self, verify=None, read=None, journal=None):
        def normal_read():
            self.reads += 1
            return metadata()
        return m.guarded_read_once(
            trusted_verify=verify or (lambda:witness()),
            trusted_read_metadata=read or normal_read,
            trusted_journal_path=journal or self.db)
    def blocked(self, response, reason):
        self.assertEqual(response["status"],"BLOCKED")
        self.assertEqual(response["reason"], reason)
        self.assertNotIn("metadata", response)
        self.assertFalse(response["approved_to_start"])
        self.assertFalse(response["approved_to_dispatch"])

    def test_valid_fixture_is_non_authorizing(self):
        result = self.run_gate()
        self.assertEqual(result["status"], "SOURCE_ONLY_READ_UNATTESTED")
        self.assertEqual(result["metadata"]["candidate_files"], 2)
        self.assertEqual(self.reads, 1)
        self.assertFalse(result["field_accepted"])
        self.assertFalse(result["task_completed"])
    def test_nonce_replay_denied(self):
        self.run_gate()
        self.blocked(self.run_gate(), "APPROVAL_ALREADY_CONSUMED")
        self.assertEqual(self.reads, 1)
    def test_approval_replay_with_new_nonce_denied(self):
        self.run_gate()
        self.blocked(self.run_gate(verify=lambda:witness(nonce="d"*32)), "APPROVAL_ALREADY_CONSUMED")
        self.assertEqual(self.reads, 1)
    def test_stop_not_engaged_blocks_before_read(self):
        self.blocked(self.run_gate(verify=lambda:witness(owner_stop_engaged=False)), "OWNER_STOP_OR_ROOT_UNVERIFIED")
        self.assertEqual(self.reads, 0)
    def test_claimed_int_not_strict_boolean(self):
        self.blocked(self.run_gate(verify=lambda:witness(owner_verified=1)), "OWNER_STOP_OR_ROOT_UNVERIFIED")
    def test_unverified_main_blocks(self):
        self.blocked(self.run_gate(verify=lambda:witness(exact_main_verified=False)), "OWNER_STOP_OR_ROOT_UNVERIFIED")
    def test_invalid_nonce_blocks(self):
        self.blocked(self.run_gate(verify=lambda:witness(nonce="bad")), "IDENTITY_INVALID")
        self.assertEqual(self.reads,0)
    def test_witness_changed_immediately_before_scan(self):
        n=[0]
        def verify():
            n[0]+=1
            return witness(stop_generation="stop-2") if n[0]==2 else witness()
        self.blocked(self.run_gate(verify=verify), "WITNESS_CHANGED")
        self.assertEqual(self.reads,0)
    def test_witness_changed_during_scan_blocks_receipt_and_replay(self):
        n=[0]
        def verify():
            n[0]+=1
            return witness(stop_generation="stop-2") if n[0]==3 else witness()
        self.blocked(self.run_gate(verify=verify), "WITNESS_CHANGED")
        self.assertEqual(self.reads,1)
        self.blocked(self.run_gate(), "APPROVAL_ALREADY_CONSUMED")
    def test_stop_revoked_after_read_blocks_receipt(self):
        n=[0]
        def verify():
            n[0]+=1
            return witness(owner_stop_engaged=False) if n[0]==3 else witness()
        self.blocked(self.run_gate(verify=verify), "OWNER_STOP_OR_ROOT_UNVERIFIED")
        self.assertEqual(self.reads,1)
    def test_modified_journal_mid_scan_blocks_receipt(self):
        def tamper():
            db = sqlite3.connect(self.db)
            try:
                db.execute("UPDATE used SET state='ALTERED'")
                db.commit()
            finally:
                db.close()
            return metadata()
        self.blocked(self.run_gate(read=tamper), "JOURNAL_CHANGED_DURING_READ")
    def test_untrusted_raw_path_is_not_returned(self):
        result=self.run_gate(read=lambda:metadata(file_path="C:\\PRIVATE\\audio.wav",book_text="secret"))
        self.assertEqual(result["status"], "SOURCE_ONLY_READ_UNATTESTED")
        self.assertNotIn("file_path",str(result))
        self.assertNotIn("secret",str(result))
    def test_failed_scanner_does_not_leak_exception(self):
        def fail():
            raise RuntimeError("secret private file path")
        self.blocked(self.run_gate(read=fail), "UNQUALIFIED_HOST_OR_READ_FAILURE")
    def test_custom_gatehold_from_scanner_cannot_leak_path(self):
        def malicious_reader():
            raise m.GateHold("C:\\PRIVATE\\sensitive_book.txt")
        result = self.run_gate(read=malicious_reader)
        self.blocked(result, "UNQUALIFIED_HOST_OR_READ_FAILURE")
        self.assertNotIn("sensitive_book", str(result))

    def test_custom_gatehold_from_owner_verifier_cannot_leak_path(self):
        def malicious_verify():
            raise m.GateHold("C:\\PRIVATE\\approval.json")
        result = self.run_gate(verify=malicious_verify)
        self.blocked(result, "UNQUALIFIED_HOST_OR_READ_FAILURE")
        self.assertNotIn("approval.json", str(result))
        self.assertEqual(self.reads, 0)

    def test_gatehold_matching_internal_reason_is_sanitized_from_callbacks(self):
        def malicious_reader():
            raise m.GateHold("APPROVAL_ALREADY_CONSUMED")
        self.blocked(self.run_gate(read=malicious_reader),
                     "UNQUALIFIED_HOST_OR_READ_FAILURE")

    def test_wrong_scope_blocks(self):
        self.blocked(self.run_gate(read=lambda:metadata(scope="model")), "INVENTORY_RECEIPT_INVALID")
    def test_forged_hashes_block_metadata_mode(self):
        self.blocked(self.run_gate(read=lambda:metadata(individual_hashes=[{"raw":"secret"}])), "INVENTORY_RECEIPT_INVALID")
    def test_disallowed_journal_parent_blocks(self):
        self.blocked(self.run_gate(journal=self.db.parent/"missing"/"journal.db"), "JOURNAL_PATH_UNQUALIFIED")
    def test_forged_verifier_dict_blocks(self):
        self.blocked(self.run_gate(verify=lambda:{"owner_verified":True}), "TRUSTED_WITNESS_MISSING")
    def test_metadata_failure_still_consumes_one_shot(self):
        self.blocked(self.run_gate(read=lambda:metadata(candidate_files=-1)), "INVENTORY_RECEIPT_INVALID")
        self.blocked(self.run_gate(), "APPROVAL_ALREADY_CONSUMED")

if __name__ == "__main__":
    unittest.main()
