from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .runtime import sanitize_error_message, sanitize_url

MAX_NETWORK_EVENTS = 180
NETWORK_RESOURCE_TYPES = {"xhr", "fetch", "media"}
SAYDI_ORIGIN = "https://voice.saydi.ai"
SAFE_ERROR_PATHS = {"/api/session/start", "/api/samples", "/api/gpu/eta"}
SAFE_ERROR_KEYS = {"error", "message", "detail", "code", "status", "reason", "type"}
DEFAULT_D3_SAMPLE = "Xin chào MAGASIN. Đây là bài kiểm tra tạo giọng nói."


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_network_url(value: str) -> str:
    return sanitize_url(value)


def _is_safe_error_endpoint(url: str) -> bool:
    try:
        p = urlsplit(url)
        return f"{p.scheme}://{p.netloc}" == SAYDI_ORIGIN and p.path in SAFE_ERROR_PATHS
    except Exception:
        return False


def _safe_error_json(value: Any, *, depth: int = 0) -> Any:
    if depth > 2:
        return None
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return sanitize_error_message(value, limit=280)
    if isinstance(value, list):
        out = [_safe_error_json(v, depth=depth + 1) for v in value[:3]]
        return [v for v in out if v is not None]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, child in value.items():
            if str(key).lower() not in SAFE_ERROR_KEYS:
                continue
            safe = _safe_error_json(child, depth=depth + 1)
            if safe is not None:
                out[str(key)] = safe
        return out or None
    return sanitize_error_message(str(value), limit=280)


def classify_session_bootstrap(events: list[dict[str, Any]]) -> dict[str, Any]:
    statuses: dict[str, list[int]] = {path: [] for path in SAFE_ERROR_PATHS}
    details: dict[str, list[Any]] = {path: [] for path in SAFE_ERROR_PATHS}
    for event in events:
        if event.get("kind") != "response":
            continue
        try:
            path = urlsplit(str(event.get("url") or "")).path
        except Exception:
            continue
        if path not in statuses:
            continue
        status = event.get("status")
        if isinstance(status, int):
            statuses[path].append(status)
        if event.get("error_json") is not None:
            details[path].append(event["error_json"])

    session_statuses = statuses["/api/session/start"]
    sample_statuses = statuses["/api/samples"]
    gpu_statuses = statuses["/api/gpu/eta"]
    if any(200 <= s < 300 for s in session_statuses):
        state, blocking = "SESSION_STARTED", False
    elif 403 in session_statuses:
        state, blocking = "SESSION_START_FORBIDDEN", True
    elif any(s >= 400 for s in session_statuses):
        state, blocking = "SESSION_START_HTTP_ERROR", True
    elif any(s in {401, 403} for s in sample_statuses):
        state, blocking = "SESSION_NOT_ESTABLISHED", True
    else:
        state, blocking = "SESSION_START_NOT_OBSERVED", False

    return {
        "state": state,
        "blocking": blocking,
        "session_start_statuses": session_statuses,
        "samples_statuses": sample_statuses,
        "gpu_eta_statuses": gpu_statuses,
        "safe_error_details": {k: v for k, v in details.items() if v},
    }


def _network_event_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [e for e in events if e.get("kind") == "request_failed"]
    http_errors = [
        e for e in events
        if e.get("kind") == "response" and isinstance(e.get("status"), int) and int(e["status"]) >= 400
    ]
    return {
        "event_count": len(events),
        "request_failed_count": len(failed),
        "http_error_count": len(http_errors),
        "http_error_statuses": sorted({int(e["status"]) for e in http_errors}),
        "failed_urls": list(dict.fromkeys(e.get("url") for e in failed if e.get("url")))[:12],
        "http_error_urls": list(dict.fromkeys(e.get("url") for e in http_errors if e.get("url")))[:12],
    }


