"""SAYDI002-VN-001: OFFLINE inspection of untrusted GitHub Issue requests.

This module deliberately has NO GitHub client, no local file access, no
dispatch, no credential handling and no Owner authorization implementation.
A syntactically valid Issue is still NOT an approved H4 operation.
"""
from __future__ import annotations

import json
import re
from typing import Any

SCHEMA = "MAGASIN_SAYDI_VN001_GITHUB_RELAY_REQUEST_V1"
RESULT_SCHEMA = "MAGASIN_SAYDI_VN001_GITHUB_RELAY_PREFLIGHT_V1"
REPO = "magasincoffee/magasin-media-robot"
TASK = "SAYDI002-VN-001"
OWNER_LOGIN = "magasincoffee"
OWNER_ACCOUNT_ID = 191064507  # An untrusted payload may claim this; not proof.
SHA = re.compile(r"[0-9a-f]{40}\Z")
ROOT_KEY = re.compile(r"[a-z0-9_-]{1,40}\Z")
ISSUE_URL = re.compile(
    r"https://github[.]com/magasincoffee/magasin-media-robot/issues/([1-9][0-9]*)\Z"
)
REPO_API = "https://api.github.com/repos/" + REPO
BODY_FIELDS = frozenset({
    "schema", "task_id", "target", "action", "root_key", "scope",
    "mode", "expected_main_sha",
})
SCOPE = frozenset({"audio", "narrator", "checkpoint", "model"})
MAX_BODY_BYTES = 1024


class RelayHold(ValueError):
    """Fixed error tokens only. Never echo Issue body or private content."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    item = {}
    for key, value in pairs:
        if key in item:
            raise ValueError("DUPLICATE_KEY")
        item[key] = value
    return item


def inspect_untrusted_issue(issue: Any, *, expected_main_sha: str) -> dict[str, Any]:
    """Inspect an *untrusted*, caller-provided Issue snapshot, not GitHub auth.

    Regardless of result this helper NEVER allows local read/dispatch.
    Future real use needs a separate live authenticated GitHub fetch, verified
    issue-bound one-shot Owner approval, replay/STOP/SOT/host root witnesses
    and an independently reviewed, authorized H4 read-only handler.
    """
    deny = {
        "schema": RESULT_SCHEMA,
        "task_id": TASK,
        "status": "BLOCKED",
        "reason": "UNTRUSTED_ISSUE",
        "request_shape_valid": False,
        "github_identity_authenticated": False,
        "owner_issue_approval_verified": False,
        "replay_and_stop_verified": False,
        "sot_main_verified": False,
        "h4_mcp_transport_qualified": False,
        "can_read_v5": False,
        "approved_to_dispatch": False,
        "approved_to_start": False,
        "task_completed": False,
        "production_modified": False,
    }
    try:
        if type(expected_main_sha) is not str or SHA.fullmatch(expected_main_sha) is None:
            raise RelayHold("MAIN_COMMIT_UNVERIFIED")
        if type(issue) is not dict or issue.get("repository_url") != REPO_API:
            raise RelayHold("ISSUE_REPOSITORY_INVALID")
        if (type(issue.get("id")) is not int or issue["id"] <= 0 or
                type(issue.get("number")) is not int or issue["number"] <= 0 or
                issue.get("state") != "open" or "pull_request" in issue):
            raise RelayHold("ISSUE_NOT_OPEN_REQUEST")
        url = issue.get("html_url")
        if type(url) is not str or len(url) > 170 or (match := ISSUE_URL.fullmatch(url)) is None:
            raise RelayHold("ISSUE_URL_INVALID")
        if int(match.group(1)) != issue["number"]:
            raise RelayHold("ISSUE_URL_NUMBER_MISMATCH")
        issuer = issue.get("user")
        if (type(issuer) is not dict or
                type(issuer.get("id")) is not int or
                issuer["id"] != OWNER_ACCOUNT_ID or
                issuer.get("login") != OWNER_LOGIN or
                issuer.get("type") != "User"):
            raise RelayHold("ISSUE_CLAIMED_OWNER_MISMATCH")
        body = issue.get("body")
        if (type(body) is not str or
                len(body.encode("utf-8")) > MAX_BODY_BYTES):
            raise RelayHold("ISSUE_BODY_INVALID")
        try:
            command = json.loads(body, object_pairs_hook=_reject_duplicate_keys)
        except (ValueError, UnicodeError):
            raise RelayHold("ISSUE_BODY_INVALID") from None
        if type(command) is not dict or set(command) != BODY_FIELDS:
            raise RelayHold("ISSUE_REQUEST_FIELDS_INVALID")
        if (command["schema"] != SCHEMA or command["task_id"] != TASK or
                command["target"] != "saydi" or
                command["action"] != "inventory_v5_readonly" or
                command["mode"] != "metadata" or
                type(command["scope"]) is not str or command["scope"] not in SCOPE or
                type(command["root_key"]) is not str or
                ROOT_KEY.fullmatch(command["root_key"]) is None or
                command["expected_main_sha"] != expected_main_sha):
            raise RelayHold("ISSUE_REQUEST_NOT_ALLOWLISTED")
        # This does NOT authenticate sender or authorize H4; even API response
        # metadata can be caller-forged until fetched by a trusted verifier.
        return {
            **deny, "status": "PREFLIGHT_SHAPE_ONLY_UNATTESTED",
            "reason": "NEEDS_INDEPENDENT_GITHUB_OWNER_STOP_SOT_PROOF",
            "request_shape_valid": True,
        }
    except RelayHold as error:
        return {**deny, "reason": str(error)}
