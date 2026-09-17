from pathlib import Path

from saydivoice_discovery.models import DiscoveryConfig
from saydivoice_discovery.runtime import build_runtime_paths


def _ready_probe():
    return {
        "url": "https://voice.saydi.ai/vi/studio/tts/",
        "title": "SaydiVoice",
        "visible_text": "TTS Studio Tạo giọng Độ ổn định giọng Biểu cảm Tốc độ đọc",
        "has_password_input": False,
        "has_textarea": False,
        "has_contenteditable": True,
        "button_texts": ["Tạo giọng nói", "Tự động", "VI"],
        "link_texts": [],
        "elements": [
            {"tag": "div", "contenteditable": True, "text": "must be suppressed"},
            {"tag": "button", "text": "Tự động"},
            {"tag": "button", "text": "Tạo giọng nói"},
        ],
    }


def test_runner_writes_d2_catalog_paths_when_catalog_capture_succeeds(monkeypatch, tmp_path: Path):
    from saydivoice_discovery import runner

    class FakePage:
        def screenshot(self, path: str, full_page: bool = False):
            Path(path).write_bytes(b"fake-png")

    class FakeContext:
        def close(self): pass

    class FakePlaywright:
        def stop(self): pass

    fake_raw_catalog = {
        "settings": [],
        "format_options": [{"text": "MP3", "role": "tab", "aria_selected": "true"}],
        "voice_current": "Tự động",
        "voice_opened": True,
        "voice_options": [{"text": "Voice A", "role": "option"}],
        "language_current": "VI",
        "language_opened": True,
        "language_options": [{"text": "VI", "role": "option"}],
        "pause_options": [],
        "warnings": [],
    }

    monkeypatch.setattr(runner, "open_and_probe", lambda cfg, paths: (_ready_probe(), (FakePlaywright(), FakeContext()), FakePage()))
    monkeypatch.setattr(runner, "capture_d2_catalog", lambda page: fake_raw_catalog)

    report = runner.run_discovery(DiscoveryConfig(), build_runtime_paths(tmp_path))

    assert report.run_status == "CAPTURED"
    assert report.runner_version == "0.3.0"
    assert report.voice_catalog_path is not None
    assert report.settings_catalog_path is not None
    assert Path(report.voice_catalog_path).exists()
    assert Path(report.settings_catalog_path).exists()


def test_runner_keeps_d1_capture_when_d2_catalog_probe_fails(monkeypatch, tmp_path: Path):
    from saydivoice_discovery import runner

    class FakePage:
        def screenshot(self, path: str, full_page: bool = False):
            Path(path).write_bytes(b"fake-png")

    class FakeContext:
        def close(self): pass

    class FakePlaywright:
        def stop(self): pass

    monkeypatch.setattr(runner, "open_and_probe", lambda cfg, paths: (_ready_probe(), (FakePlaywright(), FakeContext()), FakePage()))
    monkeypatch.setattr(runner, "capture_d2_catalog", lambda page: (_ for _ in ()).throw(RuntimeError("provider changed")))

    report = runner.run_discovery(DiscoveryConfig(), build_runtime_paths(tmp_path))

    assert report.run_status == "CAPTURED"
    assert report.surface_map_path is not None
    assert report.voice_catalog_path is None
    assert report.settings_catalog_path is None
    assert any("D2 catalog capture was incomplete" in note for note in report.notes)