class _NetworkRecorder:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self._pending: list[tuple[dict[str, Any], Any]] = []

    def _append(self, event: dict[str, Any]) -> None:
        if len(self.events) < MAX_NETWORK_EVENTS:
            self.events.append(event)

    def attach(self, page: Any) -> None:
        def on_request(request: Any) -> None:
            try:
                if request.resource_type not in NETWORK_RESOURCE_TYPES:
                    return
                self._append({
                    "at": _now(), "kind": "request", "method": str(request.method),
                    "resource_type": str(request.resource_type), "url": _safe_network_url(str(request.url)),
                })
            except Exception:
                pass

        def on_response(response: Any) -> None:
            try:
                request = response.request
                if request.resource_type not in NETWORK_RESOURCE_TYPES:
                    return
                headers = response.headers or {}
                event = {
                    "at": _now(), "kind": "response", "method": str(request.method),
                    "resource_type": str(request.resource_type), "url": _safe_network_url(str(response.url)),
                    "status": int(response.status), "content_type": str(headers.get("content-type", ""))[:120],
                }
                self._append(event)
                if int(response.status) >= 400 and "json" in event["content_type"].lower() and _is_safe_error_endpoint(str(response.url)):
                    self._pending.append((event, response))
            except Exception:
                pass

        def on_failed(request: Any) -> None:
            try:
                if request.resource_type not in NETWORK_RESOURCE_TYPES:
                    return
                self._append({
                    "at": _now(), "kind": "request_failed", "method": str(request.method),
                    "resource_type": str(request.resource_type), "url": _safe_network_url(str(request.url)),
                    "failure": sanitize_error_message(str(request.failure or "request failed"), limit=240),
                })
            except Exception:
                pass

        page.on("request", on_request)
        page.on("response", on_response)
        page.on("requestfailed", on_failed)

    def finalize_error_details(self) -> None:
        pending, self._pending = self._pending, []
        for event, response in pending:
            try:
                response.finished()
                safe = _safe_error_json(response.json())
                if safe is not None:
                    event["error_json"] = safe
            except Exception:
                pass

    def mark(self) -> int:
        return len(self.events)

    def since(self, index: int) -> list[dict[str, Any]]:
        return list(self.events[index:])


GENERATION_STATE_SCRIPT = r"""
() => {
  const visible = (el) => {
    if (!el) return false;
    const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  };
  const textOf = (el) => (el?.innerText || el?.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 220);
  const controls = Array.from(document.querySelectorAll('button, a, [role="button"]')).filter(visible);
  const generate = controls.find(el => textOf(el) === 'Tạo giọng nói') || null;
  const cancelControls = controls.map(textOf).filter(t => /^(hủy|huỷ|cancel)$/i.test(t));
  const live = Array.from(document.querySelectorAll('[role="alert"], [aria-live], [data-sonner-toast], .toast, .Toastify__toast'))
    .filter(visible).map(textOf).filter(Boolean).slice(0, 12);
  const bodyText = (document.body?.innerText || '').replace(/\s+/g, ' ');
  const quotaMatch = bodyText.match(/Còn\s+\d+\s+lượt[^\n]{0,80}/i);
  const resultControls = controls.map(textOf).filter(t => /tải|download|phát|play|nghe|lưu/i.test(t)).slice(0, 20);
  return {
    generate: generate ? {text: textOf(generate), disabled: generate.disabled === true || generate.getAttribute('aria-disabled') === 'true', aria_busy: generate.getAttribute('aria-busy')} : null,
    cancel_controls: [...new Set(cancelControls)], audio_count: document.querySelectorAll('audio').length,
    quota_text: quotaMatch ? quotaMatch[0] : null, alerts: [...new Set(live)], result_controls: [...new Set(resultControls)],
  };
}
"""


def _quota_number(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"\b(\d+)\b", text)
    return int(match.group(1)) if match else None


def _snapshot(page: Any) -> dict[str, Any]:
    raw = page.evaluate(GENERATION_STATE_SCRIPT) or {}
    return {
        "at": _now(), "generate": raw.get("generate"), "cancel_controls": list(raw.get("cancel_controls") or []),
        "audio_count": int(raw.get("audio_count") or 0), "quota_text": raw.get("quota_text"),
        "alerts": list(raw.get("alerts") or []), "result_controls": list(raw.get("result_controls") or []),
    }


