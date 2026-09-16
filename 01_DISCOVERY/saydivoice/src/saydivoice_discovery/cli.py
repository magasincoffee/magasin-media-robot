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
        description="MAGASIN SaydiVoice Discovery Runner V0.1 (read-only discovery pass)."
    )
    parser.add_argument("--headless", action="store_true", help="Run Chromium headless (default is visible).")
    parser.add_argument("--runtime-root", type=Path, help="Override local runtime root for testing/diagnostics.")
    parser.add_argument("--timeout-ms", type=int, default=45_000, help="Navigation/default Playwright timeout.")
    parser.add_argument("--settle-ms", type=int, default=1_500, help="Wait after DOMContentLoaded before probing.")
    parser.add_argument("--chromium-executable", help="Optional Chromium/Chrome executable path for diagnostics.")
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
    )
    paths = build_runtime_paths(args.runtime_root) if args.runtime_root else build_runtime_paths()
    report = run_discovery(config, paths, verbose=args.verbose)

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"Run: {report.run_id}")
        print(f"State: {report.page_state}")
        print(f"Status: {report.run_status}")
        if report.error:
            print(f"Error: {report.error}", file=sys.stderr)

    return EXIT_CODES[report.run_status]


if __name__ == "__main__":
    raise SystemExit(main())
