"""Pure synthetic V5 SHA-page continuity tests. No H4, MCP, audio or network."""
import copy
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("sut", Path(__file__).with_name("vn001_v5_hash_page_reconcile.py"))
sut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sut)


def fixture():
    m = {"schema": sut.SCHEMA, "mode": "metadata", "scope": "audio",
         "candidate_files": 3, "candidate_bytes": 24, "kinds": {"audio": 3},
         "metadata_fingerprint_sha256": "a" * 64, "hash_batch_offset": 0,
         "complete_file_hash_inventory": False, "source_and_audio_changed": False,
         "production_modified": False, "worker_started": False, "approved_to_start": False, "approved_to_dispatch": False}
    pages = []
    for off, sizes in ((0, [6, 8]), (2, [10])):
        p = dict(m)
        p.update({"mode": "hash", "hash_batch_offset": off,
                  "hashed_files": len(sizes), "unhashed_files": 3 - len(sizes),
                  "next_hash_offset": None if off + len(sizes) == 3 else off + len(sizes),
                  "hash_page_final": off + len(sizes) == 3,
                  "complete_file_hash_inventory": False,
                  "hash_blocked_reason": None, "production_modified": False,
                  "individual_hashes": [
                      {"anonymous_file_id": f"{off+i+1:016x}",
                       "sha256": f"{off+i+1:064x}", "bytes": n}
                      for i, n in enumerate(sizes)]})
        pages.append(p)
    return m, pages


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.meta, self.pages = fixture()

    def hold(self, code, pages=None, meta=None):
        with self.assertRaisesRegex(sut.ReconciliationHold, "^" + code + "$"):
            sut.reconcile_pages(self.meta if meta is None else meta,
                                self.pages if pages is None else pages)

    def test_valid_synthetic_pages_still_unattested(self):
        result = sut.reconcile_pages(self.meta, self.pages)
        self.assertEqual(result["status"], "HASH_PAGES_RECONCILED_UNATTESTED")
        self.assertEqual((result["file_count"], result["hashed_bytes"]), (3, 24))
        for key in ("approved_v5_asset_set_verified", "checkpoint_ownership_verified",
                    "narrator_identity_verified", "owner_authorization_verified",
                    "live_h4_inventory_verified", "v6_step_1_1_done",
                    "approved_to_dispatch", "approved_to_start", "production_modified"):
            self.assertFalse(result[key], key)

    def test_missing_order_replay_and_extra_pages(self):
        self.hold("HASH_PAGES_INCOMPLETE_OR_BYTES_DRIFT", self.pages[:1])
        self.hold("HASH_PAGE_MISSING_REPLAY_OR_OUT_OF_ORDER", self.pages[::-1])
        self.hold("HASH_PAGE_MISSING_REPLAY_OR_OUT_OF_ORDER", self.pages[:1] * 2)
        self.hold("HASH_PAGE_AFTER_FINAL", self.pages + self.pages[-1:])

    def test_changed_fingerprint_and_identity(self):
        for key, value in (("scope", "model"), ("metadata_fingerprint_sha256", "b" * 64),
                           ("candidate_bytes", 25)):
            p = copy.deepcopy(self.pages)
            p[1][key] = value
            self.hold("HASH_PAGE_METADATA_DRIFT", p)

    def test_duplicate_entry_and_foreign_path(self):
        p = copy.deepcopy(self.pages)
        p[1]["individual_hashes"][0]["anonymous_file_id"] = "0000000000000001"
        self.hold("HASH_ENTRY_REPLAY_OR_COLLISION", p)
        p = copy.deepcopy(self.pages)
        p[1]["individual_hashes"][0]["anonymous_file_id"] = "../private"
        self.hold("HASH_ENTRY_INVALID", p)

    def test_offset_and_byte_drift(self):
        p = copy.deepcopy(self.pages)
        p[1]["next_hash_offset"] = False
        self.hold("HASH_PAGE_NEXT_OFFSET_INVALID", p)
        p = copy.deepcopy(self.pages)
        p[1]["individual_hashes"][0]["bytes"] = 9
        self.hold("HASH_PAGES_INCOMPLETE_OR_BYTES_DRIFT", p)

    def test_forged_dispatch_or_worker_flags_hold(self):
        for key in ("worker_started", "production_modified", "approved_to_start",
                    "approved_to_dispatch", "source_and_audio_changed"):
            p = copy.deepcopy(self.pages)
            p[1][key] = True
            self.hold("HASH_PAGE_POLICY_OR_BLOCKER_INVALID", p)
        m = dict(self.meta, approved_to_start=True)
        self.hold("METADATA_READONLY_POLICY_INVALID", meta=m)


if __name__ == "__main__":
    unittest.main(verbosity=2)
