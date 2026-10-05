from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import re
import unicodedata
from typing import Iterable

from .contracts import canonical_hash


NARRATION_DIRECTOR_VERSION = "narration-director-v3-clause-level"


@dataclass(frozen=True, slots=True)
class StoryDeliveryPolicy:
    beat: str
    tempo_factor: float
    pause_before_ms: int
    pause_after_ms: int
    emphasis: str
    energy: str

    def validate(self) -> None:
        if not 0.5 <= self.tempo_factor <= 1.0:
            raise ValueError("tempo_factor must be within [0.5,1.0]")
        if self.pause_before_ms < 0 or self.pause_after_ms < 0:
            raise ValueError("pause values must be non-negative")


@dataclass(frozen=True, slots=True)
class DirectedNarrationSegment:
    segment_id: str
    canonical_text: str
    spoken_text: str
    beat: str
    tempo_factor: float
    pause_before_ms: int
    pause_after_ms: int
    emphasis: str
    energy: str
    confidence: float
    cues: tuple[str, ...]
    director_version: str = NARRATION_DIRECTOR_VERSION

    def validate(self) -> None:
        if not self.segment_id.strip():
            raise ValueError("segment_id is required")
        if not self.canonical_text.strip():
            raise ValueError("canonical_text is required")
        if not self.spoken_text.strip():
            raise ValueError("spoken_text is required")
        if not 0.5 <= self.tempo_factor <= 1.0:
            raise ValueError("tempo_factor must be within [0.5,1.0]")
        if self.pause_before_ms < 0 or self.pause_after_ms < 0:
            raise ValueError("pause values must be non-negative")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0,1]")

    @property
    def canonical_sha256(self) -> str:
        return sha256(self.canonical_text.encode("utf-8")).hexdigest()

    @property
    def spoken_sha256(self) -> str:
        return sha256(self.spoken_text.encode("utf-8")).hexdigest()

    @property
    def fingerprint(self) -> str:
        self.validate()
        return canonical_hash(asdict(self))


STORY_POLICIES: dict[str, StoryDeliveryPolicy] = {
    "NARRATIVE": StoryDeliveryPolicy(
        beat="NARRATIVE",
        tempo_factor=1.00,
        pause_before_ms=120,
        pause_after_ms=650,
        emphasis="natural",
        energy="medium",
    ),
    "REFLECTIVE_SAD": StoryDeliveryPolicy(
        beat="REFLECTIVE_SAD",
        tempo_factor=1.00,
        pause_before_ms=220,
        pause_after_ms=1050,
        emphasis="soft",
        energy="low",
    ),
    "TENSION": StoryDeliveryPolicy(
        beat="TENSION",
        tempo_factor=1.00,
        pause_before_ms=100,
        pause_after_ms=500,
        emphasis="focused",
        energy="medium_high",
    ),
    "DIALOGUE_TENDER": StoryDeliveryPolicy(
        beat="DIALOGUE_TENDER",
        tempo_factor=1.00,
        pause_before_ms=220,
        pause_after_ms=950,
        emphasis="intimate",
        energy="low_medium",
    ),
    "DIALOGUE_TENSION": StoryDeliveryPolicy(
        beat="DIALOGUE_TENSION",
        tempo_factor=1.00,
        pause_before_ms=140,
        pause_after_ms=650,
        emphasis="firm",
        energy="medium_high",
    ),
    "WARM_RELIEF": StoryDeliveryPolicy(
        beat="WARM_RELIEF",
        tempo_factor=1.00,
        pause_before_ms=160,
        pause_after_ms=850,
        emphasis="warm",
        energy="medium",
    ),
    "SCENE_TRANSITION": StoryDeliveryPolicy(
        beat="SCENE_TRANSITION",
        tempo_factor=1.00,
        pause_before_ms=450,
        pause_after_ms=1350,
        emphasis="reset",
        energy="low_medium",
    ),
    "RESOLUTION": StoryDeliveryPolicy(
        beat="RESOLUTION",
        tempo_factor=1.00,
        pause_before_ms=350,
        pause_after_ms=1500,
        emphasis="warm_reflective",
        energy="low_medium",
    ),
}

_DIALOGUE_RE = re.compile(r"[“”\"]")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÀ-ỸĐ“\"])")

