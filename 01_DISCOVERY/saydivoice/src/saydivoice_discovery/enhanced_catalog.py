from __future__ import annotations

import re
from typing import Any

LEAF_TEXT_SCRIPT = r"""
() => {
  const visible = (el) => {
    if (!el) return false;
    const s = getComputedStyle(el); const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  };
  const unsafe = (el) => {
    if (!el) return true;
    if (el.matches?.('input, textarea, [contenteditable="true"], [role="textbox"]')) return true;
    if (el.closest?.('textarea, [contenteditable="true"], [role="textbox"]')) return true;
    return false;
  };
  const textOf = (el) => (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
  return Array.from(document.querySelectorAll('body *'))
    .filter(visible)
    .filter(el => !unsafe(el))
    .filter(el => el.childElementCount === 0)
    .map(el => ({
      text: textOf(el).slice(0, 140),
      tag: el.tagName?.toLowerCase() || null,
      role: el.getAttribute('role'),
      aria_selected: el.getAttribute('aria-selected'),
      aria_checked: el.getAttribute('aria-checked'),
      disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true'
    }))
    .filter(x => x.text);
}
"""

_GENERIC = {
    "xóa", "xoá", "clear", "+", "-", "−", "×", "chọn giọng",
    "khám phá", "đã chọn", "giọng của tôi", "yêu thích",
    "tất cả ngôn ngữ", "tất cả giới tính", "tất cả mục đích",
}


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _fingerprint(item: dict[str, Any]) -> tuple[str, str | None, str | None]:
    return (_norm(item.get("text")), item.get("tag"), item.get("role"))


def visible_delta(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str | None, str | None], int] = {}
    for item in before:
        fp = _fingerprint(item)
        counts[fp] = counts.get(fp, 0) + 1
    out: list[dict[str, Any]] = []
    for item in after:
        fp = _fingerprint(item)
        if counts.get(fp, 0):
            counts[fp] -= 1
        else:
            out.append(item)
    return out


def extract_language_options(delta: list[dict[str, Any]], current_label: str | None = None) -> list[dict[str, Any]]:
    current = _norm(current_label)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in delta:
        text = re.sub(r"\s+", " ", str(item.get("text") or "")).strip()
        key = _norm(text)
        if not text or key == current or key in _GENERIC or len(text) > 40:
            continue
        if re.fullmatch(r"\d+\s+giọng", key):
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "text": text,
            "role": item.get("role") or "language_option",
            "aria_selected": item.get("aria_selected"),
            "aria_checked": item.get("aria_checked"),
            "disabled": bool(item.get("disabled", False)),
        })
    return out


def extract_voice_options(delta: list[dict[str, Any]], current_label: str | None = None) -> list[dict[str, Any]]:
    texts = [re.sub(r"\s+", " ", str(item.get("text") or "")).strip() for item in delta]
    current = (current_label or "").strip()
    current_key = _norm(current)
    descriptor = next((t for t in texts if "hệ thống tự chọn giọng" in _norm(t)), None)
    if current and descriptor and any(_norm(t) == current_key for t in texts):
        return [{
            "text": f"{current} — {descriptor}",
            "role": "voice_card",
            "aria_selected": None,
            "aria_checked": None,
            "disabled": False,
        }]

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in delta:
        text = re.sub(r"\s+", " ", str(item.get("text") or "")).strip()
        key = _norm(text)
        if not text or key in _GENERIC or re.fullmatch(r"\d+\s+giọng", key):
            continue
        if "nhập để tìm kiếm" in key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "text": text,
            "role": item.get("role") or "voice_surface_item",
            "aria_selected": item.get("aria_selected"),
            "aria_checked": item.get("aria_checked"),
            "disabled": bool(item.get("disabled", False)),
        })
    return out


def _snapshot(page: Any) -> list[dict[str, Any]]:
    try:
        return page.evaluate(LEAF_TEXT_SCRIPT) or []
    except Exception:
        return []


def _open_capture_close(page: Any, *, name: str) -> tuple[bool, list[dict[str, Any]]]:
    before = _snapshot(page)
    try:
        locator = page.get_by_role("button", name=name, exact=True)
        if locator.count() < 1:
            return False, []
        locator.first.click(timeout=3_000)
        page.wait_for_timeout(700)
        delta = visible_delta(before, _snapshot(page))
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        return True, delta
    except Exception:
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return False, []


def capture_d2_enhancements(page: Any, *, voice_current: str | None, language_current: str | None) -> dict[str, Any]:
    """Second-pass capture for provider custom surfaces that expose no stable option roles.

    It reads visible leaf labels only, excludes editable/input content, never changes a selection,
    and closes each opened surface with Escape.
    """
    updates: dict[str, Any] = {}
    warnings: list[str] = []

    voice_opened, voice_delta = _open_capture_close(page, name=voice_current or "Tự động")
    if voice_opened:
        voice_options = extract_voice_options(voice_delta, voice_current)
        if voice_options:
            updates["voice_options"] = voice_options
        else:
            warnings.append("Enhanced voice surface capture found no semantic voice card labels.")

    language_opened, language_delta = _open_capture_close(page, name=language_current or "VI")
    if language_opened:
        language_options = extract_language_options(language_delta, language_current)
        if language_options:
            updates["language_options"] = language_options
        else:
            warnings.append("Enhanced language surface capture found no visible language labels.")

    if warnings:
        updates["enhancement_warnings"] = warnings
    return updates
