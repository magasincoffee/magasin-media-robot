"""Offline strict stdio protocol and security tests for SAYDI tunnel MCP target."""
from __future__ import annotations
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SUT = Path(__file__).with_name("vn001_private_mcp_stdio.py")
spec = importlib.util.spec_from_file_location("vn001_mcp_stdio", SUT)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
SHA = "a" * 40
ARGS = {
    "schema": server.MCP_SCHEMA,
    "task_id": server.TASK_ID,
    "target": "saydi",
    "action": "inventory_v5_readonly",
    "root_key": "chapter2",
    "scope": "audio",
    "mode": "metadata",
    "hash_offset": 0,
    "expected_metadata_sha256": None,
    "expected_main_sha": SHA,
}

def message(method, **kwargs):
    return {"jsonrpc": "2.0", "id": 1, "method": method, **kwargs}


class StdioReadOnlyTests(unittest.TestCase):
    def test_one_exact_tool_and_read_only_annotation(self):
        tools = server.dispatch(message("tools/list"))["result"]["tools"]
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], server.TOOL)
        self.assertTrue(tools[0]["annotations"]["readOnlyHint"])
        self.assertFalse(tools[0]["annotations"]["destructiveHint"])
        self.assertEqual(set(tools[0]["inputSchema"]["required"]), server.FIELDS)
        self.assertFalse(tools[0]["inputSchema"]["additionalProperties"])

    def test_initialize_and_notification_without_job(self):
        r = server.dispatch(message("initialize"))
        self.assertEqual(r["result"]["capabilities"], {"tools": {"listChanged": False}})
        self.assertIsNone(server.dispatch({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertEqual(server.dispatch(message("ping"))["result"], {})

    def test_method_allowlist_refuses_file_and_shell(self):
        for method in ("resources/read", "sampling/createMessage", "shell/execute",
                       "prompts/get", "tools/execute", "jobs/dispatch"):
            self.assertEqual(server.dispatch(message(method))["error"]["code"], -32601)

    def test_tool_allowlist_blocks_extra_methods_or_fields(self):
        for args in ({**ARGS, "cmd": "powershell.exe"}, {**ARGS, "command": "stop"},
                     {**ARGS, "owner_start": True}):
            with self.subTest(args=args):
                r = server.dispatch(message(
                    "tools/call", params={"name": server.TOOL, "arguments": args}
                ))
                self.assertEqual(r["error"]["message"], "UNAUTHORIZED_TOOL_ARGUMENTS")

    def test_only_expected_tool_can_be_called(self):
        out = server.dispatch(message(
            "tools/call", params={"name": "saydi_start_worker", "arguments": ARGS}
        ))
        self.assertEqual(out["error"]["message"], "TOOL_NOT_ALLOWLISTED")

    def test_exact_readonly_result_no_start_or_done(self):
        calls = []
        def fake(req, **kwargs):
            calls.append((req, kwargs))
            return {"schema": server.MCP_SCHEMA, "status": "READ_ONLY_RECEIPT_UNATTESTED",
                    "approved_to_start": False, "approved_to_dispatch": False,
                    "task_completed": False}
        x = server.dispatch(
            message("tools/call", params={"name": server.TOOL, "arguments": ARGS}),
            inventory_call=fake, root_config={},
            trusted_transport_authenticated=True,
        )
        self.assertFalse(x["result"]["isError"])
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][1]["transport_authenticated"])
        self.assertEqual(calls[0][1]["locally_approved_roots"], {})
        self.assertFalse(json.loads(x["result"]["content"][0]["text"])["task_completed"])

    def test_stdin_alone_never_establishes_mcp_authentication(self):
        called = []
        def scanner(*args, **kwargs):
            called.append(True)
            raise AssertionError("SCANNER_MUST_NOT_RUN")
        result = server.dispatch(
            message("tools/call", params={"name": server.TOOL, "arguments": ARGS}),
            inventory_call=scanner, root_config={"chapter2": {"scope": "audio", "path": "C:/SAYDI"}},
        )
        self.assertEqual(called, [])
        self.assertTrue(result["result"]["isError"])
        payload = json.loads(result["result"]["content"][0]["text"])
        self.assertEqual(payload["reason"], "MCP_TRANSPORT_NOT_AUTHENTICATED")
        self.assertFalse(payload["approved_to_start"])
        self.assertFalse(payload["approved_to_dispatch"])

    def test_client_cannot_inject_trust_as_tool_argument(self):
        args = dict(ARGS, trusted_transport_authenticated=True)
        result = server.dispatch(message(
            "tools/call", params={"name": server.TOOL, "arguments": args}
        ))
        self.assertEqual(result["error"]["message"], "UNAUTHORIZED_TOOL_ARGUMENTS")

    def test_actual_stdio_valid_tool_call_fails_closed(self):
        requests = [message("initialize"), message("tools/call",
            params={"name": server.TOOL, "arguments": ARGS})]
        process = subprocess.run(
            [sys.executable, str(SUT)],
            input="\n".join(json.dumps(x) for x in requests) + "\n",
            capture_output=True, encoding="utf-8", timeout=8,
            env={**os.environ, server.ROOT_CONFIG_ENV: ""},
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        replies = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(len(replies), 2)
        self.assertTrue(replies[1]["result"]["isError"])
        receipt = json.loads(replies[1]["result"]["content"][0]["text"])
        self.assertEqual(receipt["reason"], "MCP_TRANSPORT_NOT_AUTHENTICATED")
        self.assertFalse(receipt["worker_started"])

    def test_unhandled_adapter_exception_redacted_and_blocked(self):
        def bad(*args, **kwargs):
            raise OSError("PRIVATE_PATH_C:/hidden")
        result = server.dispatch(
            message("tools/call", params={"name": server.TOOL, "arguments": ARGS}),
            inventory_call=bad
        )
        self.assertTrue(result["result"]["isError"])
        self.assertNotIn("PRIVATE_PATH", json.dumps(result))
        self.assertIn("LOCAL_VERIFIER_FAILED_CLOSED", json.dumps(result))

    def test_bad_root_env_not_dumped(self):
        with patch.dict(os.environ, {server.ROOT_CONFIG_ENV: '{"secret":{"path":"C:/Users", "scope":"audio"}}'}):
            self.assertEqual(server._read_local_root_config()["secret"]["path"], "C:/Users")
            # Config is only candidate; the separate local bridge enforces
            # the C:/SAYDI, D:/SAYDI canonical roots and host restriction.
        with patch.dict(os.environ, {server.ROOT_CONFIG_ENV: "not-json"}):
            self.assertEqual(server._read_local_root_config(), {})

    def test_stdio_piping_initialize_tool_list_invalid_request(self):
        requests = [
            message("initialize"),
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            message("tools/list"),
            message("tools/call", params={"name": "write_files", "arguments": ARGS}),
        ]
        process = subprocess.run(
            [sys.executable, str(SUT)],
            input="\n".join(json.dumps(x) for x in requests) + "\n",
            capture_output=True, encoding="utf-8", timeout=8,
            env={**os.environ, server.ROOT_CONFIG_ENV: ""},
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        responses = [json.loads(x) for x in process.stdout.splitlines()]
        self.assertEqual(len(responses), 3)
        self.assertEqual(responses[1]["result"]["tools"][0]["name"], server.TOOL)
        self.assertEqual(responses[-1]["error"]["message"], "TOOL_NOT_ALLOWLISTED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