_TENSION = (
    "bất ngờ",
    "dồn dập",
    "giật mình",
    "mất điện",
    "đập vào",
    "thở hổn hển",
    "sợ",
    "run",
    "siết chặt",
    "cao hơn bình thường",
)
_REFLECTIVE = (
    "nhớ",
    "cha mất",
    "nghẹn",
    "giận",
    "xa cách",
    "yếu",
    "mắt đỏ",
    "không khóc",
    "cúi mặt",
    "ký ức",
    "nỗi sợ",
)
_WARM = (
    "bật cười",
    "mỉm cười",
    "ánh nắng",
    "nhẹ dần",
    "vui",
    "ở lại",
    "trở về",
    "sáng",
    "nhớ nhà",
)
_TRANSITIONS = (
    "đêm đó",
    "sáng hôm sau",
    "chiều ba mươi",
    "khi đồng hồ",
    "gần nửa đêm",
)
_RESOLUTION = (
    "giao thừa",
    "ở lại thêm",
    "vẫn chờ mình trở về",
    "đủ để người đi xa",
)


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def _contains_any(text: str, terms: Iterable[str]) -> tuple[str, ...]:
    normalized = _norm(text)
    return tuple(term for term in terms if term in normalized)


def classify_story_beat(text: str) -> tuple[str, tuple[str, ...], float]:
    """Classify one narration unit using deterministic, auditable cues.

    This is deliberately conservative. It does not claim to understand all
    literary emotion; it only assigns a delivery policy when explicit textual
    evidence is present.
    """

    normalized = _norm(text)
    cues: list[str] = []

    transition_hits = _contains_any(text, _TRANSITIONS)
    resolution_hits = _contains_any(text, _RESOLUTION)
    tension_hits = _contains_any(text, _TENSION)
    reflective_hits = _contains_any(text, _REFLECTIVE)
    warm_hits = _contains_any(text, _WARM)
    is_dialogue = bool(_DIALOGUE_RE.search(text))

    if resolution_hits:
        cues.extend(f"resolution:{x}" for x in resolution_hits)
        return "RESOLUTION", tuple(cues), 0.92

    if transition_hits:
        cues.extend(f"transition:{x}" for x in transition_hits)
        if tension_hits:
            cues.extend(f"tension:{x}" for x in tension_hits)
        return "SCENE_TRANSITION", tuple(cues), 0.90

    if is_dialogue:
        cues.append("dialogue")
        if tension_hits or any(x in normalized for x in ("sao mẹ", "thương hại", "không nói")):
            cues.extend(f"tension:{x}" for x in tension_hits)
            return "DIALOGUE_TENSION", tuple(cues), 0.90
        if reflective_hits or warm_hits or any(x in normalized for x in ("mẹ ơi", "con về", "nhớ nhà")):
            cues.extend(f"reflective:{x}" for x in reflective_hits)
            cues.extend(f"warm:{x}" for x in warm_hits)
            return "DIALOGUE_TENDER", tuple(cues), 0.90
        return "DIALOGUE_TENDER", tuple(cues), 0.72

    if tension_hits:
        cues.extend(f"tension:{x}" for x in tension_hits)
        return "TENSION", tuple(cues), 0.88

    if reflective_hits:
        cues.extend(f"reflective:{x}" for x in reflective_hits)
        return "REFLECTIVE_SAD", tuple(cues), 0.84

    if warm_hits:
        cues.extend(f"warm:{x}" for x in warm_hits)
        return "WARM_RELIEF", tuple(cues), 0.84

    return "NARRATIVE", ("default_narrative",), 0.60


def _shape_punctuation(text: str, beat: str) -> str:
    """Apply semantic-preserving punctuation hints for VieNeu.

    No words are inserted, removed, or reordered. Punctuation is the only
    provider-facing hint because the current VieNeu path has no verified
    discrete emotion control.
    """

    spoken = unicodedata.normalize("NFC", text).strip()

    if beat in {"REFLECTIVE_SAD", "DIALOGUE_TENDER", "RESOLUTION"}:
        if spoken.endswith("."):
            spoken = spoken[:-1].rstrip() + "…"
    elif beat == "SCENE_TRANSITION":
        # A transition benefits from an audible reset after its first clause.
        comma = spoken.find(",")
        if comma > 0:
            spoken = spoken[:comma] + "…" + spoken[comma + 1 :]
    elif beat == "TENSION":
        # Preserve sharp punctuation; avoid ellipses that would deflate tension.
        spoken = re.sub(r"\.{3,}", "…", spoken)

    return spoken


