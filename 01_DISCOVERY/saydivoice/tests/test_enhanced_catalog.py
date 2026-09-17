from saydivoice_discovery.enhanced_catalog import (
    extract_language_options,
    extract_voice_options,
    visible_delta,
)


def item(text, tag="div", role=None):
    return {"text": text, "tag": tag, "role": role, "aria_selected": None, "aria_checked": None, "disabled": False}


def test_visible_delta_keeps_only_new_leaf_items():
    before = [item("VI", "button"), item("Cài đặt")]
    after = before + [item("English"), item("Tiếng Việt")]
    assert [x["text"] for x in visible_delta(before, after)] == ["English", "Tiếng Việt"]


def test_language_options_capture_provider_visible_labels():
    delta = [
        item("English"), item("Tiếng Việt"), item("中文"), item("日本語"), item("한국어"),
        item("Deutsch"), item("Español"), item("Français"),
    ]
    options = extract_language_options(delta, "VI")
    assert [x["text"] for x in options] == [
        "English", "Tiếng Việt", "中文", "日本語", "한국어", "Deutsch", "Español", "Français"
    ]


def test_voice_options_ignore_tabs_and_build_current_auto_card():
    delta = [
        item("Chọn giọng"), item("Khám phá", role="tab"), item("Đã chọn", role="tab"),
        item("Giọng của tôi", role="tab"), item("Yêu thích", role="tab"), item("1 giọng"),
        item("Tự động"), item("Hệ thống tự chọn giọng"), item("Xoá", "button"),
    ]
    options = extract_voice_options(delta, "Tự động")
    assert options == [{
        "text": "Tự động — Hệ thống tự chọn giọng",
        "role": "voice_card",
        "aria_selected": None,
        "aria_checked": None,
        "disabled": False,
    }]


def test_voice_fallback_does_not_promote_modal_navigation_as_voice_options():
    delta = [item("Khám phá"), item("Đã chọn"), item("Yêu thích"), item("Xoá")]
    assert extract_voice_options(delta, "Tự động") == []
