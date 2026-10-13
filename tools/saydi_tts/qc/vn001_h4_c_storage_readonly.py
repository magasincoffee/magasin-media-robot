"""SAYDI002-VN-001: strictly read-only C: TEMP and protected output size audit.

No audio/text bytes read; only stat metadata in two fixed H4 scopes.
No CLI paths, environment-provided roots, deletion/migration, subprocess,
process control or network. Results are aggregate counts, never filenames.
This is NOT checkpoint provenance, safe-to-delete classification, or START.
"""
from __future__ import annotations

import json
import os
import platform
import stat
import time
from pathlib import Path
from typing import Any, Callable

SCHEMA = "saydi-vn001-h4-c-storage-audit-v1"
H4 = "DESKTOP-H4A16IL"
# No arbitrary user-selected scan targets in deployed CLI.
SCOPES = {
    "user_temp": Path(r"C:\Users\admin\AppData\Local\Temp"),
    "saydi_output": Path(r"C:\SAYDI\output"),
}
MAX_FILES_PER_SCOPE = 30000
MAX_SECONDS_PER_SCOPE = 25
MAX_DEPTH = 16
DAYS_7_SECONDS = 7 * 24 * 3600
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class AuditHold(Exception):
    """Fail closed; do not disclose underlying path or exception text."""


def _reparse(stat_result: os.stat_result) -> bool:
    return bool(getattr(stat_result, "st_file_attributes", 0) & REPARSE_POINT)


def scan_scope(
    root: Path,
    *,
    now: float | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    max_files: int = MAX_FILES_PER_SCOPE,
    max_seconds: int = MAX_SECONDS_PER_SCOPE,
    max_depth: int = MAX_DEPTH,
) -> dict[str, Any]:
    """Read only file sizes/timestamps, bounded; no path or content in receipt."""
    if not (1 <= max_files <= MAX_FILES_PER_SCOPE and
            1 <= max_seconds <= MAX_SECONDS_PER_SCOPE and
            1 <= max_depth <= MAX_DEPTH):
        raise ValueError("INVALID_BOUNDS")
    if root.is_symlink() or not root.is_dir():
        raise AuditHold("ROOT_MISSING_OR_UNSAFE")
    try:
        st = root.lstat()
        if _reparse(st) or not stat.S_ISDIR(st.st_mode):
            raise AuditHold("ROOT_REPARSE_REJECTED")
    except OSError as exc:
        raise AuditHold("ROOT_METADATA_UNREADABLE") from exc
    total_files = 0
    total_bytes = 0
    older_7d_files = 0
    older_7d_bytes = 0
    skipped_reparse = 0
    dirs = 0
    cutoff = (time.time() if now is None else now) - DAYS_7_SECONDS
    deadline = monotonic() + max_seconds
    stack: list[tuple[Path, int]] = [(root, 0)]

    while stack:
        if monotonic() > deadline:
            raise AuditHold("TIME_BUDGET_EXCEEDED_NO_COMPLETE_CLAIM")
        parent, depth = stack.pop()
        if depth > max_depth:
            raise AuditHold("DEPTH_BUDGET_EXCEEDED_NO_COMPLETE_CLAIM")
        try:
            with os.scandir(parent) as entries:
                for item in entries:
                    if monotonic() > deadline:
                        raise AuditHold("TIME_BUDGET_EXCEEDED_NO_COMPLETE_CLAIM")
                    try:
                        m = item.stat(follow_symlinks=False)
                        if item.is_symlink() or _reparse(m):
                            skipped_reparse += 1
                            continue
                        if stat.S_ISDIR(m.st_mode):
                            if depth >= max_depth:
                                raise AuditHold("DEPTH_BUDGET_EXCEEDED_NO_COMPLETE_CLAIM")
                            stack.append((Path(item.path), depth + 1))
                            dirs += 1
                            continue
                        if not stat.S_ISREG(m.st_mode):
                            continue
                        total_files += 1
                        if total_files > max_files:
                            raise AuditHold("FILE_BUDGET_EXCEEDED_NO_COMPLETE_CLAIM")
                        total_bytes += m.st_size
                        if m.st_mtime <= cutoff:
                            older_7d_files += 1
                            older_7d_bytes += m.st_size
                    except OSError as exc:
                        raise AuditHold("ENTRY_METADATA_UNREADABLE") from exc
        except OSError as exc:
            raise AuditHold("DIRECTORY_UNREADABLE_NO_COMPLETE_CLAIM") from exc

    return {
        # A skipped junction/symlink can conceal more files. Never assert
        # completeness or capacity provenance for an incomplete subtree.
        "status": ("READ_ONLY_METADATA_PARTIAL_REPARSE_SKIPPED"
                   if skipped_reparse else "READ_ONLY_METADATA_COMPLETE"),
        "file_count": total_files,
        "subdirectory_count": dirs,
        "logical_bytes": total_bytes,
        "older_than_7d_file_count": older_7d_files,
        "older_than_7d_logical_bytes": older_7d_bytes,
        "skipped_reparse_entries": skipped_reparse,
        "safe_to_delete_verified": False,
        "checkpoint_owner_verified": False,
    }


def _is_h4() -> bool:
    return os.name == "nt" and platform.node().upper() == H4


def run_h4() -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "host": H4,
        "status": "READ_ONLY_PARTIAL_UNATTESTED",
        "production_modified": False,
        "owner_stop_changed": False,
        "worker_started": False,
        "approved_to_start": False,
        "approved_to_dispatch": False,
        "safe_to_delete_verified": False,
        "checkpoint_owner_verified": False,
        "audio_sha_verified": False,
        "scopes": {},
    }
    if not _is_h4():
        return {**receipt, "status": "BLOCKED", "reason": "WRONG_HOST"}
    for name, root in SCOPES.items():
        try:
            receipt["scopes"][name] = scan_scope(root)
        except (AuditHold, OSError, ValueError):
            # Never reveal a real path or filename in an error.
            receipt["scopes"][name] = {
                "status": "BLOCKED",
                "reason": "SCOPED_READ_UNAVAILABLE_OR_BOUNDED",
                "safe_to_delete_verified": False,
            }
    if all(s["status"] == "READ_ONLY_METADATA_COMPLETE"
           for s in receipt["scopes"].values()):
        receipt["status"] = "READ_ONLY_METADATA_UNATTESTED"
    return receipt


def main() -> int:
    result = run_h4()
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0 if result["status"] == "READ_ONLY_METADATA_UNATTESTED" else 21


if __name__ == "__main__":
    raise SystemExit(main())
