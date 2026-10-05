from __future__ import annotations

import unittest

from saydi_audiobook.director import (
    STORY_POLICIES,
    classify_story_beat,
    direct_story_segment,
    direct_story_text,
    direct_story_clauses,
    plan_fingerprint,
)


class NarrationDirectorTests(unittest.TestCase):
    def test_reflective_sentence_uses_pause_not_global_slowdown(self):
        segment = direct_story_segment(
            "Minh nhớ đến ngày cha mất, cổ họng nghẹn lại.",
            segment_id="s1",
        )
        self.assertEqual(segment.beat, "REFLECTIVE_SAD")
        self.assertEqual(segment.tempo_factor, 1.0)
        self.assertGreater(segment.pause_after_ms, STORY_POLICIES["NARRATIVE"].pause_after_ms)

    def test_tension_keeps_natural_speed_with_shorter_pause(self):
        segment = direct_story_segment(
            "Bất ngờ cánh cửa bật mở, Minh giật mình quay lại.",
            segment_id="s2",
        )
        self.assertEqual(segment.beat, "TENSION")
        self.assertEqual(segment.tempo_factor, 1.0)
        self.assertLess(segment.pause_after_ms, STORY_POLICIES["REFLECTIVE_SAD"].pause_after_ms)

    def test_tender_dialogue_is_detected(self):
        beat, cues, confidence = classify_story_beat('“Mẹ ơi, con về rồi.”')
        self.assertEqual(beat, "DIALOGUE_TENDER")
        self.assertIn("dialogue", cues)
        self.assertGreaterEqual(confidence, 0.8)

    def test_scene_transition_gets_long_reset_pause(self):
        segment = direct_story_segment(
            "Sáng hôm sau, mưa tạnh.",
            segment_id="s3",
        )
        self.assertEqual(segment.beat, "SCENE_TRANSITION")
        self.assertGreaterEqual(segment.pause_after_ms, 900)

    def test_punctuation_shaping_does_not_change_words(self):
        source = "Minh nhớ đến ngày cha mất."
        segment = direct_story_segment(source, segment_id="s4", beat="REFLECTIVE_SAD")
        self.assertEqual(segment.canonical_text, source)
        self.assertTrue(segment.spoken_text.endswith("…"))
        # Only final punctuation is changed.
        self.assertEqual(segment.spoken_text[:-1], source[:-1])

    def test_story_text_is_split_into_directed_units(self):
        text = (
            "Chiều xuống rất chậm. Minh đứng trước căn nhà cũ.\n\n"
            "“Mẹ ơi, con về rồi.” Không ai trả lời.\n\n"
            "Bất ngờ cánh cửa bật mở. Minh giật mình."
        )
        plan = direct_story_text(text)
        self.assertGreaterEqual(len(plan), 4)
        self.assertTrue(any(s.beat == "DIALOGUE_TENDER" for s in plan))
        self.assertTrue(any(s.beat == "TENSION" for s in plan))
        self.assertEqual(len({s.segment_id for s in plan}), len(plan))
        self.assertEqual(len(plan_fingerprint(plan)), 64)


    def test_clause_level_plan_keeps_natural_speed_and_more_breath_points(self):
        text = (
            "Minh muốn đáp thật bình thường, nhưng cổ họng nghẹn lại. "
            "Anh đặt túi xuống ghế. “Con chỉ về mấy hôm thôi.” "
            "Mẹ gật đầu, đôi tay vẫn chậm rãi nhặt từng cọng rau."
        )
        plan = direct_story_clauses(text)
        self.assertGreaterEqual(len(plan), 4)
        self.assertTrue(all(s.tempo_factor == 1.0 for s in plan))
        self.assertEqual(" ".join(s.canonical_text for s in plan).replace("  ", " "), text)

    def test_pause_first_policy_does_not_time_stretch_voice(self):
        for policy in STORY_POLICIES.values():
            policy.validate()
            self.assertEqual(policy.tempo_factor, 1.0)


if __name__ == "__main__":
    unittest.main()
