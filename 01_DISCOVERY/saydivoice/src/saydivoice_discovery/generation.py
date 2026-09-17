from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_D3_SAMPLE = "Xin chào MAGASIN. Đây là bài kiểm tra tạo giọng nói."

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
    .filter(visible)
    .map(textOf)
    .filter(Boolean)
    .slice(0, 12);
  const bodyText = (document.body?.innerText || '').replace(/\s+/g, ' ');
  const quotaMatch = bodyText.match(/Còn\s+\d+\s+lượt[^\n]{0,80}/i);
  const resultControls = controls.map(textOf).filter(t => /tải|download|phát|play|nghe|lưu/i.test(t)).slice(0, 20);
  return {
    generate: generate ? {
      text: textOf(generate),
      disabled: generate.disabled === true || generate.getAttribute('aria-disabled') === 'true',
      aria_busy: generate.getAttribute('aria-busy'),
    } : null,
    cancel_controls: [...new Set(cancelControls)],
    audio_count: document.querySelectorAll('audio').length,
    quota_text: quotaMatch ? quotaMatch[0] : null,
    alerts: [...new Set(live)],
    result_controls: [...new Set(resultControls)],
  };
}
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _quota_number(text: str | None) -> int | None:
    if not text:
        return None
    m = re.search(r"\b(\d+)\b", text)
    return int(m.group(1)) if m else None


def _snapshot(page: Any) -> dict[str, Any]:
    raw = page.evaluate(GENERATION_STATE_SCRIPT) or {}
    return {
        "at": _now(),
        "generate": raw.get("generate"),
        "cancel_controls": list(raw.get("cancel_controls") or []),
        "audio_count": int(raw.get("audio_count") or 0),
        "quota_text": raw.get("quota_text"),
        "alerts": list(raw.get("alerts") or []),
        "result_controls": list(raw.get("result_controls") or []),
    }


