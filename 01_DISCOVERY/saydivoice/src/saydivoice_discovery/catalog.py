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

GENERIC_SURFACE_TEXT = {"xóa", "xoá", "clear", "+", "-", "×"}


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


def _option_items(raw: list[dict[str, Any]], *, exclude_texts: set[str] | None = None) -> list[dict[str, Any]]:
    excluded = {_norm(x) for x in (exclude_texts or set())} | GENERIC_SURFACE_TEXT
    cleaned: list[dict[str, Any]] = []
    for item in raw:
        text = _safe_text(item.get("text"))
        if not text or _norm(text) in excluded:
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


def _display_value(label: str | None, text_hint: str | None) -> str | None:
    label_n = _norm(label)
    hint = _safe_text(text_hint, 240) or ""
    if not hint:
        return None
    remainder = re.sub(re.escape(label or ""), "", hint, count=1, flags=re.IGNORECASE).strip(" :-")
    if label_n == "độ ổn định giọng":
        m = re.search(r"[-+]?\d+(?:[.,]\d+)?", remainder)
        return m.group(0).replace(",", ".") if m else None
    if label_n == "tốc độ đọc":
        m = re.search(r"[-+]?\d+(?:[.,]\d+)?\s*[×x]?", remainder)
        return re.sub(r"\s+", "", m.group(0)).replace(",", ".") if m else None
    if label_n == "biểu cảm":
        return remainder or None
    if label_n == "ngắt nghỉ":
        for state in ("Đang tắt", "Đang bật"):
            if _norm(state) in _norm(remainder):
                return state
    return None


def _setting_record(raw: dict[str, Any]) -> dict[str, Any]:
    label = _safe_text(raw.get("label"))
    current = raw.get("current") or {}
    value = current.get("value")
    if value is not None:
        value = _safe_text(value, 80)
    text_hint = _safe_text(raw.get("text_hint"), 200)
    return {
        "label": label,
        "found": bool(raw.get("found")),
        "control_tag": _safe_text(current.get("tag")),
        "control_role": _safe_text(current.get("role")),
        "control_type": _safe_text(current.get("type")),
        "value": value,
        "display_value": _display_value(label, text_hint),
        "aria_valuenow": _safe_text(current.get("aria_valuenow"), 80),
        "aria_valuemin": _safe_text(current.get("aria_valuemin"), 80),
        "aria_valuemax": _safe_text(current.get("aria_valuemax"), 80),
        "aria_label": _safe_text(current.get("aria_label")),
        "text_hint": text_hint,
        "locator_hints": _dedupe(raw.get("locator_hints") or []),
    }


