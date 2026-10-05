from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import unicodedata
from typing import Iterable

from .contracts import BookProfile, canonical_hash


PROSODY_PROFILE_VERSION = "prosody-profile-v1"


@dataclass(frozen=True, slots=True)
class ProsodyEnvelope:
    profile_key: str
    label: str
    min_speaking_rate_wpm: float
    max_speaking_rate_wpm: float
    min_pause_ratio: float
    max_pause_ratio: float
    min_pitch_variation_semitones: float
    max_pitch_variation_semitones: float
    min_energy_variation_db: float
    max_energy_variation_db: float
    version: str = PROSODY_PROFILE_VERSION

    def validate(self) -> None:
        if not self.profile_key.strip():
            raise ValueError("profile_key is required")
        if self.min_speaking_rate_wpm <= 0:
            raise ValueError("min_speaking_rate_wpm must be > 0")
        if self.max_speaking_rate_wpm <= self.min_speaking_rate_wpm:
            raise ValueError("speaking-rate envelope is invalid")
        if not 0.0 <= self.min_pause_ratio < self.max_pause_ratio <= 1.0:
            raise ValueError("pause-ratio envelope is invalid")
        if self.min_pitch_variation_semitones < 0:
            raise ValueError("min pitch variation must be >= 0")
        if self.max_pitch_variation_semitones <= self.min_pitch_variation_semitones:
            raise ValueError("pitch-variation envelope is invalid")
        if self.min_energy_variation_db < 0:
            raise ValueError("min energy variation must be >= 0")
        if self.max_energy_variation_db <= self.min_energy_variation_db:
            raise ValueError("energy-variation envelope is invalid")

    @property
    def fingerprint(self) -> str:
        self.validate()
        return canonical_hash(asdict(self))


PROSODY_ENVELOPES: dict[str, ProsodyEnvelope] = {
    "BUSINESS_CLEAR": ProsodyEnvelope(
        profile_key="BUSINESS_CLEAR",
        label="Business Clear",
        min_speaking_rate_wpm=120.0,
        max_speaking_rate_wpm=180.0,
        min_pause_ratio=0.06,
        max_pause_ratio=0.28,
        min_pitch_variation_semitones=0.65,
        max_pitch_variation_semitones=4.8,
        min_energy_variation_db=1.5,
        max_energy_variation_db=12.0,
    ),
    "STORY_NARRATIVE": ProsodyEnvelope(
        profile_key="STORY_NARRATIVE",
        label="Story Narrative",
        min_speaking_rate_wpm=95.0,
        max_speaking_rate_wpm=165.0,
        min_pause_ratio=0.08,
        max_pause_ratio=0.36,
        min_pitch_variation_semitones=1.00,
        max_pitch_variation_semitones=6.5,
        min_energy_variation_db=2.0,
        max_energy_variation_db=15.0,
    ),
    "GENERAL_CLEAR": ProsodyEnvelope(
        profile_key="GENERAL_CLEAR",
        label="General Clear",
        min_speaking_rate_wpm=110.0,
        max_speaking_rate_wpm=175.0,
        min_pause_ratio=0.06,
        max_pause_ratio=0.32,
        min_pitch_variation_semitones=0.75,
        max_pitch_variation_semitones=5.5,
        min_energy_variation_db=1.5,
        max_energy_variation_db=13.0,
    ),
}


@dataclass(frozen=True, slots=True)
class ProsodyEvaluation:
    profile_key: str
    profile_fingerprint: str
    status: str
    reasons: tuple[str, ...]
    measured: dict[str, float | None]


@dataclass(frozen=True, slots=True)
class OwnerStyleResolution:
    requested_style: str
    profile_key: str
    source: str
    matched_aliases: tuple[str, ...]


def get_prosody_envelope(profile_key: str) -> ProsodyEnvelope:
    key = profile_key.strip().upper()
    if key not in PROSODY_ENVELOPES:
        raise ValueError(f"unsupported narration profile: {profile_key}")
    envelope = PROSODY_ENVELOPES[key]
    envelope.validate()
    return envelope


def evaluate_prosody_metrics(
    *,
    profile_key: str,
    speaking_rate_wpm: float | None,
    pause_ratio: float | None,
    pitch_variation_semitones: float | None,
    energy_variation_db: float | None,
) -> ProsodyEvaluation:
    envelope = get_prosody_envelope(profile_key)
    reasons: list[str] = []

    if speaking_rate_wpm is None:
        reasons.append("missing_speaking_rate")
    elif speaking_rate_wpm < envelope.min_speaking_rate_wpm:
        reasons.append("pace_too_slow")
    elif speaking_rate_wpm > envelope.max_speaking_rate_wpm:
        reasons.append("pace_too_fast")

    if pause_ratio is None:
        reasons.append("missing_pause_ratio")
    elif pause_ratio < envelope.min_pause_ratio:
        reasons.append("insufficient_pauses")
    elif pause_ratio > envelope.max_pause_ratio:
        reasons.append("excessive_pauses")

    if pitch_variation_semitones is None:
        reasons.append("missing_pitch_variation")
    elif pitch_variation_semitones < envelope.min_pitch_variation_semitones:
        reasons.append("flat_intonation")
    elif pitch_variation_semitones > envelope.max_pitch_variation_semitones:
        reasons.append("excessive_pitch_variation")

    if energy_variation_db is None:
        reasons.append("missing_energy_variation")
    elif energy_variation_db < envelope.min_energy_variation_db:
        reasons.append("flat_dynamics")
    elif energy_variation_db > envelope.max_energy_variation_db:
        reasons.append("excessive_dynamics")

    return ProsodyEvaluation(
        profile_key=envelope.profile_key,
        profile_fingerprint=envelope.fingerprint,
        status="PASS" if not reasons else "REVIEW",
        reasons=tuple(reasons),
        measured={
            "speaking_rate_wpm": speaking_rate_wpm,
            "pause_ratio": pause_ratio,
            "pitch_variation_semitones": pitch_variation_semitones,
            "energy_variation_db": energy_variation_db,
        },
    )


