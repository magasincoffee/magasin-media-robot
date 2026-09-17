from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .browser import open_and_probe
from .classifier import classify_auth_state, classify_page_state
from .evidence import make_page_signals
from .generation import _NetworkRecorder, _network_event_summary
from .models import DiscoveryConfig
from .runtime import build_runtime_paths


GENERIC = {
    "chọn giọng", "khám phá", "đã chọn", "giọng của tôi", "yêu thích",
    "tất cả ngôn ngữ", "tất cả giới tính", "tất cả mục đích", "xóa", "xoá",
    "wav", "mp3", "flac", "ogg", "cài đặt", "lịch sử", "tạo giọng nói",
}

VOICE_BUTTON_CANDIDATES = r"""
() => {
  const visible = (el) => {
    const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  };
  const text = (el) => (el.innerText || el.textContent || '').replace(/\s+/g,' ').trim();
  return Array.from(document.querySelectorAll('button,[role="button"]'))
    .filter(visible)
    .map(el => {
      const r = el.getBoundingClientRect();
      return {text:text(el).slice(0,140), x:r.x, y:r.y, w:r.width, h:r.height};
    })
    .filter(x => x.text);
}
"""

SURFACE_SNAPSHOT = r"""
() => {
  const visible = (el) => {
    if (!el) return false;
    const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  };
  const unsafe = (el) => el.matches?.('input[type="password"],textarea,[contenteditable="true"],[role="textbox"]') || !!el.closest?.('textarea,[contenteditable="true"],[role="textbox"]');
  const text = (el) => (el.innerText || el.textContent || '').replace(/\s+/g,' ').trim();
  const nodes = Array.from(document.querySelectorAll('body *')).filter(visible).filter(el => !unsafe(el));
  const leaf = nodes.filter(el => el.childElementCount === 0).map(el => ({
    text:text(el).slice(0,180),
    tag:el.tagName.toLowerCase(), role:el.getAttribute('role'),
    aria_selected:el.getAttribute('aria-selected'), aria_checked:el.getAttribute('aria-checked'),
    aria_expanded:el.getAttribute('aria-expanded'), aria_label:el.getAttribute('aria-label'),
    disabled:el.disabled === true || el.getAttribute('aria-disabled') === 'true'
  })).filter(x => x.text);
  const controls = Array.from(document.querySelectorAll('button,[role="button"],[role="option"],[role="menuitem"],[role="tab"],input[type="checkbox"],input[type="radio"],input[type="range"],[role="slider"],[aria-valuenow]'))
    .filter(visible).filter(el => !unsafe(el)).map(el => {
      const r=el.getBoundingClientRect();
      return {
        text:text(el).slice(0,180), tag:el.tagName.toLowerCase(), role:el.getAttribute('role'), type:el.getAttribute('type'),
        value:(el.tagName==='INPUT' ? el.value : null), min:el.getAttribute('min'), max:el.getAttribute('max'), step:el.getAttribute('step'),
        aria_valuenow:el.getAttribute('aria-valuenow'), aria_valuemin:el.getAttribute('aria-valuemin'), aria_valuemax:el.getAttribute('aria-valuemax'),
        aria_selected:el.getAttribute('aria-selected'), aria_checked:el.getAttribute('aria-checked'), aria_label:el.getAttribute('aria-label'),
        x:r.x,y:r.y,w:r.width,h:r.height
      };
    });
  const dialogs = Array.from(document.querySelectorAll('[role="dialog"]')).filter(visible).map(el => text(el).slice(0,5000));
  const selects = Array.from(document.querySelectorAll('select')).map(el => ({
    value:el.value,
    aria_label:el.getAttribute('aria-label'),
    name:el.getAttribute('name'),
    options:Array.from(el.options || []).map(o => ({text:(o.textContent||'').replace(/\s+/g,' ').trim(), value:o.value, selected:o.selected, disabled:o.disabled}))
  }));
  return {leaf, controls, dialogs, selects};
}
"""

SCROLL_DIALOG = r"""
() => {
  const visible = (el) => { const s=getComputedStyle(el),r=el.getBoundingClientRect(); return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0; };
  const dialog = Array.from(document.querySelectorAll('[role="dialog"]')).find(visible);
  if (!dialog) return {found:false, scrollers:0};
  const candidates = [dialog, ...dialog.querySelectorAll('*')].filter(visible).filter(el => el.scrollHeight > el.clientHeight + 30);
  for (const el of candidates) el.scrollTop = el.scrollHeight;
  return {found:true, scrollers:candidates.length};
}
"""

