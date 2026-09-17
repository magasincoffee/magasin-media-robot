from __future__ import annotations

from saydivoice_discovery.voice_controls import clean, parse_pause_values


def test_clean_collapses_whitespace() -> None:
    assert clean("  A\n  B   C ") == "A B C"


def test_parse_pause_values_from_observed_ui_text() -> None:
    text = (
        "Ngắt nghỉ Tự động chèn ngắt nghỉ theo dấu câu Đang tắt "
        "Dấu chấm • − 0.45s + Dấu phẩy , − 0.25s + "
        "Dấu chấm phẩy ; − 0.3s + Xuống dòng ¶ − 0.6s + Đặt mặc định"
    )
    assert parse_pause_values(text) == {
        "dot_seconds": 0.45,
        "comma_seconds": 0.25,
        "semicolon_seconds": 0.30,
        "newline_seconds": 0.60,
    }
