from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from .browser import open_and_probe, probe_page
from .catalog import capture_d2_catalog, write_catalog_outputs
from .classifier import classify_auth_state, classify_page_state
from .enhanced_catalog import capture_d2_enhancements
from .evidence import make_page_signals, sanitize_inventory, write_dom_inventory
from .generation import run_generation_lifecycle
from .logging_utils import configure_logging
from .models import DiscoveryConfig, DiscoveryReport, RunStatus, RuntimePaths
from .runtime import build_runtime_paths, sanitize_error_message, sanitize_url
from .surface import write_surface_outputs

RUNNER_VERSION = "0.4.1"


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

    logger.info("Starting SaydiVoice discovery V0.4.1", extra={"event": "run_started"})
    browser_bundle = None
    try:
        raw_probe, browser_bundle, page = open_and_probe(cfg, runtime)
        signals = make_page_signals(raw_probe)
        state = classify_page_state(signals)

        if state == "LOGIN_REQUIRED" and cfg.login_wait_seconds > 0 and not cfg.headless:
            logger.info(
                f"Manual login may be completed in the open browser; waiting up to {cfg.login_wait_seconds}s",
                extra={"event": "login_wait_started"},
            )
            remaining_ms = cfg.login_wait_seconds * 1000
            poll_ms = max(500, cfg.login_poll_ms)
            while remaining_ms > 0:
                wait_ms = min(poll_ms, remaining_ms)
                page.wait_for_timeout(wait_ms)
                remaining_ms -= wait_ms
                raw_probe = probe_page(page)
                signals = make_page_signals(raw_probe)
                state = classify_page_state(signals)
                if state != "LOGIN_REQUIRED":
                    logger.info(
                        f"Page state changed after manual login wait: {state}",
                        extra={"event": "login_wait_state_changed"},
                    )
                    break

        auth_state = classify_auth_state(signals, state)
        elements = sanitize_inventory(raw_probe.get("elements", []))

        write_dom_inventory(inventory_path, elements)
        surface_map_path, selectors_path = write_surface_outputs(run_dir, signals, elements, auth_state)

        voice_catalog_path = None
        settings_catalog_path = None
        generation_lifecycle_path = None
        notes = [
            "Discovery never enters credentials or downloads audio.",
            "Generate is never invoked unless the operator explicitly supplies --allow-generate.",
            "DOM inventory excludes input/editor values, cookies, storage, authorization headers, and raw HTML.",
            "D1 surface map and ranked selector candidates were generated from current visible controls.",
        ]

        if state == "TTS_READY":
            try:
                catalog_raw = capture_d2_catalog(page, evidence_dir=run_dir)
                try:
                    enhancements = capture_d2_enhancements(
                        page,
                        voice_current=catalog_raw.get("voice_current"),
                        language_current=catalog_raw.get("language_current"),
                    )
                    if enhancements.get("voice_options"):
                        catalog_raw["voice_options"] = enhancements["voice_options"]
                    if enhancements.get("language_options"):
                        catalog_raw["language_options"] = enhancements["language_options"]
                    if enhancements.get("enhancement_warnings"):
                        catalog_raw.setdefault("warnings", []).extend(enhancements["enhancement_warnings"])
                    notes.append("D2.1 custom-surface pass captured privacy-safe visible leaf labels for provider controls that expose no conventional option roles.")
                except Exception as enhanced_exc:
                    safe_enhanced_error = sanitize_error_message(f"{type(enhanced_exc).__name__}: {enhanced_exc}")
                    catalog_raw.setdefault("warnings", []).append(f"Enhanced custom-surface capture incomplete: {safe_enhanced_error}")
                    logger.warning(
                        f"D2 enhanced surface capture incomplete: {safe_enhanced_error}",
                        extra={"event": "d2_enhanced_incomplete"},
                    )

                voice_catalog_path, settings_catalog_path = write_catalog_outputs(run_dir, catalog_raw)
                notes.append(
                    "D2 opened voice/language/pause surfaces only for observation, restored them when practical, and captured current settings evidence plus per-surface screenshots."
                )
                logger.info(
                    "D2 voice/settings catalogs captured without Generate/download actions",
                    extra={"event": "d2_catalog_captured"},
                )
            except Exception as catalog_exc:
                safe_catalog_error = sanitize_error_message(f"{type(catalog_exc).__name__}: {catalog_exc}")
                notes.append(f"D2 catalog capture was incomplete: {safe_catalog_error}")
                logger.warning(
                    f"D2 catalog capture incomplete: {safe_catalog_error}",
                    extra={"event": "d2_catalog_incomplete"},
                )

            if cfg.allow_generate:
                try:
                    generation_lifecycle_path = run_generation_lifecycle(
                        page,
                        evidence_dir=run_dir,
                        timeout_ms=cfg.generation_timeout_ms,
                        poll_ms=cfg.generation_poll_ms,
                        retry_after_reload_error=cfg.generation_retry_after_reload_error,
                    )
                    if cfg.generation_retry_after_reload_error:
                        notes.append("D3 allowed one initial controlled generation and at most one reload retry only when the provider explicitly returned a reload-page error; no download was clicked.")
                    else:
                        notes.append("D3 performed one explicitly authorized controlled generation; no download control was clicked.")
                    logger.info(
                        "D3 controlled generation lifecycle captured",
                        extra={"event": "d3_generation_captured"},
                    )
                except Exception as generation_exc:
                    safe_generation_error = sanitize_error_message(f"{type(generation_exc).__name__}: {generation_exc}")
                    notes.append(f"D3 controlled generation capture was incomplete: {safe_generation_error}")
                    logger.warning(
                        f"D3 controlled generation incomplete: {safe_generation_error}",
                        extra={"event": "d3_generation_incomplete"},
                    )

        page.screenshot(path=str(screenshot_path), full_page=True)

        report = DiscoveryReport(
            schema_version="1.4",
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
            auth_state=auth_state,
            surface_map_path=str(surface_map_path),
            selectors_path=str(selectors_path),
            voice_catalog_path=str(voice_catalog_path) if voice_catalog_path else None,
            settings_catalog_path=str(settings_catalog_path) if settings_catalog_path else None,
            generation_lifecycle_path=str(generation_lifecycle_path) if generation_lifecycle_path else None,
            notes=notes,
        )
        report_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(
            f"Discovery captured with state={state}, auth_state={auth_state}; report={report_path}",
            extra={"event": "run_completed"},
        )
        return report
    except Exception as exc:
        report = DiscoveryReport(
            schema_version="1.4",
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
