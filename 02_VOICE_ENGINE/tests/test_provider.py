from dataclasses import dataclass, field
from pathlib import Path

from magasin_voice_engine.models import (
    AppliedSettings,
    DownloadReceipt,
    FailureDisposition,
    GenerationReceipt,
    PreflightResult,
    RunState,
    VoiceRequest,
)
from magasin_voice_engine.provider import SaydiVoiceProvider


@dataclass
class FakeBackend:
    provider_name: str = "saydivoice"
    preflight_result: PreflightResult = field(
        default_factory=lambda: PreflightResult(
            ready=True,
            page_state="TTS_READY",
            auth_state="AUTHENTICATED_OR_HIDDEN",
            voice="Adam — Giọng hot tiktok",
            audio_format="MP3",
        )
    )
    generation_result: GenerationReceipt = field(
        default_factory=lambda: GenerationReceipt(
            success=True,
            terminal_state="SUCCESS_SIGNAL",
            attempt_count=1,
            provider_history_created=True,
            content_type="audio/mpeg",
        )
    )
    download_result: DownloadReceipt = field(
        default_factory=lambda: DownloadReceipt(
            success=True,
            local_audio_path=Path("out.mp3"),
            byte_count=123,
            sha256="abc123",
            suggested_filename="out.mp3",
        )
    )
    preflight_calls: int = 0
    apply_calls: int = 0
    generate_calls: int = 0
    download_calls: int = 0
    close_calls: int = 0

    def preflight(self):
        self.preflight_calls += 1
        return self.preflight_result

    def apply_settings(self, preset):
        self.apply_calls += 1
        return AppliedSettings(
            voice=preset.voice,
            preset_key=preset.key,
            stability_ratio=preset.stability_ratio,
            speed_ratio=preset.speed_ratio,
            audio_format=preset.audio_format,
            pause_enabled=preset.pause.enabled,
        )

    def generate(self, text, *, timeout_seconds):
        self.generate_calls += 1
        return self.generation_result

    def download(self, output_directory, *, timeout_seconds):
        self.download_calls += 1
        if self.download_result.local_audio_path == Path("out.mp3"):
            return DownloadReceipt(
                success=self.download_result.success,
                local_audio_path=Path(output_directory) / "out.mp3",
                byte_count=self.download_result.byte_count,
                sha256=self.download_result.sha256,
                suggested_filename=self.download_result.suggested_filename,
                error_message=self.download_result.error_message,
                disposition=self.download_result.disposition,
            )
        return self.download_result

    def close(self):
        self.close_calls += 1


def test_no_generate_without_explicit_authorization(tmp_path):
    backend = FakeBackend()
    result = SaydiVoiceProvider(backend, enable_status=False).run(
        VoiceRequest(text="Xin chào", output_directory=tmp_path, allow_generate=False)
    )
    assert result.status == RunState.ACTION_REQUIRED
    assert result.error_code == "GENERATE_NOT_AUTHORIZED"
    assert backend.preflight_calls == 1
    assert backend.apply_calls == 0
    assert backend.generate_calls == 0
    assert backend.download_calls == 0
    assert backend.close_calls == 1


def test_successful_generation_is_exactly_one_attempt_and_no_download_by_default(tmp_path):
    backend = FakeBackend()
    result = SaydiVoiceProvider(backend, enable_status=False).run(
        VoiceRequest(
            text="Xin chào",
            preset_key="tiktok_energetic",
            output_directory=tmp_path,
            allow_generate=True,
        )
    )
    assert result.status == RunState.SUCCESS
    assert result.generation_attempt_count == 1
    assert result.provider_history_created is True
    assert result.voice == "Adam — Giọng hot tiktok"
    assert result.details["download_performed"] is False
    assert backend.apply_calls == 1
    assert backend.generate_calls == 1
    assert backend.download_calls == 0


def test_successful_generate_and_download_returns_local_metadata(tmp_path):
    backend = FakeBackend()
    result = SaydiVoiceProvider(backend, enable_status=False).run(
        VoiceRequest(
            text="Xin chào",
            output_directory=tmp_path,
            allow_generate=True,
            allow_download=True,
        )
    )
    assert result.status == RunState.SUCCESS
    assert result.local_audio_path == tmp_path / "out.mp3"
    assert result.byte_count == 123
    assert result.sha256 == "abc123"
    assert backend.generate_calls == 1
    assert backend.download_calls == 1


