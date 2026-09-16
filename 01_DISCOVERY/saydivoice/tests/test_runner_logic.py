import json
from pathlib import Path

from saydivoice_discovery.models import DiscoveryReport
from saydivoice_discovery.runner import status_for_state


def test_status_mapping_is_explicit():
    assert status_for_state("TTS_READY") == "CAPTURED"
    assert status_for_state("LOGIN_REQUIRED") == "LOGIN_REQUIRED"
    assert status_for_state("ACCESS_BLOCKED") == "ACCESS_BLOCKED"
    assert status_for_state("UNKNOWN") == "UNKNOWN"


def test_report_serializes_without_non_json_types(tmp_path: Path):
    report = DiscoveryReport(
        schema_version="1.0",
        runner_version="0.1.0",
        run_id="test",
        started_at="2026-09-17T00:00:00+00:00",
        finished_at="2026-09-17T00:00:01+00:00",
        target_url="https://voice.saydi.ai/vi/studio/tts/",
        final_url="https://voice.saydi.ai/vi/studio/tts/",
        page_title="SaydiVoice",
        page_state="UNKNOWN",
        run_status="UNKNOWN",
        screenshot_path=None,
        dom_inventory_path=None,
        element_count=0,
    )
    encoded = json.dumps(report.to_dict(), ensure_ascii=False)
    assert '"runner_version": "0.1.0"' in encoded


def test_runner_orchestrates_capture_and_cleanup(monkeypatch, tmp_path: Path):
    from saydivoice_discovery import runner
    from saydivoice_discovery.models import DiscoveryConfig
    from saydivoice_discovery.runtime import build_runtime_paths

    class FakePage:
        def screenshot(self, path: str, full_page: bool = False):
            Path(path).write_bytes(b"fake-png")

    class FakeContext:
        closed = False

        def close(self):
            self.closed = True

    class FakePlaywright:
        stopped = False

        def stop(self):
            self.stopped = True

    context = FakeContext()
    playwright = FakePlaywright()
    raw_probe = {
        "url": "https://voice.saydi.ai/vi/studio/tts/?session=secret",
        "title": "SaydiVoice",
        "visible_text": "TTS Studio Tạo giọng",
        "has_password_input": False,
        "has_textarea": True,
        "has_contenteditable": False,
        "button_texts": ["Tạo giọng"],
        "link_texts": ["Đăng nhập"],
        "elements": [{"tag": "textarea", "placeholder": "Nhập nội dung", "text": "private script"}],
    }

    monkeypatch.setattr(runner, "open_and_probe", lambda cfg, paths: (raw_probe, (playwright, context), FakePage()))
    paths = build_runtime_paths(tmp_path)
    report = runner.run_discovery(DiscoveryConfig(), paths)

    assert report.run_status == "CAPTURED"
    assert report.final_url == "https://voice.saydi.ai/vi/studio/tts/"
    assert Path(report.screenshot_path).exists()
    assert Path(report.dom_inventory_path).exists()
    assert "private script" not in Path(report.dom_inventory_path).read_text(encoding="utf-8")
    assert context.closed is True
    assert playwright.stopped is True
