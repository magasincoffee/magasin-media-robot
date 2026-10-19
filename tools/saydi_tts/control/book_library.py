# -*- coding: utf-8 -*-
"""SAYDI local-first multi-book library (safe registration, not audio synthesis).

A book identity is an immutable provenance namespace, not a chapter selector.
Importing a file *never* updates the legacy active production job or V5 source.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

BOOK_ROOT = Path(r"D:\SAYDI\BOOK_LIBRARY")
CONTROL_ROOT = Path(r"C:\SAYDI\control")
SELECTION = CONTROL_ROOT / "selected_book.json"
LEGACY_ID = "legacy-v5"
ALLOWED_SUFFIXES = {".pdf", ".txt", ".docx", ".epub"}
MAX_BOOK_BYTES = 60 * 1024 * 1024
MIN_BOOK_BYTES = 1
LOCK = threading.RLock()

def timestamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")

def read_json(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, UnicodeError, ValueError):
        return {}

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".pending")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def sanitize_title(raw):
    if not isinstance(raw, str):
        raise ValueError("BOOK_TITLE_REQUIRED")
    title = re.sub(r"\s+", " ", raw).strip()
    if not 1 <= len(title) <= 120 or any(ord(c) < 32 for c in title):
        raise ValueError("BOOK_TITLE_INVALID")
    return title

def safe_filename(raw):
    if not isinstance(raw, str) or not raw:
        raise ValueError("BOOK_FILENAME_REQUIRED")
    name = raw.replace("\\", "/").split("/")[-1].strip()
    if not name or len(name) > 180 or any(ord(c) < 32 for c in name):
        raise ValueError("BOOK_FILENAME_INVALID")
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_SUFFIXES:
        raise ValueError("BOOK_FORMAT_UNSUPPORTED")
    return name, ext

def legacy():
    return {
        "id": LEGACY_ID,
        "title": "Sách V5 hiện tại (11 chương)",
        "status": "PRODUCTION_CHECKPOINTED",
        "source_format": "legacy canonical TXT",
        "chapters": 11,
        "can_produce": True,
        "source_registered": True,
        "legacy": True,
        "description": "Tác vụ V5 đang vận hành; không thay đổi nguồn hoặc checkpoint.",
    }

def catalog():
    result = [legacy()]
    try:
        entries = sorted(BOOK_ROOT.iterdir(), key=lambda x: x.name)
    except OSError:
        return result
    for folder in entries[:300]:
        if not folder.is_dir() or not re.fullmatch(r"book-[0-9a-f]{16}", folder.name):
            continue
        item = read_json(folder / "book.json")
        if item.get("id") != folder.name:
            continue
        result.append({
            "id": item["id"],
            "title": item.get("title", "Chưa đặt tên"),
            "status": item.get("status", "UNKNOWN"),
            "source_format": item.get("source_format"),
            "chapters": item.get("chapters"),
            "can_produce": False,
            "source_registered": True,
            "legacy": False,
            "created_at": item.get("created_at"),
            "original_filename": item.get("original_filename"),
            "source_bytes": item.get("source_bytes"),
            "description": "Đã lưu nguồn độc lập; chờ kiểm tra cấu trúc và duyệt giọng V5.",
        })
    return result

def get_book(book_id):
    if book_id == LEGACY_ID:
        return legacy()
    if not isinstance(book_id, str) or not re.fullmatch(r"book-[0-9a-f]{16}", book_id):
        raise ValueError("UNKNOWN_BOOK")
    file = BOOK_ROOT / book_id / "book.json"
    book = read_json(file)
    if book.get("id") != book_id or not file.is_file():
        raise ValueError("UNKNOWN_BOOK")
    return book

def selected_id():
    v = read_json(SELECTION).get("book_id", LEGACY_ID)
    try:
        get_book(v)
        return v
    except ValueError:
        return LEGACY_ID

def choose_book(book_id):
    with LOCK:
        info = get_book(book_id)
        write_json(SELECTION, {"book_id": info["id"], "updated_at": timestamp()})
    return {"selected_book_id": info["id"], "production_book_id": LEGACY_ID,
            "can_produce": info["id"] == LEGACY_ID}

def overview():
    return {"selected_book_id": selected_id(),
            "production_book_id": LEGACY_ID,
            "catalog": catalog(),
            "warning": "Chọn sách chỉ thay đổi chế độ xem. Công việc cũ vẫn giữ checkpoint; sách mới chưa được phép render."}

def import_stream(title, encoded_filename, stream, length, rights_confirmed):
    """Stream bytes to a fresh local namespace; do not parse or synthesize yet."""
    title = sanitize_title(title)
    source_name, ext = safe_filename(unquote(encoded_filename))
    if rights_confirmed is not True:
        raise ValueError("BOOK_RIGHTS_CONFIRMATION_REQUIRED")
    if type(length) is not int or length < MIN_BOOK_BYTES or length > MAX_BOOK_BYTES:
        raise ValueError("BOOK_SIZE_INVALID")
    if not hasattr(stream, "read"):
        raise ValueError("BOOK_SOURCE_REQUIRED")
    with LOCK:
        book_id = "book-" + uuid.uuid4().hex[:16]
        folder = BOOK_ROOT / book_id
        folder.mkdir(parents=True, exist_ok=False)
        destination = folder / ("source.original" + ext)
        digest = hashlib.sha256()
        copied = 0
        try:
            with destination.open("xb") as target:
                while copied < length:
                    part = stream.read(min(1024 * 1024, length - copied))
                    if not part:
                        raise ValueError("BOOK_UPLOAD_TRUNCATED")
                    target.write(part)
                    digest.update(part)
                    copied += len(part)
            doc = {
                "id": book_id, "title": title, "created_at": timestamp(),
                "status": "IMPORTED_NEEDS_INGESTION_AND_APPROVAL",
                "source_format": ext[1:].upper(),
                "original_filename": source_name,
                "source_bytes": copied,
                "source_sha256": digest.hexdigest(),
                "stored_source": destination.name,
                "rights_confirmed": True,
                "chapters": None,
                "can_produce": False,
                "original_immutable": True,
                "voice_sample_approved": False,
                "text_structure_approved": False,
                "production_enabled": False,
                "rendered_segments": 0,
                "quality_review": "NOT_STARTED",
            }
            write_json(folder / "book.json", doc)
            return {k: doc[k] for k in (
                "id", "title", "status", "source_format", "source_bytes",
                "source_sha256", "chapters", "can_produce")}
        except Exception:
            shutil.rmtree(folder, ignore_errors=True)
            raise
