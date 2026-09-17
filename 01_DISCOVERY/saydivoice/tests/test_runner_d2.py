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


def _bundle():
    class FakePage:
        def screenshot(self, path: str, full_page: bool = False):
            Path(path).write_bytes(b"fake-png")
    class FakeContext:
        def close(self): pass
    class FakePlaywright:
        def stop(self): pass
    return FakePage(), (FakePlaywright(), FakeContext())


def _raw_catalog():
    return {
        "settings": [],
        "format_options": [{"text": "MP3", "role": "tab", "aria_selected": "true"}],
        "voice_current": "Tự động", "voice_opened": True, "voice_closed": True,
        "voice_options": [{"text": "Voice A", "role": "option"}],
        "language_current": "VI", "language_opened": True, "language_closed": True,
        "language_options": [{"text": "Tiếng Việt", "role": "option"}],
        "pause_current": "Đang tắt", "pause_opened": True, "pause_closed": True,
        "pause_options": [], "pause_panel": {}, "warnings": [],
    }


def test_runner_writes_d2_catalog_paths_when_catalog_capture_succeeds(monkeypatch, tmp_path: Path):
    from saydivoice_discovery import runner
    page, bundle = _bundle()
    monkeypatch.setattr(runner, "open_and_probe", lambda cfg, paths: (_ready_probe(), bundle, page))
    monkeypatch.setattr(runner, "capture_d2_catalog", lambda page, evidence_dir=None: _raw_catalog())
    monkeypatch.setattr(runner, "capture_d2_enhancements", lambda page, voice_current=None, language_current=None: {})

    report = runner.run_discovery(DiscoveryConfig(), build_runtime_paths(tmp_path))

    assert report.run_status == "CAPTURED"
    assert report.runner_version == "0.4.0"
    assert report.voice_catalog_path is not None
    assert report.settings_catalog_path is not None
    assert report.generation_lifecycle_path is None


def test_runner_invokes_d3_only_when_explicitly_allowed(monkeypatch, tmp_path: Path):
    from saydivoice_discovery import runner
    page, bundle = _bundle()
    monkeypatch.setattr(runner, "open_and_probe", lambda cfg, paths: (_ready_probe(), bundle, page))
    monkeypatch.setattr(runner, "capture_d2_catalog", lambda page, evidence_dir=None: _raw_catalog())
    monkeypatch.setattr(runner, "capture_d2_enhancements", lambda page, voice_current=None, language_current=None: {})
    calls = []
    def fake_generation(page, evidence_dir, timeout_ms, poll_ms):
        calls.append((timeout_ms, poll_ms))
        out = evidence_dir / "generation_lifecycle.json"
        out.write_text("{}", encoding="utf-8")
        return out
    monkeypatch.setattr(runner, "run_generation_lifecycle", fake_generation)

    report = runner.run_discovery(DiscoveryConfig(allow_generate=True), build_runtime_paths(tmp_path))
    assert calls == [(60_000, 500)]
    assert report.generation_lifecycle_path is not None


def test_runner_overrides_weak_options_with_enhanced_surface_results(monkeypatch, tmp_path: Path):
    from saydivoice_discovery import runner
    page, bundle = _bundle()
    raw = _raw_catalog()
    raw["voice_options"] = [{"text": "Khám phá", "role": "tab"}]
    raw["language_options"] = []
    enhanced = {
        "voice_options": [{"text": "Tự động — Hệ thống tự chọn giọng", "role": "voice_card"}],
        "language_options": [{"text": "Tiếng Việt", "role": "language_option"}],
    }
    monkeypatch.setattr(runner, "open_and_probe", lambda cfg, paths: (_ready_probe(), bundle, page))
    monkeypatch.setattr(runner, "capture_d2_catalog", lambda page, evidence_dir=None: raw)
    monkeypatch.setattr(runner, "capture_d2_enhancements", lambda page, voice_current=None, language_current=None: enhanced)

    report = runner.run_discovery(DiscoveryConfig(), build_runtime_paths(tmp_path))
    voice = Path(report.voice_catalog_path).read_text(encoding="utf-8")
    settings = Path(report.settings_catalog_path).read_text(encoding="utf-8")
    assert "Hệ thống tự chọn giọng" in voice
    assert "Tiếng Việt" in settings


def test_runner_keeps_d1_capture_when_d2_catalog_probe_fails(monkeypatch, tmp_path: Path):
    from saydivoice_discovery import runner
    page, bundle = _bundle()
    monkeypatch.setattr(runner, "open_and_probe", lambda cfg, paths: (_ready_probe(), bundle, page))
    monkeypatch.setattr(runner, "capture_d2_catalog", lambda page, evidence_dir=None: (_ for _ in ()).throw(RuntimeError("provider changed")))

    report = runner.run_discovery(DiscoveryConfig(), build_runtime_paths(tmp_path))

    assert report.run_status == "CAPTURED"
    assert report.surface_map_path is not None
    assert report.voice_catalog_path is None
    assert report.settings_catalog_path is None
    assert any("D2 catalog capture was incomplete" in note for note in report.notes)
