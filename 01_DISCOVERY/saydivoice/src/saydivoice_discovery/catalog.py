from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runtime import sanitize_text

# D2 is intentionally non-destructive. Only these read-only/open-menu targets may be clicked.
SAFE_TRIGGERS: dict[str, tuple[str, ...]] = {
    "voice": ("Tự động",),
    "language": ("VI",),
    "pause": ("Đang tắt",),
    "settings": ("Cài đặt",),
}

VISIBLE_CONTROL_PROBE = r"""
() => {
  const norm = (v) => (v || '').replace(/\s+/g, ' ').trim();
  const isVisible = (el) => {
    const s = window.getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
  };
  const inEditor = (el) => !!el.closest('[contenteditable="true"], textarea, input[type="text"], input[type="email"], input[type="password"]');
  const selector = [
    'button','a','select','input[type="range"]','input[type="radio"]','input[type="checkbox"]',
    '[role="button"]','[role="option"]','[role="menuitem"]','[role="menuitemradio"]',
    '[role="radio"]','[role="checkbox"]','[role="tab"]','[role="slider"]','[role="combobox"]',
    '[aria-valuenow]','[tabindex="0"]'
  ].join(',');
  const nodes = Array.from(document.querySelectorAll(selector)).filter(isVisible).filter(el => !inEditor(el)).slice(0, 500);
  return nodes.map((el, index) => {
    const tag = el.tagName.toLowerCase();
    const type = el.getAttribute('type');
    const allowValue = type === 'range';
    return {
      index,
      tag,
      role: el.getAttribute('role'),
      text: norm(el.innerText || el.textContent || '').slice(0, 240),
      aria_label: el.getAttribute('aria-label'),
      aria_selected: el.getAttribute('aria-selected'),
      aria_checked: el.getAttribute('aria-checked'),
      aria_valuenow: el.getAttribute('aria-valuenow'),
      aria_valuemin: el.getAttribute('aria-valuemin'),
      aria_valuemax: el.getAttribute('aria-valuemax'),
      type,
      value: allowValue ? el.value : null,
      test_id: el.getAttribute('data-testid') || el.getAttribute('data-test') || el.getAttribute('data-qa'),
      class_name: typeof el.className === 'string' ? el.className.slice(0, 240) : null,
      style: (el.getAttribute('style') || '').slice(0, 240),
      disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true'
    };
  });
}
"""

SETTINGS_CONTEXT_PROBE = r"""
() => {
  const labels = ['Độ ổn định giọng', 'Biểu cảm', 'Tốc độ đọc', 'Ngắt nghỉ', 'Định dạng tệp'];
  const norm = (v) => (v || '').replace(/\s+/g, ' ').trim();
  const isVisible = (el) => {
    const s = window.getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
  };
  const all = Array.from(document.querySelectorAll('body *')).filter(isVisible);
  const findExact = (label) => all
    .filter(el => norm(el.innerText || el.textContent || '') === label)
    .sort((a,b) => (a.getBoundingClientRect().width * a.getBoundingClientRect().height) - (b.getBoundingClientRect().width * b.getBoundingClientRect().height))[0];

  const output = {};
  for (const label of labels) {
    const anchor = findExact(label);
    if (!anchor) {
      output[label] = {found: false};
      continue;
    }
    let cluster = anchor.parentElement;
    let depth = 0;
    while (cluster && depth < 4) {
      const txt = norm(cluster.innerText || cluster.textContent || '');
      if (txt.length >= label.length && txt.length <= 500 && !cluster.querySelector('[contenteditable="true"],textarea,input[type="text"],input[type="email"],input[type="password"]')) break;
      cluster = cluster.parentElement;
      depth += 1;
    }
    cluster = cluster || anchor.parentElement || anchor;
    const descendants = Array.from(cluster.querySelectorAll('*')).filter(isVisible).slice(0, 60).map((el, index) => {
      const type = el.getAttribute('type');
      const role = el.getAttribute('role');
      const allowValue = type === 'range';
      const interesting = type === 'range' || role || el.hasAttribute('aria-valuenow') || el.hasAttribute('tabindex') || el.tagName.toLowerCase() === 'button';
      if (!interesting) return null;
      return {
        index,
        tag: el.tagName.toLowerCase(),
        role,
        text: norm(el.innerText || el.textContent || '').slice(0, 180),
        aria_label: el.getAttribute('aria-label'),
        aria_valuenow: el.getAttribute('aria-valuenow'),
        aria_valuemin: el.getAttribute('aria-valuemin'),
        aria_valuemax: el.getAttribute('aria-valuemax'),
        type,
        value: allowValue ? el.value : null,
        tabindex: el.getAttribute('tabindex'),
        class_name: typeof el.className === 'string' ? el.className.slice(0, 240) : null,
        style: (el.getAttribute('style') || '').slice(0, 240)
      };
    }).filter(Boolean);
    output[label] = {
      found: true,
      text: norm(cluster.innerText || cluster.textContent || '').slice(0, 420),
      descendants
    };
  }
  return output;
}
"""


def _clean_value(value: Any, limit: int = 240) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return sanitize_text(str(value), limit)


