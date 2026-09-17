from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from .browser import open_and_probe
from .classifier import classify_auth_state, classify_page_state
from .evidence import make_page_signals
from .generation import (
    DEFAULT_D3_SAMPLE,
    _NetworkRecorder,
    _network_event_summary,
    _run_attempt,
    _settle_page,
    classify_session_bootstrap,
)
from .models import DiscoveryConfig
from .runtime import build_runtime_paths, sanitize_error_message


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_suggested_filename(value: str) -> str:
    name = Path(value or "download.bin").name[:180]
    return re.sub(r"[\r\n\t]", "_", name) or "download.bin"


def _capture_download(page: Any, *, evidence_dir: Path, timeout_ms: int) -> dict[str, Any]:
    control = page.get_by_role("button", name="Tải về", exact=True).first
    if control.count() < 1:
        control = page.get_by_text("Tải về", exact=True).first
    if control.count() < 1:
        return {
            "clicked": False,
            "completed": False,
            "error": "Download control not found after successful generation.",
            "local_file_retained": False,
        }

    temp_path: Path | None = None
    try:
        with page.expect_download(timeout=max(3_000, timeout_ms)) as download_info:
            control.click(timeout=5_000)
        download = download_info.value
        suggested = _safe_suggested_filename(str(download.suggested_filename or "download.bin"))
        suffix = Path(suggested).suffix.lower()
        temp_path = evidence_dir / f"_d4_download_temp{suffix or '.bin'}"
        download.save_as(str(temp_path))
        size = temp_path.stat().st_size
        sha256 = _sha256_file(temp_path)
        return {
            "clicked": True,
            "completed": True,
            "suggested_filename": suggested,
            "extension": suffix,
            "size_bytes": size,
            "sha256": sha256,
            "local_file_retained": False,
        }
    except Exception as exc:
        return {
            "clicked": True,
            "completed": False,
            "error": sanitize_error_message(f"{type(exc).__name__}: {exc}"),
            "local_file_retained": False,
        }
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass


def run_d4_download(
    page: Any,
    *,
    evidence_dir: Path,
    sample_text: str = DEFAULT_D3_SAMPLE,
    generation_timeout_ms: int = 60_000,
    generation_poll_ms: int = 500,
    download_timeout_ms: int = 15_000,
) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    test_page = page.context.new_page()
    recorder = _NetworkRecorder()
    recorder.attach(test_page)
    attempt: dict[str, Any] | None = None
    download_meta: dict[str, Any] = {
        "clicked": False,
        "completed": False,
        "error": "Generation did not reach a download-ready success state.",
        "local_file_retained": False,
    }
    try:
        test_page.goto(page.url, wait_until="domcontentloaded", timeout=45_000)
        _settle_page(test_page)
        recorder.finalize_error_details()
        preflight_events = recorder.since(0)
        preflight = classify_session_bootstrap(preflight_events)

        if not preflight.get("blocking"):
            attempt = _run_attempt(
                test_page,
                evidence_dir=evidence_dir,
                sample_text=sample_text,
                timeout_ms=generation_timeout_ms,
                poll_ms=generation_poll_ms,
                attempt_no=1,
                recorder=recorder,
            )
            if attempt["analysis"].get("terminal_state") == "SUCCESS_SIGNAL":
                test_page.screenshot(path=str(evidence_dir / "d4_before_download.png"), full_page=True)
                download_meta = _capture_download(
                    test_page,
                    evidence_dir=evidence_dir,
                    timeout_ms=download_timeout_ms,
                )
                test_page.wait_for_timeout(500)
                test_page.screenshot(path=str(evidence_dir / "d4_after_download.png"), full_page=True)

        recorder.finalize_error_details()
        payload = {
            "schema_version": "1.0",
            "mode": "D4_CONTROLLED_DOWNLOAD_DISCOVERY",
            "sample_text_length": len(sample_text),
            "sample_text_sha256": hashlib.sha256(sample_text.encode("utf-8")).hexdigest(),
            "generation_attempt_count": 1 if attempt is not None else 0,
            "preflight_session": preflight,
            "preflight_network_summary": _network_event_summary(preflight_events),
            "generation_analysis": attempt["analysis"] if attempt else {
                "terminal_state": "PREFLIGHT_BLOCKED",
                "processing_observed": False,
            },
            "download": download_meta,
            "network_summary": _network_event_summary(recorder.events),
            "notes": [
                "D4 requires explicit --allow-generate and --allow-download authorization.",
                "Exactly one controlled generation attempt is used; no reload retry is performed.",
                "The downloaded audio is hashed/measured locally and deleted before evidence upload.",
                "No cookies, authorization headers, request bodies, successful response bodies, query strings, or fragments are persisted.",
            ],
        }
        out = evidence_dir / "d4_download.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return out
    finally:
        try:
            test_page.close()
        except Exception:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MAGASIN SaydiVoice D4 controlled download discovery.")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--chromium-executable")
    parser.add_argument("--allow-generate", action="store_true")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--generation-timeout-ms", type=int, default=60_000)
    parser.add_argument("--generation-poll-ms", type=int, default=500)
    parser.add_argument("--download-timeout-ms", type=int, default=15_000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not (args.allow_generate and args.allow_download):
        print("D4_BLOCKED: both --allow-generate and --allow-download are required.", file=sys.stderr)
        return 12

    runtime = build_runtime_paths(args.runtime_root) if args.runtime_root else build_runtime_paths()
    runtime.create()
    cfg = DiscoveryConfig(
        headless=False,
        navigation_timeout_ms=60_000,
        settle_ms=2_500,
        chromium_executable_path=args.chromium_executable,
    )

    browser_bundle = None
    try:
        raw, browser_bundle, page = open_and_probe(cfg, runtime)
        signals = make_page_signals(raw)
        state = classify_page_state(signals)
        auth = classify_auth_state(signals, state)
        if state != "TTS_READY" or auth != "AUTHENTICATED_OR_HIDDEN":
            print(json.dumps({"gate": "FAIL_SESSION", "page_state": state, "auth_state": auth}, ensure_ascii=False))
            return 20

        run_dir = runtime.runs_dir / "d4_latest"
        out = run_d4_download(
            page,
            evidence_dir=run_dir,
            generation_timeout_ms=max(2_000, args.generation_timeout_ms),
            generation_poll_ms=max(200, args.generation_poll_ms),
            download_timeout_ms=max(3_000, args.download_timeout_ms),
        )
        payload = json.loads(out.read_text(encoding="utf-8"))
        success = (
            (payload.get("generation_analysis") or {}).get("terminal_state") == "SUCCESS_SIGNAL"
            and bool((payload.get("download") or {}).get("completed"))
        )
        print(json.dumps({
            "gate": "PASS" if success else "FAIL_D4",
            "evidence": str(out),
            "generation_state": (payload.get("generation_analysis") or {}).get("terminal_state"),
            "download_completed": bool((payload.get("download") or {}).get("completed")),
            "size_bytes": (payload.get("download") or {}).get("size_bytes"),
            "extension": (payload.get("download") or {}).get("extension"),
        }, ensure_ascii=False, indent=2))
        return 0 if success else 25
    finally:
        if browser_bundle is not None:
            playwright, context = browser_bundle
            try:
                context.close()
            finally:
                playwright.stop()


if __name__ == "__main__":
    raise SystemExit(main())