def _normalize_style_request(value: str) -> str:
    value = unicodedata.normalize("NFC", value).casefold()
    value = re.sub(r"[^\wÀ-ỹĐđ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


_STYLE_ALIASES: dict[str, tuple[str, ...]] = {
    "BUSINESS_CLEAR": (
        "business",
        "kinh doanh",
        "doanh nghiep",
        "doanh nghiệp",
        "quan tri",
        "quản trị",
        "chuyen nghiep",
        "chuyên nghiệp",
        "ro rang",
        "rõ ràng",
        "authoritative",
    ),
    "STORY_NARRATIVE": (
        "story",
        "fiction",
        "truyen",
        "truyện",
        "ke chuyen",
        "kể chuyện",
        "cam xuc",
        "cảm xúc",
        "narrative",
        "expressive",
    ),
    "GENERAL_CLEAR": (
        "general",
        "tong quat",
        "tổng quát",
        "trung tinh",
        "trung tính",
        "neutral",
        "clear",
    ),
}


def resolve_owner_style_request(
    requested_style: str | None,
    *,
    book_profile: BookProfile | None = None,
) -> OwnerStyleResolution:
    raw = (requested_style or "").strip()
    normalized = _normalize_style_request(raw)

    if normalized:
        matches: list[tuple[str, str]] = []
        for key, aliases in _STYLE_ALIASES.items():
            for alias in aliases:
                normalized_alias = _normalize_style_request(alias)
                if normalized_alias and normalized_alias in normalized:
                    matches.append((key, alias))
        if matches:
            counts: dict[str, int] = {}
            for key, _alias in matches:
                counts[key] = counts.get(key, 0) + 1
            best_key = sorted(
                counts,
                key=lambda key: (-counts[key], list(PROSODY_ENVELOPES).index(key)),
            )[0]
            aliases = tuple(alias for key, alias in matches if key == best_key)
            return OwnerStyleResolution(
                requested_style=raw,
                profile_key=best_key,
                source="owner_request",
                matched_aliases=aliases,
            )

        direct = raw.upper()
        if direct in PROSODY_ENVELOPES:
            return OwnerStyleResolution(
                requested_style=raw,
                profile_key=direct,
                source="owner_profile_key",
                matched_aliases=(raw,),
            )

    if book_profile is not None:
        for key in book_profile.recommended_narration_profiles:
            if key in PROSODY_ENVELOPES:
                return OwnerStyleResolution(
                    requested_style=raw,
                    profile_key=key,
                    source="book_profile",
                    matched_aliases=(),
                )

    return OwnerStyleResolution(
        requested_style=raw,
        profile_key="GENERAL_CLEAR",
        source="default",
        matched_aliases=(),
    )


_PROVIDER_SUPPORTED_CONTROLS: dict[str, frozenset[str]] = {
    # Current VieNeu field path has verified structural controls only.
    # No discrete emotion/mood parameter is claimed.
    "vieneu-local": frozenset(
        {
            "segmentation",
            "punctuation",
            "pause_insertion",
            "voice_reference",
        }
    ),
    "saydivoice": frozenset(
        {
            "voice",
            "stability_expression_axis",
            "speed",
            "pause_enabled",
            "output_format",
        }
    ),
}


def filter_provider_supported_controls(
    provider: str,
    requested_controls: dict[str, object],
) -> tuple[dict[str, object], tuple[str, ...]]:
    supported = _PROVIDER_SUPPORTED_CONTROLS.get(provider.strip().casefold(), frozenset())
    accepted = {
        key: value
        for key, value in requested_controls.items()
        if key in supported
    }
    rejected = tuple(
        key
        for key in requested_controls
        if key not in supported
    )
    return accepted, rejected


def profile_fingerprints() -> dict[str, str]:
    return {
        key: envelope.fingerprint
        for key, envelope in PROSODY_ENVELOPES.items()
    }


def acceptance_matches_profile(
    accepted_profile_fingerprint: str | None,
    profile_key: str,
) -> bool:
    if not accepted_profile_fingerprint:
        return False
    return accepted_profile_fingerprint == get_prosody_envelope(profile_key).fingerprint