def _fingerprint(snapshot: dict[str, Any]) -> str:
    return json.dumps({k: v for k, v in snapshot.items() if k != "at"}, ensure_ascii=False, sort_keys=True)


def analyze_generation_trace(trace: list[dict[str, Any]], baseline_alerts: list[str] | None = None) -> dict[str, Any]:
    if not trace:
        return {"terminal_state": "NO_TRACE", "processing_observed": False, "new_alerts": []}
    baseline = set(baseline_alerts or [])
    new_alerts: list[str] = []
    for snap in trace[1:]:
        for alert in snap.get("alerts") or []:
            if alert not in baseline and alert not in new_alerts:
                new_alerts.append(alert)
    first_had_generate = trace[0].get("generate") is not None
    processing = any(
        bool((s.get("generate") or {}).get("disabled"))
        or str((s.get("generate") or {}).get("aria_busy") or "").lower() == "true"
        or bool(s.get("cancel_controls"))
        or (first_had_generate and s.get("generate") is None)
        for s in trace[1:]
    )
    error_terms = ("lỗi", "không tải được", "không thể", "thất bại", "failed", "error", "try again", "tải lại")
    error_alerts = [a for a in new_alerts if any(term in a.lower() for term in error_terms)]
    first, last = trace[0], trace[-1]
    q0, q1 = _quota_number(first.get("quota_text")), _quota_number(last.get("quota_text"))
    quota_decreased = q0 is not None and q1 is not None and q1 < q0
    audio_increased = int(last.get("audio_count") or 0) > int(first.get("audio_count") or 0)
    result_appeared = bool(set(last.get("result_controls") or []) - set(first.get("result_controls") or []))
    terminal = "ERROR" if error_alerts else "SUCCESS_SIGNAL" if (audio_increased or result_appeared or quota_decreased) else "PROCESSING_OR_TIMEOUT" if processing else "NO_TERMINAL_SIGNAL"
    return {
        "terminal_state": terminal, "processing_observed": processing, "new_alerts": new_alerts,
        "error_alerts": error_alerts, "quota_before": q0, "quota_after": q1, "quota_decreased": quota_decreased,
        "audio_count_before": int(first.get("audio_count") or 0), "audio_count_after": int(last.get("audio_count") or 0),
        "result_control_appeared": result_appeared,
    }


def should_retry_after_reload(analysis: dict[str, Any]) -> bool:
    if analysis.get("terminal_state") != "ERROR":
        return False
    text = " ".join(str(x) for x in analysis.get("error_alerts") or []).lower()
    return "tải lại trang" in text or "reload" in text


def _settle_page(page: Any) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:
        pass
    page.wait_for_timeout(1_500)


def _run_attempt(page: Any, *, evidence_dir: Path, sample_text: str, timeout_ms: int, poll_ms: int, attempt_no: int, recorder: _NetworkRecorder) -> dict[str, Any]:
    editor = page.locator('[contenteditable="true"]').first
    generate = page.get_by_role("button", name="Tạo giọng nói", exact=True).first
    if editor.count() < 1 or generate.count() < 1:
        raise RuntimeError("D3 requires a visible contenteditable editor and Generate button")
    mark = recorder.mark()
    before = _snapshot(page)
    trace = [before]
    page.screenshot(path=str(evidence_dir / f"d3_attempt{attempt_no}_before.png"), full_page=True)
    if attempt_no == 1:
        page.screenshot(path=str(evidence_dir / "d3_before_generate.png"), full_page=True)
    editor.fill(sample_text)
    page.wait_for_timeout(500)
    generate.click(timeout=5_000)
    elapsed, last_fp = 0, None
    while elapsed <= max(2_000, timeout_ms):
        snap = _snapshot(page)
        fp = _fingerprint(snap)
        if fp != last_fp:
            trace.append(snap)
            last_fp = fp
        analysis = analyze_generation_trace(trace, baseline_alerts=before.get("alerts") or [])
        if analysis["terminal_state"] in {"SUCCESS_SIGNAL", "ERROR"}:
            break
        wait = max(200, poll_ms)
        page.wait_for_timeout(wait)
        elapsed += wait
    page.screenshot(path=str(evidence_dir / f"d3_attempt{attempt_no}_after.png"), full_page=True)
    recorder.finalize_error_details()
    events = recorder.since(mark)
    return {
        "attempt": attempt_no, "baseline_alerts": list(before.get("alerts") or []), "trace": trace,
        "analysis": analyze_generation_trace(trace, baseline_alerts=before.get("alerts") or []),
        "network_events": events, "network_summary": _network_event_summary(events),
    }


