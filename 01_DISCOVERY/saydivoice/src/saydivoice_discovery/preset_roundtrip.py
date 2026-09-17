from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .browser import open_and_probe
from .classifier import classify_auth_state, classify_page_state
from .evidence import make_page_signals
from .models import DiscoveryConfig
from .runtime import build_runtime_paths, sanitize_error_message
from .voice_controls import (
    apply_preset,
    current_voice,
    read_pause_profile,
    selected_format,
    set_format,
    set_pause_enabled,
    set_slider_ratio,
    set_voice,
    slider_state,
)
from .voice_presets import get_preset


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def snapshot(page):
    return {
        "voice": current_voice(page, ("Adam — Giọng hot tiktok", "THEANH28 - Nữ")),
        "stability": slider_state(page, 0),
        "speed": slider_state(page, 1),
        "format": selected_format(page),
        "pause": asdict(read_pause_profile(page)),
    }


def close_ratio(a: dict, b: dict, tolerance: float = 0.04) -> bool:
    if not a.get("found") or not b.get("found"):
        return False
    return abs(float(a.get("ratio") or 0.0) - float(b.get("ratio") or 0.0)) <= tolerance


def run(page, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    preset = get_preset("review_natural")
    original = snapshot(page)
    data = {
        "schema_version": "1.0",
        "mode": "VOICE_PRESET_REVERSIBLE_ROUNDTRIP",
        "started_at": now(),
        "preset": preset.key,
        "original": original,
        "generate_click_count": 0,
        "download_click_count": 0,
        "restore_errors": [],
    }
    page.screenshot(path=str(out_dir / "01_before.png"), full_page=True)

    try:
        data["applied"] = apply_preset(page, preset, configure_pause_enable=True)
        data["after_apply"] = snapshot(page)
        applied = data["after_apply"]
        data["apply_checks"] = {
            "voice": applied["voice"] == preset.voice,
            "stability": abs(float(applied["stability"].get("ratio") or 0.0) - preset.stability_ratio) <= 0.04,
            "speed": abs(float(applied["speed"].get("ratio") or 0.0) - preset.speed_ratio) <= 0.04,
            "format": applied["format"] == preset.audio_format,
            "pause_enabled": bool(applied["pause"]["enabled"]) == preset.pause.enabled,
        }
        page.screenshot(path=str(out_dir / "02_applied.png"), full_page=True)
    except Exception as exc:
        data["apply_error"] = sanitize_error_message(f"{type(exc).__name__}: {exc}")
        data["apply_checks"] = {}
    finally:
        try:
            if original.get("voice"):
                set_voice(page, str(original["voice"]))
        except Exception as exc:
            data["restore_errors"].append(sanitize_error_message(f"voice: {exc}"))
        try:
            set_slider_ratio(page, 0, float(original["stability"].get("ratio") or 0.60))
        except Exception as exc:
            data["restore_errors"].append(sanitize_error_message(f"stability: {exc}"))
        try:
            set_slider_ratio(page, 1, float(original["speed"].get("ratio") or 0.50))
        except Exception as exc:
            data["restore_errors"].append(sanitize_error_message(f"speed: {exc}"))
        try:
            if original.get("format"):
                set_format(page, str(original["format"]))
        except Exception as exc:
            data["restore_errors"].append(sanitize_error_message(f"format: {exc}"))
        try:
            set_pause_enabled(page, bool(original["pause"]["enabled"]))
        except Exception as exc:
            data["restore_errors"].append(sanitize_error_message(f"pause: {exc}"))

    data["final"] = snapshot(page)
    final = data["final"]
    data["restored"] = bool(
        final["voice"] == original["voice"]
        and close_ratio(final["stability"], original["stability"])
        and close_ratio(final["speed"], original["speed"])
        and final["format"] == original["format"]
        and bool(final["pause"]["enabled"]) == bool(original["pause"]["enabled"])
        and not data["restore_errors"]
    )
    data["pass"] = bool(
        data.get("apply_checks")
        and all(data["apply_checks"].values())
        and data["restored"]
        and not data.get("apply_error")
    )
    data["finished_at"] = now()
    page.screenshot(path=str(out_dir / "03_restored.png"), full_page=True)
    out = out_dir / "preset_roundtrip.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Reversible Saydi voice preset roundtrip")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--chromium-executable")
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
        out = run(page, runtime.runs_dir / "preset_roundtrip_latest")
        data = json.loads(out.read_text(encoding="utf-8"))
        print(json.dumps({
            "gate": "PASS" if data["pass"] else "FAIL_PRESET_ROUNDTRIP",
            "preset": data["preset"],
            "apply_checks": data.get("apply_checks"),
            "restored": data["restored"],
            "restore_errors": data["restore_errors"],
            "generate_click_count": 0,
            "download_click_count": 0,
            "evidence": str(out),
        }, ensure_ascii=False, indent=2))
        return 0 if data["pass"] else 25
    except Exception as exc:
        print(json.dumps({"gate": "FAIL", "error": sanitize_error_message(f"{type(exc).__name__}: {exc}")}, ensure_ascii=False))
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
