from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .browser import open_and_probe
from .classifier import classify_auth_state, classify_page_state
from .evidence import make_page_signals
from .generation import _NetworkRecorder, _network_event_summary
from .models import DiscoveryConfig
from .runtime import build_runtime_paths

_COUNTER_RE = re.compile(r"(?P<current>\d[\d.,]*)\s*/\s*(?P<limit>\d[\d.,]*)")


def _to_int(value: str) -> int:
    return int(re.sub(r"\D", "", value))


def parse_counter(text: str | None) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    match = _COUNTER_RE.search(text)
    if not match:
        return None, None
    return _to_int(match.group("current")), _to_int(match.group("limit"))


def classify_input_state(length: int, limit: int | None, generate_enabled: bool) -> str:
    if length == 0 and not generate_enabled:
        return "EMPTY_BLOCKED_UI"
    if limit is not None and length > limit and not generate_enabled:
        return "OVER_LIMIT_BLOCKED_UI"
    if (limit is None or length <= limit) and generate_enabled:
        return "ACCEPTED_UI"
    return "AMBIGUOUS"


def _is_tts_request(event: dict[str, Any]) -> bool:
    if event.get("kind") != "request":
        return False
    try:
        return urlsplit(str(event.get("url") or "")).path == "/api/tts"
    except Exception:
        return False


D5_SNAPSHOT_SCRIPT = r"""
() => {
  const visible = (el) => {
    if (!el) return false;
    const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  };
  const textOf = (el) => (el?.innerText || el?.textContent || '').replace(/\s+/g, ' ').trim();
  const editor = Array.from(document.querySelectorAll('[contenteditable="true"]')).find(visible) || null;
  const controls = Array.from(document.querySelectorAll('button,[role="button"]')).filter(visible);
  const generate = controls.find(el => textOf(el) === 'Tạo giọng nói') || null;
  const bodyText = (document.body?.innerText || '').replace(/\s+/g, ' ');
  const counter = bodyText.match(/\d[\d.,]*\s*\/\s*\d[\d.,]*/)?.[0] || null;
  const candidates = Array.from(document.querySelectorAll('[role="alert"],[aria-live],p,span,div'))
    .filter(visible)
    .map(textOf)
    .filter(t => t && t.length <= 180 && /(tối đa|vượt|ký tự|character|bắt buộc|không được để trống|nhập văn bản)/i.test(t))
    .slice(0, 12);
  return {
    editor_length: editor ? textOf(editor).length : null,
    counter_text: counter,
    generate_present: !!generate,
    generate_enabled: !!generate && !(generate.disabled === true || generate.getAttribute('aria-disabled') === 'true'),
    validation_messages: [...new Set(candidates)],
  };
}
"""


def _snapshot(page: Any) -> dict[str, Any]:
    raw = page.evaluate(D5_SNAPSHOT_SCRIPT) or {}
    current, limit = parse_counter(raw.get("counter_text"))
    return {
        "editor_length": raw.get("editor_length"),
        "counter_text": raw.get("counter_text"),
        "counter_current": current,
        "counter_limit": limit,
        "generate_present": bool(raw.get("generate_present")),
        "generate_enabled": bool(raw.get("generate_enabled")),
        "validation_messages": list(raw.get("validation_messages") or []),
    }


def run_d5_input_limits(page: Any, *, evidence_dir: Path, settle_ms: int = 450) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    test_page = page.context.new_page()
    recorder = _NetworkRecorder()
    recorder.attach(test_page)
    original_text = ""
    editor = None
    try:
        test_page.goto(page.url, wait_until="domcontentloaded", timeout=45_000)
        test_page.wait_for_timeout(1_500)
        editor = test_page.locator('[contenteditable="true"]').first
        if editor.count() < 1:
            raise RuntimeError("Visible contenteditable editor not found.")
        original_text = editor.inner_text()

        initial = _snapshot(test_page)
        limit = initial.get("counter_limit") or 20_000
        limit_source = "observed_counter" if initial.get("counter_limit") else "fallback_20000"
        cases = [0, 1, int(limit), int(limit) + 1]
        observations: list[dict[str, Any]] = []

        network_mark = recorder.mark()
        for length in cases:
            editor.fill("A" * length)
            test_page.wait_for_timeout(max(200, settle_ms))
            snap = _snapshot(test_page)
            observations.append({
                "target_length": length,
                "counter_text": snap.get("counter_text"),
                "counter_current": snap.get("counter_current"),
                "counter_limit": snap.get("counter_limit"),
                "generate_present": snap.get("generate_present"),
                "generate_enabled": snap.get("generate_enabled"),
                "classification": classify_input_state(length, int(limit), bool(snap.get("generate_enabled"))),
                "validation_messages": snap.get("validation_messages") or [],
            })

        test_page.screenshot(path=str(evidence_dir / "d5_over_limit_state.png"), full_page=True)
        recorder.finalize_error_details()
        events = recorder.since(network_mark)
        tts_requests = [e for e in events if _is_tts_request(e)]
        payload = {
            "schema_version": "1.0",
            "mode": "D5_READONLY_INPUT_LIMITS",
            "advertised_limit": int(limit),
            "limit_source": limit_source,
            "observations": observations,
            "tts_request_count": len(tts_requests),
            "network_summary": _network_event_summary(events),
            "network_urls": list(dict.fromkeys(str(e.get("url")) for e in events if e.get("url")))[:24],
            "privacy_note": "Synthetic A-only test payloads are used. The original editor text is kept only in memory for restoration and is never written to evidence.",
            "notes": [
                "No Generate or Download control is clicked in D5 read-only input-limit characterization.",
                "The original editor content is restored before the disposable test tab closes.",
                "A D5 PASS requires zero /api/tts requests during these client-side validation checks.",
            ],
        }
        out = evidence_dir / "d5_input_limits.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return out
    finally:
        if editor is not None:
            try:
                editor.fill(original_text)
                test_page.wait_for_timeout(250)
            except Exception:
                pass
        try:
            test_page.close()
        except Exception:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MAGASIN SaydiVoice D5 read-only input-limit characterization.")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--chromium-executable")
    parser.add_argument("--settle-ms", type=int, default=450)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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

        run_dir = runtime.runs_dir / "d5_limits_latest"
        out = run_d5_input_limits(page, evidence_dir=run_dir, settle_ms=max(200, args.settle_ms))
        payload = json.loads(out.read_text(encoding="utf-8"))
        observations = payload.get("observations") or []
        classifications = {str(item.get("classification")) for item in observations}
        pass_gate = (
            int(payload.get("tts_request_count") or 0) == 0
            and "EMPTY_BLOCKED_UI" in classifications
            and "OVER_LIMIT_BLOCKED_UI" in classifications
            and "ACCEPTED_UI" in classifications
        )
        print(json.dumps({
            "gate": "PASS" if pass_gate else "REVIEW",
            "evidence": str(out),
            "advertised_limit": payload.get("advertised_limit"),
            "tts_request_count": payload.get("tts_request_count"),
            "classifications": sorted(classifications),
        }, ensure_ascii=False, indent=2))
        return 0 if pass_gate else 25
    finally:
        if browser_bundle is not None:
            playwright, context = browser_bundle
            try:
                context.close()
            finally:
                playwright.stop()


if __name__ == "__main__":
    raise SystemExit(main())
