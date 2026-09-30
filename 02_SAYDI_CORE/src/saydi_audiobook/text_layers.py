from __future__ import annotations

from hashlib import sha256
import re
import unicodedata

from .contracts import TextLayers


_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?])")
_SPACE_AFTER_PUNCT = re.compile(r"([,.;:!?])(?=[^\s\n])")
_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_BLANK = re.compile(r"\n{3,}")


def normalize_text(raw: str) -> str:
    text = unicodedata.normalize("NFC", raw.replace("\r\n", "\n").replace("\r", "\n"))
    lines = [_MULTI_SPACE.sub(" ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = _SPACE_AFTER_PUNCT.sub(r"\1 ", text)
    text = _MULTI_BLANK.sub("\n\n", text)
    return text.strip()


def spoken_render(normalized: str) -> str:
    # Deliberately conservative in the first slice: preserve words and meaning.
    # More ambitious punctuation/number/unit interpretation belongs to SAYDI-004.
    paragraphs: list[str] = []
    for p in (x.strip() for x in normalized.split("\n\n")):
        if not p:
            continue
        if p[-1] not in ".!?…:;\"'”’":
            p = p + "."
        paragraphs.append(p)
    return "\n\n".join(paragraphs)


def build_text_layers(raw: str) -> TextLayers:
    source_sha = sha256(raw.encode("utf-8")).hexdigest()
    normalized = normalize_text(raw)
    layers = TextLayers(
        original_text=raw,
        normalized_text=normalized,
        spoken_text=spoken_render(normalized),
        source_sha256=source_sha,
    )
    layers.validate()
    return layers
