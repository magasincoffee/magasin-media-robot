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

    processing = any(
        bool((snap.get("generate") or {}).get("disabled"))
        or str((snap.get("generate") or {}).get("aria_busy") or "").lower() == "true"
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


def run_generation_lifecycle(
    page: Any,
    *,
    evidence_dir: Path,
    sample_text: str = DEFAULT_D3_SAMPLE,
    timeout_ms: int = 60_000,
    poll_ms: int = 500,
) -> Path:
    """Run one explicitly authorized generation in a disposable same-session tab.

    This function intentionally does not download audio. It records only structural lifecycle
    evidence and the fixed sample's length/hash, never editor text from the provider page.
    """
    evidence_dir.mkdir(parents=True, exist_ok=True)
    test_page = page.context.new_page()
    trace: list[dict[str, Any]] = []
    try:
        test_page.goto(page.url, wait_until="domcontentloaded", timeout=45_000)
        test_page.wait_for_timeout(1_500)

        editor = test_page.locator('[contenteditable="true"]').first
        generate = test_page.get_by_role("button", name="Tạo giọng nói", exact=True).first
        if editor.count() < 1 or generate.count() < 1:
            raise RuntimeError("D3 requires a visible contenteditable editor and Generate button")

        before = _snapshot(test_page)
        trace.append(before)
        test_page.screenshot(path=str(evidence_dir / "d3_before_generate.png"), full_page=True)

        editor.fill(sample_text)
        test_page.wait_for_timeout(300)
        generate.click(timeout=5_000)

        deadline = max(2_000, timeout_ms)
        elapsed = 0
        last_fp = None
        while elapsed <= deadline:
            snap = _snapshot(test_page)
            fp = _fingerprint(snap)
            if fp != last_fp:
                trace.append(snap)
                last_fp = fp
            analysis = analyze_generation_trace(trace, baseline_alerts=before.get("alerts") or [])
            if analysis["terminal_state"] in {"SUCCESS_SIGNAL", "ERROR"}:
                break
            test_page.wait_for_timeout(max(200, poll_ms))
            elapsed += max(200, poll_ms)

        test_page.screenshot(path=str(evidence_dir / "d3_after_generate.png"), full_page=True)
        analysis = analyze_generation_trace(trace, baseline_alerts=before.get("alerts") or [])
        payload = {
            "schema_version": "1.0",
            "mode": "D3_CONTROLLED_GENERATION",
            "sample_text_length": len(sample_text),
            "sample_text_sha256": hashlib.sha256(sample_text.encode("utf-8")).hexdigest(),
            "download_clicked": False,
            "trace": trace,
            "analysis": analysis,
            "notes": [
                "Generation was allowed only by the explicit --allow-generate operator flag.",
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
