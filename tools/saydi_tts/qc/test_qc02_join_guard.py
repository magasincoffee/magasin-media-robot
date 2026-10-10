"""Contract tests for the SAYDI QC02 opt-in join guard. Does not load TTS."""
import array
import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path

from qc02_join_guard import chunk_edge, inspect_candidate, MARKS

def pcm(path,samples):
    a=array.array("h",samples)
    with wave.open(str(path),"wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(48000)
        f.writeframes(a.tobytes())

class Qc02JoinGuardTests(unittest.TestCase):
    def test_smooth_edges_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/"001.wav";b=Path(tmp)/"002.wav"
            pcm(a,[0]*4800);pcm(b,[0]*4800)
            boundary=(0,0.,.1,a,.610)
            entry=inspect_candidate(0,[boundary,(1,.710,.810,b,.610)],boundary)
            self.assertEqual(entry["technical_flag"],"NO_CONFIRMED_EDGE_POP")
            self.assertTrue(entry["review_required"])

    def test_known_discontinuous_edge_is_flagged_for_review_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/"001.wav";b=Path(tmp)/"002.wav"
            values=[0]*4800;values[-1]=26000
            pcm(a,values);pcm(b,[0]*4800)
            boundary=(0,0.,.1,a,.610)
            entry=inspect_candidate(0,[boundary,(1,.710,.810,b,.610)],boundary)
            self.assertEqual(entry["technical_flag"],"TECHNICAL_EDGE_CANDIDATE")
            self.assertTrue(entry["review_required"])
            self.assertEqual(values[-1],26000)

    def test_canonical_five_marks_stable(self):
        self.assertEqual(MARKS["00:23:34"],1414.0)
        self.assertEqual(len(MARKS),5)

if __name__=="__main__":
    unittest.main(verbosity=2)
