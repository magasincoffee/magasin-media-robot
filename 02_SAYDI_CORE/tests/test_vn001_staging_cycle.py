"""Integrated offline VN-001 diagnosis. No protected V5 access or model start."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys

P = Path(__file__).resolve().parents[2] / "tools/saydi_tts/qc/vn001_staging_cycle.py"
spec = importlib.util.spec_from_file_location("vn001_staging_cycle", P)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

class IntegratedStageTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)

    def events(self, report):
        return [json.loads(x) for x in (self.root / report["log_file"]).read_text().splitlines()]

    def test_one_integrated_run_has_repair_and_alternative(self):
        r = m.fixture_demo(self.root, commit="a"*40)
        self.assertEqual(r["mode"], "SYNTHETIC_OFFLINE")
        self.assertEqual(r["passed"], ["GRANT", "SEQUENTIAL_RESOURCE"])
        self.assertEqual(r["held"], ["CHECKPOINT"])
        self.assertEqual(r["alternative_routes"],
                         {"CHECKPOINT": "METADATA_ONLY_HOLD_CHECKPOINT"})
        self.assertFalse(r["field_accepted"])
        self.assertFalse(r["worker_started"])
        self.assertFalse(r["task_completed"])
        events = self.events(r)
        self.assertEqual([(x["probe"], x["result"]) for x in events], [
            ("GRANT", "FAIL"), ("GRANT", "ATTEMPTED"), ("GRANT", "PASS"),
            ("CHECKPOINT", "FAIL"), ("CHECKPOINT", "HOLD"),
            ("SEQUENTIAL_RESOURCE", "PASS")])
        self.assertEqual(events[4]["alternate_route"], "METADATA_ONLY_HOLD_CHECKPOINT")
        self.assertTrue(all(not e["field_accepted"] and not e["worker_started"]
                            for e in events))
        self.assertTrue(all(e["commit"] == "a"*40 for e in events))
        self.assertTrue(all("path" not in e and "secret" not in e for e in events))

    def test_repair_budget_two_then_alternative(self):
        r = m.run_cycle(self.root, (m.Probe("GRANT", lambda: False, lambda: None),))
        events = self.events(r)
        self.assertEqual(sum(e["phase"] == "PROBE" for e in events), 3)
        self.assertEqual(sum(e["phase"] == "FIXTURE_REPAIR" for e in events), 2)
        self.assertEqual(sum(e["phase"] == "ALTERNATIVE" for e in events), 1)
        self.assertEqual(r["recommendation"], "REVIEW_ALTERNATIVE_METHOD")

    def test_callback_exception_sanitized_in_log(self):
        def failure():
            raise RuntimeError("secret_token=PRIVATE_DATA private/book.wav")
        r = m.run_cycle(self.root, (m.Probe("GRANT", failure),))
        body = (self.root / r["log_file"]).read_text()
        self.assertNotIn("secret_token", body)
        self.assertNotIn("private/book", body)
        self.assertEqual(r["held"], ["GRANT"])

    def test_no_overwrite_on_run_id_replay(self):
        run_id = "1"*24
        m.run_cycle(self.root, (m.Probe("GRANT", lambda: True),), run_id=run_id)
        with self.assertRaises(FileExistsError):
            m.run_cycle(self.root, (m.Probe("GRANT", lambda: True),), run_id=run_id)

    def test_h4_stage_and_traversal_denied(self):
        with mock.patch.object(m.socket, "gethostname", return_value=m.H4_NAME):
            with self.assertRaises(m.StageRefusal):
                m.run_cycle(self.root, (m.Probe("GRANT", lambda: True),))
        with self.assertRaises(m.StageRefusal):
            m.run_cycle(self.root / ".." / "redirect",
                        (m.Probe("GRANT", lambda: True),))

    def test_invalid_probe_and_commit_denied_before_log(self):
        with self.assertRaises(m.StageRefusal):
            m.run_cycle(self.root, (m.Probe("ARBITRARY_SHELL", lambda: True),))
        with self.assertRaises(m.StageRefusal):
            m.run_cycle(self.root, (m.Probe("GRANT", lambda: True),),
                        commit="private-sha")
        self.assertEqual(list(self.root.glob("*.jsonl")), [])

if __name__ == "__main__":
    unittest.main()
