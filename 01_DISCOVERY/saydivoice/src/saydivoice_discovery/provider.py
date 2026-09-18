from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

from .browser import probe_page
from .classifier import classify_auth_state, classify_page_state
from .d4_download import _safe_suggested_filename
from .evidence import make_page_signals
from .generation import (
    _NetworkRecorder,
    _run_attempt,
    _settle_page,
    classify_session_bootstrap,
)
from .runtime import sanitize_error_message
from .voice_controls import apply_preset
from .voice_presets import SUPPORTED_FORMATS, VoicePreset, get_preset

ProviderStatus = Literal["SUCCESS", "FAILED", "PREFLIGHT_BLOCKED"]
ProviderErrorClass = Literal["fix_input", "re_auth", "retry", "do_not_retry"]


@dataclass(frozen=True, slots=True)
class SaydiVoiceRequest:
    text: str
    preset_key: str
    output_directory: Path
    voice_override: str | None = None
    format_override: str | None = None
    download_requested: bool = False
    generation_timeout_ms: int = 60_000
    download_timeout_ms: int = 15_000


@dataclass(frozen=True, slots=True)
class PreflightResult:
    ready: bool
    page_state: str
    auth_state: str
    generate_enabled: bool
    editor_ready: bool
    session_state: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class GenerationResult:
    terminal_state: str
    provider_history_created: bool = False
    error: str | None = None


@dataclass(frozen=True, slots=True)
class DownloadArtifact:
    local_audio_path: Path
    byte_count: int
    sha256: str


@dataclass(frozen=True, slots=True)
class SaydiVoiceResult:
    status: ProviderStatus
    provider: str
    voice: str
    preset_key: str
    format: str
    local_audio_path: str | None
    byte_count: int | None
    sha256: str | None
    provider_history_created: bool
    error_class: ProviderErrorClass | None
    retryable: bool
    attempt_count: int
    error: str | None = None


class SaydiVoiceRuntime(Protocol):
    def preflight(self) -> PreflightResult: ...

    def apply_controls(
        self,
        preset: VoicePreset,
        *,
        voice: str,
        audio_format: str,
    ) -> dict[str, object]: ...

    def generate_once(self, text: str, *, timeout_ms: int) -> GenerationResult: ...

    def download_once(
        self,
        output_directory: Path,
        *,
        audio_format: str,
        timeout_ms: int,
    ) -> DownloadArtifact: ...


def _validate_request(request: SaydiVoiceRequest) -> tuple[VoicePreset, str, str]:
    text = request.text.strip()
    if not text:
        raise ValueError("text is required")
    if len(text) > 20_000:
        raise ValueError("text exceeds the 20000-character provider boundary")

    preset = get_preset(request.preset_key)

    voice = (request.voice_override or preset.voice).strip()
    if not voice:
        raise ValueError("voice must not be blank")

    audio_format = (request.format_override or preset.audio_format).upper().strip()
    if audio_format not in SUPPORTED_FORMATS:
        raise ValueError(f"unsupported audio format: {audio_format}")

    output = Path(request.output_directory)
    if request.download_requested and not output.is_absolute():
        raise ValueError("output_directory must be absolute when download is requested")

    if request.generation_timeout_ms < 2_000:
        raise ValueError("generation_timeout_ms must be at least 2000")
    if request.download_timeout_ms < 3_000:
        raise ValueError("download_timeout_ms must be at least 3000")

    return preset, voice, audio_format


def _classify_preflight_error(preflight: PreflightResult) -> ProviderErrorClass:
    if preflight.page_state == "LOGIN_REQUIRED":
        return "re_auth"
    if preflight.auth_state in {"ANONYMOUS", "UNKNOWN"}:
        return "re_auth"
    if preflight.session_state in {
        "SESSION_START_FORBIDDEN",
        "SESSION_NOT_ESTABLISHED",
    }:
        return "re_auth"
    if preflight.page_state == "ACCESS_BLOCKED":
        return "do_not_retry"
    return "retry"


def _classify_generation_error(result: GenerationResult) -> ProviderErrorClass:
    terminal = (result.terminal_state or "").upper()
    detail = (result.error or "").lower()
    if terminal in {"TIMEOUT", "NO_TERMINAL_SIGNAL"}:
        return "retry"
    if any(token in detail for token in ("login", "auth", "session", "401", "403")):
        return "re_auth"
    if any(token in detail for token in ("invalid", "unsupported", "too long")):
        return "fix_input"
    if terminal == "ERROR":
        return "retry"
    return "do_not_retry"


