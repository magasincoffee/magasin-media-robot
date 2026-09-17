from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .browser import open_and_probe
from .classifier import classify_auth_state, classify_page_state
from .evidence import make_page_signals
from .models import DiscoveryConfig
from .runtime import build_runtime_paths, sanitize_error_message
from .voice_controls import apply_preset
from .voice_presets import describe_preset, get_preset

DEFAULT_PRESET = "tiktok_energetic"
SAMPLE_TEXT = "MAGASIN xin chào. Đây là bản thử preset TikTok năng lượng."


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def usage_text(page: Any) -> str | None:
    body = clean(page.locator("body").inner_text())
    matches = re.findall(r"\b\d[\d,.]*\s*/\s*20,000\b", body)
    return matches[0] if matches else None


def snapshot(page: Any) -> dict[str, Any]:
    generate = page.get_by_role("button", name="Tạo giọng nói", exact=True)
    controls = page.evaluate(
        r"""
() => Array.from(document.querySelectorAll('button,a,[role="button"]'))
.filter(el=>{const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0})
.map(el=>(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim()).filter(Boolean)
"""
    ) or []
    alerts = page.evaluate(
        r"""
() => Array.from(document.querySelectorAll('[role="alert"],[aria-live],[data-sonner-toast],.toast,.Toastify__toast'))
.filter(el=>{const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0})
.map(el=>(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim()).filter(Boolean).slice(0,12)
"""
    ) or []
    return {
        "at": now(),
        "generate_present": generate.count() > 0,
        "generate_enabled": bool(generate.count() > 0 and generate.first.is_enabled()),
        "audio_count": page.locator("audio").count(),
        "result_controls": sorted(
            set(x for x in controls if re.search(r"tải|download|phát|play|nghe|lưu", x, re.I))
        ),
        "alerts": sorted(set(alerts)),
        "usage_text": usage_text(page),
    }


def safe_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        return url[:240]


