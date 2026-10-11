"""SAYDI002-003 non-generative authenticated provider readiness preflight.

Only runs on the exact recovered DESKTOP-4K7IM13 profile host.
Never writes text to TTS, selects a voice, clicks Generate, or uses login.
Personal Chrome profile, full catalogs and browser evidence stay local.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .models import DiscoveryConfig
from .runner import run_discovery
from .runtime import build_runtime_paths
from .voice_presets import get_preset

SCHEMA = "saydi002-003-authenticated-preflight-v1"
EXPECTED_HOST = "DESKTOP-4K7IM13"
PRESET = "audiobook_south_male_clip"


def _safe_load(path: str | None, *, local_root: Path) -> dict[str, Any] | None:
    if not path:
        return None
    candidate = Path(path).resolve()
    if not candidate.is_file() or local_root.resolve() not in candidate.parents:
        return None
    return json.loads(candidate.read_text(encoding="utf-8"))


def evaluate(
    report: dict[str, Any],
    voice: dict[str, Any] | None,
    settings: dict[str, Any] | None,
    *, host: str, profile_exists: bool, profile_locked: bool = False
) -> dict[str, Any]:
    """Strictly reject unverifiable auth, voice controls or output format.

    Emit only metadata. Never serialize UI HTML, book text or actual profiles.
    """
    preset = get_preset(PRESET)
    checks = {
        "expected_host": host.strip().upper() == EXPECTED_HOST,
        "persistent_profile_exists": profile_exists,
        "profile_not_locked": not profile_locked,
        "page_ready": report.get("page_state") == "TTS_READY",
        "authenticated": report.get("auth_state") == "AUTHENTICATED_OR_HIDDEN",
        "captured": report.get("run_status") == "CAPTURED",
        "no_generation_lifecycle": not bool(report.get("generation_lifecycle_path")),
        "voice_surface_opened": bool(voice and voice.get("opened")),
        "voice_surface_closed": bool(voice and voice.get("closed_after_observation")),
        "required_voice_available": bool(
            voice and (
                voice.get("current_label") == preset.voice
                or any(
                    isinstance(v, dict) and v.get("text") == preset.voice
                    for v in voice.get("options", [])
                )
            )
        ),
        "stability_control_seen": bool(
            settings and (settings.get("settings") or {}).get("stability", {}).get("found")
        ),
        "speed_control_seen": bool(
            settings and (settings.get("settings") or {}).get("speed", {}).get("found")
        ),
        "pause_control_seen": bool(
            settings and (settings.get("settings") or {}).get("pause", {}).get("found")
        ),
        "mp3_format_available": bool(
            settings and preset.audio_format in (
                (settings.get("settings") or {}).get("output_format", {}).get("options") or []
            )
        ),
    }
    return {
        "schema": SCHEMA,
        "task_id": "SAYDI002-003",
        "host_match": checks["expected_host"],
        "preset": PRESET,
        "checks": checks,
        "generate_clicks": 0 if checks["no_generation_lifecycle"] else None,
        "new_audio_files": 0 if checks["no_generation_lifecycle"] else None,
        "status": "PASS" if all(checks.values()) else "BLOCKED_OR_REVIEW",
        "owner_audio_approval": False,
        "production_authorized": False,
        "private_data_exported": False,
    }


def run_preflight(*, host: str, chrome_path: Path, evidence_path: Path) -> dict[str, Any]:
    runtime = build_runtime_paths()
    if host.strip().upper() != EXPECTED_HOST:
        raise ValueError("WRONG_HOST_NO_PROFILE_OPENED")
    if not runtime.profile_dir.is_dir():
        raise ValueError("MISSING_RECOVERED_PROFILE_NO_PROFILE_OPENED")
    if not chrome_path.is_file():
        raise ValueError("CHROME_NOT_INSTALLED")
    # The GitHub PowerShell wrapper checks for an active Chrome process holding
    # the recovered profile. No process termination or profile deletion.
    if not evidence_path.is_absolute() or runtime.profile_dir in evidence_path.parents:
        raise ValueError("UNSAFE_EVIDENCE_PATH")
    if evidence_path.exists():
        raise FileExistsError("EXCLUSIVE_EVIDENCE_FILE_REQUIRED")

    config = DiscoveryConfig(
        headless=False,
        chromium_executable_path=str(chrome_path),
        allow_generate=False, login_wait_seconds=0,
        generation_retry_after_reload_error=False,
        navigation_timeout_ms=60000, settle_ms=2500,
    )
    report_obj = run_discovery(config, runtime)
    report = report_obj.to_dict()
    voice = _safe_load(report.get("voice_catalog_path"), local_root=runtime.root)
    settings = _safe_load(report.get("settings_catalog_path"), local_root=runtime.root)
    result = evaluate(report, voice, settings, host=host, profile_exists=True)
    result["report_sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    with evidence_path.open("x", encoding="utf-8") as writer:
        json.dump(result, writer, ensure_ascii=False, indent=2)
        writer.write("\n")
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SAYDI002-003 authenticated non-Generate field preflight")
    p.add_argument("--chrome", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--allow-authenticated-preflight", action="store_true")
    args = p.parse_args(argv)
    if not args.allow_authenticated_preflight:
        print("SAYDI002_003_PREFLIGHT_DISABLED_DEFAULT")
        return 0
    host = os.environ.get("COMPUTERNAME", "")
    try:
        result = run_preflight(host=host, chrome_path=args.chrome, evidence_path=args.output)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        # Fixed error class only: no browser URLs, errors, credential data, voice
        # catalog, manuscript or screenshot paths printed in public CI logs.
        print("SAYDI002_003_RESULT=BLOCKED_OR_REVIEW")
        print("SAYDI002_003_ERROR_CLASS=" + type(exc).__name__)
        return 21
    print("SAYDI002_003_HOST_MATCH=" + str(result["host_match"]).lower())
    print("SAYDI002_003_GENERATE_CLICKS=" + str(result["generate_clicks"]))
    print("SAYDI002_003_RESULT=" + result["status"])
    print("SAYDI002_003_CHECKS=" + json.dumps(result["checks"], sort_keys=True))
    return 0 if result["status"] == "PASS" else 21


if __name__ == "__main__":
    raise SystemExit(main())
