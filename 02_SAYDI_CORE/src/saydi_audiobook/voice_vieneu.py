"""Opt-in VieNeu v3 Turbo ONNX adapter for isolated SAYDI V6 runs.

SOURCE COMPONENT ONLY. Importing this module does not start a model, worker
or authorize SAYDI START. The independent trusted H4 runtime controller must
supply admission() that verifies genuine Owner grant, V6-local START/STOP
generation, locks, source provenance, RAM, storage and worker ownership.
Never treat this callable, CI mocks or a GitHub Issue as authentication.
No production entrypoint installs or invokes this provider yet.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Callable
import gc
import platform
import socket
import wave

from .contracts import VoiceRequest, VoiceResult, canonical_hash
from .voice import VoiceProvider

HOST = "DESKTOP-H4A16IL"


class VieNeuOnnxVoiceProvider(VoiceProvider):
    provider_name = "vieneu-v3-turbo-onnx-v6-candidate"
    output_format = "WAV"

    def __init__(
        self,
        *,
        v6_output_root: Path,
        voice_name: str,
        host_admission: Callable[[], Any] | None = None,
        engine_factory: Callable[[], Any] | None = None,
    ):
        if not voice_name or not voice_name.strip():
            raise ValueError("VOICE_CANDIDATE_REQUIRED")
        self.output_root = Path(v6_output_root)
        self.voice_name = voice_name
        # Defaults are intentionally HOLD; production caller must use a
        # separately reviewed, authenticated H4 host source.
        self._host_admission = host_admission
        self._engine_factory = engine_factory

    @property
    def narration_settings_fingerprint(self) -> str:
        return canonical_hash({
            "provider": self.provider_name,
            "voice_candidate": self.voice_name,
            "backend": "onnx",
            "output_format": "WAV",
            "revision": "v6-audition-contract-v1",
        })

    def _result(self, request: VoiceRequest, status: str, *,
                output: Path | None = None, error: str | None = None) -> VoiceResult:
        audio_hash = None
        count = 0
        duration_ms = None
        if status == "SUCCESS" and output is not None:
            data = output.read_bytes()
            count = len(data)
            audio_hash = sha256(data).hexdigest()
            with wave.open(str(output), "rb") as reader:
                duration_ms = round(1000 * reader.getnframes() / reader.getframerate())
        return VoiceResult(
            operation_id=request.operation_id,
            sample_id=request.sample_id,
            status=status,
            provider=self.provider_name,
            local_audio_path=str(output) if status == "SUCCESS" else None,
            audio_sha256=audio_hash,
            byte_count=count,
            duration_ms=duration_ms,
            error_class=error,
            retryable=False,
            provider_voice=self.voice_name,
            provider_reference=None,
        )

    def generate(self, request: VoiceRequest) -> VoiceResult:
        request.validate()
        if request.output_format != "WAV" or request.voice_key not in ("default", self.voice_name):
            return self._result(request, "ACTION_REQUIRED", error="FORMAT_OR_VOICE_MISMATCH")
        if platform.system() != "Windows" or socket.gethostname().upper() != HOST:
            return self._result(request, "ACTION_REQUIRED", error="H4_WINDOWS_REQUIRED")
        if self._host_admission is None or self._engine_factory is None:
            return self._result(request, "ACTION_REQUIRED", error="SAYDI_LOCAL_START_NOT_INSTALLED")
        # Caller verifies authentication, permissions, STOP, locks and
        # capacity. Provider does NOT authorize START from a supplied Boolean.
        # Source-only gate: no model import occurs before the trusted callback.
        try:
            admit = self._host_admission()
            if admit is not True:
                return self._result(request, "ACTION_REQUIRED", error="SAYDI_RUNTIME_ADMISSION_HOLD")
        except Exception:
            return self._result(request, "ACTION_REQUIRED", error="SAYDI_RUNTIME_ADMISSION_ERROR")

        root = self.output_root.resolve(strict=True)
        path = Path(request.output_path).resolve()
        if path.parent == root or not path.is_relative_to(root) or path.suffix.lower() != ".wav":
            return self._result(request, "ACTION_REQUIRED", error="V6_ISOLATION_REQUIRED")
        if path.exists() or path.is_symlink():
            return self._result(request, "ACTION_REQUIRED", error="NO_OVERWRITE_EXISTING_AUDIO")

        # Dedicated V6 caller guarantees no VieNeu/Whisper concurrency.
        # A genuine subprocess-unload witness must be provided separately
        # before any next ASR stage; gc.collect() alone is insufficient.
        engine = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            engine = self._engine_factory()
            audio = engine.infer(request.text, voice=self.voice_name)
            engine.save(audio, str(path))
            result = self._result(request, "SUCCESS", output=path)
            result.validate()
            return result
        except Exception:
            return self._result(request, "FAILED", error="VIENEU_RENDER_FAILED")
        finally:
            if engine is not None:
                del engine
                gc.collect()
