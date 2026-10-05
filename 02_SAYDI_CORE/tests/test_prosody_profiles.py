from __future__ import annotations

import unittest

from saydi_audiobook.analysis import RuleBasedAnalysisProvider
from saydi_audiobook.prosody import (
    acceptance_matches_profile,
    evaluate_prosody_metrics,
    filter_provider_supported_controls,
    get_prosody_envelope,
    profile_fingerprints,
    resolve_owner_style_request,
)


class ProsodyProfileTests(unittest.TestCase):
    def test_business_profile_accepts_clear_midrange_delivery(self):
        result = evaluate_prosody_metrics(
            profile_key="BUSINESS_CLEAR",
            speaking_rate_wpm=150.0,
            pause_ratio=0.15,
            pitch_variation_semitones=1.8,
            energy_variation_db=6.0,
        )
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.reasons, ())

    def test_business_profile_catches_too_fast_delivery(self):
        result = evaluate_prosody_metrics(
            profile_key="BUSINESS_CLEAR",
            speaking_rate_wpm=240.0,
            pause_ratio=0.15,
            pitch_variation_semitones=1.8,
            energy_variation_db=6.0,
        )
        self.assertEqual(result.status, "REVIEW")
        self.assertIn("pace_too_fast", result.reasons)

    def test_story_profile_catches_flat_ai_like_delivery(self):
        result = evaluate_prosody_metrics(
            profile_key="STORY_NARRATIVE",
            speaking_rate_wpm=135.0,
            pause_ratio=0.13,
            pitch_variation_semitones=0.25,
            energy_variation_db=0.6,
        )
        self.assertEqual(result.status, "REVIEW")
        self.assertIn("flat_intonation", result.reasons)
        self.assertIn("flat_dynamics", result.reasons)

    def test_general_profile_catches_too_slow_delivery(self):
        result = evaluate_prosody_metrics(
            profile_key="GENERAL_CLEAR",
            speaking_rate_wpm=75.0,
            pause_ratio=0.16,
            pitch_variation_semitones=1.4,
            energy_variation_db=5.0,
        )
        self.assertEqual(result.status, "REVIEW")
        self.assertIn("pace_too_slow", result.reasons)

    def test_owner_style_request_maps_to_expected_profiles(self):
        self.assertEqual(
            resolve_owner_style_request("sách kinh doanh rõ ràng chuyên nghiệp").profile_key,
            "BUSINESS_CLEAR",
        )
        self.assertEqual(
            resolve_owner_style_request("truyện kể chuyện nhiều cảm xúc").profile_key,
            "STORY_NARRATIVE",
        )
        self.assertEqual(
            resolve_owner_style_request("đọc trung tính, tổng quát").profile_key,
            "GENERAL_CLEAR",
        )

    def test_unknown_style_falls_back_to_book_profile(self):
        book = RuleBasedAnalysisProvider().analyze_book(
            "Doanh nghiệp cần chiến lược, khách hàng, doanh thu và lợi nhuận."
        )
        resolution = resolve_owner_style_request("phong cách riêng chưa biết", book_profile=book)
        self.assertEqual(resolution.profile_key, "BUSINESS_CLEAR")
        self.assertEqual(resolution.source, "book_profile")

    def test_profile_change_invalidates_previous_qc_acceptance(self):
        business = get_prosody_envelope("BUSINESS_CLEAR")
        self.assertTrue(
            acceptance_matches_profile(business.fingerprint, "BUSINESS_CLEAR")
        )
        self.assertFalse(
            acceptance_matches_profile(business.fingerprint, "STORY_NARRATIVE")
        )
        fingerprints = profile_fingerprints()
        self.assertEqual(len(set(fingerprints.values())), 3)

    def test_provider_control_filter_never_fabricates_emotion(self):
        accepted, rejected = filter_provider_supported_controls(
            "vieneu-local",
            {
                "segmentation": "sentence",
                "pause_insertion": True,
                "emotion": "sad",
                "speed": 0.8,
            },
        )
        self.assertEqual(
            accepted,
            {"segmentation": "sentence", "pause_insertion": True},
        )
        self.assertIn("emotion", rejected)
        self.assertIn("speed", rejected)

    def test_saydivoice_filter_uses_only_verified_controls(self):
        accepted, rejected = filter_provider_supported_controls(
            "saydivoice",
            {
                "speed": 0.4,
                "pause_enabled": True,
                "mood": "warm",
            },
        )
        self.assertEqual(accepted, {"speed": 0.4, "pause_enabled": True})
        self.assertEqual(rejected, ("mood",))


if __name__ == "__main__":
    unittest.main()