SETTINGS_SNAPSHOT = r"""
() => {
  const visible = (el) => { const s=getComputedStyle(el),r=el.getBoundingClientRect(); return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0; };
  const text = (el) => (el?.innerText || el?.textContent || '').replace(/\s+/g,' ').trim();
  const labels = ['Độ ổn định giọng','Biểu cảm','Tốc độ đọc','Ngắt nghỉ','Định dạng tệp'];
  const all = Array.from(document.querySelectorAll('body *')).filter(visible);
  const sliders = Array.from(document.querySelectorAll('input[type="range"],[role="slider"],[aria-valuenow]')).filter(visible).map(el => {
    const r=el.getBoundingClientRect();
    let nearest=null, best=1e9;
    for (const label of labels) {
      const node=all.find(x => text(x)===label); if (!node) continue;
      const lr=node.getBoundingClientRect(); const d=Math.abs(r.y-lr.y); if (d<best && lr.y<=r.y+30) {best=d;nearest=label;}
    }
    return {label_hint:nearest, value:el.value ?? null, min:el.getAttribute('min'), max:el.getAttribute('max'), step:el.getAttribute('step'), aria_valuenow:el.getAttribute('aria-valuenow'), aria_valuemin:el.getAttribute('aria-valuemin'), aria_valuemax:el.getAttribute('aria-valuemax'), aria_label:el.getAttribute('aria-label'), y:r.y};
  });
  const body = (document.body?.innerText || '').replace(/\s+/g,' ').trim();
  const formatButtons = Array.from(document.querySelectorAll('button,[role="tab"]')).filter(visible).map(el => ({text:text(el), selected:el.getAttribute('aria-selected'), checked:el.getAttribute('aria-checked')})).filter(x => ['WAV','MP3','FLAC','OGG'].includes(x.text));
  return {body_excerpt:body.slice(0,5000), sliders, format_buttons:formatButtons};
}
"""


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _dedupe_text(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = (item.get("text"), item.get("tag"), item.get("role"), item.get("aria_selected"), item.get("aria_checked"))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _is_tts_request(event: dict[str, Any]) -> bool:
    if event.get("kind") != "request":
        return False
    try:
        return urlsplit(str(event.get("url") or "")).path == "/api/tts"
    except Exception:
        return False


def _pick_voice_button(page: Any) -> str | None:
    candidates = page.evaluate(VOICE_BUTTON_CANDIDATES) or []
    excluded = {
        "tạo giọng nói", "thêm người nói", "nhập kịch bản", "phụ đề thành giọng nói", "cài ứng dụng",
        "đăng nhập", "đang tắt", "đang bật", "wav", "mp3", "flac", "ogg", "vi", "en",
        "english", "tiếng việt", "中文", "日本語", "한국어",
    }
    plausible = []
    for c in candidates:
        t = str(c.get("text") or "").strip()
        n = _norm(t)
        x = float(c.get("x") or 0)
        y = float(c.get("y") or 9999)
        if not t or n in excluded or len(t) > 100:
            continue
        if not (55 <= y <= 190):
            continue
        if not (180 <= x <= 900):
            continue
        plausible.append(c)
    plausible.sort(key=lambda x: (abs(float(x.get("y") or 9999) - 100), float(x.get("x") or 9999), len(str(x.get("text") or ""))))
    return str(plausible[0].get("text")) if plausible else None


def _filter_options_from_selects(selects: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for item in selects:
        options = list(item.get("options") or [])
        labels = [_norm(str(o.get("text") or "")) for o in options]
        key = None
        if any("tất cả ngôn ngữ" in x for x in labels):
            key = "language"
        elif any("tất cả giới tính" in x for x in labels):
            key = "gender"
        elif any("tất cả mục đích" in x for x in labels):
            key = "purpose"
        if key:
            out[key] = options
    return out


def run_d5a(page: Any, *, evidence_dir: Path) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    test_page = page.context.new_page()
    recorder = _NetworkRecorder()
    recorder.attach(test_page)
    try:
        test_page.goto(page.url, wait_until="domcontentloaded", timeout=45_000)
        test_page.wait_for_timeout(1800)
        network_mark = recorder.mark()

        settings = test_page.evaluate(SETTINGS_SNAPSHOT) or {}
        test_page.screenshot(path=str(evidence_dir / "d5a_settings.png"), full_page=True)

        voice_current = _pick_voice_button(test_page)
        voice_opened = False
        surface_labels: list[dict[str, Any]] = []
        filter_options: dict[str, list[dict[str, Any]]] = {}
        modal_text = None
        scroll_info: dict[str, Any] = {}

        if voice_current:
            loc = test_page.get_by_role("button", name=voice_current, exact=True)
            if loc.count() < 1:
                loc = test_page.locator("button:visible").filter(has_text=voice_current)
            if loc.count() > 0:
                loc.first.click(timeout=4000)
                test_page.wait_for_timeout(800)
                snap1 = test_page.evaluate(SURFACE_SNAPSHOT) or {}
                voice_opened = bool(snap1.get("dialogs")) and any("chọn giọng" in _norm(x) for x in snap1.get("dialogs", []))
                surface_labels.extend(snap1.get("leaf", []))
                modal_text = (snap1.get("dialogs") or [None])[0]
                filter_options.update(_filter_options_from_selects(snap1.get("selects") or []))
                test_page.screenshot(path=str(evidence_dir / "d5a_voice_modal_top.png"), full_page=True)

                if voice_opened:
                    scroll_info = test_page.evaluate(SCROLL_DIALOG) or {}
                    test_page.wait_for_timeout(650)
                    snap2 = test_page.evaluate(SURFACE_SNAPSHOT) or {}
                    surface_labels.extend(snap2.get("leaf", []))
                    for key, value in _filter_options_from_selects(snap2.get("selects") or []).items():
                        filter_options.setdefault(key, value)
                    test_page.screenshot(path=str(evidence_dir / "d5a_voice_modal_bottom.png"), full_page=True)
                test_page.keyboard.press("Escape")
                test_page.wait_for_timeout(250)

        surface_labels = _dedupe_text(surface_labels)
        candidate_labels = []
        for item in surface_labels:
            t = str(item.get("text") or "").strip()
            if not t or _norm(t) in GENERIC or len(t) > 90:
                continue
            if re.fullmatch(r"\d+\s+giọng", _norm(t)):
                continue
            if "nhập để tìm kiếm" in _norm(t):
                continue
            candidate_labels.append(item)

        keyword_texts = []
        corpus = " ".join([str(settings.get("body_excerpt") or ""), str(modal_text or "")] + [str(x.get("text") or "") for x in surface_labels])
        for keyword in ("tâm trạng", "cảm xúc", "emotion", "mood", "tone", "tông", "phong cách", "biểu cảm", "mục đích"):
            if keyword.lower() in corpus.lower():
                keyword_texts.append(keyword)

        recorder.finalize_error_details()
        events = recorder.since(network_mark)
        tts_requests = [e for e in events if _is_tts_request(e)]
        payload = {
            "schema_version": "1.1",
            "mode": "D5A_READONLY_VOICE_STYLE_DISCOVERY",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "voice_current": voice_current,
            "voice_selector_opened": voice_opened,
            "voice_surface_candidate_labels": candidate_labels,
            "voice_surface_candidate_count": len(candidate_labels),
            "filter_options": filter_options,
            "scroll_info": scroll_info,
            "settings": settings,
            "style_keywords_observed": keyword_texts,
            "explicit_emotion_control_confirmed": any(k in keyword_texts for k in ("tâm trạng", "cảm xúc", "emotion", "mood")),
            "tts_request_count": len(tts_requests),
            "network_summary": _network_event_summary(events),
            "privacy_note": "No editor/script values, cookies, authorization headers, request bodies, response bodies, storage, or credentials are persisted.",
            "notes": [
                "D5A is read-only: it opens and scrolls selector/settings surfaces but never selects a voice, changes a setting, clicks Generate, or clicks Download.",
                "Filter option lists are read from existing select DOM without choosing an option.",
                "A PASS requires an authenticated TTS page, a real voice dialog/settings surface, and zero /api/tts requests.",
            ],
        }
        out = evidence_dir / "d5a_voice_style.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return out
    finally:
        try:
            test_page.close()
        except Exception:
            pass


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="MAGASIN SaydiVoice D5A read-only voice/style discovery")
    p.add_argument("--runtime-root", type=Path)
    p.add_argument("--chromium-executable")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runtime = build_runtime_paths(args.runtime_root) if args.runtime_root else build_runtime_paths()
    runtime.create()
    cfg = DiscoveryConfig(headless=False, navigation_timeout_ms=60_000, settle_ms=2500, chromium_executable_path=args.chromium_executable)
    browser_bundle = None
    try:
        raw, browser_bundle, page = open_and_probe(cfg, runtime)
        signals = make_page_signals(raw)
        state = classify_page_state(signals)
        auth = classify_auth_state(signals, state)
        if state != "TTS_READY" or auth != "AUTHENTICATED_OR_HIDDEN":
            print(json.dumps({"gate":"FAIL_SESSION","page_state":state,"auth_state":auth}, ensure_ascii=False))
            return 20
        run_dir = runtime.runs_dir / "d5a_voice_style_latest"
        out = run_d5a(page, evidence_dir=run_dir)
        payload = json.loads(out.read_text(encoding="utf-8"))
        passed = bool(payload.get("voice_selector_opened")) and int(payload.get("tts_request_count") or 0) == 0 and bool((payload.get("settings") or {}).get("sliders") or (payload.get("settings") or {}).get("format_buttons"))
        print(json.dumps({
            "gate":"PASS" if passed else "REVIEW",
            "evidence":str(out),
            "voice_current":payload.get("voice_current"),
            "voice_surface_candidate_count":payload.get("voice_surface_candidate_count"),
            "filter_groups":sorted((payload.get("filter_options") or {}).keys()),
            "style_keywords_observed":payload.get("style_keywords_observed"),
            "explicit_emotion_control_confirmed":payload.get("explicit_emotion_control_confirmed"),
            "tts_request_count":payload.get("tts_request_count"),
        }, ensure_ascii=False, indent=2))
        return 0 if passed else 25
    finally:
        if browser_bundle is not None:
            playwright, context = browser_bundle
            try:
                context.close()
            finally:
                playwright.stop()


if __name__ == "__main__":
    raise SystemExit(main())