def test_generation_failure_is_not_retried_or_downloaded(tmp_path):
    backend = FakeBackend(
        generation_result=GenerationReceipt(
            success=False,
            terminal_state="HTTP_429",
            attempt_count=1,
            error_message="rate limited",
            disposition=FailureDisposition.RETRY,
        )
    )
    result = SaydiVoiceProvider(backend, enable_status=False).run(
        VoiceRequest(
            text="Xin chào",
            output_directory=tmp_path,
            allow_generate=True,
            allow_download=True,
        )
    )
    assert result.status == RunState.RETRYABLE_FAILURE
    assert result.retryable is True
    assert result.generation_attempt_count == 1
    assert backend.generate_calls == 1
    assert backend.download_calls == 0


def test_preflight_reauth_stops_before_setting_mutation(tmp_path):
    backend = FakeBackend(
        preflight_result=PreflightResult(
            ready=False,
            page_state="TTS_NOT_READY",
            auth_state="LOGIN_REQUIRED",
            error_message="login required",
            disposition=FailureDisposition.RE_AUTH,
        )
    )
    result = SaydiVoiceProvider(backend, enable_status=False).run(
        VoiceRequest(text="Xin chào", output_directory=tmp_path, allow_generate=True)
    )
    assert result.status == RunState.ACTION_REQUIRED
    assert result.error_class == FailureDisposition.RE_AUTH
    assert backend.apply_calls == 0
    assert backend.generate_calls == 0


def test_invalid_request_never_opens_provider(tmp_path):
    backend = FakeBackend()
    result = SaydiVoiceProvider(backend, enable_status=False).run(
        VoiceRequest(text="", output_directory=tmp_path, allow_generate=True)
    )
    assert result.status == RunState.ACTION_REQUIRED
    assert result.error_class == FailureDisposition.FIX_INPUT
    assert backend.preflight_calls == 0
    assert backend.generate_calls == 0


def test_unknown_preset_is_fix_input(tmp_path):
    backend = FakeBackend()
    result = SaydiVoiceProvider(backend, enable_status=False).run(
        VoiceRequest(
            text="Xin chào",
            preset_key="missing",
            output_directory=tmp_path,
            allow_generate=True,
        )
    )
    assert result.status == RunState.ACTION_REQUIRED
    assert result.error_class == FailureDisposition.FIX_INPUT
    assert backend.preflight_calls == 0


def test_provider_publishes_terminal_done_state(tmp_path):
    from magasin_voice_engine.supervisor_status import RobotStatus, SupervisorStateStore

    backend = FakeBackend()
    store = SupervisorStateStore(tmp_path / "status")
    result = SaydiVoiceProvider(
        backend,
        status_store=store,
        job_id="test-job",
        heartbeat_seconds=1,
    ).run(
        VoiceRequest(
            text="Xin chào",
            output_directory=tmp_path,
            allow_generate=True,
        )
    )

    state = store.load()
    assert result.status == RunState.SUCCESS
    assert state.status == RobotStatus.DONE.value
    assert state.job_id == "test-job"
    assert state.current_step == "complete"
    assert state.last_completed_step == "generate"
    assert state.requires_user is False


def test_provider_publishes_wait_user_without_generate_authorization(tmp_path):
    from magasin_voice_engine.supervisor_status import RobotStatus, SupervisorStateStore

    backend = FakeBackend()
    store = SupervisorStateStore(tmp_path / "status")
    result = SaydiVoiceProvider(
        backend,
        status_store=store,
        job_id="test-job",
        heartbeat_seconds=1,
    ).run(
        VoiceRequest(
            text="Xin chào",
            output_directory=tmp_path,
            allow_generate=False,
        )
    )

    state = store.load()
    assert result.status == RunState.ACTION_REQUIRED
    assert state.status == RobotStatus.WAIT_USER.value
    assert state.requires_user is True
    assert state.last_completed_step == "provider_preflight"
