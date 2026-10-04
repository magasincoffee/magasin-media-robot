from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
import json
from pathlib import Path
import re
import unicodedata
from typing import Iterable, Literal


PronunciationCategory = Literal[
    "abbreviation",
    "unit",
    "name",
    "foreign_term",
    "number",
    "other",
]


@dataclass(frozen=True, slots=True)
class PronunciationEntry:
    key: str
    source: str
    spoken: str
    category: PronunciationCategory
    case_sensitive: bool = False
    whole_word: bool = True

    def validate(self) -> None:
        if not self.key.strip():
            raise ValueError("pronunciation key is required")
        if not self.source.strip():
            raise ValueError("pronunciation source is required")
        if not self.spoken.strip():
            raise ValueError("pronunciation spoken form is required")
        if self.category not in {
            "abbreviation",
            "unit",
            "name",
            "foreign_term",
            "number",
            "other",
        }:
            raise ValueError(f"unsupported pronunciation category: {self.category}")


@dataclass(frozen=True, slots=True)
class PronunciationLexicon:
    version: str
    locale: str
    entries: tuple[PronunciationEntry, ...]

    def validate(self) -> None:
        if not self.version.strip():
            raise ValueError("lexicon version is required")
        if not self.locale.strip():
            raise ValueError("lexicon locale is required")

        keys: set[str] = set()
        identity: set[tuple[str, bool, bool]] = set()
        for entry in self.entries:
            entry.validate()
            if entry.key in keys:
                raise ValueError(f"duplicate pronunciation key: {entry.key}")
            keys.add(entry.key)

            source_key = (
                unicodedata.normalize("NFC", entry.source)
                if entry.case_sensitive
                else unicodedata.normalize("NFC", entry.source).casefold()
            )
            signature = (source_key, entry.case_sensitive, entry.whole_word)
            if signature in identity:
                raise ValueError(f"duplicate pronunciation source: {entry.source}")
            identity.add(signature)

    @classmethod
    def from_dict(cls, payload: dict) -> "PronunciationLexicon":
        entries = tuple(
            PronunciationEntry(
                key=str(item["key"]),
                source=str(item["source"]),
                spoken=str(item["spoken"]),
                category=str(item["category"]),
                case_sensitive=bool(item.get("case_sensitive", False)),
                whole_word=bool(item.get("whole_word", True)),
            )
            for item in payload.get("entries", [])
        )
        lexicon = cls(
            version=str(payload["version"]),
            locale=str(payload.get("locale", "vi-VN")),
            entries=entries,
        )
        lexicon.validate()
        return lexicon


@dataclass(frozen=True, slots=True)
class AppliedPronunciationOverride:
    key: str
    category: PronunciationCategory
    source_text: str
    spoken_text: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class SpokenFormResult:
    canonical_text: str
    spoken_text: str
    lexicon_version: str
    applied_overrides: tuple[AppliedPronunciationOverride, ...]
    unresolved_suspect_tokens: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return self.canonical_text != self.spoken_text


@dataclass(frozen=True, slots=True)
class _Candidate:
    start: int
    end: int
    entry: PronunciationEntry
    source_text: str


def load_pronunciation_lexicon(path: str | Path) -> PronunciationLexicon:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return PronunciationLexicon.from_dict(payload)


def load_default_vietnamese_lexicon() -> PronunciationLexicon:
    data = resources.files("saydi_audiobook").joinpath("data/vi_pronunciation_lexicon_v1.json")
    payload = json.loads(data.read_text(encoding="utf-8"))
    return PronunciationLexicon.from_dict(payload)


def _entry_matches(text: str, entry: PronunciationEntry) -> list[_Candidate]:
    source = unicodedata.normalize("NFC", entry.source)
    escaped = re.escape(source)
    if entry.whole_word:
        escaped = rf"(?<!\w){escaped}(?!\w)"
    flags = 0 if entry.case_sensitive else re.IGNORECASE
    return [
        _Candidate(
            start=m.start(),
            end=m.end(),
            entry=entry,
            source_text=text[m.start():m.end()],
        )
        for m in re.finditer(escaped, text, flags)
    ]


def _resolve_overlaps(candidates: Iterable[_Candidate]) -> list[_Candidate]:
    # Earliest source position wins; at the same position the longest explicit
    # lexicon entry wins. This allows "CEO Việt Nam" to outrank "CEO".
    ordered = sorted(
        candidates,
        key=lambda x: (x.start, -(x.end - x.start), x.entry.key),
    )
    selected: list[_Candidate] = []
    occupied_until = -1
    for candidate in ordered:
        if candidate.start < occupied_until:
            continue
        selected.append(candidate)
        occupied_until = candidate.end
    return selected


_VI_DIGITS = {
    0: "không",
    1: "một",
    2: "hai",
    3: "ba",
    4: "bốn",
    5: "năm",
    6: "sáu",
    7: "bảy",
    8: "tám",
    9: "chín",
}


def _read_two_digits(value: int, *, full: bool = False) -> str:
    if not 0 <= value <= 99:
        raise ValueError("two-digit value out of range")
    tens, ones = divmod(value, 10)
    if tens == 0:
        if full and ones:
            return "lẻ " + _VI_DIGITS[ones]
        return _VI_DIGITS[ones] if ones else ""

    if tens == 1:
        prefix = "mười"
    else:
        prefix = _VI_DIGITS[tens] + " mươi"

    if ones == 0:
        return prefix
    if ones == 1 and tens > 1:
        suffix = "mốt"
    elif ones == 5 and tens >= 1:
        suffix = "lăm"
    else:
        suffix = _VI_DIGITS[ones]
    return prefix + " " + suffix


