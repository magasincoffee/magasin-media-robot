from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import re
import unicodedata
from typing import Iterable, Sequence

from .director import classify_story_beat


EDITORIAL_QA_VERSION = "editorial-qa-v1"

_SENTENCE_RE = re.compile(r'.+?(?:[.!?…](?:["”])?|$)(?=\s+|$)', re.UNICODE)
_STRONG_SPLIT_RE = re.compile(
    r'(?<=[;:])\s+|,\s+(?=(?:nhưng|rồi|còn|và|chỉ|như|khi|nếu|vì|làm|mẹ|cha|anh|bà|ông|tôi|chúng ta)\b)',
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class EditorialReadingUnit:
    unit_id: str
    canonical_text: str
    spoken_text: str
    beat: str
    pause_after_ms: int
    emphasis_phrases: tuple[str, ...]
    must_check_phrases: tuple[str, ...]
    pronunciation_qc_required: bool
    editorial_version: str = EDITORIAL_QA_VERSION

    @property
    def canonical_sha256(self) -> str:
        return sha256(self.canonical_text.encode("utf-8")).hexdigest()

    @property
    def spoken_sha256(self) -> str:
        return sha256(self.spoken_text.encode("utf-8")).hexdigest()

    def as_manifest_item(self) -> dict:
        payload = asdict(self)
        payload["canonical_sha256"] = self.canonical_sha256
        payload["spoken_sha256"] = self.spoken_sha256
        return payload


def _normalize_phrase(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


def _phrase_hits(text: str, phrases: Sequence[str]) -> tuple[str, ...]:
    folded = unicodedata.normalize("NFC", text).casefold()
    hits: list[str] = []
    for phrase in phrases:
        normalized = _normalize_phrase(phrase)
        if normalized and normalized.casefold() in folded:
            hits.append(normalized)
    return tuple(dict.fromkeys(hits))


def _pause_for_unit(text: str, beat: str) -> int:
    stripped = text.rstrip()
    if stripped.endswith(("…", "...")):
        base = 800
    elif stripped.endswith("?"):
        base = 650
    elif stripped.endswith("!"):
        base = 550
    elif stripped.endswith((".", "”", '"')):
        base = 450
    elif stripped.endswith((",", ";", ":")):
        base = 300
    else:
        base = 380

    if beat in {"REFLECTIVE_SAD", "DIALOGUE_TENDER"}:
        base += 180
    elif beat == "SCENE_TRANSITION":
        base += 350
    elif beat == "RESOLUTION":
        base += 450
    elif beat == "TENSION":
        base = max(280, base - 80)

    return min(base, 1500)


def split_for_editorial_reading(text: str, *, max_chars: int = 150) -> list[str]:
    """Split source into short semantic units without paraphrasing it.

    The returned strings preserve source words. Only whitespace at unit
    boundaries is normalized. Long sentences are split at strong punctuation
    so VieNeu receives enough context to sound natural without being forced to
    rush through a paragraph-sized chunk.
    """

    normalized = unicodedata.normalize("NFC", text).strip()
    if not normalized:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", normalized) if p.strip()]
    units: list[str] = []

    for paragraph in paragraphs:
        sentences = [x.strip() for x in _SENTENCE_RE.findall(paragraph) if x.strip()]
        for sentence in sentences or [paragraph]:
            if len(sentence) <= max_chars:
                units.append(sentence)
                continue

            parts = [x.strip() for x in _STRONG_SPLIT_RE.split(sentence) if x.strip()]
            if len(parts) == 1:
                units.append(sentence)
            else:
                units.extend(parts)

    return units


def compile_editorial_reading(
    text: str,
    *,
    must_check_phrases: Iterable[str] = (),
    emphasis_phrases: Iterable[str] = (),
    max_chars: int = 150,
) -> list[EditorialReadingUnit]:
    """Create a deterministic pre-render reading script for VieNeu.

    This stage decides *how the text should be delivered* before synthesis:
    semantic chunking, pause intent, emphasis metadata and phrases that must be
    verified by post-render pronunciation QC. It never treats pre-render
    editing as a substitute for post-render QC.
    """

    must_check = tuple(_normalize_phrase(x) for x in must_check_phrases if _normalize_phrase(x))
    emphasis = tuple(_normalize_phrase(x) for x in emphasis_phrases if _normalize_phrase(x))

    items: list[EditorialReadingUnit] = []
    for idx, unit in enumerate(split_for_editorial_reading(text, max_chars=max_chars)):
        beat, _cues, _confidence = classify_story_beat(unit)
        check_hits = _phrase_hits(unit, must_check)
        emphasis_hits = _phrase_hits(unit, emphasis)
        items.append(
            EditorialReadingUnit(
                unit_id=f"editorial_{idx:04d}",
                canonical_text=unit,
                spoken_text=unit,
                beat=beat,
                pause_after_ms=_pause_for_unit(unit, beat),
                emphasis_phrases=emphasis_hits,
                must_check_phrases=check_hits,
                pronunciation_qc_required=bool(check_hits),
            )
        )

    return items


def editorial_manifest(
    text: str,
    *,
    must_check_phrases: Iterable[str] = (),
    emphasis_phrases: Iterable[str] = (),
    max_chars: int = 150,
) -> dict:
    normalized = unicodedata.normalize("NFC", text).strip()
    units = compile_editorial_reading(
        normalized,
        must_check_phrases=must_check_phrases,
        emphasis_phrases=emphasis_phrases,
        max_chars=max_chars,
    )
    manifest_units = [item.as_manifest_item() for item in units]
    render_segments = [
        {
            "index": idx,
            "beat": item.beat,
            "tempo_factor": 1.0,
            "pause_before_ms": 0,
            "pause_after_ms": item.pause_after_ms,
            "canonical_text": item.canonical_text,
            "spoken_text": item.spoken_text,
            "emphasis_phrases": list(item.emphasis_phrases),
            "must_check_phrases": list(item.must_check_phrases),
            "pronunciation_qc_required": item.pronunciation_qc_required,
            "editorial_unit_id": item.unit_id,
            "canonical_sha256": item.canonical_sha256,
            "spoken_sha256": item.spoken_sha256,
        }
        for idx, item in enumerate(units)
    ]
    return {
        "schema_version": EDITORIAL_QA_VERSION,
        "source_sha256": sha256(normalized.encode("utf-8")).hexdigest(),
        "unit_count": len(units),
        "post_render_qc_required": True,
        "units": manifest_units,
        "segments": render_segments,
    }
