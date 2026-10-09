# -*- coding: utf-8 -*-
"""Synthetic tests for SAFE chapter selection, durable queue and CSRF gate."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer

import control_commands as jobs
import media_control as server

class OperatorTests(unittest.TestCase):
    def test_chapter_selection_and_job_queue(self):
        with tempfile.TemporaryDirectory() as folder:
            temp=Path(folder)
            with patch.object(jobs,"SELECTED",temp/"selected.json"),\
                 patch.object(jobs,"JOB",temp/"job.json"),\
                 patch.object(jobs,"LOG",temp/"job.log"),\
                 patch.object(jobs,"launch_tick",return_value=12345),\
                 patch.object(jobs,"chapter_data",return_value={"can_resume":True}):
                out=jobs.submit("select",3)
                self.assertEqual(out["selected"],3)
                self.assertEqual(jobs.selected_chapter(),3)
                q=jobs.submit("resume",3)
                self.assertEqual(q["state"],"QUEUED")
                self.assertEqual(jobs.job_status()["chapter"],3)
                with self.assertRaises(RuntimeError):
                    jobs.submit("resume",4)
                with self.assertRaises(ValueError):
                    jobs.submit("resume",12)

    def test_web_api_requires_csrf_and_allowed_origin(self):
        http=ThreadingHTTPServer(("127.0.0.1",0),server.Handler)
        http.daemon_threads=True
        th=threading.Thread(target=http.serve_forever,daemon=True);th.start()
        base=f"http://127.0.0.1:{http.server_port}"
        payload=json.dumps({"action":"select","chapter":3}).encode()
        try:
            with patch.object(server,"PORT",http.server_port),\
                 patch.object(server.jobs,"submit",return_value={"accepted":True,"selected":3}):
                request=urllib.request.Request(base+"/api/command",data=payload,
                         method="POST",headers={"Content-Type":"application/json"})
                with self.assertRaises(urllib.error.HTTPError) as err:
                    urllib.request.urlopen(request,timeout=4)
                self.assertEqual(err.exception.code,403)
                request=urllib.request.Request(base+"/api/command",data=payload,method="POST",
                    headers={"Content-Type":"application/json","X-Saydi-Csrf":server.CSRF_TOKEN,
                             "Origin":"http://127.0.0.1:"+str(http.server_port)})
                with urllib.request.urlopen(request,timeout=4) as response:
                    self.assertEqual(response.status,202)
                    self.assertTrue(json.loads(response.read())["accepted"])
                request=urllib.request.Request(base+"/api/command",data=payload,method="POST",
                    headers={"Content-Type":"application/json","X-Saydi-Csrf":server.CSRF_TOKEN,
                             "Origin":"http://untrusted.example"})
                with self.assertRaises(urllib.error.HTTPError) as err:
                    urllib.request.urlopen(request,timeout=4)
                self.assertEqual(err.exception.code,403)
        finally:
            http.shutdown();http.server_close();th.join(timeout=3)

if __name__=="__main__":
    unittest.main(verbosity=2)
