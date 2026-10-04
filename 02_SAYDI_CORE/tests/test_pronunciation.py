from __future__ import annotations

import unittest

from saydi_audiobook.pronunciation import (
    PronunciationEntry,
    PronunciationLexicon,
    build_pronunciation_repair_plan,
    build_spoken_form,
    load_default_vietnamese_lexicon,
    vietnamese_integer_spoken_form,
)


class PronunciationTests(unittest.TestCase):
    def test_default_lexicon_and_integer_normalization_do_not_mutate_canonical(self):
        source = "AI xử lý 15 kg dữ liệu."
        result = build_spoken_form(source)

        self.assertEqual(result.canonical_text, source)
        self.assertEqual(result.spoken_text, "ây ai xử lý mười lăm ki-lô-gam dữ liệu.")
        self.assertTrue(result.changed)
        self.assertEqual(result.lexicon_version, "vi-pronunciation-v1")
        self.assertEqual(
            [x.key for x in result.applied_overrides],
            ["abbr:AI", "number:15", "unit:kg"],
        )

    def test_targeted_repair_only_changes_named_suspects(self):
        source = "AI truyền 12 kg dữ liệu qua API."
        result = build_pronunciation_repair_plan(
            source,
            suspect_tokens=("AI", "12"),
        )

        self.assertEqual(result.canonical_text, source)
        self.assertEqual(result.spoken_text, "ây ai truyền mười hai kg dữ liệu qua API.")
        self.assertEqual(
            [x.key for x in result.applied_overrides],
            ["abbr:AI", "number:12"],
        )
        self.assertEqual(result.unresolved_suspect_tokens, ())

    def test_unknown_suspect_is_preserved_for_review(self):
        source = "Thuật ngữ Zephyr cần được đọc nhất quán."
        result = build_pronunciation_repair_plan(
            source,
            suspect_tokens=("Zephyr",),
        )

        self.assertEqual(result.spoken_text, source)
        self.assertEqual(result.unresolved_suspect_tokens, ("Zephyr",))
        self.assertFalse(result.changed)

    def test_custom_name_and_foreign_term_are_explicit_and_auditable(self):
        lexicon = PronunciationLexicon(
            version="test-v1",
            locale="vi-VN",
            entries=(
                PronunciationEntry(
                    key="name:dak-lak",
                    source="Đắk Lắk",
                    spoken="Đắc Lắc",
                    category="name",
                ),
                PronunciationEntry(
                    key="foreign:acme",
                    source="ACME",
                    spoken="ác-mi",
                    category="foreign_term",
                    case_sensitive=True,
                ),
            ),
        )
        source = "Đắk Lắk hợp tác với ACME."
        result = build_spoken_form(source, lexicon=lexicon, normalize_integers=False)

        self.assertEqual(source, result.canonical_text)
        self.assertEqual(result.spoken_text, "Đắc Lắc hợp tác với ác-mi.")
        self.assertEqual(
            [(x.key, x.category, x.source_text, x.spoken_text) for x in result.applied_overrides],
            [
                ("name:dak-lak", "name", "Đắk Lắk", "Đắc Lắc"),
                ("foreign:acme", "foreign_term", "ACME", "ác-mi"),
            ],
        )

    def test_longest_explicit_entry_wins_for_overlapping_terms(self):
        lexicon = PronunciationLexicon(
            version="test-v2",
            locale="vi-VN",
            entries=(
                PronunciationEntry(
                    key="abbr:AI",
                    source="AI",
                    spoken="ây ai",
                    category="abbreviation",
                    case_sensitive=True,
                ),
                PronunciationEntry(
                    key="foreign:OpenAI",
                    source="OpenAI",
                    spoken="ô-pần ây-ai",
                    category="foreign_term",
                    case_sensitive=True,
                ),
            ),
        )
        result = build_spoken_form(
            "OpenAI và AI.",
            lexicon=lexicon,
            normalize_integers=False,
        )
        self.assertEqual(result.spoken_text, "ô-pần ây-ai và ây ai.")
        self.assertEqual(
            [x.key for x in result.applied_overrides],
            ["foreign:OpenAI", "abbr:AI"],
        )

    def test_integer_rules_cover_common_vietnamese_forms(self):
        self.assertEqual(vietnamese_integer_spoken_form("0"), "không")
        self.assertEqual(vietnamese_integer_spoken_form("15"), "mười lăm")
        self.assertEqual(vietnamese_integer_spoken_form("21"), "hai mươi mốt")
        self.assertEqual(vietnamese_integer_spoken_form("105"), "một trăm lẻ năm")
        self.assertEqual(
            vietnamese_integer_spoken_form("2026"),
            "hai nghìn không trăm hai mươi sáu",
        )
        self.assertIsNone(vietnamese_integer_spoken_form("12.5"))
        self.assertIsNone(vietnamese_integer_spoken_form("1234567"))

    def test_default_lexicon_is_versioned_and_valid(self):
        lexicon = load_default_vietnamese_lexicon()
        lexicon.validate()
        self.assertEqual(lexicon.version, "vi-pronunciation-v1")
        self.assertEqual(lexicon.locale, "vi-VN")
        self.assertGreaterEqual(len(lexicon.entries), 6)


if __name__ == "__main__":
    unittest.main()
