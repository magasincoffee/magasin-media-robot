"""Synthetic SAYDI future task preparation tests; never touch real book audio."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from v5_future_delivery_inventory import assess, main, SCHEMA

HEAD = 'a'*40
SOT = 'b'*40
HASH = 'c'*64


def fixture():
    return {"schema":SCHEMA, "pr_head_sha":HEAD,"sot_main_sha":SOT,
            "targets":["SAYDI-009","SAYDI-010","SAYDI-011"],
            "chapters":[{"chapter":1,"segment_count":347,"master_mp3_sha256":None,
                         "qc_report_sha256":None,"duration_ms":None,
                         "material_review_count":120}]}


class FutureDeliveryInventoryTests(unittest.TestCase):
    def check(self, mutate=None):
        obj=fixture()
        if mutate:mutate(obj)
        return assess(obj,HEAD,SOT)

    def test_missing_evidence_never_authorizes_export(self):
        r=self.check()
        self.assertEqual(r['status'],'PREPARATION_ONLY_NO_SOT_ADVANCE')
        self.assertFalse(r['export_allowed'])
        self.assertEqual(len(r['chapter_findings']),3)

    def test_plans_three_existing_sot_tasks_only(self):
        r=self.check()
        self.assertEqual([x['task_id'] for x in r['planned_targets']],
                         ['SAYDI-009','SAYDI-010','SAYDI-011'])
        self.assertTrue(all(not x['task_ready'] and not x['task_done'] for x in r['planned_targets']))

    def test_all_reported_hashes_still_not_proof(self):
        def fill(m):m['chapters'][0].update(master_mp3_sha256=HASH,
                                qc_report_sha256=HASH,duration_ms=200000,
                                material_review_count=0)
        r=self.check(fill)
        self.assertEqual(r['chapter_findings'],[])
        self.assertFalse(r['reported_audio_sha_authenticated'])
        self.assertFalse(r['ffprobe_or_m4b_validation_done'])
        self.assertFalse(r['owner_acceptance_authenticated'])
        self.assertFalse(r['installer_deploy_allowed'])
        self.assertFalse(r['chapter_final'])

    def test_stale_pr_head_rejected(self):
        with self.assertRaisesRegex(ValueError,'STALE_PR_OR_SOT_REF'):
            self.check(lambda m:m.update(pr_head_sha='0'*40))

    def test_stale_sot_rejected(self):
        with self.assertRaisesRegex(ValueError,'STALE_PR_OR_SOT_REF'):
            self.check(lambda m:m.update(sot_main_sha='0'*40))

    def test_unapproved_new_task_cannot_be_added(self):
        with self.assertRaisesRegex(ValueError,'AUTHORITY_TASK_ORDER_CHANGED'):
            self.check(lambda m:m['targets'].append('P3'))

    def test_no_out_of_order_tasks(self):
        with self.assertRaisesRegex(ValueError,'AUTHORITY_TASK_ORDER_CHANGED'):
            self.check(lambda m:m['targets'].reverse())

    def test_duplicate_chapter_refused(self):
        with self.assertRaisesRegex(ValueError,'INVALID_OR_DUPLICATE_CHAPTER'):
            self.check(lambda m:m['chapters'].append(copy.deepcopy(m['chapters'][0])))

    def test_out_of_order_chapter_refused(self):
        with self.assertRaisesRegex(ValueError,'CHAPTER_ORDER_CHANGED'):
            self.check(lambda m:m['chapters'].insert(0,dict(m['chapters'][0],chapter=2)))

    def test_unresolved_material_errors_reported(self):
        r=self.check()
        self.assertEqual(r['chapter_findings'][-1]['count'],120)

    def test_bad_segments_refused(self):
        with self.assertRaisesRegex(ValueError,'INVALID_SEGMENT_COUNT'):
            self.check(lambda m:m['chapters'][0].update(segment_count=0))

    def test_boolean_review_count_refused(self):
        with self.assertRaisesRegex(ValueError,'INVALID_REVIEW_COUNT'):
            self.check(lambda m:m['chapters'][0].update(material_review_count=True))

    def test_bad_audio_sha_refused(self):
        with self.assertRaisesRegex(ValueError,'INVALID_MASTER_DIGEST'):
            self.check(lambda m:m['chapters'][0].update(master_mp3_sha256='wrong'))

    def test_extra_private_book_text_refused(self):
        with self.assertRaisesRegex(ValueError,'INVALID_CHAPTER_ROW'):
            self.check(lambda m:m['chapters'][0].update(manuscript_text='secret'))

    def test_no_sensitive_information_in_report(self):
        self.assertNotIn('secret',json.dumps(self.check()))

    def test_default_off_creates_no_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); inp=d/'plan.json'; out=d/'report.json'
            inp.write_text(json.dumps(fixture()),encoding='utf-8')
            script=Path(__file__).with_name('v5_future_delivery_inventory.py')
            run=subprocess.run([sys.executable,str(script),'--input',str(inp),
                '--output',str(out),'--expected-head',HEAD,'--expected-sot',SOT],
                capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn('DISABLED_DEFAULT',run.stdout)
            self.assertFalse(out.exists())

    def test_opt_in_writes_exclusive_metadata_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); inp=d/'plan.json'; out=d/'report.json'
            inp.write_text(json.dumps(fixture()),encoding='utf-8')
            script=Path(__file__).with_name('v5_future_delivery_inventory.py')
            cmd=[sys.executable,str(script),'--input',str(inp),'--output',str(out),
                 '--expected-head',HEAD,'--expected-sot',SOT,
                 '--enable-next-task-inventory']
            first=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stderr)
            self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            self.assertFalse(json.loads(out.read_text())['chapter_final'])

    def test_production_folder_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); inp=d/'plan.json'; out=d/'chunks'/'report.json'
            inp.write_text(json.dumps(fixture()),encoding='utf-8')
            script=Path(__file__).with_name('v5_future_delivery_inventory.py')
            cmd=[sys.executable,str(script),'--input',str(inp),'--output',str(out),
                 '--expected-head',HEAD,'--expected-sot',SOT,
                 '--enable-next-task-inventory']
            p=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertFalse(out.exists())


if __name__=='__main__': unittest.main(verbosity=2)
