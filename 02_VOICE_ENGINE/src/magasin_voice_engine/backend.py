from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .models import (
    AppliedSettings,
    DownloadReceipt,
    FailureDisposition,
    GenerationReceipt,
    PreflightResult,
)
from .presets import VoicePreset


class VoiceBackendError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        disposition: FailureDisposition = FailureDisposition.DO_NOT_RETRY,
        code: str = "BACKEND_ERROR",
    ) -> None:
        super().__init__(message)
        self.disposition = disposition
        self.code = code


class VoiceBackend(Protocol):
    provider_name: str

    def preflight(self) -> PreflightResult:
        """Open/inspect the provider without performing Generate or Download."""
        ...

    def apply_settings(self, preset: VoicePreset) -> AppliedSettings:
        """Apply and verify the requested voice/style controls."""
        ...

    def generate(self, text: str, *, timeout_seconds: float) -> GenerationReceipt:
        """Perform exactly one Generate attempt. Backend implementations must not retry."""
        ...

    def download(self, output_directory: Path, *, timeout_seconds: float) -> DownloadReceipt:
        """Download the already generated result exactly once."""
        ...

    def close(self) -> None:
        ...
