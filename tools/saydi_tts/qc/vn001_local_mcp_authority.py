"""Fresh GitHub-main SAYDI SOT read gate for one local H4 inventory request.

No task dispatcher, worker activation, local write, fallback cache or SOT edit.
The only allowed network destination is the pinned GitHub API repo on HTTPS.
A missing/changed/unreadable SOT MUST block local inventory even when Owner STOP
permits independent non-actuating observation.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from urllib.request import Request, HTTPRedirectHandler, build_opener

SCHEMA = "MAGASIN_SAYDI_VN001_VERIFIED_MAIN_V1"
REPOSITORY = "magasincoffee/magasin-media-robot"
SOT_PATH = "00_PROJECT/SOURCE_OF_TRUTH.md"
TASK_ID = "SAYDI002-VN-001"
SHA = re.compile(r"^[a-f0-9]{40}$")
API = "https://api.github.com/repos/" + REPOSITORY
MAX_JSON_BYTES = 300_000
MAX_SOT_BYTES = 180_000
ANCHOR = "### Sole authorized SAYDI-002 local VieNeu queue (migrated from retired temporary SOT)"
END = "**Existing evidence (not closure):**"


class VerificationHold(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise VerificationHold("GITHUB_REDIRECT_REJECTED")


def _read_json_https(url: str, *, opener=None, token: str | None = None) -> dict:
    # This function deliberately accepts only two endpoint shapes.
    if not (
        url == API + "/commits/main" or
        re.fullmatch(re.escape(API + "/contents/" + SOT_PATH + "?ref=") + r"[a-f0-9]{40}", url)
    ):
        raise VerificationHold("URL_NOT_ALLOWLISTED")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "SAYDI-VN001-ReadOnly-SOT/1.0",
    }
    if token is not None:
        if type(token) is not str or not (8 <= len(token) <= 2048) or "\n" in token or "\r" in token:
            raise VerificationHold("TOKEN_INVALID")
        headers["Authorization"] = "Bearer " + token
    req = Request(url, headers=headers, method="GET")
    transport = opener or build_opener(NoRedirect())
    try:
        with transport.open(req, timeout=8) as response:
            if response.status != 200 or response.geturl() != url:
                raise VerificationHold("GITHUB_ORIGIN_OR_STATUS_INVALID")
            raw = response.read(MAX_JSON_BYTES + 1)
    except (OSError, ValueError) as exc:
        raise VerificationHold("GITHUB_UNAVAILABLE") from exc
    if len(raw) > MAX_JSON_BYTES:
        raise VerificationHold("GITHUB_RESPONSE_OVERSIZED")
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise VerificationHold("GITHUB_JSON_INVALID") from exc
    if type(result) is not dict:
        raise VerificationHold("GITHUB_JSON_NOT_OBJECT")
    return result


def verify_current_main(
    *,
    expected_sha: str,
    fetch_json=None,
    token: str | None = None,
) -> dict:
    """Verify pinned main->contents->same main with no stale-cache acceptance.

    fetch_json is ONLY for offline unit tests or an independently trusted
    transport library supplied by the host, never exposed to request clients.
    """
    if type(expected_sha) is not str or not SHA.fullmatch(expected_sha):
        raise VerificationHold("EXPECTED_MAIN_SHA_INVALID")
    if fetch_json is None:
        get = lambda url: _read_json_https(url, token=token)
    else:
        get = fetch_json
    try:
        before = get(API + "/commits/main")
        if type(before) is not dict or before.get("sha") != expected_sha:
            raise VerificationHold("MAIN_SHA_CHANGED")
        raw = get(API + "/contents/" + SOT_PATH + "?ref=" + expected_sha)
        if (type(raw) is not dict or raw.get("type") != "file" or
                raw.get("path") != SOT_PATH or raw.get("encoding") != "base64" or
                type(raw.get("content")) is not str or
                type(raw.get("sha")) is not str or
                SHA.fullmatch(raw["sha"]) is None):
            raise VerificationHold("SOT_METADATA_UNTRUSTED")
        try:
            data = base64.b64decode(raw["content"].replace("\n", ""), validate=True)
            text = data.decode("utf-8-sig")
        except (ValueError, UnicodeError) as exc:
            raise VerificationHold("SOT_CONTENT_INVALID") from exc
        if len(data) < 1000 or len(data) > MAX_SOT_BYTES:
            raise VerificationHold("SOT_SIZE_OUT_OF_BOUNDS")
        blob_sha = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        if blob_sha != raw["sha"]:
            raise VerificationHold("SOT_BLOB_HASH_MISMATCH")
        after = get(API + "/commits/main")
        if type(after) is not dict or after.get("sha") != expected_sha:
            raise VerificationHold("MAIN_DIVERGED")
    except VerificationHold:
        raise
    except Exception as exc:
        raise VerificationHold("GITHUB_VERIFIER_UNAVAILABLE") from exc

    # Text checks are newline-agnostic. Cryptographic evidence above always
    # uses the exact raw GitHub bytes, never this normalized text.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("# SAYDI Audiobook — Source of Truth\n"):
        raise VerificationHold("SOT_CANONICAL_HEADER_MISSING")
    if (text.count(ANCHOR) != 1 or text.count(END) < 1 or
            text.count("## OWNER LOCK — ONE SAYDI SOURCE OF TRUTH") != 1):
        raise VerificationHold("SOT_AUTHORITY_AMBIGUOUS")
    queue = text.split(ANCHOR, 1)[1].split(END, 1)[0]
    row = r"^\| \*\*SAYDI002-VN-001\*\* \| \*\*IN_PROGRESS / active\*\* \|"
    if not re.search(row, queue, re.M):
        raise VerificationHold("SOT_TASK_NOT_IN_PROGRESS")
    if "**Authoritative selected task remains `SAYDI-002 = NEXT`" not in text:
        raise VerificationHold("SOT_PARENT_TASK_NOT_CURRENT")
    if "Supervisor SOT is independent" not in text:
        raise VerificationHold("SOT_CROSS_PROJECT_BOUNDARY_MISSING")
    return {
        "schema": SCHEMA,
        "verified_exact_main": True,
        "repository": REPOSITORY,
        "sot_path": SOT_PATH,
        "main_sha": expected_sha,
        "github_blob_sha": raw["sha"],
        "sot_content_sha256": hashlib.sha256(data).hexdigest(),
        "active_task_id": TASK_ID,
        "task_status": "IN_PROGRESS",
        "production_dispatch_authorized": False,
        "worker_started": False,
        "owner_start_verified": False,
        "task_completed": False,
    }
