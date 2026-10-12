"""SAYDI V6 1.1 — callable adapter for an *existing* trusted H4 local MCP.

Not a server, listener, daemon, scheduler, or production dispatcher.
An authenticated local MCP transport MAY call handle_inventory() only after
separately verified GitHub-main SOT evidence and locally configured roots.
No field in a caller-controlled request can supply that authorization.

Does not authorize Supervisor project selection, specialist START, TTS,
Whisper, worker resume, automated release, Owner DONE, or any writes.
"""
from __future__ import annotations

import importlib.util
import os
import re
import socket
from pathlib import Path, PureWindowsPath
from typing import Any

SCHEMA = "MAGASIN_SAYDI_VN001_MCP_READONLY_V1"
TASK = "SAYDI002-VN-001"
REPOSITORY = "magasincoffee/magasin-media-robot"
SOT_PATH = "00_PROJECT/SOURCE_OF_TRUTH.md"
SOT_SHA = re.compile(r"^[0-9a-f]{40}$")
META_SHA = re.compile(r"^[0-9a-f]{64}$")
ROOT_NAME = re.compile(r"^[a-z0-9_-]{1,40}$")
HOST = "DESKTOP-H4A16IL"
FIELDS = frozenset({
    "schema", "task_id", "target", "action", "root_key", "scope",
    "mode", "hash_offset", "expected_metadata_sha256", "expected_main_sha",
})
SCOPES = frozenset({"audio", "narrator", "checkpoint", "model"})
ALLOWED_ROOTS = ("C:\\SAYDI", "D:\\SAYDI")


class LocalReadRejected(ValueError):
    pass


def _is_h4() -> bool:
    return os.name == "nt" and socket.gethostname().upper() == HOST


def _root_is_allowed(root: Path) -> bool:
    """Only canonical SAYDI roots. Resolve reparse points before checking."""
    try:
        if root.is_symlink() or not root.is_dir() or not root.is_absolute():
            return False
        absolute = PureWindowsPath(str(root.resolve(strict=True)))
        return any(
            absolute == base or base in absolute.parents
            for base in (PureWindowsPath(p) for p in ALLOWED_ROOTS)
        )
    except (OSError, ValueError, RuntimeError):
        return False


def _validate_request(request: Any, *, verified_sot: Any,
                      transport_authenticated: bool) -> tuple[str, str, int, str | None]:
    if transport_authenticated is not True:
        raise LocalReadRejected("MCP_TRANSPORT_NOT_AUTHENTICATED")
    if type(request) is not dict or set(request) != FIELDS:
        raise LocalReadRejected("REQUEST_SCHEMA_NOT_ALLOWLISTED")
    if (request.get("schema") != SCHEMA or request.get("task_id") != TASK or
            request.get("target") != "saydi" or
            request.get("action") != "inventory_v5_readonly"):
        raise LocalReadRejected("REQUEST_ACTION_NOT_ALLOWLISTED")
    key = request.get("root_key")
    scope = request.get("scope")
    mode = request.get("mode")
    offset = request.get("hash_offset")
    expected = request.get("expected_metadata_sha256")
    revision = request.get("expected_main_sha")
    if type(key) is not str or not ROOT_NAME.fullmatch(key):
        raise LocalReadRejected("ROOT_KEY_INVALID")
    if scope not in SCOPES or mode not in ("metadata", "hash"):
        raise LocalReadRejected("READ_SCOPE_OR_MODE_INVALID")
    if type(offset) is not int or offset < 0 or offset > 5000:
        raise LocalReadRejected("HASH_OFFSET_INVALID")
    if mode == "metadata" and offset != 0:
        raise LocalReadRejected("METADATA_OFFSET_INVALID")
    if expected is not None and (type(expected) is not str or not META_SHA.fullmatch(expected)):
        raise LocalReadRejected("METADATA_SHA_INVALID")
    if offset > 0 and expected is None:
        raise LocalReadRejected("PAGED_HASH_REQUIRES_FINGERPRINT")
    if type(revision) is not str or not SOT_SHA.fullmatch(revision):
        raise LocalReadRejected("MAIN_REVISION_INVALID")
    # This evidence is a distinct trusted local verifier output, never
    # obtained by deserializing the caller request or an old chat message.
    if (type(verified_sot) is not dict or
            verified_sot.get("verified_exact_main") is not True or
            verified_sot.get("repository") != REPOSITORY or
            verified_sot.get("sot_path") != SOT_PATH or
            verified_sot.get("main_sha") != revision or
            verified_sot.get("active_task_id") != TASK or
            verified_sot.get("task_status") != "IN_PROGRESS" or
            verified_sot.get("production_dispatch_authorized") is not False):
        raise LocalReadRejected("SOT_MAIN_AUTHORITY_UNVERIFIED")
    return key, scope, offset, expected