def sanitize_control_snapshot(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean: list[dict[str, Any]] = []
    for item in raw[:500]:
        tag = str(item.get("tag") or "").lower()
        role = str(item.get("role") or "").lower()
        type_ = str(item.get("type") or "").lower()
        is_editor = tag in {"textarea"} or role == "textbox" or type_ in {"text", "email", "password"}
        clean.append({
            "index": int(item.get("index", len(clean))),
            "tag": _clean_value(item.get("tag"), 40),
            "role": _clean_value(item.get("role"), 80),
            "text": None if is_editor else _clean_value(item.get("text"), 240),
            "aria_label": _clean_value(item.get("aria_label"), 180),
            "aria_selected": _clean_value(item.get("aria_selected"), 16),
            "aria_checked": _clean_value(item.get("aria_checked"), 16),
            "aria_valuenow": _clean_value(item.get("aria_valuenow"), 60),
            "aria_valuemin": _clean_value(item.get("aria_valuemin"), 60),
            "aria_valuemax": _clean_value(item.get("aria_valuemax"), 60),
            "type": _clean_value(item.get("type"), 40),
            "value": _clean_value(item.get("value"), 80) if type_ == "range" else None,
            "test_id": _clean_value(item.get("test_id"), 120),
            "class_name": _clean_value(item.get("class_name"), 240),
            "style": _clean_value(item.get("style"), 240),
            "disabled": bool(item.get("disabled", False)),
        })
    return clean


def _fingerprint(item: dict[str, Any]) -> str:
    keys = ("tag", "role", "text", "aria_label", "aria_selected", "aria_checked", "aria_valuenow", "type", "test_id", "class_name")
    return json.dumps({k: item.get(k) for k in keys}, ensure_ascii=False, sort_keys=True)


def diff_controls(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[dict[str, Any]]:
    before_set = {_fingerprint(item) for item in before}
    return [item for item in after if _fingerprint(item) not in before_set]


def sanitize_settings_context(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for label, item in raw.items():
        safe_label = sanitize_text(str(label), 120) or "unknown"
        if not isinstance(item, dict):
            continue
        descendants = sanitize_control_snapshot(item.get("descendants", []))
        out[safe_label] = {
            "found": bool(item.get("found", False)),
            "text": sanitize_text(item.get("text"), 420) if item.get("text") else None,
            "descendants": descendants,
        }
    return out


def _safe_click_exact_button(page: Any, names: tuple[str, ...]) -> str | None:
    for name in names:
        try:
            locator = page.get_by_role("button", name=name, exact=True)
            if locator.count() > 0 and locator.first.is_visible():
                locator.first.click()
                return name
        except Exception:
            continue
    return None


def capture_trigger_surface(page: Any, kind: str, settle_ms: int = 600) -> dict[str, Any]:
    if kind not in SAFE_TRIGGERS:
        raise ValueError(f"Unsafe catalog trigger: {kind}")

    before = sanitize_control_snapshot(page.evaluate(VISIBLE_CONTROL_PROBE))
    clicked_name = _safe_click_exact_button(page, SAFE_TRIGGERS[kind])
    if clicked_name is None:
        return {"kind": kind, "status": "TRIGGER_NOT_FOUND", "trigger": None, "new_controls": [], "visible_controls_after": []}

    page.wait_for_timeout(max(100, settle_ms))
    after = sanitize_control_snapshot(page.evaluate(VISIBLE_CONTROL_PROBE))
    added = diff_controls(before, after)

    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
    except Exception:
        pass

    return {"kind": kind, "status": "CAPTURED", "trigger": clicked_name, "new_controls": added, "visible_controls_after": after}


def build_voice_catalog(capture: dict[str, Any]) -> dict[str, Any]:
    options: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in capture.get("new_controls", []):
        text = sanitize_text(item.get("text"), 240) or sanitize_text(item.get("aria_label"), 240)
        if not text:
            continue
        fp = text.casefold()
        if fp in seen:
            continue
        seen.add(fp)
        options.append({
            "label": text,
            "role": item.get("role"),
            "tag": item.get("tag"),
            "aria_selected": item.get("aria_selected"),
            "aria_checked": item.get("aria_checked"),
            "test_id": item.get("test_id"),
        })
    return {
        "schema_version": "1.0",
        "capture_status": capture.get("status"),
        "trigger": capture.get("trigger"),
        "options": options,
        "raw_new_controls": capture.get("new_controls", []),
        "note": "Options are observational evidence from a read-only menu/dialog open. No voice is selected by D2.",
    }


def build_settings_catalog(settings_context: dict[str, Any], language_capture: dict[str, Any], pause_capture: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "settings": settings_context,
        "language_surface": {"status": language_capture.get("status"), "trigger": language_capture.get("trigger"), "new_controls": language_capture.get("new_controls", [])},
        "pause_surface": {"status": pause_capture.get("status"), "trigger": pause_capture.get("trigger"), "new_controls": pause_capture.get("new_controls", [])},
        "note": "D2 only opens read-only selectors and records visible options/current setting evidence. Generate/download are never invoked.",
    }


def run_catalog_discovery(page: Any, run_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    settings_raw = page.evaluate(SETTINGS_CONTEXT_PROBE)
    settings_context = sanitize_settings_context(settings_raw)

    voice_capture = capture_trigger_surface(page, "voice")
    language_capture = capture_trigger_surface(page, "language")
    pause_capture = capture_trigger_surface(page, "pause")

    voice_catalog = build_voice_catalog(voice_capture)
    settings_catalog = build_settings_catalog(settings_context, language_capture, pause_capture)

    voice_path = run_dir / "voice_catalog.json"
    settings_path = run_dir / "settings_catalog.json"
    voice_path.write_text(json.dumps(voice_catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    settings_path.write_text(json.dumps(settings_catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "voice_capture_status": voice_capture.get("status"),
        "voice_option_count": len(voice_catalog["options"]),
        "language_capture_status": language_capture.get("status"),
        "pause_capture_status": pause_capture.get("status"),
        "settings_labels_found": [label for label, item in settings_context.items() if item.get("found")],
    }
    return voice_path, settings_path, summary