def build_catalog(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    settings: dict[str, Any] = {}
    for item in raw.get("settings", []):
        key = SETTINGS_KEYS.get(_norm(item.get("label")))
        if key:
            settings[key] = _setting_record(item)

    formats = _option_items(raw.get("format_options", []))
    selected_format = next((item["text"] for item in formats if item.get("aria_selected") == "true"), None)
    output_record = settings.get("output_format") or {
        "label": "Định dạng tệp",
        "found": bool(formats),
        "control_tag": None,
        "control_role": "tablist" if formats else None,
        "control_type": None,
        "value": None,
        "display_value": None,
        "aria_valuenow": None,
        "aria_valuemin": None,
        "aria_valuemax": None,
        "aria_label": None,
        "text_hint": None,
        "locator_hints": [],
    }
    output_record["found"] = bool(formats) or bool(output_record.get("found"))
    output_record["value"] = selected_format
    output_record["display_value"] = selected_format
    output_record["options"] = [item["text"] for item in formats]
    settings["output_format"] = output_record

    voice_options = _option_items(raw.get("voice_options", []), exclude_texts={raw.get("voice_current") or "", "Tự động"})
    language_options = _option_items(raw.get("language_options", []), exclude_texts={raw.get("language_current") or ""})
    pause_options = _option_items(raw.get("pause_options", []), exclude_texts={raw.get("pause_current") or "", "Đang tắt", "Đang bật"})

    warnings = list(raw.get("warnings") or [])
    if bool(raw.get("voice_opened")) and not voice_options:
        warnings.append("Voice selector opened but no meaningful voice options were identified; inspect voice surface evidence.")
    if bool(raw.get("language_opened")) and not language_options:
        warnings.append("Language selector opened but no meaningful language options were identified; inspect language surface evidence.")
    if bool(raw.get("pause_opened")) and not bool(raw.get("pause_closed")):
        warnings.append("Pause settings surface did not restore to its original collapsed state automatically.")

    voice_catalog = {
        "schema_version": "1.1",
        "current_label": _safe_text(raw.get("voice_current")),
        "opened": bool(raw.get("voice_opened")),
        "closed_after_observation": bool(raw.get("voice_closed")),
        "option_count": len(voice_options),
        "options": voice_options,
        "surface_evidence_path": _safe_text(raw.get("voice_evidence_path"), 260),
        "notes": [
            "Voice selector was opened only for observation; no voice was selected.",
            "Generic controls such as Clear/Delete are excluded from voice option counts.",
            "Catalog remains local runtime evidence and is not committed automatically.",
        ],
    }

    settings_catalog = {
        "schema_version": "1.1",
        "language": {
            "current_label": _safe_text(raw.get("language_current")),
            "opened": bool(raw.get("language_opened")),
            "closed_after_observation": bool(raw.get("language_closed")),
            "options": language_options,
            "surface_evidence_path": _safe_text(raw.get("language_evidence_path"), 260),
        },
        "settings": settings,
        "pause": {
            "opened": bool(raw.get("pause_opened")),
            "closed_after_observation": bool(raw.get("pause_closed")),
            "current_label": _safe_text(raw.get("pause_current")),
            "options": pause_options,
            "panel": raw.get("pause_panel") or {},
            "surface_evidence_path": _safe_text(raw.get("pause_evidence_path"), 260),
        },
        "format_options": formats,
        "warnings": list(dict.fromkeys(_safe_text(w, 300) for w in warnings if _safe_text(w, 300))),
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

SURFACE_ITEMS_SCRIPT = r"""
() => {
  const visible = (el) => {
    if (!el) return false;
    const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  };
  const unsafe = (el) => {
    if (!el) return true;
    if (el.matches?.('input[type="text"], input[type="password"], textarea, [contenteditable="true"], [role="textbox"]')) return true;
    return !!el.closest?.('textarea, [contenteditable="true"], [role="textbox"]');
  };
  const textOf = (el) => (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 180);
  const selector = [
    'button','label','input[type="checkbox"]','input[type="radio"]',
    '[role="option"]','[role="menuitem"]','[role="menuitemradio"]','[role="menuitemcheckbox"]',
    '[role="radio"]','[role="switch"]','[role="tab"]','[role="dialog"] button',
    '[data-radix-collection-item]','[tabindex]:not([tabindex="-1"])'
  ].join(',');
  return Array.from(document.querySelectorAll(selector))
    .filter(visible)
    .filter(el => !unsafe(el))
    .map(el => ({
      text: textOf(el),
      role: el.getAttribute('role'),
      tag: el.tagName?.toLowerCase() || null,
      type: el.getAttribute('type'),
      aria_selected: el.getAttribute('aria-selected'),
      aria_checked: el.getAttribute('aria-checked'),
      aria_expanded: el.getAttribute('aria-expanded'),
      disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true'
    }))
    .filter(x => x.text || x.type === 'checkbox' || x.type === 'radio');
}
"""

PAUSE_PANEL_SCRIPT = r"""
() => {
  const norm = (v) => (v || '').replace(/\s+/g, ' ').trim().toLowerCase();
  const textOf = (el) => (el?.innerText || el?.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 180);
  const visible = (el) => {
    if (!el) return false;
    const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  };
  const rows = ['Dấu chấm','Dấu phẩy','Dấu chấm phẩy','Xuống dòng'];
  const all = Array.from(document.querySelectorAll('body *')).filter(visible);
  const rowData = rows.map(label => {
    const labelEl = all.find(el => norm(textOf(el)) === norm(label));
    if (!labelEl) return {label, found:false, text:null};
    let scope = labelEl.parentElement;
    for (let depth=0; depth<4 && scope; depth++, scope=scope.parentElement) {
      const t = textOf(scope);
      if (t.length <= 100 && (t.includes('s') || t.includes('+') || t.includes('-'))) {
        return {label, found:true, text:t};
      }
    }
    return {label, found:true, text:textOf(labelEl.parentElement || labelEl)};
  });
  const checkbox = Array.from(document.querySelectorAll('input[type="checkbox"], [role="checkbox"]')).find(visible);
  const defaultButton = Array.from(document.querySelectorAll('button, [role="button"]'))
    .filter(visible).find(el => norm(textOf(el)) === norm('Đặt mặc định'));
  return {
    automatic_checkbox_present: !!checkbox,
    automatic_checkbox_checked: checkbox ? (checkbox.checked === true || checkbox.getAttribute('aria-checked') === 'true') : null,
    rows: rowData,
    default_button_present: !!defaultButton
  };
}
"""


def _fingerprint(item: dict[str, Any]) -> str:
    return json.dumps(
        {
            "text": _safe_text(item.get("text")),
            "role": _safe_text(item.get("role")),
            "tag": _safe_text(item.get("tag")),
            "type": _safe_text(item.get("type")),
            "aria_selected": _safe_text(item.get("aria_selected")),
            "aria_checked": _safe_text(item.get("aria_checked")),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _surface_delta(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[dict[str, Any]]:
    before_counts: dict[str, int] = {}
    for item in before:
        fp = _fingerprint(item)
        before_counts[fp] = before_counts.get(fp, 0) + 1
    delta: list[dict[str, Any]] = []
    for item in after:
        fp = _fingerprint(item)
        count = before_counts.get(fp, 0)
        if count > 0:
            before_counts[fp] = count - 1
        else:
            delta.append(item)
    return delta


def _surface_snapshot(page: Any) -> list[dict[str, Any]]:
    try:
        return page.evaluate(SURFACE_ITEMS_SCRIPT) or []
    except Exception:
        return []


def _try_restore(page: Any, locator: Any, before: list[dict[str, Any]]) -> bool:
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
    except Exception:
        pass
    remaining = _surface_delta(before, _surface_snapshot(page))
    if not remaining:
        return True
    try:
        locator.first.click(timeout=3_000)
        page.wait_for_timeout(250)
    except Exception:
        return False
    return not _surface_delta(before, _surface_snapshot(page))


def _try_open_surface(
    page: Any,
    *,
    role: str,
    name: str,
    exact: bool = True,
    evidence_path: Path | None = None,
    capture_pause_panel: bool = False,
) -> tuple[bool, bool, list[dict[str, Any]], dict[str, Any]]:
    before = _surface_snapshot(page)
    try:
        locator = page.get_by_role(role, name=name, exact=exact)
        if locator.count() < 1:
            return False, True, [], {}
        locator.first.click(timeout=3_000)
        page.wait_for_timeout(900)
        after = _surface_snapshot(page)
        delta = _surface_delta(before, after)
        if evidence_path is not None:
            page.screenshot(path=str(evidence_path), full_page=True)
        panel = page.evaluate(PAUSE_PANEL_SCRIPT) if capture_pause_panel else {}
        closed = _try_restore(page, locator, before)
        return True, closed, delta, panel or {}
    except Exception:
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return False, False, [], {}


def capture_d2_catalog(page: Any, *, evidence_dir: Path | None = None) -> dict[str, Any]:
    raw = page.evaluate(CATALOG_PAGE_SCRIPT) or {}
    warnings: list[str] = []

    voice_current = None
    language_current = None
    pause_current = None
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
    try:
        pause = page.get_by_role("button", name=re.compile(r"Đang (?:tắt|bật)", re.IGNORECASE))
        if pause.count() > 0:
            pause_current = (pause.first.inner_text() or "").strip()
    except Exception:
        warnings.append("Could not read current pause selector label.")

    if evidence_dir is not None:
        evidence_dir.mkdir(parents=True, exist_ok=True)
    voice_evidence = evidence_dir / "d2_voice_surface.png" if evidence_dir else None
    language_evidence = evidence_dir / "d2_language_surface.png" if evidence_dir else None
    pause_evidence = evidence_dir / "d2_pause_surface.png" if evidence_dir else None

    voice_opened, voice_closed, voice_options, _ = _try_open_surface(
        page, role="button", name="Tự động", evidence_path=voice_evidence
    )
    language_opened, language_closed, language_options, _ = _try_open_surface(
        page, role="button", name="VI", evidence_path=language_evidence
    )
    pause_opened, pause_closed, pause_options, pause_panel = _try_open_surface(
        page,
        role="button",
        name=pause_current or "Đang tắt",
        evidence_path=pause_evidence,
        capture_pause_panel=True,
    )

    if not voice_opened:
        warnings.append("Voice selector did not open in this pass.")
    if not language_opened:
        warnings.append("Language selector did not open in this pass.")
    if not pause_opened:
        warnings.append("Pause selector did not open in this pass.")
    if pause_opened and not pause_closed:
        warnings.append("Pause selector opened but could not be restored to the original collapsed state.")

    raw.update(
        {
            "voice_current": voice_current,
            "language_current": language_current,
            "pause_current": pause_current,
            "voice_opened": voice_opened,
            "voice_closed": voice_closed,
            "language_opened": language_opened,
            "language_closed": language_closed,
            "pause_opened": pause_opened,
            "pause_closed": pause_closed,
            "voice_options": voice_options,
            "language_options": language_options,
            "pause_options": pause_options,
            "pause_panel": pause_panel,
            "voice_evidence_path": str(voice_evidence) if voice_evidence else None,
            "language_evidence_path": str(language_evidence) if language_evidence else None,
            "pause_evidence_path": str(pause_evidence) if pause_evidence else None,
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
