"""Source-only fixture tests: never touch H4 or SAYDI private assets."""
import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

P = Path(__file__).resolve().parents[1] / "tools/saydi_tts/qc/vn001_v6_project_grant_gate.py"
spec = importlib.util.spec_from_file_location("vn001_v6_project_grant_gate", P)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
NOW = 1792100000


def proof(**changes):
    args = dict(grant_id="a"*32, owner_id=191064507,
        main_sha="b"*40, stop_generation="STOP-42", stop_authority=m.STOP_AUTHORITY, root_key="v5_checkpoint",
        scope="checkpoint", expires_epoch=NOW+20000, max_operations=3,
        owner_identity_verified=True, project_grant_verified=True,
        main_verified=True, transport_verified=True, root_verified=True,
        stop_generation_verified=True, saydi_stop_engaged=True,
        grant_not_revoked=True)
    args.update(changes)
    return m.HostAttestation(**args)


def metadata(**changes):
    args=dict(scope="checkpoint", candidate_files=4, candidate_bytes=950,
              metadata_fingerprint_sha256="c"*64)
    args.update(changes)
    return args


class TestProjectGrant(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.journal=Path(t.name)/"task-grant.sqlite"
        self.calls=0

    def run_gate(self, index=0, op_id=None, verify=None, reader=None, journal=None,
                 now=None):
        def read():
            self.calls+=1
            return metadata()
        return m.read_project_grant_child(
            host_verify=verify or (lambda:proof()),
            host_read_metadata=reader or read,
            host_journal=journal or self.journal,
            child_index=index, child_id=op_id or f"{index+1:032x}",
            host_now_epoch=now or (lambda:NOW))

    def blocked(self, response, reason):
        self.assertEqual(response["status"],"BLOCKED")
        self.assertEqual(response["reason"],reason)
        self.assertNotIn("metadata",response)
        self.assertFalse(response["approved_to_start"])
        self.assertFalse(response["field_accepted"])

    def test_one_grant_authorizes_ordered_multiple_fixture_children(self):
        a=self.run_gate(0)
        b=self.run_gate(1)
        c=self.run_gate(2)
        self.assertEqual([a["status"],b["status"],c["status"]],
                         ["SOURCE_ONLY_CHILD_ACCEPTED_UNATTESTED"]*3)
        self.assertEqual(self.calls,3)
        self.assertTrue(a["grant_reusable_for_remaining_children"])
        self.assertTrue(b["grant_reusable_for_remaining_children"])
        self.assertFalse(c["grant_reusable_for_remaining_children"])
        self.assertTrue(c["child_consumed"])
        self.assertFalse(c["task_completed"])

    def test_duplicate_same_child_blocked(self):
        self.run_gate()
        replay=self.run_gate()
        self.blocked(replay, "CHILD_OUT_OF_ORDER_OR_REPLAY")
        self.assertFalse(replay["child_consumed"])
        self.assertEqual(self.calls,1)

    def test_skipping_child_is_blocked(self):
        self.blocked(self.run_gate(1), "CHILD_OUT_OF_ORDER_OR_REPLAY")
        self.assertEqual(self.calls,0)

    def test_reusing_child_id_with_different_seq_is_blocked(self):
        self.run_gate(0,op_id="d"*32)
        self.blocked(self.run_gate(1,op_id="d"*32), "CHILD_REPLAY_BLOCKED")
        self.assertEqual(self.calls,1)

    def test_exceed_max_op_count_blocks(self):
        self.run_gate(0)
        self.run_gate(1)
        self.run_gate(2)
        self.blocked(self.run_gate(3), "CHILD_SCOPE_EXCEEDED")

    def test_same_project_grant_supports_scoped_checkpoint_audio_model(self):
        self.assertEqual(self.run_gate(0)["status"], "SOURCE_ONLY_CHILD_ACCEPTED_UNATTESTED")
        def audio():
            return metadata(scope="audio")
        next_result=self.run_gate(1,verify=lambda:proof(root_key="v5_audio",scope="audio"),
                                  reader=audio)
        self.assertEqual(next_result["status"], "SOURCE_ONLY_CHILD_ACCEPTED_UNATTESTED")
        self.assertEqual(next_result["metadata"]["scope"],"audio")
        final=self.run_gate(2,verify=lambda:proof(root_key="v5_model",scope="model"),
                            reader=lambda:metadata(scope="model"))
        self.assertEqual(final["status"], "SOURCE_ONLY_CHILD_ACCEPTED_UNATTESTED")

    def test_root_changed_inside_child_suppresses_all_receipt(self):
        n=[0]
        def verify():
            n[0]+=1
            return proof(root_key="v5_audio",scope="audio") if n[0]==3 else proof()
        self.blocked(self.run_gate(verify=verify),"STOP_OR_GRANT_CHANGED")
        self.assertEqual(self.calls,1)

    def test_local_saydi_stop_not_engaged_still_allows_scoped_readonly(self):
        r=self.run_gate(verify=lambda:proof(saydi_stop_engaged=False))
        self.assertEqual(r["status"], "SOURCE_ONLY_CHILD_ACCEPTED_UNATTESTED")
        self.assertFalse(r["approved_to_start"])
        self.assertFalse(r["approved_to_dispatch"])
        self.assertEqual(self.calls,1)

    def test_supervisor_stop_origin_cannot_authorize_saydi_inventory(self):
        r=self.run_gate(verify=lambda:proof(stop_authority="SUPERVISOR"))
        self.blocked(r, "GRANT_SCOPE_OR_EXPIRY_INVALID")
        self.assertEqual(self.calls,0)

    def test_missing_saydi_stop_origin_fails_closed(self):
        r=self.run_gate(verify=lambda:proof(stop_authority=""))
        self.blocked(r, "GRANT_SCOPE_OR_EXPIRY_INVALID")
        self.assertEqual(self.calls,0)

    def test_fake_saydi_stop_flag_is_rejected(self):
        r=self.run_gate(verify=lambda:proof(saydi_stop_engaged=1))
        self.blocked(r, "GRANT_SCOPE_OR_EXPIRY_INVALID")
        self.assertEqual(self.calls,0)

    def test_single_operation_grant_is_exhausted_after_success(self):
        single=lambda:proof(max_operations=1)
        done=self.run_gate(0,verify=single)
        self.assertEqual(done["status"],"SOURCE_ONLY_CHILD_ACCEPTED_UNATTESTED")
        self.assertFalse(done["grant_reusable_for_remaining_children"])
        self.assertTrue(done["child_consumed"])
        next_child=self.run_gate(1,verify=single)
        self.blocked(next_child,"CHILD_SCOPE_EXCEEDED")
        self.assertFalse(next_child["child_consumed"])

    def test_stop_engaged_allows_read_only_and_never_start(self):
        result=self.run_gate()
        self.assertEqual(result["status"],"SOURCE_ONLY_CHILD_ACCEPTED_UNATTESTED")
        self.assertFalse(result["approved_to_dispatch"])
        self.assertFalse(result["approved_to_start"])

    def test_revoked_after_read_suppresses_entire_receipt(self):
        n=[0]
        def verify():
            n[0]+=1
            return proof(grant_not_revoked=False) if n[0]==3 else proof()
        rejected=self.run_gate(verify=verify)
        self.blocked(rejected,"GRANT_STOP_OR_TRANSPORT_UNVERIFIED")
        self.assertTrue(rejected["child_consumed"])
        self.assertEqual(self.calls,1)
        self.blocked(self.run_gate(),"CHILD_OUT_OF_ORDER_OR_REPLAY")

    def test_stop_gen_changed_before_read_consumes_and_holds(self):
        n=[0]
        def verify():
            n[0]+=1
            return proof(stop_generation="STOP-43") if n[0]==2 else proof()
        self.blocked(self.run_gate(verify=verify),"STOP_OR_GRANT_CHANGED")
        self.assertEqual(self.calls,0)

    def test_expired_grant_blocks(self):
        self.blocked(self.run_gate(verify=lambda:proof(expires_epoch=NOW-1)),
                     "GRANT_SCOPE_OR_EXPIRY_INVALID")
        self.assertEqual(self.calls,0)

    def test_forged_owner_boolean_blocks(self):
        self.blocked(self.run_gate(verify=lambda:proof(owner_identity_verified=1)),
                     "GRANT_STOP_OR_TRANSPORT_UNVERIFIED")

    def test_bad_transport_blocks(self):
        self.blocked(self.run_gate(verify=lambda:proof(transport_verified=False)),
                     "GRANT_STOP_OR_TRANSPORT_UNVERIFIED")

    def test_reader_exception_redacts_private_path(self):
        def bad():
            raise m.Hold("C:\\SAYDI\\private.wav")
        x=self.run_gate(reader=bad)
        self.blocked(x,"HOST_CALLBACK_FAILED")
        self.assertTrue(x["child_consumed"])
        self.assertNotIn("private",str(x))

    def test_reader_base_exception_redacts_private_path(self):
        def bad():
            raise SystemExit("C:\\SAYDI\\secret")
        self.blocked(self.run_gate(reader=bad),"HOST_CALLBACK_FAILED")

    def test_forged_schema_equality_has_no_effect(self):
        class Evil:
            def __eq__(self,other):
                raise m.Hold("PRIVATE_DATA")
        self.blocked(self.run_gate(reader=lambda:metadata(scope=Evil())),
                     "METADATA_UNQUALIFIED")

    def test_private_extra_keys_removed(self):
        data=metadata(path="C:\\SAYDI\\secret.wav",book="private")
        x=self.run_gate(reader=lambda:data)
        self.assertNotIn("secret",str(x))
        self.assertNotIn("private",str(x))
        self.assertEqual(x["metadata"]["candidate_files"],4)

    def test_journal_tampering_suppresses_receipt(self):
        def bad():
            db=sqlite3.connect(self.journal)
            try:
                db.execute("UPDATE child_reads SET state='ALTERED'")
                db.commit()
            finally:
                db.close()
            return metadata()
        self.blocked(self.run_gate(reader=bad),"JOURNAL_WITNESS_CHANGED")

    def test_no_trusted_callback_blocks(self):
        self.blocked(self.run_gate(verify=lambda:{"approved":True}),
                     "HOST_PROOF_MISSING")

    def test_missing_journal_parent_blocks(self):
        self.blocked(self.run_gate(journal=self.journal.parent/"bad"/"database.db"),
                     "JOURNAL_HOST_PATH_UNQUALIFIED")
        self.assertEqual(self.calls,0)

    def test_false_scopes_block(self):
        self.blocked(self.run_gate(verify=lambda:proof(scope="all")),
                     "GRANT_SCOPE_OR_EXPIRY_INVALID")

    def test_change_owner_bound_grant_blocks(self):
        self.run_gate()
        self.blocked(self.run_gate(1,verify=lambda:proof(owner_id=22)),
                     "GRANT_BINDING_DRIFT")

    def test_non_integer_clock_blocks(self):
        self.blocked(self.run_gate(now=lambda:"2031-01"),"CLOCK_UNQUALIFIED")

if __name__=="__main__":
    unittest.main()