def _fingerprint(snapshot: dict[str, Any]) -> str:
    stable = {k: v for k, v in snapshot.items() if k != "at"}
    return json.dumps(stable, ensure_ascii=False, sort_keys=True)


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
        bool((snap.get("generate") or {}).get("disabled"))
        or str((snap.get("generate") or {}).get("aria_busy") or "").lower() == "true"
        or bool(snap.get("cancel_controls"))
        or (first_had_generate and snap.get("generate") is None)
        for snap in trace[1:]
    )
    error_terms = ("lỗi", "không tải được", "không thể", "thất bại", "failed", "error", "try again", "tải lại")
    error_alerts = [a for a in new_alerts if any(term in a.lower() for term in error_terms)]

    first, last = trace[0], trace[-1]
    first_quota = _quota_number(first.get("quota_text"))
    last_quota = _quota_number(last.get("quota_text"))
    quota_decreased = first_quota is not None and last_quota is not None and last_quota < first_quota
    audio_increased = int(last.get("audio_count") or 0) > int(first.get("audio_count") or 0)
    result_appeared = bool(set(last.get("result_controls") or []) - set(first.get("result_controls") or []))

    if error_alerts:
        terminal = "ERROR"
    elif audio_increased or result_appeared or quota_decreased:
        terminal = "SUCCESS_SIGNAL"
    elif processing:
        terminal = "PROCESSING_OR_TIMEOUT"
    else:
        terminal = "NO_TERMINAL_SIGNAL"

    return {
        "terminal_state": terminal,
        "processing_observed": processing,
        "new_alerts": new_alerts,
        "error_alerts": error_alerts,
        "quota_before": first_quota,
        "quota_after": last_quota,
        "quota_decreased": quota_decreased,
        "audio_count_before": int(first.get("audio_count") or 0),
        "audio_count_after": int(last.get("audio_count") or 0),
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


def _run_attempt(
    page: Any,
    *,
    evidence_dir: Path,
    sample_text: str,
    timeout_ms: int,
    poll_ms: int,
    attempt_no: int,
) -> dict[str, Any]:
    editor = page.locator('[contenteditable="true"]').first
    generate = page.get_by_role("button", name="Tạo giọng nói", exact=True).first
    if editor.count() < 1 or generate.count() < 1:
        raise RuntimeError("D3 requires a visible contenteditable editor and Generate button")

    before = _snapshot(page)
    trace = [before]
    page.screenshot(path=str(evidence_dir / f"d3_attempt{attempt_no}_before.png"), full_page=True)
    if attempt_no == 1:
        page.screenshot(path=str(evidence_dir / "d3_before_generate.png"), full_page=True)

    editor.fill(sample_text)
    page.wait_for_timeout(500)
    generate.click(timeout=5_000)

    deadline = max(2_000, timeout_ms)
    elapsed = 0
    last_fp = None
    while elapsed <= deadline:
        snap = _snapshot(page)
        fp = _fingerprint(snap)
        if fp != last_fp:
            trace.append(snap)
            last_fp = fp
        analysis = analyze_generation_trace(trace, baseline_alerts=before.get("alerts") or [])
        if analysis["terminal_state"] in {"SUCCESS_SIGNAL", "ERROR"}:
            break
        wait_ms = max(200, poll_ms)
        page.wait_for_timeout(wait_ms)
        elapsed += wait_ms

    page.screenshot(path=str(evidence_dir / f"d3_attempt{attempt_no}_after.png"), full_page=True)
    analysis = analyze_generation_trace(trace, baseline_alerts=before.get("alerts") or [])
    return {"attempt": attempt_no, "trace": trace, "analysis": analysis}


def run_generation_lifecycle(
    page: Any,
    *,
    evidence_dir: Path,
    sample_text: str = DEFAULT_D3_SAMPLE,
    timeout_ms: int = 60_000,
    poll_ms: int = 500,
    retry_after_reload_error: bool = False,
) -> Path:
    """Run an explicitly authorized controlled generation probe in a disposable same-session tab.

    By default there is one generation attempt. When retry_after_reload_error is explicitly
    enabled, exactly one additional attempt is permitted only after the provider returns a
    reload-page error. No download control is clicked.
    """
    evidence_dir.mkdir(parents=True, exist_ok=True)
    test_page = page.context.new_page()
    attempts: list[dict[str, Any]] = []
    reload_retry_used = False
    try:
        test_page.goto(page.url, wait_until="domcontentloaded", timeout=45_000)
        _settle_page(test_page)

        first = _run_attempt(
            test_page,
            evidence_dir=evidence_dir,
            sample_text=sample_text,
            timeout_ms=timeout_ms,
            poll_ms=poll_ms,
            attempt_no=1,
        )
        attempts.append(first)

        if retry_after_reload_error and should_retry_after_reload(first["analysis"]):
            reload_retry_used = True
            test_page.reload(wait_until="domcontentloaded", timeout=45_000)
            _settle_page(test_page)
            second = _run_attempt(
                test_page,
                evidence_dir=evidence_dir,
                sample_text=sample_text,
                timeout_ms=timeout_ms,
                poll_ms=poll_ms,
                attempt_no=2,
            )
            attempts.append(second)

        test_page.screenshot(path=str(evidence_dir / "d3_after_generate.png"), full_page=True)
        final = attempts[-1]
        payload = {
            "schema_version": "1.1",
            "mode": "D3_CONTROLLED_GENERATION",
            "sample_text_length": len(sample_text),
            "sample_text_sha256": hashlib.sha256(sample_text.encode("utf-8")).hexdigest(),
            "download_clicked": False,
            "attempt_count": len(attempts),
            "reload_retry_authorized": bool(retry_after_reload_error),
            "reload_retry_used": reload_retry_used,
            "attempts": attempts,
            "trace": final["trace"],
            "analysis": final["analysis"],
            "notes": [
                "Generation was allowed only by the explicit --allow-generate operator flag.",
                "A second attempt is allowed only when --retry-after-reload-error is explicitly authorized and the first provider error asks to reload the page.",
                "The controlled generation runs in a disposable same-session tab and never clicks a download control.",
                "Editor text is not persisted in generation_lifecycle.json; only fixed-sample length/hash are stored.",
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
