from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

MAX_TEXT_CHARS = 20_000
SUPPORTED_FORMATS = frozenset({"WAV", "MP3", "FLAC", "OGG"})


class RunState(StrEnum):
    SUCCESS = "SUCCESS"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    FATAL_FAILURE = "FATAL_FAILURE"


class FailureDisposition(StrEnum):
    FIX_INPUT = "fix_input"
    RE_AUTH = "re_auth"
    RETRY = "retry"
    DO_NOT_RETRY = "do_not_retry"


@dataclass(frozen=True, slots=True)
class VoiceRequest:
    text: str
    preset_key: str = "review_natural"
    voice_override: str | None = None
    format_override: str | None = None
    output_directory: Path = field(default_factory=Path.cwd)
    allow_generate: bool = False
    allow_download: bool = False
    generation_timeout_seconds: float = 90.0
    download_timeout_seconds: float = 20.0

    def validate(self) -> None:
        if not self.text or not self.text.strip():
            raise ValueError("text must not be empty")
        if len(self.text) > MAX_TEXT_CHARS:
            raise ValueError(f"text exceeds {MAX_TEXT_CHARS} characters")
        if not self.preset_key.strip():
            raise ValueError("preset_key is required")
        if self.voice_override is not None and not self.voice_override.strip():
            raise ValueError("voice_override must not be blank")
        if self.format_override is not None and self.format_override.upper() not in SUPPORTED_FORMATS:
            raise ValueError(f"unsupported format_override: {self.format_override}")
        if self.generation_timeout_seconds <= 0:
            raise ValueError("generation_timeout_seconds must be > 0")
        if self.download_timeout_seconds <= 0:
            raise ValueError("download_timeout_seconds must be > 0")
        if self.allow_download and not self.allow_generate:
            raise ValueError("allow_download requires allow_generate")


@dataclass(frozen=True, slots=True)
class PreflightResult:
    ready: bool
    page_state: str
    auth_state: str
    voice: str | None = None
    audio_format: str | None = None
    error_message: str | None = None
    disposition: FailureDisposition | None = None


@dataclass(frozen=True, slots=True)
class AppliedSettings:
    voice: str
    preset_key: str
    stability_ratio: float
    speed_ratio: float
    audio_format: str
    pause_enabled: bool


@dataclass(frozen=True, slots=True)
class GenerationReceipt:
    success: bool
    terminal_state: str
    attempt_count: int
    provider_history_created: bool = False
    content_type: str | None = None
    error_message: str | None = None
    disposition: FailureDisposition | None = None


@dataclass(frozen=True, slots=True)
class DownloadReceipt:
    success: bool
    local_audio_path: Path | None = None
    byte_count: int | None = None
    sha256: str | None = None
    suggested_filename: str | None = None
    error_message: str | None = None
    disposition: FailureDisposition | None = None


@dataclass(frozen=True, slots=True)
class VoiceResult:
    status: RunState
    provider: str
    preset_key: str
    voice: str | None = None
    audio_format: str | None = None
    local_audio_path: Path | None = None
    byte_count: int | None = None
    sha256: str | None = None
    provider_history_created: bool = False
    generation_attempt_count: int = 0
    error_class: FailureDisposition | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["error_class"] = self.error_class.value if self.error_class else None
        payload["local_audio_path"] = str(self.local_audio_path) if self.local_audio_path else None
        return payload
