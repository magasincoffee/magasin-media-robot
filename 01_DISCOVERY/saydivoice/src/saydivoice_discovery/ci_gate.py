from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .runtime import build_runtime_paths


def _latest(paths: list[Path]) -> Path | None:
    existing = [p for p in paths if p.exists()]
    return max(existing, key=lambda p: p.stat().st_mtime) if existing else None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CI acceptance gate for the latest SaydiVoice live run.")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--require-generation-success", action="store_true")
    args = parser.parse_args(argv)

    runtime = build_runtime_paths(args.runtime_root) if args.runtime_root else build_runtime_paths()
    report_path = _latest(list(runtime.reports_dir.glob("discovery_report_*.json")))
    if report_path is None:
        print("GATE_FAIL: no discovery report found")
        return 20

    report = _read_json(report_path)
    summary: dict[str, Any] = {
        "report": str(report_path),
        "run_status": report.get("run_status"),
        "page_state": report.get("page_state"),
        "auth_state": report.get("auth_state"),
    }
    if report.get("run_status") != "CAPTURED" or report.get("page_state") != "TTS_READY":
        print(json.dumps({**summary, "gate": "FAIL_PAGE"}, ensure_ascii=False, indent=2))
        return 21
    if report.get("auth_state") != "AUTHENTICATED_OR_HIDDEN":
        print(json.dumps({**summary, "gate": "FAIL_AUTH"}, ensure_ascii=False, indent=2))
        return 22

    if args.require_generation_success:
        gen_raw = report.get("generation_lifecycle_path")
        if not gen_raw:
            print(json.dumps({**summary, "gate": "FAIL_NO_D3"}, ensure_ascii=False, indent=2))
            return 23
        gen_path = Path(str(gen_raw))
        if not gen_path.exists():
            print(json.dumps({**summary, "gate": "FAIL_D3_MISSING", "generation": str(gen_path)}, ensure_ascii=False, indent=2))
            return 24
        gen = _read_json(gen_path)
        terminal = (gen.get("analysis") or {}).get("terminal_state")
        summary.update({
            "generation": str(gen_path),
            "terminal_state": terminal,
            "attempt_count": gen.get("attempt_count"),
            "preflight_session": (gen.get("preflight_session") or {}).get("state"),
        })
        if terminal != "SUCCESS_SIGNAL":
            print(json.dumps({**summary, "gate": "FAIL_D3"}, ensure_ascii=False, indent=2))
            return 25

    print(json.dumps({**summary, "gate": "PASS"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