def _inventory_module():
    # Load only an exact local sibling (never a request-provided executable).
    path = Path(__file__).with_name("vn001_v5_readonly_inventory.py")
    spec = importlib.util.spec_from_file_location("saydi_vn001_safe_inventory", path)
    if spec is None or spec.loader is None:
        raise LocalReadRejected("INVENTORY_CODE_NOT_AVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def handle_inventory(
    request: Any,
    *,
    verified_sot: Any = None,
    transport_authenticated: bool = False,
    locally_approved_roots: Any = None,
) -> dict[str, Any]:
    """Read-only MCP tool implementation; NO web endpoint or local job queue.

    Importer must supply independently authenticated MCP transport, a fresh
    GitHub-main SOT verifier result, and H4-admin-controlled root bindings.
    No default configuration grants these proofs; fail closed.
    """
    deny = {
        "schema": SCHEMA, "task_id": TASK, "status": "BLOCKED",
        "approved_to_start": False, "approved_to_dispatch": False,
        "production_modified": False, "worker_started": False,
        "project_switch_allowed": False, "owner_stop_changed": False,
        "task_completed": False,
    }
    try:
        key, scope, offset, expected = _validate_request(
            request, verified_sot=verified_sot,
            transport_authenticated=transport_authenticated,
        )
        if not _is_h4():
            raise LocalReadRejected("WRONG_HOST")
        if type(locally_approved_roots) is not dict:
            raise LocalReadRejected("NO_LOCAL_ROOT_BINDINGS")
        binding = locally_approved_roots.get(key)
        if (type(binding) is not dict or set(binding) != {"scope", "path"} or
                binding.get("scope") != scope or
                type(binding.get("path")) is not str):
            raise LocalReadRejected("ROOT_BINDING_NOT_ALLOWLISTED")
        root = Path(binding["path"])
        if not _root_is_allowed(root):
            raise LocalReadRejected("ROOT_OUTSIDE_APPROVED_SAYDI_TREE")
        scanner = _inventory_module()
        receipt = scanner.inventory(
            root, scope=scope, mode=request["mode"], hash_offset=offset,
            expected_metadata_sha256=expected,
        )
        # Deliberately no local report file or full private filepath.
        return {
            **deny, "status": "READ_ONLY_RECEIPT_UNATTESTED",
            "root_key": key, "verified_main_sha": request["expected_main_sha"],
            "inventory": receipt,
        }
    except (LocalReadRejected, ValueError, OSError) as exc:
        # Never echo attacker-provided request or private local paths.
        safe = str(exc)
        if safe not in {
            "MCP_TRANSPORT_NOT_AUTHENTICATED", "REQUEST_SCHEMA_NOT_ALLOWLISTED",
            "REQUEST_ACTION_NOT_ALLOWLISTED", "ROOT_KEY_INVALID",
            "READ_SCOPE_OR_MODE_INVALID", "HASH_OFFSET_INVALID",
            "METADATA_OFFSET_INVALID", "METADATA_SHA_INVALID",
            "PAGED_HASH_REQUIRES_FINGERPRINT", "MAIN_REVISION_INVALID",
            "SOT_MAIN_AUTHORITY_UNVERIFIED", "WRONG_HOST",
            "NO_LOCAL_ROOT_BINDINGS", "ROOT_BINDING_NOT_ALLOWLISTED",
            "ROOT_OUTSIDE_APPROVED_SAYDI_TREE", "INVENTORY_CODE_NOT_AVAILABLE",
            "ROOT_NOT_LOCAL_DIRECTORY", "SCAN_LIMIT_EXCEEDED_NO_COMPLETE_CLAIM",
            "DIRECTORY_SCAN_FAILED", "METADATA_FINGERPRINT_CHANGED_FAIL_CLOSED",
            "HASH_OFFSET_OUT_OF_RANGE", "FILE_HASH_UNAVAILABLE",
            "FILE_CHANGED_WHILE_HASHING", "FILE_STAT_UNAVAILABLE",
        }:
            safe = "SAFE_INVENTORY_NOT_QUALIFIED"
        return {**deny, "reason": safe}
