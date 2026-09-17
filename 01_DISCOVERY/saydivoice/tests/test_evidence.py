import json
from pathlib import Path

from saydivoice_discovery.evidence import make_page_signals, sanitize_inventory, write_dom_inventory


def test_inventory_does_not_persist_input_value(tmp_path: Path):
    raw = [
        {
            "tag": "input",
            "type": "text",
            "placeholder": "Email",
            "value": "private@example.com",
            "text": "private@example.com",
            "aria_label": "Email",
        }
    ]
    inventory = sanitize_inventory(raw)
    output = tmp_path / "dom.json"
    write_dom_inventory(output, inventory)
    content = output.read_text(encoding="utf-8")
    assert "private@example.com" not in content
    parsed = json.loads(content)
    assert parsed["elements"][0]["placeholder"] == "Email"


def test_contenteditable_text_is_always_suppressed(tmp_path: Path):
    raw = [
        {
            "tag": "div",
            "contenteditable": True,
            "text": "Nội dung riêng tư trong kịch bản",
            "aria_label": None,
        }
    ]
    inventory = sanitize_inventory(raw)
    assert inventory[0].contenteditable is True
    assert inventory[0].text is None
    output = tmp_path / "dom.json"
    write_dom_inventory(output, inventory)
    assert "Nội dung riêng tư" not in output.read_text(encoding="utf-8")


def test_page_signals_url_is_sanitized():
    signals = make_page_signals(
        {
            "url": "https://voice.saydi.ai/vi/studio/tts/?code=secret",
            "title": "Saydi",
            "visible_text": "Tạo giọng",
            "button_texts": [],
            "link_texts": [],
        }
    )
    assert signals.url == "https://voice.saydi.ai/vi/studio/tts/"
