# -*- coding: utf-8 -*-
"""Offline tests: mocked state, no VieNeu, Whisper, or real manuscript needed."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer

import media_control as c

class MediaControlTests(unittest.TestCase):
    def test_review_ready_is_not_mistaken_for_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chapter = root / "Chuong_01"
            repaired = root / "Chuong_01_R2"
            chapter.mkdir()
            repaired.mkdir()
            (chapter / "render_state.json").write_text(
                json.dumps({"rendered": 3, "total": 3, "qc_checked": 3, "status": "REVIEW_NEEDS_LISTENING"})
            )
            (chapter / "FINAL_GATE.json").write_text(json.dumps({"qc_checked":3}))
            (repaired / "REVIEW_STATUS.json").write_text(
                json.dumps({"status":"FULL_R2_READY_FOR_OWNER_REVIEW",
                            "segments":3,"basic_qc_review_remaining":1,
                            "improved_segments":1,"repaired_candidates":2,"final":False})
            )
            (repaired / "AUTO_REPAIR_STATUS.json").write_text(json.dumps({"phase":"REVIEW_READY"}))
            with patch.object(c, "ROOT", root), patch.object(c, "CH", chapter), \
                 patch.object(c, "R2", repaired), patch.object(c, "processes", return_value=([], [])):
                result = c.snapshot()
                self.assertEqual(result["status"]["kind"], "review")
                self.assertFalse(result["status"]["active"])
                self.assertFalse(result["quality"]["final"])
                self.assertEqual(result["progress"]["render"], 3)
                self.assertEqual(result["quality"]["review"], 1)
                with patch.object(c, "processes", return_value=([{"pid": 12, "kind": "qc"}], [])):
                    running = c.snapshot()
                    self.assertEqual(running["status"]["kind"], "running")
                    self.assertTrue(running["status"]["active"])

    def test_local_http_is_read_only_and_range_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<!doctype html>MEDIA CONTROL", encoding="utf8")
            sample = root / "audio.mp3"
            sample.write_bytes(b"TEST_FILE_1234567890")
            server = ThreadingHTTPServer(("127.0.0.1", 0), c.Handler)
            server.daemon_threads = True
            server.timeout = 3
            runner = threading.Thread(target=server.serve_forever, daemon=True)
            runner.start()
            base = "http://127.0.0.1:" + str(server.server_port)
            try:
                with patch.object(c, "WEB", root), patch.dict(c.AUDIOS, {"begin": sample}):
                    with urllib.request.urlopen(base + "/", timeout=5) as response:
                        self.assertEqual(response.status, 200)
                        self.assertIn(b"MEDIA CONTROL", response.read())
                    req = urllib.request.Request(base + "/audio/begin", headers={"Range": "bytes=0-3"})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        self.assertEqual(response.status, 206)
                        self.assertEqual(response.read(), b"TEST")
                        self.assertTrue(response.headers.get("Content-Range", "").startswith("bytes 0-3/"))
                    with self.assertRaises(urllib.error.HTTPError) as ctx:
                        urllib.request.urlopen(
                            urllib.request.Request(base + "/api/status", data=b"x", method="POST"), timeout=5
                        )
                    self.assertEqual(ctx.exception.code, 405)
                    with self.assertRaises(urllib.error.HTTPError) as ctx:
                        urllib.request.urlopen(base + "/audio/../../secret.mp3", timeout=5)
                    self.assertEqual(ctx.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()
                runner.join(timeout=3)

if __name__ == "__main__":
    unittest.main(verbosity=2)
