from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Literal


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TextLayers:
    original_text: str
    normalized_text: str
    spoken_text: str
    source_sha256: str
    normalization_version: str = "text-v0.1"

    def validate(self) -> None:
        if not self.original_text.strip():
            raise ValueError("original_text is required")
        if not self.normalized_text.strip():
            raise ValueError("normalized_text is required")
        if not self.spoken_text.strip():
            raise ValueError("spoken_text is required")
        if len(self.source_sha256) != 64:
            raise ValueError("source_sha256 must be SHA-256 hex")


@dataclass(frozen=True, slots=True)
class BookProfile:
    genre: str
    subgenre: str
    tone: list[str]
    dialogue_density: Literal["low", "medium", "high"]
    technical_density: Literal["low", "medium", "high"]
    recommended_narration_profiles: list[str]
    confidence: float
    analysis_provider: str
    evidence: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.genre:
            raise ValueError("genre is required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0,1]")
        if not self.recommended_narration_profiles:
            raise ValueError("at least one narration profile is required")


@dataclass(frozen=True, slots=True)
class NarrationProfile:
    key: str
    label: str
    semantic_style: str
    pace: str
    expression: float
    stability: float
    pause_policy: str
    pronunciation_lexicon_version: str = "lexicon-v0"
    voice_provider: str = "unselected"
    voice_key: str = "default"
    model_key: str = "default"

    def validate(self) -> None:
        if not self.key.strip():
            raise ValueError("profile key is required")
        for name, value in (("expression", self.expression), ("stability", self.stability)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0,1]")

    @property
    def fingerprint(self) -> str:
        return canonical_hash(asdict(self))


@dataclass(frozen=True, slots=True)
class SamplePassage:
    sample_id: str
    text: str
    reason: str
    ordinal: int


@dataclass(frozen=True, slots=True)
class VoiceRequest:
    operation_id: str
    sample_id: str
    text: str
    narration_fingerprint: str
    voice_key: str
    output_path: str
    style_key: str | None = None
    output_format: Literal["WAV", "MP3", "FLAC", "OGG"] = "WAV"

    def validate(self) -> None:
        if not self.operation_id or not self.sample_id or not self.text.strip():
            raise ValueError("operation_id, sample_id and text are required")
        if len(self.narration_fingerprint) != 64:
            raise ValueError("narration_fingerprint must be SHA-256 hex")
        if not self.voice_key.strip():
            raise ValueError("voice_key is required")
        if self.output_format not in {"WAV", "MP3", "FLAC", "OGG"}:
            raise ValueError("output_format is unsupported")
        if not self.output_path.strip():
            raise ValueError("output_path is required")


@dataclass(frozen=True, slots=True)
class VoiceResult:
    operation_id: str
    sample_id: str
    status: Literal["SUCCESS", "FAILED", "ACTION_REQUIRED"]
    provider: str
    local_audio_path: str | None
    audio_sha256: str | None
    byte_count: int
    duration_ms: int | None
    error_class: str | None = None
    retryable: bool = False
    provider_voice: str | None = None
    provider_reference: str | None = None
    attempt: int = 1

    def validate(self) -> None:
        if not self.operation_id or not self.sample_id or not self.provider:
            raise ValueError("operation_id, sample_id and provider are required")
        if self.byte_count < 0:
            raise ValueError("byte_count must be >= 0")
        if self.attempt < 1:
            raise ValueError("attempt must be >= 1")
        if self.audio_sha256 is not None and len(self.audio_sha256) != 64:
            raise ValueError("audio_sha256 must be SHA-256 hex when present")
        if self.status == "SUCCESS":
            if not self.local_audio_path or not self.audio_sha256 or self.byte_count <= 0:
                raise ValueError("successful result requires path/hash/bytes")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
