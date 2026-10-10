"""Offline tests for the read-only V5 Chapter 2 QC-01/02 preview tools."""
import json
import tempfile
import unittest
import wave
from pathlib import Path
from audit_v5_chapter2 import timeline
from v5_ch02_ab_preview import pause_candidate,choose

class ScopedQcTests(unittest.TestCase):
    def test_bounded_pause_proposal_preserves_non_sentence_and_special_breaks(self):
        for words,base,expected in [(6,610,530),(30,610,690),(15,610,610),
                                   (6,900,900),(30,1020,1020),(6,180,180)]:
            with self.subTest(words=words,base=base):
                item={"canonical_text":" ".join(["từ"]*(words-1))+" cuối."}
                self.assertEqual(pause_candidate(item,base),expected)
        self.assertEqual(pause_candidate({"canonical_text":"Câu hỏi?"},700),700)

    def test_join_timeline_uses_actual_clean_wav_and_gap_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            def create(name,secs):
                path=base/name
                with wave.open(str(path),"wb") as w:
                    w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000)
                    w.writeframes(b"\0\0"*round(48000*secs))
                return path
            wav=create("000000.wav",1.0)
            gap=create("gap_610.wav",.610)
            concat=base/"concat.txt"
            concat.write_text("file '"+str(wav).replace("\\","/")+"'\n"+
                              "file '"+str(gap).replace("\\","/")+"'\n",encoding="utf8")
            item={"index":0,"canonical_text":"Đoạn cuối.","heading":False,"parent_line":0}
            joins,total=timeline([item],concat)
            self.assertEqual(len(joins),1)
            self.assertEqual(joins[0]["gap_ms"],610)
            self.assertAlmostEqual(joins[0]["time_s"],1.0)
            self.assertAlmostEqual(total,1.610,places=2)

    def test_nearest_target_chooses_changed_sentence_without_touching_source(self):
        items=[{"index":1,"canonical_text":"Một đoạn ngắn.","heading":False},
               {"index":2,"canonical_text":" ".join(["dài"]*24)+"."}]
        before=json.dumps(items,ensure_ascii=False)
        bound=[{"segment":1,"gap_ms":610,"time_s":30.0},
               {"segment":2,"gap_ms":610,"time_s":60.0}]
        distance,item,edge,proposal=choose(items,bound,30.5)
        self.assertEqual(edge["segment"],1)
        self.assertEqual(proposal,530)
        self.assertEqual(json.dumps(items,ensure_ascii=False),before)

if __name__=="__main__":
    unittest.main(verbosity=2)
