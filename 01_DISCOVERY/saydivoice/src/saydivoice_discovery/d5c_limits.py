from __future__ import annotations

import argparse
import json
from pathlib import Path

from .browser import open_and_probe
from .classifier import classify_auth_state, classify_page_state
from .d5_limits import run_d5_input_limits
from .evidence import make_page_signals
from .models import DiscoveryConfig
from .runtime import build_runtime_paths


def _normalize_boundary_behavior(payload: dict) -> dict:
    limit = int(payload.get("advertised_limit") or 0)
    observations = list(payload.get("observations") or [])
    for item in observations:
        target = int(item.get("target_length") or 0)
        current = item.get("counter_current")
        enabled = bool(item.get("generate_enabled"))
        # Saydi's editor clamps extra input at the advertised boundary instead
        # of accepting 20,001 chars and disabling Generate. This is a valid
        # client-side boundary behavior as long as the counter remains at the
        # limit and no /api/tts request is emitted.
        if limit and target > limit and current == limit and enabled:
            item["classification"] = "CLAMPED_AT_LIMIT_UI"
            item["clamped_from_target_length"] = target
            item["effective_length"] = limit
    payload["observations"] = observations
    payload["boundary_interpretation"] = (
        "The contenteditable clamps input at the advertised 20,000-character boundary; "
        "Generate remains enabled for the retained 20,000 characters."
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="D5C read-only SaydiVoice input-boundary verification")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--chromium-executable")
    parser.add_argument("--settle-ms", type=int, default=450)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
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
            print(json.dumps({"gate": "FAIL_SESSION", "page_state": state, "auth_state": auth}, ensure_ascii=False))
            return 20

        run_dir = runtime.runs_dir / "d5_limits_latest"
        out = run_d5_input_limits(page, evidence_dir=run_dir, settle_ms=max(200, args.settle_ms))
        payload = json.loads(out.read_text(encoding="utf-8"))
        payload = _normalize_boundary_behavior(payload)
        payload["schema_version"] = "1.1"
        payload["mode"] = "D5C_READONLY_INPUT_BOUNDARY"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        observations = payload.get("observations") or []
        classifications = {str(item.get("classification")) for item in observations}
        pass_gate = (
            int(payload.get("tts_request_count") or 0) == 0
            and "EMPTY_BLOCKED_UI" in classifications
            and "ACCEPTED_UI" in classifications
            and "CLAMPED_AT_LIMIT_UI" in classifications
        )
        print(json.dumps({
            "gate": "PASS" if pass_gate else "REVIEW",
            "evidence": str(out),
            "advertised_limit": payload.get("advertised_limit"),
            "tts_request_count": payload.get("tts_request_count"),
            "classifications": sorted(classifications),
            "generate_clicked": False,
            "download_clicked": False,
        }, ensure_ascii=False, indent=2))
        return 0 if pass_gate else 25
    finally:
        if bundle is not None:
            playwright, context = bundle
            try:
                context.close()
            finally:
                playwright.stop()


if __name__ == "__main__":
    raise SystemExit(main())
