from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from .browser import open_and_probe
from .classifier import classify_page_state
from .evidence import make_page_signals, sanitize_inventory, write_dom_inventory
from .logging_utils import configure_logging
from .models import DiscoveryConfig, DiscoveryReport, RunStatus, RuntimePaths
from .runtime import build_runtime_paths, sanitize_error_message, sanitize_url

RUNNER_VERSION = "0.1.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_run_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{uuid.uuid4().hex[:8]}"


def status_for_state(page_state: str) -> RunStatus:
    return {
        "TTS_READY": "CAPTURED",
        "LOGIN_REQUIRED": "LOGIN_REQUIRED",
        "ACCESS_BLOCKED": "ACCESS_BLOCKED",
        "UNKNOWN": "UNKNOWN",
    }.get(page_state, "UNKNOWN")  # type: ignore[return-value]


def run_discovery(
    config: DiscoveryConfig | None = None,
    paths: RuntimePaths | None = None,
    *,
    verbose: bool = False,
) -> DiscoveryReport:
    cfg = config or DiscoveryConfig()
    runtime = paths or build_runtime_paths()
    runtime.create()

    run_id = make_run_id()
    run_dir = runtime.runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = runtime.logs_dir / f"discovery_{run_id}.jsonl"
    logger = configure_logging(log_path, verbose=verbose)
    started = _now()

    screenshot_path = runtime.screenshots_dir / f"saydivoice_{run_id}.png"
    inventory_path = run_dir / "dom_inventory.json"
    report_path = runtime.reports_dir / f"discovery_report_{run_id}.json"

    logger.info("Starting non-destructive SaydiVoice discovery", extra={"event": "run_started"})
    browser_bundle = None
    try:
        raw_probe, browser_bundle, page = open_and_probe(cfg, runtime)
        signals = make_page_signals(raw_probe)
        state = classify_page_state(signals)
        elements = sanitize_inventory(raw_probe.get("elements", []))

        page.screenshot(path=str(screenshot_path), full_page=True)
        write_dom_inventory(inventory_path, elements)

        report = DiscoveryReport(
            schema_version="1.0",
            runner_version=RUNNER_VERSION,
            run_id=run_id,
            started_at=started,
            finished_at=_now(),
            target_url=sanitize_url(cfg.tts_url),
            final_url=signals.url,
            page_title=signals.title,
            page_state=state,
            run_status=status_for_state(state),
            screenshot_path=str(screenshot_path),
            dom_inventory_path=str(inventory_path),
            element_count=len(elements),
            notes=[
                "Discovery is read-only: no credentials were entered and no Generate/download action was invoked.",
                "DOM inventory excludes input values, cookies, storage, authorization headers, and raw HTML.",
            ],
        )
        report_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Discovery captured with state={state}; report={report_path}", extra={"event": "run_completed"})
        return report
    except Exception as exc:
        report = DiscoveryReport(
            schema_version="1.0",
            runner_version=RUNNER_VERSION,
            run_id=run_id,
            started_at=started,
            finished_at=_now(),
            target_url=sanitize_url(cfg.tts_url),
            final_url="",
            page_title="",
            page_state="UNKNOWN",
            run_status="BROWSER_ERROR",
            screenshot_path=None,
            dom_inventory_path=None,
            element_count=0,
            notes=["Browser/discovery failure. See local JSONL log; no credentials are recorded."],
            error=sanitize_error_message(f"{type(exc).__name__}: {exc}"),
        )
        report_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        logger.error(f"Discovery failed: {report.error}", extra={"event": "run_failed"})
        return report
    finally:
        if browser_bundle is not None:
            playwright, context = browser_bundle
            try:
                context.close()
            finally:
                playwright.stop()
