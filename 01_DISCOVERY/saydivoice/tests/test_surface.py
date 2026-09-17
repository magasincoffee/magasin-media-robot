import json
from pathlib import Path

from saydivoice_discovery.models import InteractiveElement, PageSignals
from saydivoice_discovery.surface import build_surface_map, locator_candidates, write_surface_outputs


def signals():
    return PageSignals(
        url="https://voice.saydi.ai/vi/studio/tts/",
        title="SaydiVoice",
        visible_text="Còn 3 lượt tạo miễn phí Đăng nhập để dùng không giới hạn Độ ổn định giọng Biểu cảm Tốc độ đọc Ngắt nghỉ Định dạng tệp",
        has_contenteditable=True,
        button_texts=("Tạo giọng nói", "Đăng nhập"),
    )


def test_surface_map_recognizes_field_controls(tmp_path: Path):
    elements = [
        InteractiveElement(index=0, tag="div", contenteditable=True),
        InteractiveElement(index=1, tag="button", text="Tự động"),
        InteractiveElement(index=2, tag="button", text="Tạo giọng nói"),
        InteractiveElement(index=3, tag="button", text="Cài đặt"),
        InteractiveElement(index=4, tag="button", role="tab", text="MP3", aria_selected="true"),
        InteractiveElement(index=5, tag="button", aria_label="Chat với trợ lý"),
    ]
    surface, selectors = build_surface_map(signals(), elements, "ANONYMOUS")
    keys = {c["semantic_key"] for c in surface["controls"]}
    assert {"script_editor", "voice_selector", "generate_button", "settings_tab", "format_mp3", "assistant_chat"} <= keys
    assert surface["observations"]["free_quota_message_visible"] is True
    assert set(surface["observations"]["settings_labels_seen"]) >= {"biểu cảm", "tốc độ đọc"}
    assert selectors["selectors"]["generate_button"][0]["strategy"] == "role_name"


def test_contenteditable_locator_never_uses_editor_text():
    element = InteractiveElement(index=1, tag="div", text=None, contenteditable=True)
    candidates = locator_candidates(element)
    encoded = json.dumps(candidates, ensure_ascii=False)
    assert "contenteditable" in encoded


def test_surface_outputs_written(tmp_path: Path):
    elements = [InteractiveElement(index=0, tag="button", text="Tạo giọng nói")]
    map_path, selectors_path = write_surface_outputs(tmp_path, signals(), elements, "ANONYMOUS")
    assert map_path.exists()
    assert selectors_path.exists()


def test_login_explanatory_copy_is_not_misclassified_as_history():
    element = InteractiveElement(index=8, tag="button", text="Đăng nhập Lưu lịch sử & giọng clone")
    surface, _ = build_surface_map(signals(), [element], "ANONYMOUS")
    assert surface["controls"][0]["semantic_key"] == "login"
