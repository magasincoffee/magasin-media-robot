import json
from pathlib import Path

from saydivoice_discovery.catalog import build_catalog, write_catalog_outputs


def raw_fixture():
    return {
        "settings": [
            {
                "label": "Độ ổn định giọng",
                "found": True,
                "text_hint": "Độ ổn định giọng 2.8",
                "current": {
                    "tag": "input",
                    "role": "slider",
                    "type": "range",
                    "value": "2.8",
                    "aria_valuenow": "2.8",
                    "aria_valuemin": "0",
                    "aria_valuemax": "5",
                },
                "locator_hints": [{"strategy": "role", "role": "slider"}],
            },
            {
                "label": "Biểu cảm",
                "found": True,
                "text_hint": "Biểu cảm Ổn định",
                "current": {},
            },
            {
                "label": "Tốc độ đọc",
                "found": True,
                "text_hint": "Tốc độ đọc 1.00×",
                "current": {
                    "tag": "div",
                    "role": "slider",
                    "type": None,
                    "value": None,
                    "aria_valuenow": "1",
                    "aria_valuemin": "0.5",
                    "aria_valuemax": "2",
                },
                "locator_hints": [{"strategy": "role", "role": "slider"}],
            },
            {
                "label": "Định dạng tệp",
                "found": True,
                "text_hint": "Định dạng tệp WAV MP3 FLAC OGG",
                "current": {"tag": "button", "type": "button", "value": None},
            },
        ],
        "format_options": [
            {"text": "WAV", "role": "tab", "aria_selected": "false"},
            {"text": "MP3", "role": "tab", "aria_selected": "true"},
            {"text": "FLAC", "role": "tab", "aria_selected": "false"},
            {"text": "OGG", "role": "tab", "aria_selected": "false"},
        ],
        "voice_current": "Tự động",
        "voice_opened": True,
        "voice_closed": True,
        "voice_options": [
            {"text": "Giọng A", "role": "option", "aria_selected": "false"},
            {"text": "Giọng B", "role": "option", "aria_selected": "false"},
        ],
        "language_current": "VI",
        "language_opened": True,
        "language_closed": True,
        "language_options": [{"text": "Tiếng Việt", "role": "option", "aria_selected": "true"}],
        "pause_current": "Đang tắt",
        "pause_opened": True,
        "pause_closed": True,
        "pause_options": [],
        "pause_panel": {
            "automatic_checkbox_present": True,
            "automatic_checkbox_checked": False,
            "rows": [
                {"label": "Dấu chấm", "found": True, "text": "Dấu chấm 0.45s"},
                {"label": "Dấu phẩy", "found": True, "text": "Dấu phẩy 0.25s"},
            ],
            "default_button_present": True,
        },
        "warnings": [],
    }


def test_build_catalog_records_slider_values_and_ranges():
    _, settings = build_catalog(raw_fixture())
    stability = settings["settings"]["stability"]
    speed = settings["settings"]["speed"]
    assert stability["value"] == "2.8"
    assert stability["display_value"] == "2.8"
    assert stability["aria_valuemin"] == "0"
    assert stability["aria_valuemax"] == "5"
    assert speed["aria_valuenow"] == "1"
    assert speed["display_value"] == "1.00×"
    assert settings["settings"]["expression"]["display_value"] == "Ổn định"


def test_build_catalog_records_selected_output_format_even_when_nearby_button_was_probed():
    _, settings = build_catalog(raw_fixture())
    output = settings["settings"]["output_format"]
    assert output["value"] == "MP3"
    assert output["display_value"] == "MP3"
    assert output["options"] == ["WAV", "MP3", "FLAC", "OGG"]


def test_voice_catalog_is_observation_only():
    voice, _ = build_catalog(raw_fixture())
    assert voice["opened"] is True
    assert voice["closed_after_observation"] is True
    assert voice["option_count"] == 2
    assert [x["text"] for x in voice["options"]] == ["Giọng A", "Giọng B"]
    assert any("no voice was selected" in note for note in voice["notes"])


def test_catalog_deduplicates_overlay_options():
    raw = raw_fixture()
    raw["voice_options"].append(dict(raw["voice_options"][0]))
    voice, _ = build_catalog(raw)
    assert voice["option_count"] == 2


def test_generic_clear_control_is_not_counted_as_voice_option():
    raw = raw_fixture()
    raw["voice_options"] = [{"text": "Xoá", "role": None}]
    voice, settings = build_catalog(raw)
    assert voice["option_count"] == 0
    assert any("no meaningful voice options" in warning for warning in settings["warnings"])


def test_pause_panel_structure_is_preserved_without_changing_settings():
    _, settings = build_catalog(raw_fixture())
    pause = settings["pause"]
    assert pause["opened"] is True
    assert pause["closed_after_observation"] is True
    assert pause["current_label"] == "Đang tắt"
    assert pause["panel"]["automatic_checkbox_checked"] is False
    assert pause["panel"]["rows"][0]["text"] == "Dấu chấm 0.45s"


def test_unrestored_pause_surface_emits_warning():
    raw = raw_fixture()
    raw["pause_closed"] = False
    _, settings = build_catalog(raw)
    assert any("did not restore" in warning for warning in settings["warnings"])


def test_catalog_does_not_copy_unrelated_script_field():
    raw = raw_fixture()
    raw["script_editor_value"] = "SECRET SCRIPT MUST NOT APPEAR"
    voice, settings = build_catalog(raw)
    encoded = json.dumps({"voice": voice, "settings": settings}, ensure_ascii=False)
    assert "SECRET SCRIPT MUST NOT APPEAR" not in encoded


def test_unknown_setting_label_is_not_promoted():
    raw = raw_fixture()
    raw["settings"].append({"label": "Unknown experimental thing", "found": True, "current": {"value": "x"}})
    _, settings = build_catalog(raw)
    assert "unknown experimental thing" not in settings["settings"]


def test_catalog_outputs_written(tmp_path: Path):
    voice_path, settings_path = write_catalog_outputs(tmp_path, raw_fixture())
    assert voice_path.name == "voice_catalog.json"
    assert settings_path.name == "settings_catalog.json"
    assert json.loads(voice_path.read_text(encoding="utf-8"))["option_count"] == 2
    assert json.loads(settings_path.read_text(encoding="utf-8"))["settings"]["output_format"]["value"] == "MP3"
