from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SETTINGS_KEYS = {
    "độ ổn định giọng": "stability",
    "biểu cảm": "expression",
    "tốc độ đọc": "speed",
    "ngắt nghỉ": "pause",
    "định dạng tệp": "output_format",
}


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _safe_text(value: Any, limit: int = 160) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text[:limit] or None


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        fingerprint = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        out.append(item)
    return out


def _option_items(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in raw:
        text = _safe_text(item.get("text"))
        if not text:
            continue
        cleaned.append(
            {
                "text": text,
                "role": _safe_text(item.get("role")),
                "aria_selected": _safe_text(item.get("aria_selected")),
                "aria_checked": _safe_text(item.get("aria_checked")),
                "disabled": bool(item.get("disabled", False)),
            }
        )
    return _dedupe(cleaned)


def _setting_record(raw: dict[str, Any]) -> dict[str, Any]:
    label = _safe_text(raw.get("label"))
    current = raw.get("current") or {}
    value = current.get("value")
    if value is not None:
        value = _safe_text(value, 80)
    return {
        "label": label,
        "found": bool(raw.get("found")),
        "control_tag": _safe_text(current.get("tag")),
        "control_role": _safe_text(current.get("role")),
        "control_type": _safe_text(current.get("type")),
        "value": value,
        "aria_valuenow": _safe_text(current.get("aria_valuenow"), 80),
        "aria_valuemin": _safe_text(current.get("aria_valuemin"), 80),
        "aria_valuemax": _safe_text(current.get("aria_valuemax"), 80),
        "aria_label": _safe_text(current.get("aria_label")),
        "text_hint": _safe_text(raw.get("text_hint"), 200),
        "locator_hints": _dedupe(raw.get("locator_hints") or []),
    }


def build_catalog(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build privacy-safe D2 voice/settings catalogs from a raw browser observation."""
    settings: dict[str, Any] = {}
    for item in raw.get("settings", []):
        key = SETTINGS_KEYS.get(_norm(item.get("label")))
        if key:
            settings[key] = _setting_record(item)

    formats = _option_items(raw.get("format_options", []))
    selected_format = next((item["text"] for item in formats if item.get("aria_selected") == "true"), None)
    settings.setdefault(
        "output_format",
        {
            "label": "Định dạng tệp",
            "found": bool(formats),
            "control_tag": None,
            "control_role": "tablist" if formats else None,
            "control_type": None,
            "value": selected_format,
            "aria_valuenow": None,
            "aria_valuemin": None,
            "aria_valuemax": None,
            "aria_label": None,
            "text_hint": None,
            "locator_hints": [],
        },
    )
    settings["output_format"]["options"] = [item["text"] for item in formats]

    voice_options = _option_items(raw.get("voice_options", []))
    language_options = _option_items(raw.get("language_options", []))
    pause_options = _option_items(raw.get("pause_options", []))

    voice_catalog = {
        "schema_version": "1.0",
        "current_label": _safe_text(raw.get("voice_current")),
        "opened": bool(raw.get("voice_opened")),
        "option_count": len(voice_options),
        "options": voice_options,
        "notes": [
            "Voice selector was opened only for observation; no voice was selected.",
            "Catalog remains local runtime evidence and is not committed automatically.",
        ],
    }

    settings_catalog = {
        "schema_version": "1.0",
        "language": {
            "current_label": _safe_text(raw.get("language_current")),
            "opened": bool(raw.get("language_opened")),
            "options": language_options,
        },
        "settings": settings,
        "pause_options": pause_options,
        "format_options": formats,
        "warnings": list(raw.get("warnings") or []),
        "privacy_note": "No script/editor values, credentials, cookies, storage, or authorization data are included.",
    }
    return voice_catalog, settings_catalog


CATALOG_PAGE_SCRIPT = r"""
() => {
  const norm = (v) => (v || '').replace(/\s+/g, ' ').trim().toLowerCase();
  const textOf = (el) => (el?.innerText || el?.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 220);
  const visible = (el) => {
    if (!el) return false;
    const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  };
  const labels = ['Độ ổn định giọng','Biểu cảm','Tốc độ đọc','Ngắt nghỉ','Định dạng tệp'];
  const all = Array.from(document.querySelectorAll('body *')).filter(visible);
  const findLabel = (label) => all.find(el => norm(textOf(el)) === norm(label));
  const candidateSelector = [
    'input[type="range"]','input[type="number"]','[role="slider"]','[aria-valuenow]',
    'select','[role="combobox"]','button','[role="button"]','[role="tab"]'
  ].join(',');
  const recordControl = (el) => {
    if (!el) return {};
    const type = el.getAttribute('type');
    let value = null;
    if (type === 'range' || type === 'number') value = el.value;
    return {
      tag: el.tagName?.toLowerCase() || null,
      role: el.getAttribute('role'),
      type,
      value,
      aria_valuenow: el.getAttribute('aria-valuenow'),
      aria_valuemin: el.getAttribute('aria-valuemin'),
      aria_valuemax: el.getAttribute('aria-valuemax'),
      aria_label: el.getAttribute('aria-label'),
    };
  };
  const locatorHints = (el) => {
    if (!el) return [];
    const out = [];
    const testId = el.getAttribute('data-testid') || el.getAttribute('data-test') || el.getAttribute('data-qa');
    if (testId) out.push({strategy:'test_id', value:testId});
    if (el.getAttribute('aria-label')) out.push({strategy:'aria_label', value:el.getAttribute('aria-label')});
    const role = el.getAttribute('role');
    if (role) out.push({strategy:'role', role});
    if (el.tagName?.toLowerCase() === 'input' && el.getAttribute('type')) out.push({strategy:'css', value:`input[type="${el.getAttribute('type')}"]`});
    return out;
  };
  const settings = labels.map(label => {
    const labelEl = findLabel(label);
    if (!labelEl) return {label, found:false};
    let scope = labelEl.parentElement;
    let control = null;
    for (let depth=0; depth<5 && scope; depth++, scope=scope.parentElement) {
      const candidates = Array.from(scope.querySelectorAll(candidateSelector)).filter(visible);
      control = candidates.find(el => el !== labelEl && !['WAV','MP3','FLAC','OGG'].includes(textOf(el))) || null;
      if (control) break;
    }
    return {
      label,
      found:true,
      text_hint: textOf(labelEl.parentElement || labelEl),
      current: recordControl(control),
      locator_hints: locatorHints(control),
    };
  });
  const formatOptions = Array.from(document.querySelectorAll('[role="tab"], button'))
    .filter(visible)
    .filter(el => ['WAV','MP3','FLAC','OGG'].includes(textOf(el)))
    .map(el => ({text:textOf(el), role:el.getAttribute('role'), aria_selected:el.getAttribute('aria-selected'), aria_checked:el.getAttribute('aria-checked'), disabled:el.disabled === true}));
  return {settings, format_options: formatOptions};
}
"""

OVERLAY_OPTIONS_SCRIPT = r"""
() => {
  const visible = (el) => {
    const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  };
  const textOf = (el) => (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 180);
  const selector = '[role="option"],[role="menuitem"],[role="menuitemradio"],[role="menuitemcheckbox"],[role="radio"],[role="listbox"] button,[data-radix-collection-item]';
  return Array.from(document.querySelectorAll(selector)).filter(visible).map(el => ({
    text: textOf(el),
    role: el.getAttribute('role'),
    aria_selected: el.getAttribute('aria-selected'),
    aria_checked: el.getAttribute('aria-checked'),
    disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true'
  })).filter(x => x.text);
}
"""


def _try_open_options(page: Any, *, role: str, name: str, exact: bool = True) -> tuple[bool, list[dict[str, Any]]]:
    try:
        locator = page.get_by_role(role, name=name, exact=exact)
        if locator.count() < 1:
            return False, []
        locator.first.click(timeout=3_000)
        page.wait_for_timeout(400)
        options = page.evaluate(OVERLAY_OPTIONS_SCRIPT)
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        return True, options or []
    except Exception:
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return False, []


def capture_d2_catalog(page: Any) -> dict[str, Any]:
    raw = page.evaluate(CATALOG_PAGE_SCRIPT) or {}
    warnings: list[str] = []

    voice_current = None
    language_current = None
    try:
        voice = page.get_by_role("button", name="Tự động", exact=True)
        if voice.count() > 0:
            voice_current = (voice.first.inner_text() or "").strip()
    except Exception:
        warnings.append("Could not read current voice selector label.")
    try:
        lang = page.get_by_role("button", name="VI", exact=True)
        if lang.count() > 0:
            language_current = (lang.first.inner_text() or "").strip()
    except Exception:
        warnings.append("Could not read current language selector label.")

    voice_opened, voice_options = _try_open_options(page, role="button", name="Tự động")
    language_opened, language_options = _try_open_options(page, role="button", name="VI")
    pause_opened, pause_options = _try_open_options(page, role="button", name="Đang tắt")

    if not voice_opened:
        warnings.append("Voice selector did not expose observable overlay options in this pass.")
    if not language_opened:
        warnings.append("Language selector did not expose observable overlay options in this pass.")
    if not pause_opened:
        warnings.append("Pause selector did not expose observable overlay options in this pass.")

    raw.update(
        {
            "voice_current": voice_current,
            "language_current": language_current,
            "voice_opened": voice_opened,
            "language_opened": language_opened,
            "pause_opened": pause_opened,
            "voice_options": voice_options,
            "language_options": language_options,
            "pause_options": pause_options,
            "warnings": warnings,
        }
    )
    return raw


def write_catalog_outputs(run_dir: Path, raw: dict[str, Any]) -> tuple[Path, Path]:
    voice_catalog, settings_catalog = build_catalog(raw)
    voice_path = run_dir / "voice_catalog.json"
    settings_path = run_dir / "settings_catalog.json"
    voice_path.write_text(json.dumps(voice_catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    settings_path.write_text(json.dumps(settings_catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return voice_path, settings_path
