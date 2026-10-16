from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from saydi_audiobook.contracts import VoiceRequest
from saydi_audiobook.voice_vieneu import VieNeuOnnxVoiceProvider

class FakeEngine:
    def __init__(self):
        self.infer_calls = 0
    def infer(self, text, *, voice):
        assert voice == "Candidate-V6"
        self.infer_calls += 1
        return b"fake-audio-payload"
    def save(self, audio, path):
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"\0" * 32000)

class VieNeuProviderSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.out = self.root / "candidates" / "sample.wav"
        self.request = VoiceRequest(
            operation_id="v6candidate-one", sample_id="new-sample-001",
            text="Xin chào. Đây là một đoạn thử.", narration_fingerprint="f" * 64,
            voice_key="Candidate-V6", output_path=str(self.out),
        )
    def tearDown(self):
        self.temp.cleanup()

    def provider(self, **overrides):
        data = dict(v6_output_root=self.root, voice_name="Candidate-V6")
        data.update(overrides)
        return VieNeuOnnxVoiceProvider(**data)

    def test_no_factory_or_admission_never_loads(self):
        factory_calls = []
        p = self.provider(engine_factory=lambda: factory_calls.append(1))
        with patch("saydi_audiobook.voice_vieneu.platform.system", return_value="Windows"), patch(
            "saydi_audiobook.voice_vieneu.socket.gethostname", return_value="DESKTOP-H4A16IL"
        ):
            result = p.generate(self.request)
        self.assertEqual(result.status, "ACTION_REQUIRED")
        self.assertEqual(result.error_class, "SAYDI_LOCAL_START_NOT_INSTALLED")
        self.assertEqual(factory_calls, [])
        self.assertFalse(self.out.exists())

    def test_failed_admission_no_io(self):
        calls = []
        p = self.provider(host_admission=lambda: False,
                          engine_factory=lambda: calls.append(1))
        with patch("saydi_audiobook.voice_vieneu.platform.system", return_value="Windows"), patch(
            "saydi_audiobook.voice_vieneu.socket.gethostname", return_value="DESKTOP-H4A16IL"
        ):
            result = p.generate(self.request)
        self.assertEqual(result.error_class, "SAYDI_RUNTIME_ADMISSION_HOLD")
        self.assertEqual(calls, [])

    def test_wrong_host_fails_closed(self):
        p = self.provider(host_admission=lambda: True, engine_factory=FakeEngine)
        with patch("saydi_audiobook.voice_vieneu.platform.system", return_value="Windows"), patch(
            "saydi_audiobook.voice_vieneu.socket.gethostname", return_value="ANOTHER-PC"
        ):
            result = p.generate(self.request)
        self.assertEqual(result.error_class, "H4_WINDOWS_REQUIRED")
        self.assertFalse(self.out.exists())

    def test_fake_engine_contract_synthetic_only(self):
        p = self.provider(host_admission=lambda: True, engine_factory=FakeEngine)
        with patch("saydi_audiobook.voice_vieneu.platform.system", return_value="Windows"), patch(
            "saydi_audiobook.voice_vieneu.socket.gethostname", return_value="DESKTOP-H4A16IL"
        ):
            result = p.generate(self.request)
        self.assertEqual(result.status, "SUCCESS")
        self.assertTrue(result.audio_sha256)
        self.assertEqual(result.duration_ms, 1000)
        self.assertEqual(result.provider_voice, "Candidate-V6")
        self.assertTrue(self.out.is_file())
        self.assertNotEqual(result.provider, "windows-sapi-prototype")

    def test_no_overwrite(self):
        self.out.parent.mkdir(parents=True)
        self.out.write_bytes(b"keep")
        p = self.provider(host_admission=lambda: True, engine_factory=FakeEngine)
        with patch("saydi_audiobook.voice_vieneu.platform.system", return_value="Windows"), patch(
            "saydi_audiobook.voice_vieneu.socket.gethostname", return_value="DESKTOP-H4A16IL"
        ):
            result = p.generate(self.request)
        self.assertEqual(result.error_class, "NO_OVERWRITE_EXISTING_AUDIO")
        self.assertEqual(self.out.read_bytes(), b"keep")

    def test_untrusted_output_root_denied(self):
        outside = self.root.parent / "never-write.wav"
        r = VoiceRequest(operation_id="x", sample_id="s", text="sample",
                         narration_fingerprint="f"*64, voice_key="Candidate-V6",
                         output_path=str(outside))
        p = self.provider(host_admission=lambda: True, engine_factory=FakeEngine)
        with patch("saydi_audiobook.voice_vieneu.platform.system", return_value="Windows"), patch(
            "saydi_audiobook.voice_vieneu.socket.gethostname", return_value="DESKTOP-H4A16IL"
        ):
            result = p.generate(r)
        self.assertEqual(result.error_class, "V6_ISOLATION_REQUIRED")
        self.assertFalse(outside.exists())

if __name__ == "__main__":
    unittest.main()
