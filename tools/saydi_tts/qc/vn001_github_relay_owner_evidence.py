"""SAYDI002-VN-001: bounded HTTPS GitHub Owner intent observation ONLY.

The read-only observation can verify that live GitHub API metadata relates an
Owner-authored Issue to a separate Owner-authored, exact-body-bound comment.
It does NOT authorize local V5 files, dispatch, START, STOP or replay clearance.
No private manuscripts, audio or raw Issue text enter its receipts.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any
from urllib.request import HTTPRedirectHandler, Request, build_opener

from tools.saydi_tts.qc.vn001_github_relay_preflight import (
    OWNER_ACCOUNT_ID, OWNER_LOGIN, REPO_API, TASK, inspect_untrusted_issue,
)

SCHEMA = "MAGASIN_SAYDI_VN001_GITHUB_OWNER_EVIDENCE_V1"
APPROVAL_SCHEMA = "MAGASIN_SAYDI_VN001_OWNER_READONLY_APPROVAL_V1"
SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
NONCE = re.compile(r"[0-9a-f]{32}\Z")
MAX_HTTP_BODY = 16_384
API = REPO_API


class EvidenceHold(ValueError):
    """Public fixed failure code, never a private body or exception detail."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise EvidenceHold("GITHUB_REDIRECT_HOLD")


def _read_live_json(url: str, *, token: str | None = None, opener=None) -> dict:
    if not re.fullmatch(
        re.escape(API) + r"/(?:git/ref/heads/main|issues/[1-9][0-9]*|issues/comments/[1-9][0-9]*)",
        url,
    ):
        raise EvidenceHold("GITHUB_ENDPOINT_NOT_ALLOWED")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "SAYDI-VN001-Owner-ReadOnly/1.0",
    }
    if token is not None:
        if type(token) is not str or not (8 <= len(token) <= 2048) or any(
            x in token for x in ("\r", "\n", "\x00")
        ):
            raise EvidenceHold("GITHUB_TOKEN_INVALID")
        headers["Authorization"] = "Bearer " + token
    try:
        req = Request(url, method="GET", headers=headers)
        with (opener if opener is not None else build_opener(_NoRedirect())).open(
            req, timeout=8
        ) as response:
            if response.status != 200 or response.geturl() != url:
                raise EvidenceHold("GITHUB_ORIGIN_OR_STATUS_INVALID")
            raw = response.read(MAX_HTTP_BODY + 1)
    except EvidenceHold:
        raise
    except (OSError, ValueError, TimeoutError):
        raise EvidenceHold("GITHUB_UNAVAILABLE") from None
    if len(raw) > MAX_HTTP_BODY:
        raise EvidenceHold("GITHUB_JSON_OVERSIZED")
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise EvidenceHold("GITHUB_JSON_INVALID") from None
    if type(parsed) is not dict:
        raise EvidenceHold("GITHUB_JSON_NOT_OBJECT")
    return parsed


def _utc(value: Any) -> datetime:
    if type(value) is not str or not re.fullmatch(
        r"20[0-9]{2}-(?:0[1-9]|1[0-2])-(?:[0-2][0-9]|3[01])T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]Z",
        value,
    ):
        raise EvidenceHold("GITHUB_TIMESTAMP_INVALID")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise EvidenceHold("GITHUB_TIMESTAMP_INVALID") from None


def _owner(user: Any) -> bool:
    return (
        type(user) is dict
        and type(user.get("id")) is int
        and user["id"] == OWNER_ACCOUNT_ID
        and user.get("login") == OWNER_LOGIN
        and user.get("type") == "User"
    )


def _pinned_sha(record: Any, expected: str) -> bool:
    if type(record) is not dict or record.get("ref") != "refs/heads/main":
        return False
    obj = record.get("object")
    return (
        type(obj) is dict
        and obj.get("type") == "commit"
        and type(obj.get("sha")) is str
        and obj["sha"] == expected
    )


