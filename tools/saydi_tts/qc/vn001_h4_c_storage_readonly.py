"""SAYDI002-VN-001: SOURCE/QA ONLY, bounded single-directory metadata fixture.

SECURITY HOLD:
* No live H4 scan is authorized by this module or by GitHub CI.
* The direct command-line entrypoint always exits BLOCKED, without probing C:.
* An Owner/SOT-authenticated, separately reviewed adapter is mandatory before
  local H4 file inventory. Existing local MCP authority is NOT implicitly reused.
* No recursive descent or directory queue: no mutable queued path may turn into
  a junction between checking and opening it.
* A directory below the nominated root makes the report PARTIAL, never complete.
* This is not an ownership check, safe-to-delete recommendation, or dispatch.
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
HOST = "DESKTOP-H4A16IL"
# Reference locations for a FUTURE independently gated local adapter only.
# This module deliberately does not dereference them on H4.
SCOPES = {
    "user_temp": Path(r"C:\Users\admin\AppData\Local\Temp"),
    "saydi_output": Path(r"C:\SAYDI\output"),
}
MAX_FILES_PER_SCOPE = 30000
MAX_SECONDS_PER_SCOPE = 25
DAYS_7_SECONDS = 7 * 24 * 3600
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class AuditHold(Exception):
    """Fail closed; never put private paths or OS errors in the receipt."""


def _is_h4() -> bool:
    return os.name == "nt" and platform.node().upper() == HOST


def _reparse(entry_stat: os.stat_result) -> bool:
    return bool(getattr(entry_stat, "st_file_attributes", 0) & REPARSE_POINT)


def scan_scope(
    root: Path,
    *,
    now: float | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    max_files: int = MAX_FILES_PER_SCOPE,
    max_seconds: int = MAX_SECONDS_PER_SCOPE,
) -> dict[str, Any]:
    """Only synthetic/isolated offline QA; one directory and no live H4.

    The directory path is passed by offline tests, not an exposed MCP/CLI
    argument. On real H4 this returns HOLD *before* inspecting that path.
    Caller is forbidden to treat skipped child directories as empty.
    """
    if _is_h4():
        raise AuditHold("LIVE_H4_SCAN_NOT_AUTHORIZED")
    if type(max_files) is not int or type(max_seconds) is not int or not (
        1 <= max_files <= MAX_FILES_PER_SCOPE
        and 1 <= max_seconds <= MAX_SECONDS_PER_SCOPE
    ):
        raise ValueError("INVALID_BOUNDS")
    root = Path(root)
    try:
        if root.is_symlink() or not root.is_dir():
            raise AuditHold("ROOT_MISSING_OR_UNSAFE")
        root_stat = root.lstat()
        if _reparse(root_stat) or not stat.S_ISDIR(root_stat.st_mode):
            raise AuditHold("ROOT_REPARSE_REJECTED")
    except OSError:
        raise AuditHold("ROOT_METADATA_UNREADABLE") from None

    cutoff = (time.time() if now is None else now) - DAYS_7_SECONDS
    deadline = monotonic() + max_seconds
    total_files = total_bytes = old_files = old_bytes = 0
    skipped_reparse = skipped_directories = 0
    try:
        # Do not queue/traverse child directories on any OS. On H4 this
        # entire code path is unreachable without a future reviewed change.
        with os.scandir(root) as entries:
            for item in entries:
                if monotonic() > deadline:
                    raise AuditHold("TIME_BUDGET_EXCEEDED_NO_COMPLETE_CLAIM")
                try:
                    st = item.stat(follow_symlinks=False)
                    if item.is_symlink() or _reparse(st):
                        skipped_reparse += 1
                        continue
                    if stat.S_ISDIR(st.st_mode):
                        skipped_directories += 1
                        continue
                    if not stat.S_ISREG(st.st_mode):
                        continue
                    total_files += 1
                    if total_files > max_files:
                        raise AuditHold("FILE_BUDGET_EXCEEDED_NO_COMPLETE_CLAIM")
                    total_bytes += st.st_size
                    if st.st_mtime <= cutoff:
                        old_files += 1
                        old_bytes += st.st_size
                except OSError:
                    raise AuditHold("ENTRY_METADATA_UNREADABLE") from None
    except OSError:
        raise AuditHold("DIRECTORY_UNREADABLE_NO_COMPLETE_CLAIM") from None

    partial = skipped_directories > 0 or skipped_reparse > 0
    return {
        "status": ("READ_ONLY_METADATA_PARTIAL_SKIPPED"
                   if partial else "READ_ONLY_METADATA_TOP_LEVEL_COMPLETE"),
        "file_count": total_files,
        "skipped_subdirectory_count": skipped_directories,
        "skipped_reparse_entries": skipped_reparse,
        "logical_bytes": total_bytes,
        "older_than_7d_file_count": old_files,
        "older_than_7d_logical_bytes": old_bytes,
        "complete_tree_inventory": not partial,
        "safe_to_delete_verified": False,
        "checkpoint_owner_verified": False,
    }


def run_h4() -> dict[str, Any]:
    """Non-operational stub: no installed H4 adapter is qualified yet."""
    return {
        "schema": SCHEMA,
        "host": HOST,
        "status": "BLOCKED",
        "reason": "LIVE_H4_AUTHORITY_AND_DIRECTORY_HANDLES_NOT_QUALIFIED",
        "scopes": {},
        "production_modified": False,
        "owner_stop_changed": False,
        "worker_started": False,
        "approved_to_start": False,
        "approved_to_dispatch": False,
        "safe_to_delete_verified": False,
        "checkpoint_owner_verified": False,
        "audio_sha_verified": False,
        "task_completed": False,
    }


def main() -> int:
    # Running this Python file directly on ANY host never performs a scan.
    print(json.dumps(run_h4(), sort_keys=True, ensure_ascii=True))
    return 21


if __name__ == "__main__":
    raise SystemExit(main())