def _read_three_digits(value: int, *, force_hundreds: bool = False) -> str:
    if not 0 <= value <= 999:
        raise ValueError("three-digit value out of range")
    hundreds, rest = divmod(value, 100)
    parts: list[str] = []
    if hundreds:
        parts.extend((_VI_DIGITS[hundreds], "trăm"))
        if rest:
            parts.append(_read_two_digits(rest, full=rest < 10))
    elif force_hundreds and rest:
        parts.extend(("không", "trăm", _read_two_digits(rest, full=rest < 10)))
    elif rest:
        parts.append(_read_two_digits(rest))
    return " ".join(x for x in parts if x)


def vietnamese_integer_spoken_form(token: str) -> str | None:
    """Return a conservative Vietnamese spoken form for 0..999999.

    Larger identifiers, decimals, phone numbers and mixed alphanumeric tokens
    are intentionally left unchanged because their intended reading depends on
    semantic context.
    """

    if not re.fullmatch(r"\d{1,6}", token):
        return None
    value = int(token)
    if value == 0:
        return _VI_DIGITS[0]

    thousands, rest = divmod(value, 1000)
    parts: list[str] = []
    if thousands:
        parts.append(_read_three_digits(thousands))
        parts.append("nghìn")
        if rest:
            parts.append(_read_three_digits(rest, force_hundreds=rest < 100))
    else:
        parts.append(_read_three_digits(rest))
    return " ".join(x for x in parts if x)


_NUMBER_RE = re.compile(r"(?<![\w.,])\d{1,6}(?![\w.,])")


def _number_candidates(text: str) -> list[_Candidate]:
    out: list[_Candidate] = []
    for match in _NUMBER_RE.finditer(text):
        source = match.group(0)
        spoken = vietnamese_integer_spoken_form(source)
        if not spoken or spoken == source:
            continue
        entry = PronunciationEntry(
            key=f"number:{source}",
            source=source,
            spoken=spoken,
            category="number",
            case_sensitive=True,
            whole_word=True,
        )
        out.append(
            _Candidate(
                start=match.start(),
                end=match.end(),
                entry=entry,
                source_text=source,
            )
        )
    return out


def _normalized_token(value: str) -> str:
    value = unicodedata.normalize("NFC", value).casefold().strip()
    value = re.sub(r"^[^\wÀ-ỹĐđ]+|[^\wÀ-ỹĐđ]+$", "", value)
    return re.sub(r"\s+", " ", value)


def build_spoken_form(
    canonical_text: str,
    *,
    lexicon: PronunciationLexicon | None = None,
    normalize_integers: bool = True,
    suspect_tokens: Iterable[str] | None = None,
) -> SpokenFormResult:
    """Create a TTS-only spoken form without mutating canonical text.

    When suspect_tokens is provided, explicit lexicon replacements are limited
    to entries whose source is named by the suspect set. This makes the function
    safe for targeted QC repair planning. Integer normalization is likewise
    limited to suspect numeric tokens in targeted mode.
    """

    if not isinstance(canonical_text, str) or not canonical_text:
        raise ValueError("canonical_text is required")

    canonical = unicodedata.normalize("NFC", canonical_text)
    lexicon = lexicon or load_default_vietnamese_lexicon()
    lexicon.validate()

    suspects = None
    if suspect_tokens is not None:
        suspects = tuple(str(x) for x in suspect_tokens if str(x).strip())
        suspect_norm = {_normalized_token(x) for x in suspects}
    else:
        suspect_norm = set()

    candidates: list[_Candidate] = []
    for entry in lexicon.entries:
        if suspects is not None and _normalized_token(entry.source) not in suspect_norm:
            continue
        candidates.extend(_entry_matches(canonical, entry))

    if normalize_integers:
        for candidate in _number_candidates(canonical):
            if suspects is not None and _normalized_token(candidate.source_text) not in suspect_norm:
                continue
            candidates.append(candidate)

    selected = _resolve_overlaps(candidates)

    pieces: list[str] = []
    applied: list[AppliedPronunciationOverride] = []
    cursor = 0
    for candidate in selected:
        pieces.append(canonical[cursor:candidate.start])
        pieces.append(candidate.entry.spoken)
        applied.append(
            AppliedPronunciationOverride(
                key=candidate.entry.key,
                category=candidate.entry.category,
                source_text=candidate.source_text,
                spoken_text=candidate.entry.spoken,
                start=candidate.start,
                end=candidate.end,
            )
        )
        cursor = candidate.end
    pieces.append(canonical[cursor:])
    spoken = "".join(pieces)

    unresolved: list[str] = []
    if suspects is not None:
        resolved_sources = {
            _normalized_token(item.source_text)
            for item in applied
        }
        for token in suspects:
            normalized = _normalized_token(token)
            if normalized and normalized not in resolved_sources:
                unresolved.append(token)

    return SpokenFormResult(
        canonical_text=canonical,
        spoken_text=spoken,
        lexicon_version=lexicon.version,
        applied_overrides=tuple(applied),
        unresolved_suspect_tokens=tuple(dict.fromkeys(unresolved)),
    )


def build_pronunciation_repair_plan(
    canonical_text: str,
    suspect_tokens: Iterable[str],
    *,
    lexicon: PronunciationLexicon | None = None,
) -> SpokenFormResult:
    """Build a targeted, non-destructive spoken-form repair proposal."""

    return build_spoken_form(
        canonical_text,
        lexicon=lexicon,
        normalize_integers=True,
        suspect_tokens=suspect_tokens,
    )