def _failed_result(
    *,
    preset_key: str,
    voice: str,
    audio_format: str,
    error_class: ProviderErrorClass,
    attempt_count: int,
    provider_history_created: bool = False,
    error: str | None = None,
    status: ProviderStatus = "FAILED",
) -> SaydiVoiceResult:
    return SaydiVoiceResult(
        status=status,
        provider="SAYDIVOICE",
        voice=voice,
        preset_key=preset_key,
        format=audio_format,
        local_audio_path=None,
        byte_count=None,
        sha256=None,
        provider_history_created=provider_history_created,
        error_class=error_class,
        retryable=error_class == "retry",
        attempt_count=attempt_count,
        error=sanitize_error_message(error or "") or None,
    )


class SaydiVoiceProvider:
    """Stable provider boundary.

    Validation always occurs before runtime/page access. Generation is called at
    most once per execute() invocation. Retry metadata is returned to the caller;
    this adapter never performs an implicit second Generate attempt.
    """

    def __init__(self, runtime: SaydiVoiceRuntime):
        self._runtime = runtime

    def execute(self, request: SaydiVoiceRequest) -> SaydiVoiceResult:
        try:
            preset, voice, audio_format = _validate_request(request)
        except (KeyError, ValueError, TypeError) as exc:
            return _failed_result(
                preset_key=request.preset_key,
                voice=(request.voice_override or ""),
                audio_format=(request.format_override or "").upper(),
                error_class="fix_input",
                attempt_count=0,
                error=str(exc),
            )

        preflight = self._runtime.preflight()
        if not preflight.ready:
            return _failed_result(
                preset_key=preset.key,
                voice=voice,
                audio_format=audio_format,
                error_class=_classify_preflight_error(preflight),
                attempt_count=0,
                error=preflight.reason or "SaydiVoice preflight blocked",
                status="PREFLIGHT_BLOCKED",
            )

        effective = replace(preset, voice=voice, audio_format=audio_format)
        try:
            observed = self._runtime.apply_controls(
                effective,
                voice=voice,
                audio_format=audio_format,
            )
        except Exception as exc:
            return _failed_result(
                preset_key=preset.key,
                voice=voice,
                audio_format=audio_format,
                error_class="do_not_retry",
                attempt_count=0,
                error=f"control verification failed: {type(exc).__name__}: {exc}",
            )

        if observed.get("voice") != voice or observed.get("format") != audio_format:
            return _failed_result(
                preset_key=preset.key,
                voice=voice,
                audio_format=audio_format,
                error_class="do_not_retry",
                attempt_count=0,
                error="control verification mismatch",
            )

        try:
            generation = self._runtime.generate_once(
                request.text,
                timeout_ms=request.generation_timeout_ms,
            )
        except Exception as exc:
            generation = GenerationResult(
                terminal_state="ERROR",
                provider_history_created=False,
                error=f"{type(exc).__name__}: {exc}",
            )

        if generation.terminal_state != "SUCCESS_SIGNAL":
            error_class = _classify_generation_error(generation)
            return _failed_result(
                preset_key=preset.key,
                voice=voice,
                audio_format=audio_format,
                error_class=error_class,
                attempt_count=1,
                provider_history_created=generation.provider_history_created,
                error=generation.error or generation.terminal_state,
            )

        if not request.download_requested:
            return SaydiVoiceResult(
                status="SUCCESS",
                provider="SAYDIVOICE",
                voice=voice,
                preset_key=preset.key,
                format=audio_format,
                local_audio_path=None,
                byte_count=None,
                sha256=None,
                provider_history_created=generation.provider_history_created,
                error_class=None,
                retryable=False,
                attempt_count=1,
                error=None,
            )

        try:
            artifact = self._runtime.download_once(
                Path(request.output_directory),
                audio_format=audio_format,
                timeout_ms=request.download_timeout_ms,
            )
        except Exception as exc:
            return _failed_result(
                preset_key=preset.key,
                voice=voice,
                audio_format=audio_format,
                error_class="retry",
                attempt_count=1,
                provider_history_created=generation.provider_history_created,
                error=f"download failed: {type(exc).__name__}: {exc}",
            )

        return SaydiVoiceResult(
            status="SUCCESS",
            provider="SAYDIVOICE",
            voice=voice,
            preset_key=preset.key,
            format=audio_format,
            local_audio_path=str(artifact.local_audio_path),
            byte_count=artifact.byte_count,
            sha256=artifact.sha256,
            provider_history_created=generation.provider_history_created,
            error_class=None,
            retryable=False,
            attempt_count=1,
            error=None,
        )


