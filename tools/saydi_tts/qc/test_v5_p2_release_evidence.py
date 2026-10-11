"""P2 evidence inventory tests: no actual Owner or host authority implied."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from v5_p2_release_evidence import SCHEMA, RECEIPT_SOURCES, evaluate, write_new_report

HEAD = 'a'*40
SOT = 'b'*40
HASH = 'f'*64


def base():
    return {'schema': SCHEMA, 'pr_head_sha': HEAD, 'sot_main_sha': SOT,
            'chapter': 3, 'checkpoint_sha256': None,
            'reference_sha256': None, 'receipts': []}


def pass_receipts():
    return [{'gate': gate, 'status': 'PASS', 'source': source, 'evidence_sha256': HASH}
            for gate, source in RECEIPT_SOURCES.items()]


class ReleaseEvidenceTests(unittest.TestCase):
    def test_missing_fields_explicitly_block(self):
        r = evaluate(base(), HEAD, SOT)
        self.assertEqual(r['status'], 'BLOCKED_MISSING_EVIDENCE')
        self.assertIn('exact_head_ci', r['pending_gates'])
        self.assertIn('immutable_checkpoint_snapshot', r['pending_gates'])
        self.assertFalse(r['chapter_final'])

    def test_even_all_pass_claims_are_not_authenticated(self):
        p = base(); p['receipts'] = pass_receipts()
        p['checkpoint_sha256'] = HASH; p['reference_sha256'] = HASH
        r = evaluate(p, HEAD, SOT)
        self.assertEqual(r['status'], 'RECEIPTS_SUBMITTED_UNVERIFIED')
        self.assertEqual(r['self_reported_pass_count'], len(RECEIPT_SOURCES))
        for field in ('receipt_authenticity_verified', 'independent_owner_identity_verified',
                      'sot_authorization_verified', 'exact_head_ci_verified', 'chapter_final',
                      'worker_start_allowed', 'production_write_allowed', 'automatic_merge_allowed'):
            self.assertFalse(r[field])

    def test_exact_head_stale_refused(self):
        with self.assertRaisesRegex(ValueError, 'STALE_PR_HEAD_OR_MAIN_SOT'):
            evaluate(base(), '0'*40, SOT)

    def test_sot_main_stale_refused(self):
        with self.assertRaisesRegex(ValueError, 'STALE_PR_HEAD_OR_MAIN_SOT'):
            evaluate(base(), HEAD, '0'*40)

    def test_bad_expected_sha_refused(self):
        with self.assertRaisesRegex(ValueError, 'EXPECTED_COMMIT_SHA_INVALID'):
            evaluate(base(), 'invalid', SOT)

    def test_wrong_receipt_provenance_fails(self):
        p=base();p['receipts']=[{'gate':'exact_head_ci','status':'PASS',
                                 'source':'H4_LOCAL','evidence_sha256':HASH}]
        with self.assertRaisesRegex(ValueError, 'RECEIPT_STATUS_OR_PROVENANCE_INVALID'):
            evaluate(p, HEAD, SOT)

    def test_duplicate_receipt_refused(self):
        p=base();p['receipts']=[pass_receipts()[0],pass_receipts()[0]]
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_OR_DUPLICATE_GATE'):
            evaluate(p, HEAD, SOT)

    def test_unrecognized_gate_refused(self):
        p=base(); p['receipts']=[{'gate':'auto_merge','status':'PASS','source':'GITHUB_MAIN','evidence_sha256':HASH}]
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_OR_DUPLICATE_GATE'):
            evaluate(p, HEAD, SOT)

    def test_missing_real_evidence_hash_refused(self):
        p=base();p['receipts']=[{'gate':'exact_head_ci','status':'PASS',
                                'source':'GITHUB_ACTIONS','evidence_sha256':'no'}]
        with self.assertRaisesRegex(ValueError, 'RECEIPT_DIGEST_INVALID'):
            evaluate(p, HEAD, SOT)

    def test_fake_actor_or_secret_fields_refused(self):
        p=base();p['owner_token']='private'
        with self.assertRaisesRegex(ValueError, 'UNSAFE_PACKAGE_FIELDS'):
            evaluate(p, HEAD, SOT)

    def test_failing_one_gate_blocks(self):
        p=base();p['receipts']=pass_receipts();p['receipts'][0]['status']='FAIL'
        p['checkpoint_sha256']=HASH;p['reference_sha256']=HASH
        r=evaluate(p,HEAD,SOT)
        self.assertEqual(r['status'],'BLOCKED_FAILED_GATE')
        self.assertIn('exact_head_ci',r['self_reported_failed_gates'])

    def test_non_boolean_status_not_allowed(self):
        p=base();p['receipts']=[{'gate':'exact_head_ci','status':True,'source':'GITHUB_ACTIONS',
                                'evidence_sha256':HASH}]
        with self.assertRaisesRegex(ValueError, 'RECEIPT_STATUS_OR_PROVENANCE_INVALID'):
            evaluate(p, HEAD, SOT)

    def test_protected_fingerprint_invalid(self):
        p=base();p['checkpoint_sha256']='stale'
        with self.assertRaisesRegex(ValueError, 'INVALID_PROTECTED_FINGERPRINT'):
            evaluate(p,HEAD,SOT)

    def test_h4_gates_are_separate_from_ci(self):
        r=evaluate(base(),HEAD,SOT)
        self.assertIn('off_after_reboot',r['h4_required_gates'])
        self.assertIn('owner_stop_start_durable',r['h4_required_gates'])
        self.assertNotIn('exact_head_ci',r['h4_required_gates'])

    def test_no_chapter_zero(self):
        p=base();p['chapter']=0
        with self.assertRaisesRegex(ValueError, 'INVALID_CHAPTER'):
            evaluate(p,HEAD,SOT)

    def test_report_can_only_be_written_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'p2.json';r=evaluate(base(),HEAD,SOT)
            write_new_report(dest,r)
            with self.assertRaises(FileExistsError):write_new_report(dest,r)
            self.assertFalse(json.loads(dest.read_text())['chapter_final'])

    def test_production_path_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'REFUSE_PRODUCTION_PATH'):
                write_new_report(Path(tmp)/'chunks'/'p2.json',evaluate(base(),HEAD,SOT))

    def test_cli_default_off_creates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);inp=folder/'in.json';out=folder/'out.json'
            inp.write_text(json.dumps(base()), encoding='utf-8')
            script=Path(__file__).with_name('v5_p2_release_evidence.py')
            proc=subprocess.run([sys.executable,str(script),'--input',str(inp),'--output',str(out),
                                 '--expected-head',HEAD,'--expected-sot-main',SOT],
                                text=True,capture_output=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertIn('DISABLED_DEFAULT',proc.stdout)
            self.assertFalse(out.exists())

    def test_cli_optin_still_not_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);inp=folder/'in.json';out=folder/'out.json'
            inp.write_text(json.dumps(base()), encoding='utf-8')
            script=Path(__file__).with_name('v5_p2_release_evidence.py')
            proc=subprocess.run([sys.executable,str(script),'--input',str(inp),'--output',str(out),
                                 '--expected-head',HEAD,'--expected-sot-main',SOT,
                                 '--enable-p2-inventory'],text=True,capture_output=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertFalse(json.loads(out.read_text())['worker_start_allowed'])


if __name__=='__main__': unittest.main(verbosity=2)
