from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import struct
import tempfile
import unittest
import wave

from saydi_audiobook.analysis import RuleBasedAnalysisProvider
from saydi_audiobook.contracts import VoiceRequest, VoiceResult, read_json
from saydi_audiobook.narration import choose_narration_profile, select_representative_passages
from saydi_audiobook.saydivoice import (
    SAYDIVOICE_SUPPORTED_CONTROLS,
    SAYDIVOICE_UNSUPPORTED_SEMANTIC_CONTROLS,
    SaydiVoiceAdapter,
    SaydiVoiceBackendResult,
    SaydiVoiceControls,
)
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


class MockSaydiBackend:
    def __init__(self):
        self.calls = []

    def synthesize(self, request):
        self.calls.append(request)
        payload = b"ID3\x04\x00\x00mock-saydi-audio"
        out = Path(request.output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(payload)
        return SaydiVoiceBackendResult(
            operation_id=request.operation_id,
            sample_id=request.sample_id,
            status="SUCCESS",
            local_audio_path=str(out),
            audio_sha256=sha256(payload).hexdigest(),
            byte_count=len(payload),
            duration_ms=1250,
            provider_reference="sample-ref-001",
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

    def test_saydivoice_contract_exposes_only_field_verified_controls(self):
        self.assertEqual(
            SAYDIVOICE_SUPPORTED_CONTROLS,
            {"voice", "stability_expression_axis", "speed", "pause_enabled", "output_format"},
        )
        self.assertEqual(
            SAYDIVOICE_UNSUPPORTED_SEMANTIC_CONTROLS,
            {"emotion", "mood", "prosody", "pause_timings"},
        )

    def test_saydivoice_adapter_maps_neutral_request_to_backend_contract(self):
        with tempfile.TemporaryDirectory() as td:
            backend = MockSaydiBackend()
            controls = SaydiVoiceControls(
                default_voice="Adam — Giọng hot tiktok",
                stability_ratio=0.40,
                speed_ratio=0.35,
                pause_enabled=True,
                output_format="MP3",
            )
            adapter = SaydiVoiceAdapter(backend, controls=controls)
            output = Path(td) / "sample.mp3"
            request = VoiceRequest(
                operation_id="op-001",
                sample_id="sample-001",
                text="Synthetic public-domain test.",
                narration_fingerprint="a" * 64,
                voice_key="default",
                output_path=str(output),
                output_format="MP3",
            )

            result = adapter.generate(request)

            self.assertEqual(result.status, "SUCCESS")
            self.assertEqual(result.provider, "saydivoice")
            self.assertEqual(result.provider_voice, "Adam — Giọng hot tiktok")
            self.assertEqual(result.provider_reference, "sample-ref-001")
            self.assertEqual(len(backend.calls), 1)
            command = backend.calls[0]
            self.assertEqual(command.voice, "Adam — Giọng hot tiktok")
            self.assertEqual(command.stability_ratio, 0.40)
            self.assertEqual(command.speed_ratio, 0.35)
            self.assertTrue(command.pause_enabled)
            self.assertEqual(command.output_format, "MP3")
            self.assertEqual(command.provider_contract_fingerprint, controls.fingerprint)
            self.assertEqual(command.narration_fingerprint, "a" * 64)

    def test_saydivoice_semantic_style_is_explicitly_unsupported(self):
        with tempfile.TemporaryDirectory() as td:
            backend = MockSaydiBackend()
            adapter = SaydiVoiceAdapter(backend)
            request = VoiceRequest(
                operation_id="op-002",
                sample_id="sample-002",
                text="Synthetic test.",
                narration_fingerprint="b" * 64,
                voice_key="default",
                output_path=str(Path(td) / "sample.mp3"),
                style_key="happy",
                output_format="MP3",
            )
            result = adapter.generate(request)
            self.assertEqual(result.status, "ACTION_REQUIRED")
            self.assertEqual(result.error_class, "unsupported_semantic_style")
            self.assertEqual(backend.calls, [])

    def test_saydivoice_output_contract_fails_safe_before_backend(self):
        with tempfile.TemporaryDirectory() as td:
            backend = MockSaydiBackend()
            adapter = SaydiVoiceAdapter(backend)
            request = VoiceRequest(
                operation_id="op-003",
                sample_id="sample-003",
                text="Synthetic test.",
                narration_fingerprint="c" * 64,
                voice_key="default",
                output_path=str(Path(td) / "sample.wav"),
                output_format="WAV",
            )
            result = adapter.generate(request)
            self.assertEqual(result.status, "ACTION_REQUIRED")
            self.assertEqual(result.error_class, "output_format_contract_mismatch")
            self.assertEqual(backend.calls, [])

    def test_saydivoice_settings_change_fingerprint(self):
        base = SaydiVoiceControls()
        changed = SaydiVoiceControls(speed_ratio=0.65)
        self.assertEqual(len(base.fingerprint), 64)
        self.assertNotEqual(base.fingerprint, changed.fingerprint)

    def test_saydivoice_workflow_uses_provider_settings_in_operation_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_file = root / "book.txt"
            input_file.write_text(sample_text(), encoding="utf-8")
            run_dir = root / "run"
            prepare_run(input_file, run_dir)
            decide_text(run_dir, "approve")

            backend_a = MockSaydiBackend()
            provider_a = SaydiVoiceAdapter(backend_a, controls=SaydiVoiceControls(speed_ratio=0.50))
            first = synthesize_sample(run_dir, provider_a)
            self.assertEqual(first.status, "SUCCESS")
            first_state = read_json(run_dir / "state.json")
            first_operation = first_state["voice_operation_id"]

            backend_b = MockSaydiBackend()
            provider_b = SaydiVoiceAdapter(backend_b, controls=SaydiVoiceControls(speed_ratio=0.65))
            second = synthesize_sample(run_dir, provider_b)
            self.assertEqual(second.status, "SUCCESS")
            second_state = read_json(run_dir / "state.json")
            second_operation = second_state["voice_operation_id"]

            self.assertNotEqual(first_operation, second_operation)
            self.assertEqual(len(backend_a.calls), 1)
            self.assertEqual(len(backend_b.calls), 1)


if __name__ == "__main__":
    unittest.main()