class PlaywrightSaydiRuntime:
    """Production runtime over an already-authenticated SaydiVoice page.

    This class contains the real provider-specific browser mechanics but is not
    exercised by the offline unit suite. Live generation/download still requires
    a separately authorized caller/workflow.
    """

    def __init__(self, page: Any, *, evidence_dir: Path):
        self.page = page
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self._recorder = _NetworkRecorder()
        self._recorder.attach(page)
        self._attempts = 0

    def preflight(self) -> PreflightResult:
        raw = probe_page(self.page)
        signals = make_page_signals(raw)
        page_state = classify_page_state(signals)
        auth_state = classify_auth_state(signals, page_state)

        self._recorder.finalize_error_details()
        session = classify_session_bootstrap(self._recorder.events)

        editor = self.page.locator('[contenteditable="true"]').first
        generate = self.page.get_by_role(
            "button", name="Tạo giọng nói", exact=True
        ).first
        editor_ready = editor.count() > 0 and editor.is_visible()
        generate_enabled = (
            generate.count() > 0
            and generate.is_visible()
            and generate.is_enabled()
        )

        ready = (
            page_state == "TTS_READY"
            and auth_state == "AUTHENTICATED_OR_HIDDEN"
            and editor_ready
            and generate_enabled
            and not session.get("blocking")
        )
        reason = None if ready else (
            f"page={page_state};auth={auth_state};"
            f"session={session.get('state')};editor={editor_ready};"
            f"generate={generate_enabled}"
        )
        return PreflightResult(
            ready=ready,
            page_state=page_state,
            auth_state=auth_state,
            generate_enabled=generate_enabled,
            editor_ready=editor_ready,
            session_state=str(session.get("state") or ""),
            reason=reason,
        )

    def apply_controls(
        self,
        preset: VoicePreset,
        *,
        voice: str,
        audio_format: str,
    ) -> dict[str, object]:
        effective = replace(preset, voice=voice, audio_format=audio_format)
        return apply_preset(self.page, effective)

    def generate_once(self, text: str, *, timeout_ms: int) -> GenerationResult:
        if self._attempts >= 1:
            raise RuntimeError("one-attempt guard: Generate already attempted")
        self._attempts += 1

        attempt = _run_attempt(
            self.page,
            evidence_dir=self.evidence_dir,
            sample_text=text,
            timeout_ms=timeout_ms,
            poll_ms=500,
            attempt_no=1,
            recorder=self._recorder,
        )
        analysis = attempt.get("analysis") or {}
        history_created = any(
            event.get("kind") == "response"
            and 200 <= int(event.get("status") or 0) < 300
            and urlsplit(str(event.get("url") or "")).path == "/api/library/history"
            for event in attempt.get("network_events") or []
        )
        terminal = str(analysis.get("terminal_state") or "NO_TERMINAL_SIGNAL")
        errors = analysis.get("error_alerts") or []
        error = "; ".join(str(value) for value in errors[:3]) or None
        return GenerationResult(
            terminal_state=terminal,
            provider_history_created=history_created,
            error=error,
        )

    def download_once(
        self,
        output_directory: Path,
        *,
        audio_format: str,
        timeout_ms: int,
    ) -> DownloadArtifact:
        output_directory.mkdir(parents=True, exist_ok=True)
        control = self.page.get_by_role("button", name="Tải về", exact=True).first
        if control.count() < 1:
            control = self.page.get_by_text("Tải về", exact=True).first
        if control.count() < 1:
            raise RuntimeError("Download control not found")

        with self.page.expect_download(timeout=max(3_000, timeout_ms)) as info:
            control.click(timeout=5_000)
        download = info.value
        safe_name = _safe_suggested_filename(
            str(download.suggested_filename or f"saydivoice.{audio_format.lower()}")
        )
        target = output_directory / safe_name
        if target.exists():
            raise FileExistsError(f"refusing to overwrite existing audio: {target.name}")
        download.save_as(str(target))

        digest = hashlib.sha256()
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return DownloadArtifact(
            local_audio_path=target,
            byte_count=target.stat().st_size,
            sha256=digest.hexdigest(),
        )
