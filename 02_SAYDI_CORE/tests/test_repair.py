from __future__ import annotations

import unittest

from saydi_audiobook.repair import (
    build_targeted_pronunciation_repair,
    expected_mismatch_tokens,
    repair_request_id,
)


AUDIO_SHA = "b" * 64


class RepairTests(unittest.TestCase):
    def test_expected_mismatch_tokens_use_canonical_side(self):
        suspects = expected_mismatch_tokens(
            "Nhưng phải sau 10 năm làm việc cùng nhau.",
            "Nhưng phải sau mươi năm làm việc cùng nhau.",
        )
        self.assertIn("10", suspects)
        self.assertNotIn("mươi", suspects)

    def test_known_numeric_mismatch_builds_safe_spoken_override(self):
        plan = build_targeted_pronunciation_repair(
            chunk_index=12,
            canonical_text="Nhưng phải sau 10 năm làm việc cùng nhau.",
            heard_text="Nhưng phải sau mươi năm làm việc cùng nhau.",
            source_audio_sha256=AUDIO_SHA,
        )
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan.canonical_text, "Nhưng phải sau 10 năm làm việc cùng nhau.")
        self.assertEqual(plan.spoken_text, "Nhưng phải sau mười năm làm việc cùng nhau.")
        self.assertEqual(plan.expected_suspect_tokens, ("10",))
        self.assertEqual([x.key for x in plan.applied_overrides], ["number:10"])
        self.assertEqual(plan.meta()["source_audio_sha256"], AUDIO_SHA)

    def test_unknown_word_does_not_trigger_automatic_rewrite(self):
        plan = build_targeted_pronunciation_repair(
            chunk_index=2,
            canonical_text="Paul xuất hiện trong chương này.",
            heard_text="Pao xuất hiện trong chương này.",
            source_audio_sha256=AUDIO_SHA,
        )
        self.assertIsNone(plan)

    def test_repair_request_id_is_stable_and_attempt_sensitive(self):
        first = repair_request_id(
            job_id="job-1",
            chunk_index=12,
            source_audio_sha256=AUDIO_SHA,
            spoken_text="sau mười năm",
            attempt=1,
        )
        same = repair_request_id(
            job_id="job-1",
            chunk_index=12,
            source_audio_sha256=AUDIO_SHA,
            spoken_text="sau mười năm",
            attempt=1,
        )
        second = repair_request_id(
            job_id="job-1",
            chunk_index=12,
            source_audio_sha256=AUDIO_SHA,
            spoken_text="sau mười năm",
            attempt=2,
        )
        self.assertEqual(first, same)
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("qc004-"))


if __name__ == "__main__":
    unittest.main()
