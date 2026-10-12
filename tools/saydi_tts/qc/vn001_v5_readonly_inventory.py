"""SAYDI VN-001 / V6 step 1.1: bounded, zero-write V5 file inventory.

Inventory only. Never starts VieNeu/Whisper, changes Owner STOP, touches
Supabase, copies a book/audio file, writes a manifest, or grants dispatch.
Run separately for Owner-verified audio, narrator and checkpoint directories.
Actual local file names, manuscript content and absolute paths are NOT emitted.
Hash mode deliberately has low per-run limits to avoid loading the H4 host.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "saydi-vn001-v5-readonly-inventory-v1"
HOST = "DESKTOP-H4A16IL"
SUFFIXES = {
    ".wav": "audio", ".mp3": "audio", ".m4b": "audio", ".flac": "audio",
    ".json": "checkpoint", ".sqlite": "checkpoint", ".db": "checkpoint",
    ".onnx": "model", ".pt": "model", ".pth": "model",
    ".safetensors": "model", ".ckpt": "model",
}
MAX_SCAN = 5000
MAX_HASH_FILES = 16
MAX_HASH_BYTES = 64 * 1024 * 1024


class InventoryHold(Exception):
    pass


def _directory_scan_error(error: OSError) -> None:
    # os.walk otherwise silently skips unreadable trees and could report
    # a false complete inventory. Never treat unreadable paths as empty.
    raise InventoryHold("DIRECTORY_SCAN_FAILED") from error


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as reader:
        while True:
            block = reader.read(128 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def inventory(
    root: Path,
    *,
    scope: str,
    mode: str = "metadata",
    max_scan: int = MAX_SCAN,
    max_hash_files: int = MAX_HASH_FILES,
    max_hash_bytes: int = MAX_HASH_BYTES,
    hash_offset: int = 0,
    expected_metadata_sha256: str | None = None,
) -> dict[str, Any]:
    """Inspect only explicit roots; no writes and no sound/metadata payloads."""
    if scope not in ("audio", "narrator", "checkpoint", "model"):
        raise ValueError("unknown scope")
    if mode not in ("metadata", "hash"):
        raise ValueError("unknown mode")
    if max_scan < 1 or not (0 <= max_hash_files <= 32) or not (0 <= max_hash_bytes <= 256 * 1024 * 1024):
        raise ValueError("unsafe bounded limits")
    if not isinstance(hash_offset, int) or hash_offset < 0 or hash_offset > max_scan:
        raise ValueError("unsafe hash offset")
    if mode == "metadata" and hash_offset:
        raise ValueError("metadata mode has no hash offset")
    if expected_metadata_sha256 is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", expected_metadata_sha256):
        raise ValueError("invalid expected metadata fingerprint")
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise InventoryHold("ROOT_NOT_LOCAL_DIRECTORY")
    root = root.resolve(strict=True)
    entries: list[tuple[str, Path, int, int, str]] = []
    for parent, dirs, files in os.walk(root, followlinks=False, onerror=_directory_scan_error):
        dirs[:] = sorted(
            name for name in dirs
            if not (Path(parent) / name).is_symlink()
        )
        for name in sorted(files):
            path = Path(parent) / name
            if path.is_symlink() or path.suffix.lower() not in SUFFIXES:
                continue
            if len(entries) >= max_scan:
                raise InventoryHold("SCAN_LIMIT_EXCEEDED_NO_COMPLETE_CLAIM")
            try:
                st = path.stat()
            except OSError as exc:
                raise InventoryHold("FILE_STAT_UNAVAILABLE") from exc
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            entries.append((relative, path, st.st_size, st.st_mtime_ns, SUFFIXES[path.suffix.lower()]))
    entries.sort(key=lambda x: x[0].casefold())
    counts = Counter(e[4] for e in entries)
    meta_hash = hashlib.sha256()
    # The printed digest is a comparison token, never a substitute for exact
    # full-file SHA256 of every approved file.
    for rel, _path, size, mtime_ns, kind in entries:
        meta_hash.update(
            json.dumps([rel, size, mtime_ns, kind], ensure_ascii=False).encode("utf-8") + b"\n"
        )

    fingerprint = meta_hash.hexdigest()
    if expected_metadata_sha256 is not None and fingerprint != expected_metadata_sha256.lower():
        raise InventoryHold("METADATA_FINGERPRINT_CHANGED_FAIL_CLOSED")
    if hash_offset > len(entries):
        raise InventoryHold("HASH_OFFSET_OUT_OF_RANGE")

    receipt: dict[str, Any] = {
        "schema": SCHEMA, "scope": scope, "mode": mode,
        "candidate_files": len(entries), "kinds": dict(sorted(counts.items())),
        "candidate_bytes": sum(e[2] for e in entries),
        "metadata_fingerprint_sha256": fingerprint,
        "hash_batch_offset": hash_offset,
        "next_hash_offset": None,
        "hash_page_final": False,
        "hash_blocked_reason": None,
        "individual_hashes": [], "hashed_files": 0, "unhashed_files": len(entries),
        "complete_file_hash_inventory": False,
        "source_and_audio_changed": False,
        "production_modified": False, "worker_started": False,
        "approved_to_start": False, "approved_to_dispatch": False,
        "owner_latch_verified": False, "checkpoint_ownership_verified": False,
        "narrator_identity_verified": False,
        "note": "NO_PRIVATE_PATH_OR_CONTENT; METADATA_IS_NOT_CHECKPOINT_OWNERSHIP",
    }
    if mode == "metadata":
        return receipt

    consumed = 0
    for rel, path, size, mtime_ns, _kind in entries[hash_offset:]:
        if len(receipt["individual_hashes"]) >= max_hash_files or consumed + size > max_hash_bytes:
            break
        try:
            sha = _sha_file(path)
            post = path.stat()
        except OSError as exc:
            raise InventoryHold("FILE_HASH_UNAVAILABLE") from exc
        if (post.st_size, post.st_mtime_ns) != (size, mtime_ns):
            raise InventoryHold("FILE_CHANGED_WHILE_HASHING")
        receipt["individual_hashes"].append({
            "anonymous_file_id": hashlib.sha256(rel.encode("utf-8")).hexdigest()[:16],
            "bytes": size, "sha256": sha,
        })
        consumed += size
    receipt["hashed_files"] = len(receipt["individual_hashes"])
    receipt["unhashed_files"] = len(entries) - receipt["hashed_files"]
    next_offset = hash_offset + receipt["hashed_files"]
    receipt["next_hash_offset"] = next_offset if next_offset < len(entries) else None
    receipt["hash_page_final"] = next_offset == len(entries)
    # Completing the final page does NOT mean all earlier pages were
    # actually verified. Never claim full coverage from one paged receipt.
    receipt["complete_file_hash_inventory"] = (
        hash_offset == 0 and receipt["hash_page_final"]
    )
    if next_offset < len(entries) and receipt["hashed_files"] == 0:
        receipt["hash_blocked_reason"] = "BATCH_LIMIT_NO_PROGRESS"
    return receipt


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Read-only H4 V5 inventory (no production actions)")
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--scope", required=True, choices=("audio", "narrator", "checkpoint", "model"))
    p.add_argument("--mode", choices=("metadata", "hash"), default="metadata")
    p.add_argument("--hash-offset", type=int, default=0,
                   help="deterministic file position for this small read-only batch")
    p.add_argument("--expected-metadata-sha256",
                   help="prior metadata digest; fail closed if files changed between batches")
    args = p.parse_args(argv)
    if platform.node().upper() != HOST or os.name != "nt":
        print(json.dumps({"schema": SCHEMA, "status": "HOLD",
                          "reason": "WRONG_HOST", "approved_to_start": False}))
        return 21
    try:
        result = inventory(args.root, scope=args.scope, mode=args.mode,
                           hash_offset=args.hash_offset,
                           expected_metadata_sha256=args.expected_metadata_sha256)
        result["host"] = HOST
        result["status"] = "READ_ONLY_PARTIAL" if not result["complete_file_hash_inventory"] else "READ_ONLY_HASHED"
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0
    except (InventoryHold, ValueError, OSError) as exc:
        message = str(exc) if isinstance(exc, InventoryHold) else "LOCAL_INVENTORY_UNAVAILABLE"
        print(json.dumps({"schema": SCHEMA, "status": "HOLD",
                          "reason": message, "approved_to_start": False}))
        return 21


if __name__ == "__main__":
    raise SystemExit(main())
