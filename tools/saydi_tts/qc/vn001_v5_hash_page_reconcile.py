"""SAYDI002-VN-001: pure OFFLINE reconciliation of bounded V5 SHA pages.

Cannot read local files, launch VieNeu/Whisper, issue MCP requests, mutate
checkpoints, authorize H4 scanning or establish an approved narrator.
Receipts remain untrusted until independently bound to H4/Owner/SOT.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "saydi-vn001-v5-readonly-inventory-v1"
RESULT_SCHEMA = "saydi-vn001-v5-hash-page-reconciliation-v1"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
ANON = re.compile(r"[0-9a-f]{16}\Z")
MAX_CANDIDATES = 5000
MAX_PAGE_HASHES = 32
MAX_PAGE_BYTES = 256 * 1024 * 1024
SCOPES = frozenset({"audio", "narrator", "checkpoint", "model"})


class ReconciliationHold(ValueError):
    """Fixed status codes only: no file paths, tokens or private text."""


def _natural(value: Any, bound: int | None = None) -> bool:
    return type(value) is int and value >= 0 and (bound is None or value <= bound)


def _identity(receipt: Mapping[str, Any], mode: str) -> tuple[str, int, int, str, tuple]:
    if (type(receipt) is not dict or receipt.get("schema") != SCHEMA or
            receipt.get("mode") != mode or receipt.get("scope") not in SCOPES):
        raise ReconciliationHold("RECEIPT_SCHEMA_OR_MODE_INVALID")
    count = receipt.get("candidate_files")
    size = receipt.get("candidate_bytes")
    fp = receipt.get("metadata_fingerprint_sha256")
    kinds = receipt.get("kinds")
    if (not _natural(count, MAX_CANDIDATES) or not _natural(size) or
            type(fp) is not str or SHA256.fullmatch(fp) is None or
            type(kinds) is not dict or set(kinds) - SCOPES or
            any(not _natural(value, MAX_CANDIDATES) for value in kinds.values()) or
            sum(kinds.values()) != count):
        raise ReconciliationHold("RECEIPT_IDENTITY_INVALID")
    return receipt["scope"], count, size, fp, tuple(sorted(kinds.items()))


def reconcile_pages(metadata: dict[str, Any], pages: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Check only receipt continuity, never touch the files these describe.

    Matched SHA pages are NOT proof that V5 files exist, are approved, or
    belong to the expected worker/voice/Owner lifecycle generation.
    """
    expected = _identity(metadata, "metadata")
    scope, count, expected_bytes, fingerprint, _kinds = expected
    if (type(metadata.get("hash_batch_offset")) is not int or
            metadata["hash_batch_offset"] != 0 or
            metadata.get("complete_file_hash_inventory") is not False or
            metadata.get("source_and_audio_changed") is not False or
            metadata.get("worker_started") is not False or
            metadata.get("approved_to_start") is not False or
            metadata.get("approved_to_dispatch") is not False):
        raise ReconciliationHold("METADATA_READONLY_POLICY_INVALID")
    if count == 0:
        raise ReconciliationHold("NO_V5_HASH_CANDIDATES_TO_RECONCILE")
    if (not isinstance(pages, (tuple, list)) or len(pages) == 0 or
            len(pages) > count):
        raise ReconciliationHold("HASH_PAGE_LIST_INVALID")

    offset = 0
    seen: set[str] = set()
    hashed_bytes = 0
    for page in pages:
        if offset == count:
            raise ReconciliationHold("HASH_PAGE_AFTER_FINAL")
        if _identity(page, "hash") != expected:
            raise ReconciliationHold("HASH_PAGE_METADATA_DRIFT")
        batch = page.get("individual_hashes")
        batch_size = page.get("hashed_files")
        if (not isinstance(batch, list) or not _natural(batch_size, MAX_PAGE_HASHES)
                or len(batch) != batch_size or batch_size == 0):
            raise ReconciliationHold("HASH_PAGE_EMPTY_OR_INVALID")
        if (not _natural(page.get("hash_batch_offset"), MAX_CANDIDATES) or
                page["hash_batch_offset"] != offset):
            raise ReconciliationHold("HASH_PAGE_MISSING_REPLAY_OR_OUT_OF_ORDER")
        if (page.get("hash_blocked_reason") is not None or
                page.get("source_and_audio_changed") is not False or
                page.get("production_modified") is not False or
                page.get("worker_started") is not False or
                page.get("approved_to_start") is not False or
                page.get("approved_to_dispatch") is not False or
                page.get("complete_file_hash_inventory") is not (offset == 0 and offset + batch_size == count) or
                type(page.get("unhashed_files")) is not int or
                page["unhashed_files"] != count - batch_size):
            raise ReconciliationHold("HASH_PAGE_POLICY_OR_BLOCKER_INVALID")
        page_bytes = 0
        for file in batch:
            if type(file) is not dict or set(file) != {"anonymous_file_id", "bytes", "sha256"}:
                raise ReconciliationHold("HASH_ENTRY_SHAPE_INVALID")
            file_id, digest, size = file["anonymous_file_id"], file["sha256"], file["bytes"]
            if (type(file_id) is not str or ANON.fullmatch(file_id) is None or
                    type(digest) is not str or SHA256.fullmatch(digest) is None or
                    not _natural(size, MAX_PAGE_BYTES)):
                raise ReconciliationHold("HASH_ENTRY_INVALID")
            if file_id in seen:
                raise ReconciliationHold("HASH_ENTRY_REPLAY_OR_COLLISION")
            seen.add(file_id)
            page_bytes += size
        if page_bytes > MAX_PAGE_BYTES:
            raise ReconciliationHold("HASH_PAGE_BYTE_BUDGET_EXCEEDED")
        hashed_bytes += page_bytes
        offset += batch_size
        end = offset == count
        next_offset = page.get("next_hash_offset")
        if (offset > count or page.get("hash_page_final") is not end or
                (next_offset is not None and type(next_offset) is not int) or
                next_offset != (None if end else offset)):
            raise ReconciliationHold("HASH_PAGE_NEXT_OFFSET_INVALID")
    if offset != count or hashed_bytes != expected_bytes:
        raise ReconciliationHold("HASH_PAGES_INCOMPLETE_OR_BYTES_DRIFT")
    return {
        "schema": RESULT_SCHEMA, "task_id": "SAYDI002-VN-001",
        "status": "HASH_PAGES_RECONCILED_UNATTESTED", "scope": scope,
        "file_count": count, "page_count": len(pages),
        "hashed_bytes": hashed_bytes, "metadata_fingerprint_sha256": fingerprint,
        "approved_v5_asset_set_verified": False,
        "checkpoint_ownership_verified": False, "narrator_identity_verified": False,
        "owner_authorization_verified": False, "live_h4_inventory_verified": False,
        "v6_step_1_1_done": False, "approved_to_dispatch": False,
        "approved_to_start": False, "production_modified": False,
    }