def run(page: Any, out_dir: Path, *, preset_key: str, timeout_ms: int = 90_000) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    preset = get_preset(preset_key)
    data: dict[str, Any] = {
        "schema_version": "1.1",
        "mode": "D7_CONTROLLED_PRESET_SINGLE_GENERATION",
        "started_at": now(),
        "authorized_generate_limit": 1,
        "attempt_count": 0,
        "generate_click_count": 0,
        "download_click_count": 0,
        "sample_text": SAMPLE_TEXT,
        "preset_key": preset_key,
        "target_preset": describe_preset(preset_key),
    }

    editor = page.locator('[contenteditable="true"]').first
    generate = page.get_by_role("button", name="Tạo giọng nói", exact=True).first
    if editor.count() < 1 or generate.count() < 1:
        raise RuntimeError("editor or Generate button missing")

    configured = apply_preset(page, preset, configure_pause_enable=True)
    data["configured"] = configured

    stability = configured.get("stability") or {}
    speed = configured.get("speed") or {}
    pause = configured.get("pause") or {}
    if configured.get("voice") != preset.voice:
        raise RuntimeError(
            f"voice preset mismatch: expected={preset.voice!r}, observed={configured.get('voice')!r}"
        )
    if not stability.get("found") or abs(float(stability.get("ratio") or 0.0) - preset.stability_ratio) > 0.04:
        raise RuntimeError(f"stability preset mismatch: {stability}")
    if not speed.get("found") or abs(float(speed.get("ratio") or 0.0) - preset.speed_ratio) > 0.04:
        raise RuntimeError(f"speed preset mismatch: {speed}")
    if configured.get("format") != preset.audio_format.upper():
        raise RuntimeError(
            f"format preset mismatch: expected={preset.audio_format.upper()}, observed={configured.get('format')!r}"
        )
    if bool(pause.get("enabled")) != bool(preset.pause.enabled):
        raise RuntimeError(
            f"pause preset mismatch: expected={preset.pause.enabled}, observed={pause.get('enabled')!r}"
        )
    if not generate.is_enabled():
        raise RuntimeError("Generate is disabled before authorized click")

    events: list[dict[str, Any]] = []

    def on_response(response: Any) -> None:
        try:
            request = response.request
            if request.resource_type not in {"xhr", "fetch", "media"}:
                return
            headers = response.headers or {}
            events.append(
                {
                    "at": now(),
                    "kind": "response",
                    "method": str(request.method),
                    "url": safe_url(str(response.url)),
                    "status": int(response.status),
                    "content_type": str(headers.get("content-type", ""))[:120],
                }
            )
        except Exception:
            pass

    def on_failed(request: Any) -> None:
        try:
            if request.resource_type not in {"xhr", "fetch", "media"}:
                return
            events.append(
                {
                    "at": now(),
                    "kind": "request_failed",
                    "method": str(request.method),
                    "url": safe_url(str(request.url)),
                    "failure": sanitize_error_message(str(request.failure or "request failed"), limit=240),
                }
            )
        except Exception:
            pass

    page.on("response", on_response)
    page.on("requestfailed", on_failed)

    before = snapshot(page)
    data["before"] = before
    page.screenshot(path=str(out_dir / "d7_preset_before_generate.png"), full_page=True)
    editor.fill(SAMPLE_TEXT)
    page.wait_for_timeout(500)

    # Authorization boundary: this workflow is permitted to execute exactly one
    # Generate click. There is intentionally no retry path.
    data["attempt_count"] = 1
    data["generate_click_count"] = 1
    generate.click(timeout=5_000)

    deadline = max(5_000, timeout_ms)
    elapsed = 0
    trace = [before]
    success = False
    terminal_reason = "TIMEOUT"
    while elapsed <= deadline:
        page.wait_for_timeout(500)
        elapsed += 500
        snap = snapshot(page)
        trace.append(snap)

        tts_ok = any(
            e.get("kind") == "response"
            and e.get("method") == "POST"
            and urlsplit(str(e.get("url") or "")).path == "/api/tts"
            and 200 <= int(e.get("status") or 0) < 300
            for e in events
        )
        audio_response = any(
            e.get("kind") == "response"
            and 200 <= int(e.get("status") or 0) < 300
            and str(e.get("content_type") or "").lower().startswith("audio/")
            for e in events
        )
        history_ok = any(
            e.get("kind") == "response"
            and e.get("method") == "POST"
            and urlsplit(str(e.get("url") or "")).path == "/api/library/history"
            and 200 <= int(e.get("status") or 0) < 300
            for e in events
        )
        audio_increased = int(snap.get("audio_count") or 0) > int(before.get("audio_count") or 0)
        result_appeared = bool(
            set(snap.get("result_controls") or []) - set(before.get("result_controls") or [])
        )
        new_alerts = [x for x in snap.get("alerts") or [] if x not in (before.get("alerts") or [])]
        error_alert = any(
            re.search(r"lỗi|thất bại|không thể|failed|error|try again", x, re.I)
            for x in new_alerts
        )

        if error_alert:
            terminal_reason = "ERROR_ALERT"
            break
        if tts_ok and (audio_response or history_ok or audio_increased or result_appeared):
            success = True
            terminal_reason = "SUCCESS_SIGNAL"
            break

    after = snapshot(page)
    data["after"] = after
    data["trace"] = trace
    data["network_events"] = events
    data["terminal_state"] = terminal_reason
    data["success"] = success
    data["tts_responses"] = [
        e for e in events if urlsplit(str(e.get("url") or "")).path == "/api/tts"
    ]
    data["history_responses"] = [
        e for e in events if urlsplit(str(e.get("url") or "")).path == "/api/library/history"
    ]
    data["audio_responses"] = [
        e for e in events if str(e.get("content_type") or "").lower().startswith("audio/")
    ]
    data["finished_at"] = now()
    page.screenshot(path=str(out_dir / "d7_preset_after_generate.png"), full_page=True)

    out = out_dir / "d7_controlled_generation.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="D7 controlled one-shot SaydiVoice preset generation")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--chromium-executable")
    parser.add_argument("--generation-timeout-ms", type=int, default=90_000)
    parser.add_argument("--preset", default=DEFAULT_PRESET)
    args = parser.parse_args(argv)

    runtime = build_runtime_paths(args.runtime_root) if args.runtime_root else build_runtime_paths()
    runtime.create()
    cfg = DiscoveryConfig(
        headless=False,
        navigation_timeout_ms=60_000,
        settle_ms=2_500,
        chromium_executable_path=args.chromium_executable,
    )
    bundle = None
    try:
        raw, bundle, page = open_and_probe(cfg, runtime)
        signals = make_page_signals(raw)
        state = classify_page_state(signals)
        auth = classify_auth_state(signals, state)
        if state != "TTS_READY" or auth != "AUTHENTICATED_OR_HIDDEN":
            print(json.dumps({"gate": "FAIL_SESSION", "state": state, "auth": auth}, ensure_ascii=False))
            return 20

        out = run(
            page,
            runtime.runs_dir / "d7_latest",
            preset_key=args.preset,
            timeout_ms=args.generation_timeout_ms,
        )
        data = json.loads(out.read_text(encoding="utf-8"))
        configured = data.get("configured") or {}
        print(
            json.dumps(
                {
                    "gate": "PASS" if data.get("success") else "FAIL_D7",
                    "preset_key": data.get("preset_key"),
                    "attempt_count": data.get("attempt_count"),
                    "generate_click_count": data.get("generate_click_count"),
                    "download_click_count": data.get("download_click_count"),
                    "terminal_state": data.get("terminal_state"),
                    "configured": configured,
                    "usage_before": (data.get("before") or {}).get("usage_text"),
                    "usage_after": (data.get("after") or {}).get("usage_text"),
                    "tts_responses": data.get("tts_responses"),
                    "history_responses": data.get("history_responses"),
                    "audio_responses": data.get("audio_responses"),
                    "evidence": str(out),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if data.get("success") else 25
    except Exception as exc:
        print(
            json.dumps(
                {
                    "gate": "FAIL_BEFORE_OR_DURING_D7",
                    "error": sanitize_error_message(f"{type(exc).__name__}: {exc}"),
                },
                ensure_ascii=False,
            )
        )
        return 1
    finally:
        if bundle:
            playwright, context = bundle
            try:
                context.close()
            finally:
                playwright.stop()


if __name__ == "__main__":
    raise SystemExit(main())
