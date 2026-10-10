# -*- coding: utf-8 -*-
"""Safe multi-book registration regression, no real manuscript or TTS used."""
import hashlib
import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import book_library as books
import media_control as control

class LibraryTests(unittest.TestCase):
    def test_independent_book_source_and_current_job_survive_switch(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            jobfile=root/"active_v5_job.json"
            jobfile.write_text(json.dumps({"action":"resume","chapter":3,
                "state":"QUEUED_RESOURCE","attempts":11}),encoding="utf8")
            original_job=jobfile.read_bytes()
            with patch.object(books,"BOOK_ROOT",root/"library"),\
                 patch.object(books,"SELECTION",root/"selected.json"):
                self.assertEqual(books.selected_id(),books.LEGACY_ID)
                raw="Đây là tệp thử nghiệm\nChương Một\n".encode("utf8")
                added=books.import_stream("Sách mới thử nghiệm",
                    urllib.parse.quote("Đầu sách.txt"),io.BytesIO(raw),len(raw),True)
                self.assertFalse(added["can_produce"])
                self.assertEqual(added["source_sha256"],hashlib.sha256(raw).hexdigest())
                self.assertEqual(len(books.catalog()),2)
                filename=root/"library"/added["id"]/"source.original.txt"
                self.assertEqual(filename.read_bytes(),raw)
                doc=books.get_book(added["id"])
                self.assertEqual(doc["status"],"IMPORTED_NEEDS_INGESTION_AND_APPROVAL")
                self.assertFalse(doc["voice_sample_approved"])
                self.assertTrue(doc["original_immutable"])
                response=books.choose_book(added["id"])
                self.assertEqual(response["selected_book_id"],added["id"])
                self.assertFalse(response["can_produce"])
                self.assertEqual(jobfile.read_bytes(),original_job,
                                 "A different book must not modify the legacy job")
                self.assertEqual(books.choose_book(books.LEGACY_ID)["selected_book_id"],books.LEGACY_ID)

    def test_rights_and_file_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(books,"BOOK_ROOT",Path(temp)):
                for title,name,rights in [
                    ("Tác phẩm",urllib.parse.quote("nội dung.pdf"),False),
                    ("Tác phẩm","secret.exe",True),
                    ("","source.txt",True)
                ]:
                    with self.subTest(name=name):
                        with self.assertRaises(ValueError):
                            books.import_stream(title,name,io.BytesIO(b"X"),1,rights)
                self.assertFalse(list(Path(temp).iterdir()))

    def test_local_http_upload_and_book_boundary(self):
        server=ThreadingHTTPServer(("127.0.0.1",0),control.Handler)
        server.daemon_threads=True
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        base="http://127.0.0.1:"+str(server.server_port)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            try:
                with patch.object(control,"PORT",server.server_port),\
                     patch.object(books,"BOOK_ROOT",root/"books"),\
                     patch.object(books,"SELECTION",root/"selected.json"),\
                     patch.object(control.jobs,"submit",side_effect=AssertionError("No legacy job must start")):
                    data=b"Chuong 1: Noi dung kiem tra.\n"
                    header={"Content-Type":"application/octet-stream",
                            "X-Saydi-Csrf":control.CSRF_TOKEN,
                            "Origin":base,
                            "X-Saydi-Title":urllib.parse.quote("Sách khác"),
                            "X-Saydi-Filename":urllib.parse.quote("Kiểm tra.txt"),
                            "X-Saydi-Rights":"confirmed"}
                    forbidden=urllib.request.Request(base+"/api/books/import",
                        data=data,method="POST",headers={**header,"X-Saydi-Csrf":"bad"})
                    with self.assertRaises(urllib.error.HTTPError) as e:
                        urllib.request.urlopen(forbidden,timeout=5)
                    self.assertEqual(e.exception.code,403)
                    upload=urllib.request.Request(base+"/api/books/import",
                        data=data,method="POST",headers=header)
                    with urllib.request.urlopen(upload,timeout=5) as r:
                        self.assertEqual(r.status,201)
                        imported=json.load(r)["imported"]
                    self.assertFalse(imported["can_produce"])
                    choose=urllib.request.Request(base+"/api/books/select",method="POST",
                        data=json.dumps({"book_id":imported["id"]}).encode(),
                        headers={"Origin":base,"X-Saydi-Csrf":control.CSRF_TOKEN,
                                 "Content-Type":"application/json"})
                    with urllib.request.urlopen(choose,timeout=5) as r:
                        self.assertEqual(r.status,202)
                    command=urllib.request.Request(base+"/api/command",method="POST",
                        data=json.dumps({"action":"resume","chapter":1}).encode(),
                        headers={"Origin":base,"X-Saydi-Csrf":control.CSRF_TOKEN,
                                 "Content-Type":"application/json"})
                    with self.assertRaises(urllib.error.HTTPError) as e:
                        urllib.request.urlopen(command,timeout=5)
                    self.assertEqual(e.exception.code,409)
                    self.assertEqual(books.selected_id(),imported["id"])
                    # Do not change a real user book selection in synthetic tests.
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

if __name__=="__main__":
    unittest.main(verbosity=2)