def direct_story_segment(
    canonical_text: str,
    *,
    segment_id: str,
    beat: str | None = None,
) -> DirectedNarrationSegment:
    if not canonical_text.strip():
        raise ValueError("canonical_text is required")

    if beat is None:
        beat, cues, confidence = classify_story_beat(canonical_text)
    else:
        beat = beat.strip().upper()
        if beat not in STORY_POLICIES:
            raise ValueError(f"unsupported beat: {beat}")
        cues = ("explicit_beat",)
        confidence = 1.0

    policy = STORY_POLICIES[beat]
    policy.validate()
    segment = DirectedNarrationSegment(
        segment_id=segment_id,
        canonical_text=unicodedata.normalize("NFC", canonical_text).strip(),
        spoken_text=_shape_punctuation(canonical_text, beat),
        beat=beat,
        tempo_factor=policy.tempo_factor,
        pause_before_ms=policy.pause_before_ms,
        pause_after_ms=policy.pause_after_ms,
        emphasis=policy.emphasis,
        energy=policy.energy,
        confidence=confidence,
        cues=tuple(cues),
    )
    segment.validate()
    return segment


def direct_story_text(text: str) -> list[DirectedNarrationSegment]:
    """Create sentence-level story directions while keeping source semantics.

    Sentence-level units intentionally trade some TTS context for better
    semantic pacing control. Adjacent narrative sentences are merged only when
    doing so remains short enough to avoid paragraph-length rushing.
    """

    normalized = unicodedata.normalize("NFC", text).strip()
    if not normalized:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", normalized) if p.strip()]
    raw_units: list[str] = []
    for paragraph in paragraphs:
        sentences = [x.strip() for x in _SENTENCE_SPLIT_RE.split(paragraph) if x.strip()]
        raw_units.extend(sentences or [paragraph])

    segments: list[DirectedNarrationSegment] = []
    pending: str | None = None

    def flush(value: str) -> None:
        idx = len(segments)
        segments.append(direct_story_segment(value, segment_id=f"story_{idx:03d}"))

    for unit in raw_units:
        beat, _cues, _confidence = classify_story_beat(unit)
        if beat == "NARRATIVE" and pending is not None and len(pending) + len(unit) + 1 <= 280:
            pending = pending + " " + unit
            continue

        if pending is not None:
            flush(pending)
            pending = None

        if beat == "NARRATIVE" and len(unit) < 180:
            pending = unit
        else:
            flush(unit)

    if pending is not None:
        flush(pending)

    return segments



def direct_story_clauses(text: str) -> list[DirectedNarrationSegment]:
    """Plan short sentence/clause units so emotion comes from breathing, not slowdown.

    Unlike direct_story_text(), this path never merges adjacent narrative
    sentences. Long sentences may be split at strong semantic punctuation so
    explicit pauses can be inserted between rendered units while every unit
    keeps tempo_factor=1.0.
    """

    normalized = unicodedata.normalize("NFC", text).strip()
    if not normalized:
        return []

    sentences = [
        x.strip()
        for x in re.split(r'(?<=[.!?…]["”]?)\\s+(?=[A-ZÀ-ỸĐ“"])', normalized)
        if x.strip()
    ]
    units: list[str] = []
    for sentence in sentences or [normalized]:
        if len(sentence) <= 125:
            units.append(sentence)
            continue
        parts = [
            x.strip()
            for x in re.split(
                r'(?<=[;:])\\s+|,\\s+(?=(?:nhưng|rồi|còn|và|chỉ|như|khi|nếu|vì|làm|mẹ|minh|anh|bà)\\b)',
                sentence,
                flags=re.IGNORECASE,
            )
            if x.strip()
        ]
        units.extend(parts or [sentence])

    return [
        direct_story_segment(unit, segment_id=f"clause_{idx:03d}")
        for idx, unit in enumerate(units)
    ]


def plan_fingerprint(segments: Iterable[DirectedNarrationSegment]) -> str:
    payload = [
        {
            "segment_id": s.segment_id,
            "canonical_sha256": s.canonical_sha256,
            "spoken_sha256": s.spoken_sha256,
            "beat": s.beat,
            "tempo_factor": s.tempo_factor,
            "pause_before_ms": s.pause_before_ms,
            "pause_after_ms": s.pause_after_ms,
            "director_version": s.director_version,
        }
        for s in segments
    ]
    return canonical_hash(payload)
