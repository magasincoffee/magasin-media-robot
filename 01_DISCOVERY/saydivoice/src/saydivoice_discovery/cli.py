from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .models import DiscoveryConfig
from .runner import run_discovery
from .runtime import build_runtime_paths

EXIT_CODES = {
    "CAPTURED": 0,
    "LOGIN_REQUIRED": 10,
    "ACCESS_BLOCKED": 20,
    "UNKNOWN": 30,
    "BROWSER_ERROR": 40,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MAGASIN SaydiVoice Discovery Runner V0.4.1 (D3 generation lifecycle recovery)."
    )
    parser.add_argument("--headless", action="store_true", help="Run Chromium headless (default is visible).")
    parser.add_argument("--runtime-root", type=Path, help="Override local runtime root for testing/diagnostics.")
    parser.add_argument("--timeout-ms", type=int, default=45_000, help="Navigation/default Playwright timeout.")
    parser.add_argument("--settle-ms", type=int, default=1_500, help="Wait after DOMContentLoaded before probing.")
    parser.add_argument("--chromium-executable", help="Optional Chromium/Chrome executable path for diagnostics.")
    parser.add_argument("--login-wait-seconds", type=int, default=0, help="If login is required in visible mode, keep the browser open and re-check for this many seconds.")
    parser.add_argument("--allow-generate", action="store_true", help="Explicitly authorize a controlled D3 generation. May consume provider quota.")
    parser.add_argument("--retry-after-reload-error", action="store_true", help="If the first provider error explicitly asks to reload the page, authorize exactly one reload + second controlled generation attempt.")
    parser.add_argument("--generation-timeout-ms", type=int, default=60_000, help="Maximum D3 lifecycle observation time per Generate attempt.")
    parser.add_argument("--generation-poll-ms", type=int, default=500, help="D3 lifecycle polling interval.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug-level local logging.")
    parser.add_argument("--json", action="store_true", help="Print the final report JSON to stdout.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = DiscoveryConfig(
        headless=args.headless,
        navigation_timeout_ms=max(1_000, args.timeout_ms),
        settle_ms=max(0, args.settle_ms),
        chromium_executable_path=args.chromium_executable,
        login_wait_seconds=max(0, args.login_wait_seconds),
        allow_generate=args.allow_generate,
        generation_timeout_ms=max(2_000, args.generation_timeout_ms),
        generation_poll_ms=max(200, args.generation_poll_ms),
        generation_retry_after_reload_error=bool(args.allow_generate and args.retry_after_reload_error),
    )
    paths = build_runtime_paths(args.runtime_root) if args.runtime_root else build_runtime_paths()
    report = run_discovery(config, paths, verbose=args.verbose)

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"Run: {report.run_id}")
        print(f"State: {report.page_state}")
        print(f"Auth: {report.auth_state}")
        print(f"Status: {report.run_status}")
        if report.generation_lifecycle_path:
            print(f"D3: {report.generation_lifecycle_path}")
        if report.error:
            print(f"Error: {report.error}", file=sys.stderr)

    return EXIT_CODES[report.run_status]


if __name__ == "__main__":
    raise SystemExit(main())
