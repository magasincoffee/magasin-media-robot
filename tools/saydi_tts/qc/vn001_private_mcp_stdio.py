"""SAYDI VN-001 one-tool MCP stdio target for a *future* Secure MCP Tunnel.

SOURCE / QA CANDIDATE ONLY. This is not an installer, service or general shell.
No network listener is opened, and this process never edits local files.
The trusted H4 operator must explicitly approve a tunnel-client source-only
deployment, authenticate the OpenAI tunnel/workspace, and bind local roots
before connecting a private ChatGPT plugin. Never attach a generic runner.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

VERSION = "2026-10-12-vn001-readonly"
TOOL = "saydi_vn001_inventory_readonly"
MAX_REQUEST_BYTES = 12288
MAX_ROOT_CONFIG_BYTES = 4096
ROOT_CONFIG_ENV = "SAYDI_VN001_ROOTS_JSON"
SENSITIVE = frozenset({"command", "cmd", "powershell", "owner_start", "run", "file_path"})
MCP_SCHEMA = "MAGASIN_SAYDI_VN001_MCP_READONLY_V1"
TASK_ID = "SAYDI002-VN-001"
FIELDS = {
    "schema", "task_id", "target", "action", "root_key", "scope", "mode",
    "hash_offset", "expected_metadata_sha256", "expected_main_sha",
}


def _load_bridge():
    filename = Path(__file__).with_name("vn001_local_mcp_readonly_bridge.py")
    spec = importlib.util.spec_from_file_location("saydi_local_stdio_bridge", filename)
    if spec is None or spec.loader is None:
        raise RuntimeError("VERIFIED_BRIDGE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_local_root_config() -> dict[str, Any]:
    raw = os.environ.get(ROOT_CONFIG_ENV, "")
    if not raw or len(raw.encode("utf-8")) > MAX_ROOT_CONFIG_BYTES:
        return {}
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    if type(value) is not dict or not 1 <= len(value) <= 16:
        return {}
    for key, entry in value.items():
        if not isinstance(key, str) or not key.isascii() or len(key) > 40:
            return {}
        if type(entry) is not dict or set(entry) != {"scope", "path"}:
            return {}
        if entry.get("scope") not in ("audio", "narrator", "checkpoint", "model"):
            return {}
        if not isinstance(entry.get("path"), str) or len(entry["path"]) > 260:
            return {}
    # The bridge independently resolves and rejects roots outside C:/SAYDI
    # and D:/SAYDI after host and SOT provenance qualification.
    return value


def schema() -> dict:
    return {
        "name": TOOL,
        "description": (
            "Read-only bounded SHA/metadata of a locally-approved SAYDI V5 "
            "asset folder on DESKTOP-H4A16IL. Never runs or changes workers. "
            "Only SAYDI002-VN-001; requires exact GitHub main SHA and private "
            "host configured root key. Does not mark task DONE."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": sorted(FIELDS),
            "properties": {
                "schema": {"type": "string", "enum": [MCP_SCHEMA]},
                "task_id": {"type": "string", "enum": [TASK_ID]},
                "target": {"type": "string", "enum": ["saydi"]},
                "action": {"type": "string", "enum": ["inventory_v5_readonly"]},
                "root_key": {"type": "string", "pattern": "^[a-z0-9_-]{1,40}$"},
                "scope": {"type": "string", "enum": ["audio", "narrator", "checkpoint", "model"]},
                "mode": {"type": "string", "enum": ["metadata", "hash"]},
                "hash_offset": {"type": "integer", "minimum": 0, "maximum": 5000},
                "expected_metadata_sha256": {
                    "oneOf": [
                        {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                        {"type": "null"},
                    ]
                },
                "expected_main_sha": {"type": "string", "pattern": "^[a-f0-9]{40}$"},
            },
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False,
                        "idempotentHint": True, "openWorldHint": False},
    }


def _error(id_value: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_value,
            "error": {"code": code, "message": message}}


def _result(id_value: Any, value: dict) -> dict:
    return {"jsonrpc": "2.0", "id": id_value, "result": value}


def dispatch(
    message: Any, *,
    inventory_call: Callable[..., dict] | None = None,
    root_config: dict | None = None,
) -> dict | None:
    """Single stdin JSON-RPC message; no arbitrary dispatch methods."""
    if type(message) is not dict or message.get("jsonrpc") != "2.0":
        return _error(None, -32600, "INVALID_MCP_MESSAGE")
    request_id = message.get("id")
    if request_id is not None and (type(request_id) not in (str, int) or len(str(request_id)) > 100):
        return _error(None, -32600, "INVALID_REQUEST_ID")
    method = message.get("method")
    if type(method) is not str:
        return _error(request_id, -32600, "INVALID_METHOD")
    if method == "notifications/initialized":
        return None
    if request_id is None:
        return None
    if method == "initialize":
        return _result(request_id, {
            "protocolVersion": "2025-03-26",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "saydi-vn001-private-readonly", "version": VERSION},
        })
    if method == "ping":
        return _result(request_id, {})
    if method == "tools/list":
        return _result(request_id, {"tools": [schema()]})
    if method == "tools/call":
        params = message.get("params")
        if type(params) is not dict or set(params) != {"name", "arguments"}:
            return _error(request_id, -32602, "INVALID_TOOL_PARAMETERS")
        if params["name"] != TOOL or type(params["arguments"]) is not dict:
            return _error(request_id, -32602, "TOOL_NOT_ALLOWLISTED")
        args = params["arguments"]
        if set(args) != FIELDS or any(key in args for key in SENSITIVE):
            return _error(request_id, -32602, "UNAUTHORIZED_TOOL_ARGUMENTS")
        scanner = inventory_call if inventory_call is not None else _load_bridge().handle_inventory
        try:
            # Trust originates at the manually reviewed local tunnel-client
            # stdin pipe, not the caller's JSON. Never expose these kwargs.
            receipt = scanner(
                args,
                transport_authenticated=True,
                locally_approved_roots=root_config if root_config is not None else _read_local_root_config(),
            )
        except Exception:
            receipt = {"schema": MCP_SCHEMA, "status": "BLOCKED",
                       "reason": "LOCAL_VERIFIER_FAILED_CLOSED",
                       "approved_to_start": False, "approved_to_dispatch": False,
                       "task_completed": False}
        if type(receipt) is not dict:
            receipt = {"schema": MCP_SCHEMA, "status": "BLOCKED",
                       "reason": "INVALID_LOCAL_RECEIPT",
                       "approved_to_start": False, "approved_to_dispatch": False,
                       "task_completed": False}
        return _result(request_id, {
            "content": [{"type": "text", "text": json.dumps(receipt, ensure_ascii=True, sort_keys=True)}],
            "isError": receipt.get("status") == "BLOCKED",
        })
    return _error(request_id, -32601, "METHOD_NOT_ALLOWLISTED")


def run_stdio() -> int:
    """No stdout except valid JSON-RPC; no local network sockets."""
    while True:
        data = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
        if not data:
            return 0
        if len(data) > MAX_REQUEST_BYTES:
            response = _error(None, -32600, "REQUEST_TOO_LARGE")
        else:
            try:
                message = json.loads(data.decode("utf-8"))
            except (ValueError, UnicodeError):
                response = _error(None, -32700, "INVALID_JSON")
            else:
                response = dispatch(message)
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":"), ensure_ascii=True) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(run_stdio())
