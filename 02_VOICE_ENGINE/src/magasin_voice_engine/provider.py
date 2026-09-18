from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .backend import VoiceBackend, VoiceBackendError
from .models import FailureDisposition, RunState, VoiceRequest, VoiceResult
from .presets import get_preset
from .supervisor_status import (
    HeartbeatWorker,
    RobotStatus,
    SupervisorStateStore,
    default_job_id,
)


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
    Supervisor telemetry is privacy-safe and never stores request text, auth
    material, cookies, or generated audio.
    """

    def __init__(
        self,
        backend: VoiceBackend,
        *,
        status_store: SupervisorStateStore | None = None,
        job_id: str | None = None,
        heartbeat_seconds: float = 30.0,
        enable_status: bool = True,
    ) -> None:
        self.backend = backend
        self.status_store = (status_store or SupervisorStateStore()) if enable_status else None
        self.job_id = job_id or default_job_id()
        self.heartbeat_seconds = heartbeat_seconds

    def _publish(
        self,
        status: RobotStatus,
        *,
        current_step: str | None,
        last_completed_step: str | None = None,
        next_action: str | None = None,
        retry_count: int | None = None,
        requires_user: bool = False,
        message: str | None = None,
    ) -> None:
        if self.status_store is None:
            return
        try:
            self.status_store.publish(
                status,
                job_id=self.job_id,
                current_step=current_step,
                last_completed_step=last_completed_step,
                next_action=next_action,
                retry_count=retry_count,
                requires_user=requires_user,
                message=message,
            )
        except Exception:
            # Telemetry must never break voice generation.
            pass

    def _finalize(self, result: VoiceResult, *, last_completed_step: str | None = None) -> VoiceResult:
        if result.status == RunState.SUCCESS:
            self._publish(
                RobotStatus.DONE,
                current_step="complete",
                last_completed_step=last_completed_step,
                next_action=None,
                requires_user=False,
                message="Voice Engine job completed.",
            )
            return result

        if result.status in {RunState.ACTION_REQUIRED, RunState.RETRYABLE_FAILURE}:
            if result.error_class == FailureDisposition.RE_AUTH:
                next_action = "Re-authenticate the local Saydi profile, then rerun."
            elif result.error_class == FailureDisposition.FIX_INPUT:
                next_action = "Correct the request input, then rerun."
            elif result.error_class == FailureDisposition.RETRY:
                next_action = "Review the failure and explicitly start a new attempt; Generate is never auto-retried."
            elif result.error_code == "GENERATE_NOT_AUTHORIZED":
                next_action = "Explicitly authorize Generate before rerunning this request."
            else:
                next_action = "Review the action required before continuing."
            self._publish(
                RobotStatus.WAIT_USER,
                current_step="wait_user",
                last_completed_step=last_completed_step,
                next_action=next_action,
                requires_user=True,
                message=result.error_code or "ACTION_REQUIRED",
            )
            return result

        self._publish(
            RobotStatus.FAILED,
            current_step="failed",
            last_completed_step=last_completed_step,
            next_action="Inspect the failure before starting another job.",
            requires_user=True,
            message=result.error_code or "FATAL_FAILURE",
        )
        return result

    def run(self, request: VoiceRequest) -> VoiceResult:
        provider_name = getattr(self.backend, "provider_name", "saydivoice")
        applied = None
        generation = None
        heartbeat = HeartbeatWorker(self.status_store, self.heartbeat_seconds) if self.status_store else None
        self._publish(
            RobotStatus.RUNNING,
            current_step="validate_request",
            next_action="Validate request and prepare provider preflight.",
            requires_user=False,
            message="Voice Engine started.",
        )
        if heartbeat:
            heartbeat.start()

        try:
            try:
                request.validate()
                preset = get_preset(
                    request.preset_key,
                    voice_override=request.voice_override,
                    format_override=request.format_override,
                )
            except ValueError as exc:
                return self._finalize(
                    _failure(
                        provider=provider_name,
                        preset_key=request.preset_key,
                        disposition=FailureDisposition.FIX_INPUT,
                        code="INVALID_REQUEST",
                        message=str(exc),
                    ),
                    last_completed_step=None,
                )

            self._publish(
                RobotStatus.RUNNING,
                current_step="provider_preflight",
                last_completed_step="validate_request",
                next_action="Verify authenticated Saydi provider surface.",
                message="Read-only provider preflight.",
            )
            preflight = self.backend.preflight()
            if not preflight.ready:
                disposition = preflight.disposition or FailureDisposition.RE_AUTH
                return self._finalize(
                    _failure(
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
                    ),
                    last_completed_step="validate_request",
                )

            # Authorization is checked before settings are mutated. Preflight is
            # deliberately read-only and may run without generation permission.
            if not request.allow_generate:
                return self._finalize(
                    VoiceResult(
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
                    ),
                    last_completed_step="provider_preflight",
                )

            self._publish(
                RobotStatus.RUNNING,
                current_step="apply_settings",
                last_completed_step="provider_preflight",
                next_action="Apply and verify the selected voice/style preset.",
                message="Applying verified provider settings.",
            )
            applied = self.backend.apply_settings(preset)

            self._publish(
                RobotStatus.RUNNING,
                current_step="generate",
                last_completed_step="apply_settings",
                next_action="Wait for one bounded Generate attempt.",
                message="Generate is authorized for exactly one attempt.",
            )
            generation = self.backend.generate(
                request.text,
                timeout_seconds=request.generation_timeout_seconds,
            )
            if not generation.success:
                disposition = generation.disposition or FailureDisposition.DO_NOT_RETRY
                return self._finalize(
                    _failure(
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
                    ),
                    last_completed_step="apply_settings",
                )

            if not request.allow_download:
                return self._finalize(
                    VoiceResult(
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
                    ),
                    last_completed_step="generate",
                )

            self._publish(
                RobotStatus.RUNNING,
                current_step="download",
                last_completed_step="generate",
                next_action="Save the authorized audio artifact locally.",
                message="Download is explicitly authorized.",
            )
            download = self.backend.download(
                request.output_directory,
                timeout_seconds=request.download_timeout_seconds,
            )
            if not download.success:
                disposition = download.disposition or FailureDisposition.DO_NOT_RETRY
                return self._finalize(
                    _failure(
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
                    ),
                    last_completed_step="generate",
                )

            return self._finalize(
                VoiceResult(
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
                ),
                last_completed_step="download",
            )
        except VoiceBackendError as exc:
            return self._finalize(
                _failure(
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
            )
        except Exception as exc:
            return self._finalize(
                _failure(
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
            )
        finally:
            if heartbeat:
                heartbeat.stop()
            self.backend.close()
