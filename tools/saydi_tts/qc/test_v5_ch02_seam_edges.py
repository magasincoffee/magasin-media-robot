"""Isolated QC-02 seam endpoint tests; no model loading or audio modifications."""
import array
import math
import tempfile
import unittest
import wave
from pathlib import Path
from v5_ch02_seam_edges import pcm16_edge

class SeamEdgeTests(unittest.TestCase):
    def pcm(self,path,amplitudes):
        b=array.array("h",amplitudes)
        with wave.open(str(path),"wb") as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(48000)
            f.writeframes(b.tobytes())

    def test_zero_faded_endpoints(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/"faded.wav"
            self.pcm(f,[int(6000*math.sin(i/10)) for i in range(1300)]+[0]*1152)
            result=pcm16_edge(f,tail=True)
            self.assertAlmostEqual(result["last_sample"],0,places=6)
            self.assertEqual(result["peak"],0)

    def test_unfaded_endpoint_detectable_but_not_audio_verdict(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/"unfaded.wav"
            self.pcm(f,[12000]*1250)
            result=pcm16_edge(f,tail=True)
            self.assertGreater(result["last_sample"],0.3)
            self.assertGreater(result["rms"],0.3)
            self.assertEqual(result["sample_rate"],48000)

if __name__=="__main__":
    unittest.main(verbosity=2)
