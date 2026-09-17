from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import AuthState, InteractiveElement, PageSignals

FORMAT_LABELS = {"wav", "mp3", "flac", "ogg"}


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _name_for(element: InteractiveElement) -> str:
    return element.aria_label or element.text or element.placeholder or element.name or ""


def _role_for(element: InteractiveElement) -> str | None:
    if element.role:
        return element.role
    return {"button": "button", "a": "link", "textarea": "textbox", "input": "textbox", "select": "combobox"}.get(element.tag)


def locator_candidates(element: InteractiveElement) -> list[dict[str, Any]]:
    """Rank stable locator candidates. No candidate includes editor/user values."""
    candidates: list[dict[str, Any]] = []
    role = _role_for(element)
    name = _name_for(element)

    if element.test_id:
        candidates.append({"priority": 10, "strategy": "test_id", "value": element.test_id})

    if role and name:
        candidates.append({"priority": 20, "strategy": "role_name", "role": role, "name": name, "exact": True})

    if element.aria_label:
        candidates.append({"priority": 30, "strategy": "aria_label", "value": element.aria_label})

    if element.placeholder and element.tag in {"input", "textarea"}:
        candidates.append({"priority": 40, "strategy": "placeholder", "value": element.placeholder})

    if element.contenteditable:
        candidates.append({"priority": 70, "strategy": "css", "value": '[contenteditable="true"]'})

    if role == "slider" or element.aria_valuenow is not None:
        candidates.append({"priority": 75, "strategy": "role", "role": "slider"})

    if element.text and element.tag in {"button", "a"}:
        candidates.append({"priority": 80, "strategy": "text", "value": element.text, "exact": True})

    candidates.sort(key=lambda item: item["priority"])
    return candidates


def semantic_key(element: InteractiveElement) -> str | None:
    name = _norm(_name_for(element))

    if element.contenteditable or element.role == "textbox":
        return "script_editor"

    if element.role == "tab" and name in FORMAT_LABELS:
        return f"format_{name}"

    if element.role == "slider" or element.aria_valuenow is not None:
        return "slider_unresolved"

    # Authentication controls can contain explanatory copy, so detect them before
    # generic words such as "lịch sử".
    if name.startswith("đăng nhập") or name in {"login", "sign in"}:
        return "login"

    exact = {
        "vi": "language_selector",
        "tự động": "voice_selector",
        "tạo giọng nói": "generate_button",
        "tạo giọng": "generate_button",
        "generate": "generate_button",
        "cài đặt": "settings_tab",
        "lịch sử": "history_tab",
        "đang tắt": "pause_selector",
        "thêm người nói": "add_speaker",
        "nhập kịch bản": "import_script",
        "phụ đề thành giọng nói": "subtitle_to_voice",
        "chat với trợ lý": "assistant_chat",
    }
    return exact.get(name)


def build_surface_map(
    signals: PageSignals,
    elements: list[InteractiveElement],
    auth_state: AuthState,
) -> tuple[dict[str, Any], dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    selector_map: dict[str, list[dict[str, Any]]] = {}
    unresolved_sliders: list[int] = []

    for element in elements:
        key = semantic_key(element)
        if not key:
            continue

        control = {
            "semantic_key": key,
            "element_index": element.index,
            "tag": element.tag,
            "role": _role_for(element),
            "display_name": _name_for(element) or None,
            "disabled": element.disabled,
            "aria_selected": element.aria_selected,
            "aria_checked": element.aria_checked,
            "aria_valuenow": element.aria_valuenow,
            "aria_valuemin": element.aria_valuemin,
            "aria_valuemax": element.aria_valuemax,
        }
        controls.append(control)
        selector_map.setdefault(key, []).extend(locator_candidates(element))
        if key == "slider_unresolved":
            unresolved_sliders.append(element.index)

    for key, candidates in selector_map.items():
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for candidate in sorted(candidates, key=lambda item: item["priority"]):
            fingerprint = json.dumps(candidate, ensure_ascii=False, sort_keys=True)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            unique.append(candidate)
        selector_map[key] = unique

    text = _norm(signals.visible_text)
    observations = {
        "anonymous_login_controls_visible": auth_state == "ANONYMOUS",
        "free_quota_message_visible": "lượt tạo miễn phí" in text,
        "settings_labels_seen": [
            label for label in ("độ ổn định giọng", "biểu cảm", "tốc độ đọc", "ngắt nghỉ", "định dạng tệp")
            if label in text
        ],
    }

    surface_map = {
        "schema_version": "1.0",
        "page_url": signals.url,
        "page_title": signals.title,
        "auth_state": auth_state,
        "controls": controls,
        "observations": observations,
        "unresolved": {
            "slider_element_indexes": unresolved_sliders,
            "note": "D1 records semantic controls from accessible/interactive evidence. Visual labels without a stable interactive node remain unresolved until the next live pass.",
        },
    }
    selectors = {
        "schema_version": "1.0",
        "policy": [
            "Prefer test_id when provider exposes a stable data-test attribute.",
            "Then prefer role + accessible name.",
            "Then aria-label / placeholder.",
            "Use CSS/text fallbacks only when semantic locators are unavailable.",
            "Never derive selectors from user script/editor values.",
        ],
        "selectors": selector_map,
    }
    return surface_map, selectors


def write_surface_outputs(
    run_dir: Path,
    signals: PageSignals,
    elements: list[InteractiveElement],
    auth_state: AuthState,
) -> tuple[Path, Path]:
    surface_map, selectors = build_surface_map(signals, elements, auth_state)
    map_path = run_dir / "saydi_map.json"
    selectors_path = run_dir / "selectors.json"
    map_path.write_text(json.dumps(surface_map, ensure_ascii=False, indent=2), encoding="utf-8")
    selectors_path.write_text(json.dumps(selectors, ensure_ascii=False, indent=2), encoding="utf-8")
    return map_path, selectors_path