def run_generation_lifecycle(page: Any, *, evidence_dir: Path, sample_text: str = DEFAULT_D3_SAMPLE, timeout_ms: int = 60_000, poll_ms: int = 500, retry_after_reload_error: bool = False) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    test_page = page.context.new_page()
    recorder = _NetworkRecorder()
    recorder.attach(test_page)
    attempts: list[dict[str, Any]] = []
    retry_used = False
    retry_decision = "not_evaluated"
    try:
        test_page.goto(page.url, wait_until="domcontentloaded", timeout=45_000)
        _settle_page(test_page)
        recorder.finalize_error_details()
        preflight_events = recorder.since(0)
        preflight = classify_session_bootstrap(preflight_events)
        if preflight.get("blocking"):
            retry_decision = "preflight_session_blocked"
        else:
            attempts.append(_run_attempt(test_page, evidence_dir=evidence_dir, sample_text=sample_text, timeout_ms=timeout_ms, poll_ms=poll_ms, attempt_no=1, recorder=recorder))
        if attempts and retry_after_reload_error and should_retry_after_reload(attempts[0]["analysis"]):
            retry_decision, retry_used = "reload_error_retry", True
            test_page.reload(wait_until="domcontentloaded", timeout=45_000)
            _settle_page(test_page)
            attempts.append(_run_attempt(test_page, evidence_dir=evidence_dir, sample_text=sample_text, timeout_ms=timeout_ms, poll_ms=poll_ms, attempt_no=2, recorder=recorder))
        elif attempts and not retry_after_reload_error:
            retry_decision = "retry_not_authorized"
        elif attempts and attempts[0]["analysis"].get("terminal_state") == "ERROR":
            retry_decision = "error_not_reload_specific"
        elif attempts:
            retry_decision = "retry_not_applicable"
        test_page.screenshot(path=str(evidence_dir / "d3_after_generate.png"), full_page=True)
        final = attempts[-1] if attempts else None
        analysis = final["analysis"] if final else {
            "terminal_state": "PREFLIGHT_BLOCKED", "processing_observed": False, "new_alerts": [], "error_alerts": [],
            "quota_before": None, "quota_after": None, "quota_decreased": False,
            "audio_count_before": None, "audio_count_after": None, "result_control_appeared": False,
        }
        payload = {
            "schema_version": "1.3", "mode": "D3_CONTROLLED_GENERATION",
            "sample_text_length": len(sample_text), "sample_text_sha256": hashlib.sha256(sample_text.encode("utf-8")).hexdigest(),
            "download_clicked": False, "attempt_count": len(attempts),
            "reload_retry_authorized": bool(retry_after_reload_error), "reload_retry_used": retry_used,
            "retry_decision": retry_decision, "preflight_network_events": preflight_events,
            "preflight_network_summary": _network_event_summary(preflight_events), "preflight_session": preflight,
            "attempts": attempts, "trace": final["trace"] if final else [], "analysis": analysis,
            "notes": [
                "Generation requires explicit --allow-generate authorization.",
                "The controlled generation uses a disposable same-session tab and never clicks Download.",
                "Editor text is not persisted; only the fixed sample length/hash are stored.",
                "Network evidence excludes headers, cookies, authorization, request bodies, successful response bodies, query strings, and fragments.",
            ],
        }
        out = evidence_dir / "generation_lifecycle.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return out
    finally:
        try:
            test_page.close()
        except Exception:
            pass
