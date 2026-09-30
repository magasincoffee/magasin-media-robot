from __future__ import annotations

from hashlib import sha256
import re

from .contracts import BookProfile, NarrationProfile, SamplePassage


PROFILES: dict[str, NarrationProfile] = {
    "BUSINESS_CLEAR": NarrationProfile(
        key="BUSINESS_CLEAR",
        label="Business Clear",
        semantic_style="authoritative_clear",
        pace="medium",
        expression=0.35,
        stability=0.78,
        pause_policy="controlled",
    ),
    "STORY_NARRATIVE": NarrationProfile(
        key="STORY_NARRATIVE",
        label="Story Narrative",
        semantic_style="warm_expressive",
        pace="medium_slow",
        expression=0.68,
        stability=0.52,
        pause_policy="dynamic",
    ),
    "GENERAL_CLEAR": NarrationProfile(
        key="GENERAL_CLEAR",
        label="General Clear",
        semantic_style="neutral_clear",
        pace="medium",
        expression=0.45,
        stability=0.68,
        pause_policy="balanced",
    ),
}


def choose_narration_profile(
    book: BookProfile,
    *,
    voice_provider: str = "unselected",
    voice_key: str = "default",
    model_key: str = "default",
) -> NarrationProfile:
    key = next((k for k in book.recommended_narration_profiles if k in PROFILES), "GENERAL_CLEAR")
    base = PROFILES[key]
    profile = NarrationProfile(
        key=base.key,
        label=base.label,
        semantic_style=base.semantic_style,
        pace=base.pace,
        expression=base.expression,
        stability=base.stability,
        pause_policy=base.pause_policy,
        pronunciation_lexicon_version=base.pronunciation_lexicon_version,
        voice_provider=voice_provider,
        voice_key=voice_key,
        model_key=model_key,
    )
    profile.validate()
    return profile


def select_representative_passages(spoken_text: str, *, limit: int = 3) -> list[SamplePassage]:
    paragraphs = [p.strip() for p in spoken_text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    def score(p: str) -> tuple[float, int]:
        length_score = 1.0 - min(abs(len(p) - 420) / 420, 1.0)
        dialogue = 0.5 if re.search(r"[“\"]|(^|\n)\s*[–—-]\s+", p) else 0.0
        numbers = 0.25 if re.search(r"\d", p) else 0.0
        punctuation = min(0.35, 0.03 * len(re.findall(r"[,;:!?…]", p)))
        return (length_score + dialogue + numbers + punctuation, len(p))

    ranked = sorted(enumerate(paragraphs), key=lambda x: score(x[1]), reverse=True)
    selected = []
    for idx, paragraph in ranked[: max(1, limit)]:
        digest = sha256(paragraph.encode("utf-8")).hexdigest()[:12]
        selected.append(
            SamplePassage(
                sample_id=f"sample_{digest}",
                text=paragraph,
                reason="representative_length/dialogue/numbers/punctuation",
                ordinal=idx,
            )
        )
    return sorted(selected, key=lambda s: s.ordinal)
