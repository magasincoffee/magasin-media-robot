from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .backend import VoiceBackend, VoiceBackendError
from .models import FailureDisposition, RunState, VoiceRequest, VoiceResult
from .presets import get_preset


def _state_for(disposition: FailureDisposition) -> RunState:
    if disposition == FailureDisposition.RETRY:
        return RunState.RETRYABLE_FAILURE
    if disposition in {FailureDisposition.FIX_INPUT, FailureDisposition.RE_AUTH}:
        return RunState.ACTION_REQUIRED
    return RunState.FATAL_FAILURE


def _failure(
    *,
    provider: str,
    preset_key: str,
    disposition: FailureDisposition,
    code: str,
    message: str,
    voice: str | None = None,
    audio_format: str | None = None,
    attempts: int = 0,
    history_created: bool = False,
    details: dict[str, Any] | None = None,
) -> VoiceResult:
    return VoiceResult(
        status=_state_for(disposition),
        provider=provider,
        preset_key=preset_key,
        voice=voice,
        audio_format=audio_format,
        provider_history_created=history_created,
        generation_attempt_count=attempts,
        error_class=disposition,
        error_code=code,
        error_message=message,
        retryable=disposition == FailureDisposition.RETRY,
        details=details or {},
    )


class SaydiVoiceProvider:
    """Provider-neutral orchestration around a Saydi-compatible backend.

    The provider owns policy: validate first, preflight before mutation, require
    explicit generation authorization, apply/verify settings, perform exactly
    one Generate attempt, and only Download when separately authorized.

    The backend owns browser mechanics. This class never retries Generate.
    """

    def __init__(self, backend: VoiceBackend) -> None:
        self.backend = backend

    def run(self, request: VoiceRequest) -> VoiceResult:
        provider_name = getattr(self.backend, "provider_name", "saydivoice")
        applied = None
        generation = None
        try:
            try:
                request.validate()
                preset = get_preset(
                    request.preset_key,
                    voice_override=request.voice_override,
                    format_override=request.format_override,
                )
            except ValueError as exc:
                return _failure(
                    provider=provider_name,
                    preset_key=request.preset_key,
                    disposition=FailureDisposition.FIX_INPUT,
                    code="INVALID_REQUEST",
                    message=str(exc),
                )

            preflight = self.backend.preflight()
            if not preflight.ready:
                disposition = preflight.disposition or FailureDisposition.RE_AUTH
                return _failure(
                    provider=provider_name,
                    preset_key=request.preset_key,
                    disposition=disposition,
                    code="PREFLIGHT_FAILED",
                    message=preflight.error_message or "provider preflight failed",
                    voice=preflight.voice,
                    audio_format=preflight.audio_format,
                    details={
                        "page_state": preflight.page_state,
                        "auth_state": preflight.auth_state,
                    },
                )

            # Authorization is checked before settings are mutated. Preflight is
            # deliberately read-only and may run without generation permission.
            if not request.allow_generate:
                return VoiceResult(
                    status=RunState.ACTION_REQUIRED,
                    provider=provider_name,
                    preset_key=request.preset_key,
                    voice=preflight.voice,
                    audio_format=preflight.audio_format,
                    error_class=FailureDisposition.DO_NOT_RETRY,
                    error_code="GENERATE_NOT_AUTHORIZED",
                    error_message="Generate requires explicit authorization.",
                    retryable=False,
                    details={"page_state": preflight.page_state, "auth_state": preflight.auth_state},
                )

            applied = self.backend.apply_settings(preset)
            generation = self.backend.generate(
                request.text,
                timeout_seconds=request.generation_timeout_seconds,
            )
            if not generation.success:
                disposition = generation.disposition or FailureDisposition.DO_NOT_RETRY
                return _failure(
                    provider=provider_name,
                    preset_key=request.preset_key,
                    disposition=disposition,
                    code="GENERATION_FAILED",
                    message=generation.error_message or generation.terminal_state,
                    voice=applied.voice,
                    audio_format=applied.audio_format,
                    attempts=generation.attempt_count,
                    history_created=generation.provider_history_created,
                    details={
                        "terminal_state": generation.terminal_state,
                        "applied": asdict(applied),
                    },
                )

            if not request.allow_download:
                return VoiceResult(
                    status=RunState.SUCCESS,
                    provider=provider_name,
                    preset_key=request.preset_key,
                    voice=applied.voice,
                    audio_format=applied.audio_format,
                    provider_history_created=generation.provider_history_created,
                    generation_attempt_count=generation.attempt_count,
                    details={
                        "terminal_state": generation.terminal_state,
                        "content_type": generation.content_type,
                        "download_performed": False,
                        "applied": asdict(applied),
                    },
                )

            download = self.backend.download(
                request.output_directory,
                timeout_seconds=request.download_timeout_seconds,
            )
            if not download.success:
                disposition = download.disposition or FailureDisposition.DO_NOT_RETRY
                return _failure(
                    provider=provider_name,
                    preset_key=request.preset_key,
                    disposition=disposition,
                    code="DOWNLOAD_FAILED",
                    message=download.error_message or "provider download failed",
                    voice=applied.voice,
                    audio_format=applied.audio_format,
                    attempts=generation.attempt_count,
                    history_created=generation.provider_history_created,
                    details={
                        "terminal_state": generation.terminal_state,
                        "applied": asdict(applied),
                    },
                )

            return VoiceResult(
                status=RunState.SUCCESS,
                provider=provider_name,
                preset_key=request.preset_key,
                voice=applied.voice,
                audio_format=applied.audio_format,
                local_audio_path=download.local_audio_path,
                byte_count=download.byte_count,
                sha256=download.sha256,
                provider_history_created=generation.provider_history_created,
                generation_attempt_count=generation.attempt_count,
                details={
                    "terminal_state": generation.terminal_state,
                    "content_type": generation.content_type,
                    "suggested_filename": download.suggested_filename,
                    "download_performed": True,
                    "applied": asdict(applied),
                },
            )
        except VoiceBackendError as exc:
            return _failure(
                provider=provider_name,
                preset_key=request.preset_key,
                disposition=exc.disposition,
                code=exc.code,
                message=str(exc),
                voice=applied.voice if applied else None,
                audio_format=applied.audio_format if applied else None,
                attempts=generation.attempt_count if generation else 0,
                history_created=generation.provider_history_created if generation else False,
            )
        except Exception as exc:
            return _failure(
                provider=provider_name,
                preset_key=request.preset_key,
                disposition=FailureDisposition.DO_NOT_RETRY,
                code="UNEXPECTED_PROVIDER_ERROR",
                message=f"{type(exc).__name__}: {exc}",
                voice=applied.voice if applied else None,
                audio_format=applied.audio_format if applied else None,
                attempts=generation.attempt_count if generation else 0,
                history_created=generation.provider_history_created if generation else False,
            )
        finally:
            self.backend.close()
