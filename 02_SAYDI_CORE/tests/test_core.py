from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import struct
import tempfile
import unittest
import wave

from saydi_audiobook.analysis import RuleBasedAnalysisProvider
from saydi_audiobook.contracts import VoiceResult, read_json
from saydi_audiobook.narration import choose_narration_profile, select_representative_passages
from saydi_audiobook.text_layers import build_text_layers
from saydi_audiobook.voice import VoiceProvider
from saydi_audiobook.workflow import decide_audio, decide_text, prepare_run, synthesize_sample


class WaveFixtureVoiceProvider(VoiceProvider):
    provider_name = "test-wave"

    def __init__(self):
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        out = Path(request.output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            frames = [int(1000 * ((i % 20) / 20.0 - 0.5)) for i in range(800)]
            w.writeframes(b"".join(struct.pack("<h", x) for x in frames))
        data = out.read_bytes()
        return VoiceResult(
            operation_id=request.operation_id,
            sample_id=request.sample_id,
            status="SUCCESS",
            provider=self.provider_name,
            local_audio_path=str(out),
            audio_sha256=sha256(data).hexdigest(),
            byte_count=len(data),
            duration_ms=100,
        )


def sample_text():
    return """CHIẾN LƯỢC KINH DOANH

Khách hàng không mua sản phẩm; họ mua kết quả mà sản phẩm tạo ra.

Một doanh nghiệp tốt phải hiểu thị trường, doanh thu và lợi nhuận trước khi mở rộng. Năm 2026, mục tiêu tăng trưởng là 15%.

Hãy bắt đầu từ câu hỏi: khách hàng thực sự cần điều gì?"""


class CoreTests(unittest.TestCase):
    def test_text_layers_preserve_original_and_create_spoken(self):
        raw = "Xin chào   thế giới"
        layers = build_text_layers(raw)
        self.assertEqual(layers.original_text, raw)
        self.assertEqual(layers.normalized_text, "Xin chào thế giới")
        self.assertEqual(layers.spoken_text, "Xin chào thế giới.")

    def test_rules_classify_business_and_profile(self):
        layers = build_text_layers(sample_text())
        book = RuleBasedAnalysisProvider().analyze_book(layers.spoken_text)
        self.assertEqual(book.genre, "BUSINESS")
        profile = choose_narration_profile(book)
        self.assertEqual(profile.key, "BUSINESS_CLEAR")
        self.assertEqual(len(profile.fingerprint), 64)

    def test_representative_samples_exist(self):
        samples = select_representative_passages(
            build_text_layers(sample_text()).spoken_text,
            limit=3,
        )
        self.assertTrue(1 <= len(samples) <= 3)
        self.assertTrue(all(s.text for s in samples))

    def test_vertical_slice_state_and_idempotent_voice_operation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_file = root / "book.txt"
            input_file.write_text(sample_text(), encoding="utf-8")
            run_dir = root / "run"

            state = prepare_run(input_file, run_dir, RuleBasedAnalysisProvider())
            self.assertEqual(state["status"], "TEXT_REVIEW_REQUIRED")
            state = decide_text(run_dir, "approve")
            self.assertEqual(state["status"], "TEXT_APPROVED")

            provider = WaveFixtureVoiceProvider()
            first = synthesize_sample(run_dir, provider)
            self.assertEqual(first.status, "SUCCESS")
            self.assertEqual(provider.calls, 1)

            second = synthesize_sample(run_dir, provider)
            self.assertEqual(second.status, "SUCCESS")
            self.assertEqual(
                provider.calls,
                1,
                "successful operation must be reused rather than regenerated",
            )

            state = decide_audio(run_dir, "approve")
            self.assertEqual(state["status"], "SAMPLE_APPROVED")
            self.assertEqual(
                read_json(run_dir / "voice_result.json")["audio_sha256"],
                first.audio_sha256,
            )

    def test_reject_text_blocks_synthesis(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_file = root / "book.txt"
            input_file.write_text(sample_text(), encoding="utf-8")
            run_dir = root / "run"

            prepare_run(input_file, run_dir)
            decide_text(run_dir, "reject")
            provider = WaveFixtureVoiceProvider()
            with self.assertRaisesRegex(RuntimeError, "text must be approved"):
                synthesize_sample(run_dir, provider)


if __name__ == "__main__":
    unittest.main()
