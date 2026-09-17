import pytest

from saydivoice_discovery.catalog import (
    SAFE_TRIGGERS,
    build_settings_catalog,
    build_voice_catalog,
    capture_trigger_surface,
    diff_controls,
    sanitize_control_snapshot,
    sanitize_settings_context,
)


def test_catalog_sanitizer_redacts_email_and_editor_values():
    raw = [
        {"index": 0, "tag": "input", "type": "text", "text": "private@example.com", "value": "secret"},
        {"index": 1, "tag": "button", "text": "Voice private@example.com"},
    ]
    clean = sanitize_control_snapshot(raw)
    assert clean[0]["text"] is None
    assert clean[0]["value"] is None
    assert clean[1]["text"] == "Voice [REDACTED_EMAIL]"


def test_range_value_is_allowed_as_setting_not_editor_value():
    clean = sanitize_control_snapshot([
        {"index": 0, "tag": "input", "type": "range", "value": "1.25", "aria_valuemin": "0.5", "aria_valuemax": "2"}
    ])
    assert clean[0]["value"] == "1.25"


def test_diff_controls_returns_only_added_controls():
    before = sanitize_control_snapshot([{"index": 0, "tag": "button", "text": "Tự động"}])
    after = sanitize_control_snapshot([
        {"index": 0, "tag": "button", "text": "Tự động"},
        {"index": 1, "tag": "button", "text": "Giọng A"},
    ])
    diff = diff_controls(before, after)
    assert [x["text"] for x in diff] == ["Giọng A"]


def test_voice_catalog_deduplicates_labels():
    capture = {
        "status": "CAPTURED",
        "trigger": "Tự động",
        "new_controls": [
            {"text": "Giọng A", "role": "button", "tag": "button"},
            {"text": "Giọng A", "role": "button", "tag": "button"},
            {"text": "Giọng B", "role": "option", "tag": "div"},
        ],
    }
    catalog = build_voice_catalog(capture)
    assert [o["label"] for o in catalog["options"]] == ["Giọng A", "Giọng B"]


def test_settings_context_sanitizes_text():
    raw = {
        "Tốc độ đọc": {
            "found": True,
            "text": "Tốc độ đọc private@example.com 1.00×",
            "descendants": [{"index": 0, "tag": "input", "type": "range", "value": "1.00"}],
        }
    }
    clean = sanitize_settings_context(raw)
    assert "private@example.com" not in clean["Tốc độ đọc"]["text"]
    assert clean["Tốc độ đọc"]["descendants"][0]["value"] == "1.00"


def test_settings_catalog_keeps_language_and_pause_surface():
    settings = {"Ngắt nghỉ": {"found": True, "text": "Ngắt nghỉ", "descendants": []}}
    language = {"status": "CAPTURED", "trigger": "VI", "new_controls": [{"text": "English"}]}
    pause = {"status": "CAPTURED", "trigger": "Đang tắt", "new_controls": [{"text": "Bật"}]}
    out = build_settings_catalog(settings, language, pause)
    assert out["language_surface"]["trigger"] == "VI"
    assert out["pause_surface"]["trigger"] == "Đang tắt"


def test_unsafe_trigger_is_rejected_before_page_interaction():
    with pytest.raises(ValueError):
        capture_trigger_surface(object(), "generate")


def test_safe_trigger_whitelist_never_contains_generate_or_delete():
    flat = {x.casefold() for names in SAFE_TRIGGERS.values() for x in names}
    assert "tạo giọng nói" not in flat
    assert "xoá tất cả" not in flat
