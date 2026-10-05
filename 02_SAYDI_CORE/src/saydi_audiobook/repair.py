from __future__ import annotations

from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from hashlib import sha256
import json
import re
import unicodedata

from .pronunciation import (
    AppliedPronunciationOverride,
    PronunciationLexicon,
    build_pronunciation_repair_plan,
)


_TOKEN_RE = re.compile(r"\d+|[A-Za-zÀ-ỹĐđ]+(?:[-'][A-Za-zÀ-ỹĐđ]+)*", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(unicodedata.normalize("NFC", text))


def _token_key(token: str) -> str:
    return unicodedata.normalize("NFC", token).casefold()


def expected_mismatch_tokens(expected: str, heard: str, *, limit: int = 24) -> tuple[str, ...]:
    """Return expected-side tokens involved in ASR replacement/deletion spans.

    The result is deliberately expected-side. ASR low-confidence words may be
    hallucinated or misheard, while pronunciation repair must act only on
    canonical text that actually exists in the book.
    """

    exp = _tokens(expected)
    got = _tokens(heard)
    if not exp:
        return ()

    matcher = SequenceMatcher(
        None,
        [_token_key(x) for x in exp],
        [_token_key(x) for x in got],
        autojunk=False,
    )
    suspects: list[str] = []
    for tag, i1, i2, _j1, _j2 in matcher.get_opcodes():
        if tag in {"replace", "delete"}:
            suspects.extend(exp[i1:i2])
        if len(suspects) >= limit:
            break
    return tuple(dict.fromkeys(suspects[:limit]))


@dataclass(frozen=True, slots=True)
class TargetedPronunciationRepair:
    chunk_index: int
    canonical_text: str
    spoken_text: str
    source_audio_sha256: str
    lexicon_version: str
    expected_suspect_tokens: tuple[str, ...]
    unresolved_suspect_tokens: tuple[str, ...]
    applied_overrides: tuple[AppliedPronunciationOverride, ...]

    @property
    def changed(self) -> bool:
        return self.canonical_text != self.spoken_text

    def meta(self) -> dict:
        return {
            "reason": "pronunciation_qc",
            "lexicon_version": self.lexicon_version,
            "source_audio_sha256": self.source_audio_sha256,
            "expected_suspect_tokens": list(self.expected_suspect_tokens),
            "unresolved_suspect_tokens": list(self.unresolved_suspect_tokens),
            "applied_overrides": [asdict(x) for x in self.applied_overrides],
        }


def build_targeted_pronunciation_repair(
    *,
    chunk_index: int,
    canonical_text: str,
    heard_text: str,
    source_audio_sha256: str,
    lexicon: PronunciationLexicon | None = None,
) -> TargetedPronunciationRepair | None:
    if chunk_index < 0:
        raise ValueError("chunk_index must be >= 0")
    if len(source_audio_sha256) != 64:
        raise ValueError("source_audio_sha256 must be SHA-256 hex")

    suspects = expected_mismatch_tokens(canonical_text, heard_text)
    if not suspects:
        return None

    result = build_pronunciation_repair_plan(
        canonical_text,
        suspect_tokens=suspects,
        lexicon=lexicon,
    )
    if not result.changed or not result.applied_overrides:
        return None

    return TargetedPronunciationRepair(
        chunk_index=chunk_index,
        canonical_text=result.canonical_text,
        spoken_text=result.spoken_text,
        source_audio_sha256=source_audio_sha256,
        lexicon_version=result.lexicon_version,
        expected_suspect_tokens=suspects,
        unresolved_suspect_tokens=result.unresolved_suspect_tokens,
        applied_overrides=result.applied_overrides,
    )


def repair_request_id(
    *,
    job_id: str,
    chunk_index: int,
    source_audio_sha256: str,
    spoken_text: str,
    attempt: int,
) -> str:
    if not job_id.strip():
        raise ValueError("job_id is required")
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    payload = {
        "job_id": job_id,
        "chunk_index": chunk_index,
        "source_audio_sha256": source_audio_sha256,
        "spoken_text": spoken_text,
        "attempt": attempt,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "qc004-" + sha256(raw.encode("utf-8")).hexdigest()[:32]
