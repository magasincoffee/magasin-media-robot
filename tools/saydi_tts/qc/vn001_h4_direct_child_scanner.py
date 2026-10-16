"""SAYDI V6 VN-001: Windows-only, direct-child, no-reparse metadata scanner.

SOURCE / ISOLATED STAGE ONLY. Not registered in MCP; NOT qualified as a
production V5 reader. Trusted H4 wrapper MUST provide a fixed, authorized
root, authenticated Owner V6 grant, STOP-generation lifecycle lock and
per-child replay guard. This function never accepts public MCP arguments,
returns filenames, hashes private content, or follows subdirectories.

Windows filesystem may race between ancestor validation and path-based
scandir. Because this source stage does not yet implement handle-relative
enumeration, partial receipts explicitly remain FIELD_UNATTESTED. Never
promote them to complete SHA/asset provenance or skip qualified host review.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
from typing import Any

SCHEMA = "SAYDI_VN001_WINDOWS_PARTIAL_NOFOLLOW_V1"
SUFFIXES = frozenset((".wav", ".mp3", ".flac", ".m4b", ".json", ".sqlite",
                      ".db", ".onnx", ".pt", ".pth", ".safetensors", ".ckpt"))
REPARSE_ATTRIBUTE = 0x400
MAX_CHILDREN = 1000
H4 = "DESKTOP-H4A16IL"
H4_STAGE = Path(r"C:\MAGASIN_MCP\staging\saydi_v6_grant\fixtures")
FILE_READ_ATTRIBUTES = 0x80
FILE_LIST_DIRECTORY = 0x1
FILE_SHARE_READ = 0x1
FILE_SHARE_WRITE = 0x2
FILE_SHARE_DELETE = 0x4
OPEN_EXISTING = 3
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000


class SafeHold(Exception):
    pass


class _ByHandleInfo(ctypes.Structure):
    _fields_ = [
        ("dwFileAttributes", wintypes.DWORD),
        ("ftCreationTime", wintypes.FILETIME),
        ("ftLastAccessTime", wintypes.FILETIME),
        ("ftLastWriteTime", wintypes.FILETIME),
        ("dwVolumeSerialNumber", wintypes.DWORD),
        ("nFileSizeHigh", wintypes.DWORD),
        ("nFileSizeLow", wintypes.DWORD),
        ("nNumberOfLinks", wintypes.DWORD),
        ("nFileIndexHigh", wintypes.DWORD),
        ("nFileIndexLow", wintypes.DWORD),
    ]


def _native_handle_info(path: Path, *, directory: bool) -> tuple[int, int, int]:
    """Inspect a leaf via CreateFileW(OPEN_REPARSE_POINT), without file payloads."""
    if os.name != "nt":
        raise SafeHold("WINDOWS_ONLY")
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    create = api.CreateFileW
    create.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    create.restype = wintypes.HANDLE
    get = api.GetFileInformationByHandle
    get.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ByHandleInfo)]
    get.restype = wintypes.BOOL
    close = api.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    handle = create(
        str(path), FILE_READ_ATTRIBUTES | (FILE_LIST_DIRECTORY if directory else 0),
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None, OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT | (FILE_FLAG_BACKUP_SEMANTICS if directory else 0),
        None,
    )
    if handle in (None, wintypes.HANDLE(-1).value):
        raise SafeHold("FILE_HANDLE_UNAVAILABLE")
    try:
        info = _ByHandleInfo()
        if not get(handle, ctypes.byref(info)):
            raise SafeHold("FILE_IDENTITY_UNAVAILABLE")
        if info.dwFileAttributes & REPARSE_ATTRIBUTE:
            raise SafeHold("REPARSE_REJECTED")
        is_dir = bool(info.dwFileAttributes & stat.FILE_ATTRIBUTE_DIRECTORY)
        if is_dir != directory:
            raise SafeHold("FILE_TYPE_CHANGED")
        return (int(info.dwVolumeSerialNumber),
                (int(info.nFileIndexHigh) << 32) | int(info.nFileIndexLow),
                (int(info.nFileSizeHigh) << 32) | int(info.nFileSizeLow))
    finally:
        close(handle)


def _ancestors(root: Path) -> list[Path]:
    if os.name != "nt" or not root.is_absolute() or not root.drive:
        raise SafeHold("ROOT_NOT_WINDOWS_ABSOLUTE")
    all_parts = list(reversed(root.parents)) + [root]
    return [p for p in all_parts if str(p).endswith("\\") or p != Path(root.anchor)]


def inspect_direct_metadata(root: Path, *, max_children: int = MAX_CHILDREN) -> dict[str, Any]:
    """Fail closed on reparse/identity drift; never descend or read file bytes."""
    block = {
        "schema": SCHEMA, "status": "BLOCKED", "field_accepted": False,
        "production_modified": False, "worker_started": False,
        "approved_to_start": False, "task_completed": False,
    }
    try:
        if os.name != "nt":
            raise SafeHold("WINDOWS_ONLY")
        if type(root) is not type(Path(".")) or not root.is_absolute():
            raise SafeHold("ROOT_NOT_WINDOWS_ABSOLUTE")
        if type(max_children) is not int or not 1 <= max_children <= MAX_CHILDREN:
            raise SafeHold("SCAN_LIMIT_UNQUALIFIED")
        # This source-stage implementation is not an authenticated host route.
        # On the actual H4 it MUST NOT scan C:\SAYDI / D:\SAYDI even when a
        # caller invokes this module directly, outside the MCP service.
        # Only synthetic fixture roots strictly inside the isolated stage
        # tree may be opened. Root/ancestor reparse checks still follow.
        if socket.gethostname().upper() == H4:
            # pathlib preserves '..' in .parents; Windows interprets it
            # before opening a handle. Refuse traversal lexically BEFORE any
            # filesystem operation. A path resolving into the stage is not
            # sufficient: no alias/reparse hop is allowed, either.
            if any(part in ("..", ".") for part in root.parts):
                raise SafeHold("STAGE_PATH_TRAVERSAL_REJECTED")
            if root == H4_STAGE or H4_STAGE not in root.parents:
                raise SafeHold("LIVE_H4_PROTECTED_SCAN_NOT_AUTHORIZED")
        # Check every existing parent: unlike Path.is_symlink this also
        # rejects Windows junction/reparse points. This is a static stage
        # guard, NOT an atomic handle-relative traversal qualification.
        parents = _ancestors(root)
        original: dict[Path, tuple[int, int, int]] = {}
        for parent in parents:
            original[parent] = _native_handle_info(parent, directory=True)
        rows: list[tuple[str, int, int]] = []
        skipped_directory = False
        skipped_unsupported = False
        scanned = 0
        with os.scandir(root) as it:
            for entry in it:
                scanned += 1
                if scanned > max_children:
                    raise SafeHold("SCAN_LIMIT_EXCEEDED")
                child = Path(entry.path)
                before = child.stat(follow_symlinks=False)
                if before.st_file_attributes & REPARSE_ATTRIBUTE or entry.is_symlink():
                    # HOLD on links rather than silently declaring full.
                    raise SafeHold("REPARSE_REJECTED")
                if before.st_file_attributes & stat.FILE_ATTRIBUTE_DIRECTORY:
                    _native_handle_info(child, directory=True)
                    skipped_directory = True
                    continue
                if not before.st_file_attributes & stat.FILE_ATTRIBUTE_NORMAL and not stat.S_ISREG(before.st_mode):
                    skipped_unsupported = True
                    continue
                # A direct child is opened by handle with OPEN_REPARSE_POINT
                # to ensure it is not a symlink/junction leaf.
                volume, fid, file_size = _native_handle_info(child, directory=False)
                after = child.stat(follow_symlinks=False)
                # Windows st_ino is the native FileIndex exposed by the
                # handle (dwFileIndexHigh/Low). A same-sized swap-and-restore
                # must not be accepted merely because both path stats match.
                # Fail closed on filesystems without a stable file ID.
                if (not before.st_ino or not after.st_ino
                        or fid != before.st_ino or fid != after.st_ino
                        or volume != original[root][0]
                        or before.st_dev != after.st_dev
                        or (before.st_size, before.st_mtime_ns) !=
                           (after.st_size, after.st_mtime_ns)
                        or file_size != before.st_size):
                    raise SafeHold("FILE_CHANGED_DURING_SCAN")
                if child.suffix.lower() not in SUFFIXES:
                    skipped_unsupported = True
                    continue
                rows.append((entry.name, before.st_size, before.st_mtime_ns))
        for parent in parents:
            if _native_handle_info(parent, directory=True) != original[parent]:
                raise SafeHold("ANCESTOR_CHANGED_DURING_SCAN")
        rows.sort(key=lambda x: x[0].casefold())
        digest = hashlib.sha256()
        for name, size, mtime in rows:
            digest.update(json.dumps([name, size, mtime], ensure_ascii=False).encode() + b"\n")
        return {
            **block, "status": "DIRECT_CHILD_METADATA_PARTIAL_UNATTESTED",
            "scope_limited_to_direct_children": True,
            "subdirectories_not_traversed": True,
            "skipped_child_directories": skipped_directory,
            "skipped_other_files": skipped_unsupported,
            "candidate_files": len(rows),
            "candidate_bytes": sum(row[1] for row in rows),
            "metadata_fingerprint_sha256": digest.hexdigest(),
            "file_names_exposed": False,
            "complete_v5_inventory": False,
            "content_sha_verified": False,
        }
    except SafeHold as exc:
        code = exc.args[0] if type(exc) is SafeHold and len(exc.args) == 1 and type(exc.args[0]) is str else None
        valid = {
            "WINDOWS_ONLY", "ROOT_NOT_WINDOWS_ABSOLUTE", "SCAN_LIMIT_UNQUALIFIED",
            "FILE_HANDLE_UNAVAILABLE", "FILE_IDENTITY_UNAVAILABLE",
            "REPARSE_REJECTED", "FILE_TYPE_CHANGED", "SCAN_LIMIT_EXCEEDED",
            "FILE_CHANGED_DURING_SCAN", "ANCESTOR_CHANGED_DURING_SCAN",
            "LIVE_H4_PROTECTED_SCAN_NOT_AUTHORIZED",
            "STAGE_PATH_TRAVERSAL_REJECTED",
        }
        return {**block, "reason": code if code in valid else "SAFE_SCAN_UNAVAILABLE"}
    except BaseException:
        return {**block, "reason": "SAFE_SCAN_UNAVAILABLE"}
