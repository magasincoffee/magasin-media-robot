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