def observe_owner_readonly_intent(
    *,
    issue_number: int,
    approval_comment_id: int,
    expected_main_sha: str,
    token: str | None = None,
    fetch_json=None,
) -> dict[str, Any]:
    """Read bounded GitHub API snapshots; return NON-ACTUATING intent evidence.

    fetch_json is restricted to synthetic fixtures. Production source has its
    own HTTPS client with the single hardcoded GitHub repository origin.
    Even live identity and intent evidence require a separate independently
    authenticated one-shot H4 STOP/replay/host/root gate before V5 access.
    """
    if (
        type(issue_number) is not int or not (1 <= issue_number <= 2_147_483_647)
        or type(approval_comment_id) is not int
        or not (1 <= approval_comment_id <= 9_223_372_036_854_775_807)
        or type(expected_main_sha) is not str
        or SHA.fullmatch(expected_main_sha) is None
    ):
        raise EvidenceHold("ISSUE_APPROVAL_ARGUMENTS_INVALID")

    issue_url = API + "/issues/" + str(issue_number)
    approval_url = API + "/issues/comments/" + str(approval_comment_id)
    main_url = API + "/git/ref/heads/main"
    get = (
        (lambda url: _read_live_json(url, token=token))
        if fetch_json is None else fetch_json
    )
    try:
        first_main = get(main_url)
        first_issue = get(issue_url)
        approval = get(approval_url)
        second_issue = get(issue_url)
        confirmed_approval = get(approval_url)
        last_main = get(main_url)
    except EvidenceHold:
        raise
    except Exception:
        raise EvidenceHold("GITHUB_FETCH_UNAVAILABLE") from None
    if not (_pinned_sha(first_main, expected_main_sha)
            and _pinned_sha(last_main, expected_main_sha)):
        raise EvidenceHold("GITHUB_MAIN_DRIFT")
    if type(first_issue) is not dict or type(second_issue) is not dict:
        raise EvidenceHold("ISSUE_API_SHAPE_INVALID")
    if type(approval) is not dict or type(confirmed_approval) is not dict:
        raise EvidenceHold("APPROVAL_API_SHAPE_INVALID")
    if approval != confirmed_approval:
        raise EvidenceHold("APPROVAL_CHANGED_DURING_OBSERVATION")

    # Match the complete relevant immutable approval subject before and after
    # observing the comment. An edited/closed Issue cannot silently pass.
    fixed = (
        "id", "number", "repository_url", "html_url", "state", "user", "body",
        "created_at", "updated_at",
    )
    if any(first_issue.get(x) != second_issue.get(x) for x in fixed):
        raise EvidenceHold("ISSUE_CHANGED_DURING_OBSERVATION")
    shape = inspect_untrusted_issue(first_issue, expected_main_sha=expected_main_sha)
    if shape["status"] != "PREFLIGHT_SHAPE_ONLY_UNATTESTED":
        raise EvidenceHold("ISSUE_PREFLIGHT_NOT_QUALIFIED")
    if (first_issue.get("number") != issue_number
            or not _owner(first_issue.get("user"))):
        raise EvidenceHold("ISSUE_OWNER_NOT_OBSERVED")

    if (type(approval) is not dict
            or type(approval.get("id")) is not int
            or approval["id"] != approval_comment_id
            or approval.get("issue_url") != issue_url
            or approval.get("html_url") !=
            "https://github.com/magasincoffee/magasin-media-robot/issues/"
            + str(issue_number) + "#issuecomment-" + str(approval_comment_id)
            or not _owner(approval.get("user"))):
        raise EvidenceHold("APPROVAL_OWNER_OR_ISSUE_MISMATCH")
    issued = _utc(first_issue.get("created_at"))
    created = _utc(approval.get("created_at"))
    edited = _utc(approval.get("updated_at"))
    if created < issued or edited != created:
        raise EvidenceHold("APPROVAL_TIMESTAMP_OR_EDIT_INVALID")

    raw_body = first_issue.get("body")
    approval_body = approval.get("body")
    if type(raw_body) is not str or type(approval_body) is not str:
        raise EvidenceHold("APPROVAL_BODY_INVALID")
    try:
        issue_hash = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()
        approval_bytes = approval_body.encode("utf-8")
    except UnicodeError:
        raise EvidenceHold("APPROVAL_BODY_INVALID") from None
    if len(approval_bytes) > 1024:
        raise EvidenceHold("APPROVAL_BODY_INVALID")
    try:
        intent = json.loads(
            approval_body,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (ValueError, UnicodeError):
        raise EvidenceHold("APPROVAL_BODY_INVALID") from None
    required = {
        "schema", "task_id", "action", "issue_number", "issue_id",
        "expected_main_sha", "issue_body_sha256", "one_shot_nonce",
        "read_only_metadata_only",
    }
    if type(intent) is not dict or set(intent) != required:
        raise EvidenceHold("APPROVAL_FIELDS_INVALID")
    if (
        intent["schema"] != APPROVAL_SCHEMA
        or intent["task_id"] != TASK
        or intent["action"] != "inventory_v5_readonly"
        or type(intent["issue_number"]) is not int
        or intent["issue_number"] != issue_number
        or type(intent["issue_id"]) is not int
        or intent["issue_id"] != first_issue["id"]
        or intent["expected_main_sha"] != expected_main_sha
        or type(intent["issue_body_sha256"]) is not str
        or DIGEST.fullmatch(intent["issue_body_sha256"]) is None
        or intent["issue_body_sha256"] != issue_hash
        or type(intent["one_shot_nonce"]) is not str
        or NONCE.fullmatch(intent["one_shot_nonce"]) is None
        or intent["read_only_metadata_only"] is not True
    ):
        raise EvidenceHold("APPROVAL_INTENT_NOT_BOUND")

    return {
        "schema": SCHEMA,
        "task_id": TASK,
        "status": "OWNER_INTENT_MATCHED_NON_EXECUTABLE",
        "issue_number": issue_number,
        "issue_id": first_issue["id"],
        "approval_comment_id": approval_comment_id,
        "main_sha_observed": expected_main_sha,
        "issue_body_sha256": issue_hash,
        "approval_nonce_sha256": hashlib.sha256(intent["one_shot_nonce"].encode("ascii")).hexdigest(),
        "owner_claims_match": True,
        # Synthetic fetch functions do NOT prove HTTPS platform identity.
        "github_live_https_observed": fetch_json is None,
        "owner_one_shot_consumed": False,
        "owner_issue_approval_verified_for_h4": False,
        "h4_stop_generation_verified": False,
        "h4_root_identity_verified": False,
        "replay_guard_verified": False,
        "can_read_v5": False,
        "approved_to_dispatch": False,
        "approved_to_start": False,
        "worker_started": False,
        "task_completed": False,
        "production_modified": False,
    }


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, value in pairs:
        if key in values:
            raise ValueError("DUPLICATE_APPROVAL_KEY")
        values[key] = value
    return values
