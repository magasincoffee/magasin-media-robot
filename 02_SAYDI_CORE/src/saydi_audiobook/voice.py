from __future__ import annotations

from abc import ABC, abstractmethod
from hashlib import sha256
from pathlib import Path
import platform
import subprocess

from .contracts import VoiceRequest, VoiceResult, canonical_hash


class VoiceProvider(ABC):
    provider_name = "voice-provider"
    output_format = "WAV"

    @property
    def narration_settings_fingerprint(self) -> str:
        return canonical_hash(
            {
                "provider": self.provider_name,
                "output_format": self.output_format,
            }
        )

    @abstractmethod
    def generate(self, request: VoiceRequest) -> VoiceResult:
        raise NotImplementedError


class WindowsSapiVoiceProvider(VoiceProvider):
    """Zero-API-cost local prototype voice provider for Windows workflow validation.

    This is not a claim of production audiobook narrator quality. It exists to
    prove the local audible approval workflow before a higher-quality local TTS
    backend is selected and benchmarked.
    """

    provider_name = "windows-sapi-prototype"
    output_format = "WAV"

    def __init__(self, *, rate: int = 0, voice_name: str | None = None):
        if not -10 <= rate <= 10:
            raise ValueError("SAPI rate must be within [-10,10]")
        self.rate = rate
        self.voice_name = voice_name

    @property
    def narration_settings_fingerprint(self) -> str:
        return canonical_hash(
            {
                "provider": self.provider_name,
                "output_format": self.output_format,
                "rate": self.rate,
                "voice_name": self.voice_name or "default",
            }
        )

    def generate(self, request: VoiceRequest) -> VoiceResult:
        request.validate()
        if request.output_format != "WAV":
            return VoiceResult(
                operation_id=request.operation_id,
                sample_id=request.sample_id,
                status="ACTION_REQUIRED",
                provider=self.provider_name,
                local_audio_path=None,
                audio_sha256=None,
                byte_count=0,
                duration_ms=None,
                error_class="unsupported_output_format",
                retryable=False,
                provider_voice=self.voice_name,
            )
        if platform.system().lower() != "windows":
            return VoiceResult(
                operation_id=request.operation_id,
                sample_id=request.sample_id,
                status="ACTION_REQUIRED",
                provider=self.provider_name,
                local_audio_path=None,
                audio_sha256=None,
                byte_count=0,
                duration_ms=None,
                error_class="windows_required",
                retryable=False,
                provider_voice=self.voice_name,
            )

        out = Path(request.output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        ps = r'''
param([string]$Text,[string]$Output,[int]$Rate,[string]$VoiceName)
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  $s.Rate = $Rate
  if ($VoiceName) { $s.SelectVoice($VoiceName) }
  $s.SetOutputToWaveFile($Output)
  $s.Speak($Text)
} finally {
  $s.Dispose()
}
'''
        script = out.parent / f".{request.operation_id}.sapi.ps1"
        script.write_text(ps, encoding="utf-8")
        try:
            proc = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script),
                    "-Text",
                    request.text,
                    "-Output",
                    str(out),
                    "-Rate",
                    str(self.rate),
                    "-VoiceName",
                    self.voice_name or "",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode != 0 or not out.exists() or out.stat().st_size <= 44:
                return VoiceResult(
                    operation_id=request.operation_id,
                    sample_id=request.sample_id,
                    status="FAILED",
                    provider=self.provider_name,
                    local_audio_path=str(out) if out.exists() else None,
                    audio_sha256=None,
                    byte_count=out.stat().st_size if out.exists() else 0,
                    duration_ms=None,
                    error_class="sapi_generation_failed",
                    retryable=False,
                    provider_voice=self.voice_name,
                )
            data = out.read_bytes()
            return VoiceResult(
                operation_id=request.operation_id,
                sample_id=request.sample_id,
                status="SUCCESS",
                provider=self.provider_name,
                local_audio_path=str(out),
                audio_sha256=sha256(data).hexdigest(),
                byte_count=len(data),
                duration_ms=None,
                provider_voice=self.voice_name,
            )
        finally:
            try:
                script.unlink(missing_ok=True)
            except Exception:
                pass
