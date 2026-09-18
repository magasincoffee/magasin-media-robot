from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .backend import VoiceBackendError
from .models import (
    AppliedSettings,
    DownloadReceipt,
    FailureDisposition,
    GenerationReceipt,
    PreflightResult,
)
from .presets import VoicePreset

SAYDI_TTS_URL = "https://voice.saydi.ai/vi/studio/tts/"


def default_profile_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "MAGASIN" / "MediaRobot" / "saydivoice" / "browser_profile"
    return Path.home() / ".magasin" / "MediaRobot" / "saydivoice" / "browser_profile"


def discover_chrome_executable() -> Path | None:
    candidates = [
        Path(os.environ.get("ProgramFiles", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    for candidate in candidates:
        if str(candidate) and candidate.is_file():
            return candidate
    return None


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _safe_filename(value: str | None, *, fallback: str = "saydivoice.mp3") -> str:
    name = Path(value or fallback).name[:180]
    name = re.sub(r'[<>:"/\\|?*\r\n\t]', "_", name).strip(" .")
    return name or fallback


def _unique_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    for index in range(1, 10_000):
        alternate = directory / f"{stem}_{index}{suffix}"
        if not alternate.exists():
            return alternate
    raise VoiceBackendError("unable to allocate a unique output filename", code="OUTPUT_PATH_EXHAUSTED")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _http_disposition(status: int) -> FailureDisposition:
    if status in {401, 403}:
        return FailureDisposition.RE_AUTH
    if status == 429 or status >= 500:
        return FailureDisposition.RETRY
    if status in {400, 404, 409, 413, 422}:
        return FailureDisposition.FIX_INPUT
    return FailureDisposition.DO_NOT_RETRY


def _selected_format(page: Any) -> str | None:
    items = page.evaluate(
        r"""
() => Array.from(document.querySelectorAll('.fmt-tab')).map(el=>({
  text:(el.innerText||el.textContent||'').trim(), cls:String(el.className||'')
}))
"""
    ) or []
    for item in items:
        if "active" in str(item.get("cls") or "").split():
            return _clean(item.get("text"))
    return None


def _set_format(page: Any, audio_format: str) -> str:
    target = audio_format.upper()
    if _selected_format(page) == target:
        return target
    loc = page.locator(".fmt-tab").filter(has_text=target)
    if loc.count() < 1:
        raise VoiceBackendError(
            f"format {target} is not available",
            disposition=FailureDisposition.FIX_INPUT,
            code="FORMAT_UNAVAILABLE",
        )
    loc.first.click(timeout=4_000)
    page.wait_for_timeout(350)
    observed = _selected_format(page)
    if observed != target:
        raise VoiceBackendError(f"format verification failed: {observed!r}", code="FORMAT_VERIFY_FAILED")
    return target


def _slider_ratio(page: Any, index: int) -> float | None:
    value = page.evaluate(
        r"""
(index) => {
  const el=Array.from(document.querySelectorAll('.slider'))[index];
  if(!el) return null;
  const r=el.getBoundingClientRect();
  const fill=el.querySelector('.slider-fill')?.getBoundingClientRect();
  return (fill&&r.width)?fill.width/r.width:null;
}
""",
        index,
    )
    return float(value) if value is not None else None


def _set_slider_ratio(page: Any, index: int, ratio: float, *, tolerance: float = 0.04) -> float:
    target = max(0.04, min(0.96, float(ratio)))
    loc = page.locator(".slider").nth(index)
    box = loc.bounding_box()
    if not box:
        raise VoiceBackendError(f"slider {index} is missing", code="SLIDER_MISSING")
    page.mouse.click(box["x"] + box["width"] * target, box["y"] + max(1.0, box["height"] / 2))
    page.wait_for_timeout(500)
    observed = _slider_ratio(page, index)
    if observed is None or abs(observed - target) > tolerance:
        raise VoiceBackendError(
            f"slider {index} verification failed: target={target:.3f}, observed={observed}",
            code="SLIDER_VERIFY_FAILED",
        )
    return observed


def _visible_button_texts(page: Any) -> list[str]:
    return page.evaluate(
        r"""
() => Array.from(document.querySelectorAll('button,[role="button"]'))
.filter(el=>{const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0
 && !el.closest('[role="dialog"],dialog,.modal,.dialog,[class*="modal"],[class*="dialog"]');})
.map(el=>(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim()).filter(Boolean)
"""
    ) or []


def _current_voice(page: Any, preferred: tuple[str, ...] = ()) -> str | None:
    values = [_clean(value) for value in _visible_button_texts(page)]
    for name in preferred:
        if name in values:
            return name
    for value in values:
        low = value.lower()
        if len(value) <= 140 and value not in {"Tạo giọng nói", "Chọn giọng"} and (
            "giọng" in low or " - nữ" in low or " - nam" in low
        ):
            return value
    return next((value for value in values if value.lower() == "tự động"), None)


def _open_voice_selector(page: Any, current: str) -> None:
    for loc in (page.get_by_role("button", name=current, exact=True), page.get_by_text(current, exact=True)):
        for index in range(loc.count()):
            node = loc.nth(index)
            try:
                if node.is_visible():
                    node.click(timeout=4_000)
                    page.wait_for_timeout(500)
                    if page.locator("input:visible").count() > 0:
                        return
            except Exception:
                continue
    raise VoiceBackendError("could not open voice selector", code="VOICE_SELECTOR_MISSING")


def _voice_search_input(page: Any):
    inputs = page.locator("input:visible")
    if inputs.count() < 1:
        raise VoiceBackendError("voice search input is missing", code="VOICE_SEARCH_MISSING")
    for index in range(inputs.count()):
        candidate = inputs.nth(index)
        placeholder = (candidate.get_attribute("placeholder") or "").lower()
        if any(token in placeholder for token in ("tìm", "search", "nhập")):
            return candidate
    return inputs.last


def _set_voice(page: Any, target: str) -> str:
    before = _current_voice(page, (target,))
    if before == target:
        return target
    if not before:
        raise VoiceBackendError("current voice could not be determined", code="VOICE_STATE_UNKNOWN")
    _open_voice_selector(page, before)
    search = _voice_search_input(page)
    query = target.split("—", 1)[0].split(" - ", 1)[0].strip()
    search.fill(query, timeout=4_000)
    page.wait_for_timeout(650)
    selected = page.evaluate(
        r"""
(target) => {
  const norm=s=>(s||'').replace(/\s+/g,' ').trim();
  const vis=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
  const exact=Array.from(document.querySelectorAll('*')).filter(vis).filter(e=>norm(e.innerText||e.textContent)===target);
  for(const n of exact){
    let p=n;
    for(let depth=0;depth<9&&p;depth++,p=p.parentElement){
      const buttons=Array.from(p.querySelectorAll('button')).filter(vis);
      const use=buttons.find(b=>['Dùng','Sử dụng','Use'].includes(norm(b.innerText||b.textContent)));
      if(use){use.click();return true;}
      const active=buttons.find(b=>['Xóa','Xoá','Remove'].includes(norm(b.innerText||b.textContent)));
      if(active){return true;}
    }
  }
  return false;
}
""",
        target,
    )
    if not selected:
        raise VoiceBackendError(
            f"voice {target!r} is unavailable",
            disposition=FailureDisposition.FIX_INPUT,
            code="VOICE_UNAVAILABLE",
        )
    page.wait_for_timeout(650)
    page.keyboard.press("Escape")
    page.wait_for_timeout(350)
    observed = _current_voice(page, (target,))
    if observed != target:
        raise VoiceBackendError(
            f"voice verification failed: expected={target!r}, observed={observed!r}",
            code="VOICE_VERIFY_FAILED",
        )
    return target


def _pause_section(page: Any):
    label = page.get_by_text("Ngắt nghỉ", exact=True)
    if label.count() < 1:
        raise VoiceBackendError("pause section is missing", code="PAUSE_SECTION_MISSING")
    return label.first.locator(
        "xpath=ancestor-or-self::*[contains(concat(' ', normalize-space(@class), ' '), ' st-section ')][1]"
    )


def _set_pause_enabled(page: Any, enabled: bool) -> bool:
    section = _pause_section(page)
    head = section.locator("button.dropdown.accordion-head").first
    if head.count() < 1:
        raise VoiceBackendError("pause accordion is missing", code="PAUSE_ACCORDION_MISSING")
    if (head.get_attribute("aria-expanded") or "false").lower() != "true":
        head.click(timeout=4_000)
        page.wait_for_timeout(300)
    checkbox = section.locator('input.brk-enable[type="checkbox"]').first
    if checkbox.count() < 1:
        raise VoiceBackendError("pause checkbox is missing", code="PAUSE_CHECKBOX_MISSING")
    if checkbox.is_checked() != bool(enabled):
        checkbox.click(timeout=4_000)
        page.wait_for_timeout(300)
    observed = bool(checkbox.is_checked())
    if observed != bool(enabled):
        raise VoiceBackendError("pause enable verification failed", code="PAUSE_VERIFY_FAILED")
    return observed


def _result_controls(page: Any) -> set[str]:
    values = page.evaluate(
        r"""
() => Array.from(document.querySelectorAll('button,a,[role="button"]'))
.filter(el=>{const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0})
.map(el=>(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim())
.filter(t=>/tải|download|phát|play|nghe|lưu/i.test(t))
"""
    ) or []
    return set(values)


def _alerts(page: Any) -> set[str]:
    values = page.evaluate(
        r"""
() => Array.from(document.querySelectorAll('[role="alert"],[aria-live],[data-sonner-toast],.toast,.Toastify__toast'))
.filter(el=>{const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0})
.map(el=>(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim()).filter(Boolean)
"""
    ) or []
    return set(values)


@dataclass(slots=True)
class SaydiPlaywrightConfig:
    tts_url: str = SAYDI_TTS_URL
    profile_dir: Path = field(default_factory=default_profile_dir)
    chromium_executable: Path | None = None
    headless: bool = False
    navigation_timeout_ms: int = 60_000
    settle_ms: int = 2_500


class SaydiPlaywrightBackend:
    provider_name = "saydivoice"

    def __init__(self, config: SaydiPlaywrightConfig | None = None) -> None:
        self.config = config or SaydiPlaywrightConfig()
        self._playwright = None
        self._context = None
        self._page = None

    def _ensure_open(self) -> Any:
        if self._page is not None:
            return self._page
        profile = self.config.profile_dir
        if not profile.exists() or not any(profile.iterdir()):
            raise VoiceBackendError(
                "authenticated Saydi browser profile is missing or empty",
                disposition=FailureDisposition.RE_AUTH,
                code="PROFILE_MISSING",
            )
        executable = self.config.chromium_executable or discover_chrome_executable()
        if executable is None or not Path(executable).is_file():
            raise VoiceBackendError(
                "installed Google Chrome was not found",
                disposition=FailureDisposition.DO_NOT_RETRY,
                code="CHROME_MISSING",
            )
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        try:
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile),
                executable_path=str(executable),
                headless=self.config.headless,
                accept_downloads=True,
                viewport={"width": 1440, "height": 1000},
            )
            self._context.set_default_timeout(self.config.navigation_timeout_ms)
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
            self._page.goto(
                self.config.tts_url,
                wait_until="domcontentloaded",
                timeout=self.config.navigation_timeout_ms,
            )
            self._page.wait_for_timeout(self.config.settle_ms)
            return self._page
        except Exception:
            self.close()
            raise

    def preflight(self) -> PreflightResult:
        try:
            page = self._ensure_open()
            editor = page.locator('[contenteditable="true"]')
            generate = page.get_by_role("button", name="Tạo giọng nói", exact=True)
            login = page.get_by_text("Đăng nhập", exact=True)
            login_visible = any(login.nth(i).is_visible() for i in range(login.count()))
            ready = editor.count() > 0 and generate.count() > 0 and generate.first.is_enabled() and not login_visible
            return PreflightResult(
                ready=ready,
                page_state="TTS_READY" if ready else "TTS_NOT_READY",
                auth_state="AUTHENTICATED_OR_HIDDEN" if ready else ("LOGIN_REQUIRED" if login_visible else "UNKNOWN"),
                voice=_current_voice(page),
                audio_format=_selected_format(page),
                error_message=None if ready else "Saydi TTS surface is not authenticated and ready",
                disposition=None if ready else (FailureDisposition.RE_AUTH if login_visible else FailureDisposition.RETRY),
            )
        except VoiceBackendError as exc:
            return PreflightResult(
                ready=False,
                page_state="UNKNOWN",
                auth_state="UNKNOWN",
                error_message=str(exc),
                disposition=exc.disposition,
            )
        except Exception as exc:
            return PreflightResult(
                ready=False,
                page_state="UNKNOWN",
                auth_state="UNKNOWN",
                error_message=f"{type(exc).__name__}: {exc}",
                disposition=FailureDisposition.RETRY,
            )

    def apply_settings(self, preset: VoicePreset) -> AppliedSettings:
        page = self._ensure_open()
        preset.validate()
        voice = _set_voice(page, preset.voice)
        stability = _set_slider_ratio(page, 0, preset.stability_ratio)
        speed = _set_slider_ratio(page, 1, preset.speed_ratio)
        audio_format = _set_format(page, preset.audio_format)
        pause_enabled = _set_pause_enabled(page, preset.pause.enabled)
        return AppliedSettings(
            voice=voice,
            preset_key=preset.key,
            stability_ratio=stability,
            speed_ratio=speed,
            audio_format=audio_format,
            pause_enabled=pause_enabled,
        )

    def generate(self, text: str, *, timeout_seconds: float) -> GenerationReceipt:
        page = self._ensure_open()
        editor = page.locator('[contenteditable="true"]').first
        generate = page.get_by_role("button", name="Tạo giọng nói", exact=True).first
        if editor.count() < 1 or generate.count() < 1 or not generate.is_enabled():
            raise VoiceBackendError("Generate surface is unavailable", code="GENERATE_UNAVAILABLE")

        events: list[dict[str, Any]] = []

        def on_response(response: Any) -> None:
            try:
                request = response.request
                if request.resource_type not in {"xhr", "fetch", "media"}:
                    return
                events.append(
                    {
                        "method": str(request.method),
                        "path": urlsplit(str(response.url)).path,
                        "status": int(response.status),
                        "content_type": str((response.headers or {}).get("content-type", ""))[:120],
                    }
                )
            except Exception:
                pass

        page.on("response", on_response)
        baseline_audio = page.locator("audio").count()
        baseline_controls = _result_controls(page)
        baseline_alerts = _alerts(page)
        editor.fill(text)
        page.wait_for_timeout(400)
        generate.click(timeout=5_000)

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            page.wait_for_timeout(400)
            tts_events = [event for event in events if event["path"] == "/api/tts"]
            for event in tts_events:
                status = int(event["status"])
                if status >= 400:
                    return GenerationReceipt(
                        success=False,
                        terminal_state=f"HTTP_{status}",
                        attempt_count=1,
                        error_message=f"Saydi /api/tts returned HTTP {status}",
                        disposition=_http_disposition(status),
                    )

            new_alerts = _alerts(page) - baseline_alerts
            error_alerts = [
                alert for alert in new_alerts
                if re.search(r"lỗi|thất bại|không thể|failed|error|try again", alert, re.I)
            ]
            if error_alerts:
                return GenerationReceipt(
                    success=False,
                    terminal_state="ERROR_ALERT",
                    attempt_count=1,
                    error_message=error_alerts[0][:240],
                    disposition=FailureDisposition.RETRY,
                )

            tts_ok = any(200 <= int(event["status"]) < 300 for event in tts_events)
            audio_response = any(
                200 <= int(event["status"]) < 300
                and str(event.get("content_type") or "").lower().startswith("audio/")
                for event in events
            )
            history_created = any(
                event["path"] == "/api/library/history"
                and event["method"] == "POST"
                and 200 <= int(event["status"]) < 300
                for event in events
            )
            result_ready = (
                page.locator("audio").count() > baseline_audio
                or bool(_result_controls(page) - baseline_controls)
            )
            if tts_ok and (audio_response or history_created or result_ready):
                content_type = next(
                    (
                        str(event.get("content_type") or "")
                        for event in tts_events
                        if 200 <= int(event["status"]) < 300
                    ),
                    None,
                )
                return GenerationReceipt(
                    success=True,
                    terminal_state="SUCCESS_SIGNAL",
                    attempt_count=1,
                    provider_history_created=history_created,
                    content_type=content_type,
                )

        return GenerationReceipt(
            success=False,
            terminal_state="TIMEOUT",
            attempt_count=1,
            error_message="generation timed out without a verified terminal signal",
            disposition=FailureDisposition.RETRY,
        )

    def download(self, output_directory: Path, *, timeout_seconds: float) -> DownloadReceipt:
        page = self._ensure_open()
        control = page.get_by_role("button", name="Tải về", exact=True).first
        if control.count() < 1:
            control = page.get_by_text("Tải về", exact=True).first
        if control.count() < 1:
            return DownloadReceipt(
                success=False,
                error_message="Download control is not available",
                disposition=FailureDisposition.DO_NOT_RETRY,
            )
        output_directory = Path(output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        try:
            with page.expect_download(timeout=max(3_000, int(timeout_seconds * 1000))) as info:
                control.click(timeout=5_000)
            download = info.value
            suggested = _safe_filename(str(download.suggested_filename or "saydivoice.mp3"))
            path = _unique_path(output_directory, suggested)
            download.save_as(str(path))
            return DownloadReceipt(
                success=True,
                local_audio_path=path,
                byte_count=path.stat().st_size,
                sha256=_sha256_file(path),
                suggested_filename=suggested,
            )
        except Exception as exc:
            return DownloadReceipt(
                success=False,
                error_message=f"{type(exc).__name__}: {exc}",
                disposition=FailureDisposition.RETRY,
            )

    def close(self) -> None:
        context, playwright = self._context, self._playwright
        self._page = None
        self._context = None
        self._playwright = None
        if context is not None:
            try:
                context.close()
            except Exception:
                pass
        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                pass
