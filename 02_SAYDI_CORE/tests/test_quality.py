from __future__ import annotations

import unittest

from saydi_audiobook.quality import QualityObservation, QualityPolicy, evaluate_quality


AUDIO_SHA = "a" * 64


class QualityTests(unittest.TestCase):
    def test_clear_humanlike_chunk_passes(self):
        report = evaluate_quality(
            QualityObservation(
                chunk_id="c-001",
                audio_sha256=AUDIO_SHA,
                asr_similarity=0.96,
                min_word_confidence=0.84,
                mean_word_confidence=0.93,
                speaking_rate_wpm=145,
                pause_ratio=0.17,
                pitch_variation_semitones=2.4,
                energy_variation_db=8.0,
                clipping_ratio=0.0,
            )
        )
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.pronunciation_status, "PASS")
        self.assertEqual(report.prosody_status, "PASS")
        self.assertFalse(report.owner_review_required)

    def test_unclear_words_trigger_targeted_pronunciation_repair(self):
        report = evaluate_quality(
            QualityObservation(
                chunk_id="c-002",
                audio_sha256=AUDIO_SHA,
                asr_similarity=0.79,
                min_word_confidence=0.52,
                unclear_tokens=("khởi nghiệp", "chuyển đổi"),
                speaking_rate_wpm=142,
                pause_ratio=0.15,
                pitch_variation_semitones=2.1,
                clipping_ratio=0.0,
            )
        )
        self.assertEqual(report.status, "REPAIR")
        self.assertEqual(report.pronunciation_status, "REPAIR")
        self.assertIn("apply_pronunciation_lexicon_or_spoken_form", report.repair_actions)
        self.assertIn("split_chunk_around_unclear_tokens", report.repair_actions)
        self.assertIn("rerender_affected_chunk", report.repair_actions)

    def test_flat_ai_like_delivery_triggers_prosody_repair(self):
        report = evaluate_quality(
            QualityObservation(
                chunk_id="c-003",
                audio_sha256=AUDIO_SHA,
                asr_similarity=0.96,
                min_word_confidence=0.85,
                speaking_rate_wpm=195,
                pause_ratio=0.02,
                pitch_variation_semitones=0.2,
                clipping_ratio=0.0,
            )
        )
        self.assertEqual(report.status, "REPAIR")
        self.assertEqual(report.prosody_status, "REPAIR")
        kinds = {finding.kind for finding in report.findings}
        self.assertIn("prosody_style_mismatch", kinds)

    def test_retry_budget_prevents_infinite_regeneration(self):
        policy = QualityPolicy(max_auto_attempts=2)
        report = evaluate_quality(
            QualityObservation(
                chunk_id="c-004",
                audio_sha256=AUDIO_SHA,
                attempt=2,
                asr_similarity=0.60,
                min_word_confidence=0.30,
                unclear_tokens=("SAYDI",),
                speaking_rate_wpm=145,
                pause_ratio=0.16,
                pitch_variation_semitones=1.8,
                clipping_ratio=0.0,
            ),
            policy,
        )
        self.assertEqual(report.status, "REVIEW")
        self.assertTrue(report.owner_review_required)
        self.assertEqual(report.repair_actions, ())

    def test_missing_metrics_cannot_silently_pass(self):
        report = evaluate_quality(
            QualityObservation(
                chunk_id="c-005",
                audio_sha256=AUDIO_SHA,
                asr_similarity=0.95,
                min_word_confidence=0.80,
            )
        )
        self.assertEqual(report.status, "REVIEW")
        self.assertIn("speaking_rate_wpm", report.metrics_missing)
        self.assertTrue(report.owner_review_required)


if __name__ == "__main__":
    unittest.main()
