from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from saydivoice_discovery.provider import (
    DownloadArtifact,
    GenerationResult,
    PreflightResult,
    SaydiVoiceProvider,
    SaydiVoiceRequest,
)


@dataclass
class FakeRuntime:
    preflight_result: PreflightResult = PreflightResult(
        ready=True,
        page_state="TTS_READY",
        auth_state="AUTHENTICATED_OR_HIDDEN",
        generate_enabled=True,
        editor_ready=True,
        session_state="SESSION_STARTED",
    )
    generation_result: GenerationResult = GenerationResult(
        terminal_state="SUCCESS_SIGNAL",
        provider_history_created=True,
    )
    generate_calls: int = 0
    preflight_calls: int = 0
    control_calls: int = 0
    download_calls: int = 0
    observed_voice: str | None = None
    observed_format: str | None = None
    download_artifact: DownloadArtifact | None = None

    def preflight(self) -> PreflightResult:
        self.preflight_calls += 1
        return self.preflight_result

    def apply_controls(self, preset, *, voice: str, audio_format: str):
        self.control_calls += 1
        self.observed_voice = voice
        self.observed_format = audio_format
        return {"voice": voice, "format": audio_format}

    def generate_once(self, text: str, *, timeout_ms: int) -> GenerationResult:
        self.generate_calls += 1
        if self.generate_calls > 1:
            raise AssertionError("implicit retry detected")
        return self.generation_result

    def download_once(self, output_directory: Path, *, audio_format: str, timeout_ms: int) -> DownloadArtifact:
        self.download_calls += 1
        if self.download_artifact is None:
            raise AssertionError("download was not configured")
        return self.download_artifact


def request(tmp_path: Path, **overrides) -> SaydiVoiceRequest:
    values = dict(
        text="Xin chào MAGASIN",
        preset_key="tiktok_energetic",
        output_directory=tmp_path.resolve(),
    )
    values.update(overrides)
    return SaydiVoiceRequest(**values)


def test_invalid_preset_fails_before_touching_runtime(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    result = SaydiVoiceProvider(runtime).execute(
        request(tmp_path, preset_key="missing")
    )
    assert result.status == "FAILED"
    assert result.error_class == "fix_input"
    assert result.attempt_count == 0
    assert runtime.preflight_calls == 0
    assert runtime.control_calls == 0
    assert runtime.generate_calls == 0


def test_blank_text_fails_before_preflight(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    result = SaydiVoiceProvider(runtime).execute(request(tmp_path, text="   "))
    assert result.error_class == "fix_input"
    assert runtime.preflight_calls == 0


def test_reauth_preflight_blocks_all_side_effects(tmp_path: Path) -> None:
    runtime = FakeRuntime(
        preflight_result=PreflightResult(
            ready=False,
            page_state="LOGIN_REQUIRED",
            auth_state="ANONYMOUS",
            generate_enabled=False,
            editor_ready=False,
            session_state="SESSION_NOT_ESTABLISHED",
            reason="login required",
        )
    )
    result = SaydiVoiceProvider(runtime).execute(request(tmp_path))
    assert result.status == "PREFLIGHT_BLOCKED"
    assert result.error_class == "re_auth"
    assert result.attempt_count == 0
    assert runtime.control_calls == 0
    assert runtime.generate_calls == 0


def test_voice_and_format_overrides_are_applied_before_one_generate(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    result = SaydiVoiceProvider(runtime).execute(
        request(
            tmp_path,
            voice_override="Voice Override",
            format_override="wav",
        )
    )
    assert result.status == "SUCCESS"
    assert result.voice == "Voice Override"
    assert result.format == "WAV"
    assert runtime.observed_voice == "Voice Override"
    assert runtime.observed_format == "WAV"
    assert runtime.control_calls == 1
    assert runtime.generate_calls == 1
    assert runtime.download_calls == 0


def test_generation_error_returns_retry_metadata_without_retrying(tmp_path: Path) -> None:
    runtime = FakeRuntime(
        generation_result=GenerationResult(
            terminal_state="ERROR",
            provider_history_created=False,
            error="provider temporary error",
        )
    )
    result = SaydiVoiceProvider(runtime).execute(request(tmp_path))
    assert result.status == "FAILED"
    assert result.error_class == "retry"
    assert result.retryable is True
    assert result.attempt_count == 1
    assert runtime.generate_calls == 1


def test_timeout_is_retryable_but_never_implicitly_retried(tmp_path: Path) -> None:
    runtime = FakeRuntime(
        generation_result=GenerationResult(
            terminal_state="TIMEOUT",
            error="bounded timeout",
        )
    )
    result = SaydiVoiceProvider(runtime).execute(request(tmp_path))
    assert result.error_class == "retry"
    assert result.attempt_count == 1
    assert runtime.generate_calls == 1


def test_success_without_download_does_not_touch_download_control(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    result = SaydiVoiceProvider(runtime).execute(request(tmp_path))
    assert result.status == "SUCCESS"
    assert result.local_audio_path is None
    assert result.provider_history_created is True
    assert runtime.download_calls == 0


def test_download_is_explicit_and_returns_local_metadata(tmp_path: Path) -> None:
    artifact_path = tmp_path.resolve() / "voice.mp3"
    runtime = FakeRuntime(
        download_artifact=DownloadArtifact(
            local_audio_path=artifact_path,
            byte_count=321,
            sha256="a" * 64,
        )
    )
    result = SaydiVoiceProvider(runtime).execute(
        request(tmp_path, download_requested=True)
    )
    assert result.status == "SUCCESS"
    assert result.local_audio_path == str(artifact_path)
    assert result.byte_count == 321
    assert result.sha256 == "a" * 64
    assert runtime.download_calls == 1


def test_download_requires_absolute_output_path_before_preflight(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    result = SaydiVoiceProvider(runtime).execute(
        SaydiVoiceRequest(
            text="x",
            preset_key="tiktok_energetic",
            output_directory=Path("relative"),
            download_requested=True,
        )
    )
    assert result.error_class == "fix_input"
    assert runtime.preflight_calls == 0


def test_sensitive_error_text_is_redacted(tmp_path: Path) -> None:
    runtime = FakeRuntime(
        generation_result=GenerationResult(
            terminal_state="ERROR",
            error="Bearer abcdefghijklmnopqrstuvwxyz user@example.com https://x.test/a?token=secret",
        )
    )
    result = SaydiVoiceProvider(runtime).execute(request(tmp_path))
    assert result.error is not None
    assert "user@example.com" not in result.error
    assert "token=secret" not in result.error
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in result.error
    assert "[REDACTED_EMAIL]" in result.error


@pytest.mark.parametrize("fmt", ["WAV", "MP3", "FLAC", "OGG"])
def test_supported_format_overrides_validate_offline(tmp_path: Path, fmt: str) -> None:
    runtime = FakeRuntime()
    result = SaydiVoiceProvider(runtime).execute(
        request(tmp_path, format_override=fmt)
    )
    assert result.status == "SUCCESS"
    assert result.format == fmt
