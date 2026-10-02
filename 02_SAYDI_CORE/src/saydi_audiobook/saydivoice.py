from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from .contracts import VoiceRequest, VoiceResult, canonical_hash
from .voice import VoiceProvider


SAYDIVOICE_ADAPTER_CONTRACT_VERSION = "saydivoice-adapter-v1"
SAYDIVOICE_SUPPORTED_CONTROLS = frozenset(
    {
        "voice",
        "stability_expression_axis",
        "speed",
        "pause_enabled",
        "output_format",
    }
)
SAYDIVOICE_UNSUPPORTED_SEMANTIC_CONTROLS = frozenset(
    {
        "emotion",
        "mood",
        "prosody",
        "pause_timings",
    }
)


@dataclass(frozen=True, slots=True)
class SaydiVoiceControls:
    default_voice: str = "Adam — Giọng hot tiktok"
    stability_ratio: float = 0.50
    speed_ratio: float = 0.50
    pause_enabled: bool = True
    output_format: Literal["WAV", "MP3", "FLAC", "OGG"] = "MP3"

    def validate(self) -> None:
        if not self.default_voice.strip():
            raise ValueError("default_voice is required")
        for name, value in (
            ("stability_ratio", self.stability_ratio),
            ("speed_ratio", self.speed_ratio),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0,1]")
        if self.output_format not in {"WAV", "MP3", "FLAC", "OGG"}:
            raise ValueError("unsupported SaydiVoice output format")

    @property
    def fingerprint(self) -> str:
        self.validate()
        return canonical_hash(
            {
                "contract_version": SAYDIVOICE_ADAPTER_CONTRACT_VERSION,
                "default_voice": self.default_voice,
                "stability_ratio": self.stability_ratio,
                "speed_ratio": self.speed_ratio,
                "pause_enabled": self.pause_enabled,
                "output_format": self.output_format,
            }
        )


@dataclass(frozen=True, slots=True)
class SaydiVoiceBackendRequest:
    operation_id: str
    sample_id: str
    text: str
    narration_fingerprint: str
    provider_contract_fingerprint: str
    voice: str
    stability_ratio: float
    speed_ratio: float
    pause_enabled: bool
    output_format: Literal["WAV", "MP3", "FLAC", "OGG"]
    output_path: str


@dataclass(frozen=True, slots=True)
class SaydiVoiceBackendResult:
    operation_id: str
    sample_id: str
    status: Literal["SUCCESS", "FAILED", "ACTION_REQUIRED"]
    local_audio_path: str | None = None
    audio_sha256: str | None = None
    byte_count: int = 0
    duration_ms: int | None = None
    provider_reference: str | None = None
    error_class: str | None = None
    retryable: bool = False
    attempt: int = 1


class SaydiVoiceBackend(Protocol):
    """Provider/browser implementation boundary.

    A concrete implementation may use browser automation, but that implementation
    lives outside the audiobook core. This protocol is deliberately data-only.
    """

    def synthesize(self, request: SaydiVoiceBackendRequest) -> SaydiVoiceBackendResult:
        ...


def _safe_provider_reference(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value or len(value) > 200:
        return None
    lowered = value.lower()
    if "://" in value or any(token in lowered for token in ("token", "cookie", "authorization", "bearer ")):
        return None
    return value


class SaydiVoiceAdapter(VoiceProvider):
    provider_name = "saydivoice"

    def __init__(self, backend: SaydiVoiceBackend, *, controls: SaydiVoiceControls | None = None):
        self.backend = backend
        self.controls = controls or SaydiVoiceControls()
        self.controls.validate()

    @property
    def output_format(self) -> str:
        return self.controls.output_format

    @property
    def narration_settings_fingerprint(self) -> str:
        return self.controls.fingerprint

    def _action_required(self, request: VoiceRequest, error_class: str, *, voice: str | None = None) -> VoiceResult:
        return VoiceResult(
            operation_id=request.operation_id,
            sample_id=request.sample_id,
            status="ACTION_REQUIRED",
            provider=self.provider_name,
            local_audio_path=None,
            audio_sha256=None,
            byte_count=0,
            duration_ms=None,
            error_class=error_class,
            retryable=False,
            provider_voice=voice,
        )

    def generate(self, request: VoiceRequest) -> VoiceResult:
        request.validate()
        self.controls.validate()

        # SaydiVoice exposes a real voice selector and a single expression↔stability
        # axis. No field evidence supports a discrete mood/emotion/prosody selector.
        if request.style_key:
            return self._action_required(request, "unsupported_semantic_style")

        if request.output_format != self.controls.output_format:
            return self._action_required(request, "output_format_contract_mismatch")

        expected_suffix = "." + self.controls.output_format.lower()
        if Path(request.output_path).suffix.lower() != expected_suffix:
            return self._action_required(request, "output_path_format_mismatch")

        voice = self.controls.default_voice if request.voice_key == "default" else request.voice_key
        command = SaydiVoiceBackendRequest(
            operation_id=request.operation_id,
            sample_id=request.sample_id,
            text=request.text,
            narration_fingerprint=request.narration_fingerprint,
            provider_contract_fingerprint=self.narration_settings_fingerprint,
            voice=voice,
            stability_ratio=self.controls.stability_ratio,
            speed_ratio=self.controls.speed_ratio,
            pause_enabled=self.controls.pause_enabled,
            output_format=self.controls.output_format,
            output_path=request.output_path,
        )

        try:
            backend_result = self.backend.synthesize(command)
        except Exception:
            return VoiceResult(
                operation_id=request.operation_id,
                sample_id=request.sample_id,
                status="FAILED",
                provider=self.provider_name,
                local_audio_path=None,
                audio_sha256=None,
                byte_count=0,
                duration_ms=None,
                error_class="saydivoice_backend_error",
                retryable=False,
                provider_voice=voice,
            )

        if (
            backend_result.operation_id != request.operation_id
            or backend_result.sample_id != request.sample_id
        ):
            return VoiceResult(
                operation_id=request.operation_id,
                sample_id=request.sample_id,
                status="FAILED",
                provider=self.provider_name,
                local_audio_path=None,
                audio_sha256=None,
                byte_count=0,
                duration_ms=None,
                error_class="provider_result_identity_mismatch",
                retryable=False,
                provider_voice=voice,
            )

        result = VoiceResult(
            operation_id=request.operation_id,
            sample_id=request.sample_id,
            status=backend_result.status,
            provider=self.provider_name,
            local_audio_path=backend_result.local_audio_path,
            audio_sha256=backend_result.audio_sha256,
            byte_count=backend_result.byte_count,
            duration_ms=backend_result.duration_ms,
            error_class=backend_result.error_class,
            retryable=backend_result.retryable,
            provider_voice=voice,
            provider_reference=_safe_provider_reference(backend_result.provider_reference),
            attempt=backend_result.attempt,
        )
        result.validate()
        return result
