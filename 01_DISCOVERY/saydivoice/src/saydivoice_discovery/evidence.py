from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .models import InteractiveElement, PageSignals
from .runtime import sanitize_text, sanitize_url

MAX_VISIBLE_TEXT = 4_000
MAX_ELEMENTS = 300


def make_page_signals(raw: dict[str, Any]) -> PageSignals:
    return PageSignals(
        url=sanitize_url(str(raw.get("url", ""))),
        title=sanitize_text(str(raw.get("title", "")), 300) or "",
        visible_text=sanitize_text(str(raw.get("visible_text", "")), MAX_VISIBLE_TEXT) or "",
        has_password_input=bool(raw.get("has_password_input", False)),
        has_textarea=bool(raw.get("has_textarea", False)),
        has_contenteditable=bool(raw.get("has_contenteditable", False)),
        button_texts=tuple(sanitize_text(str(x), 160) or "" for x in raw.get("button_texts", [])[:80]),
        link_texts=tuple(sanitize_text(str(x), 160) or "" for x in raw.get("link_texts", [])[:80]),
    )


def sanitize_inventory(raw_elements: Iterable[dict[str, Any]]) -> list[InteractiveElement]:
    clean: list[InteractiveElement] = []
    for index, item in enumerate(raw_elements):
        if index >= MAX_ELEMENTS:
            break
        input_type = sanitize_text(item.get("type"), 40)
        tag = sanitize_text(item.get("tag"), 40) or "unknown"
        role = sanitize_text(item.get("role"), 80)
        is_editor = tag in {"input", "textarea", "select"} or role == "textbox"
        safe_text = None if is_editor else sanitize_text(item.get("text"), 180)
        clean.append(
            InteractiveElement(
                index=index,
                tag=tag,
                role=role,
                name=sanitize_text(item.get("name"), 160),
                text=safe_text,
                input_type=input_type,
                placeholder=sanitize_text(item.get("placeholder"), 160),
                aria_label=sanitize_text(item.get("aria_label"), 160),
                test_id=sanitize_text(item.get("test_id"), 120),
            )
        )
    return clean


def write_dom_inventory(path: Path, elements: list[InteractiveElement]) -> None:
    payload = {
        "schema_version": "1.0",
        "privacy_note": "No input values, cookies, localStorage, sessionStorage, authorization headers, or raw HTML are captured.",
        "elements": [element.__dict__ for element in elements],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
