"""SAYDI V6 VN-001 durable project-grant / ordered read-page admission.

SOURCE/QA ONLY. Does not verify GitHub identity, read a file, bind a Windows
root, expose a network tool, grant START, or change H4 STOP. A *separately*
reviewed H4 host must supply fixed trusted callbacks, verified grant identity,
no-follow scanner, STOP-generation witness, and a host-owned journal path.
Never expose the callbacks, witness, journal path or scanner to a MCP caller.
"""
from __future__ import annotations
from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Callable

SCHEMA = "MAGASIN_SAYDI_V6_PROJECT_GRANT_READ_V1"
TASK = "SAYDI002-VN-001"
REPO = "magasincoffee/magasin-media-robot"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
OPAQUE = re.compile(r"[a-zA-Z0-9_.:-]{1,96}\Z")
GRANT_ID = re.compile(r"[a-f0-9]{32}\Z")
ROOT = re.compile(r"[a-z0-9_-]{1,40}\Z")
READ_SCOPES = frozenset(("checkpoint", "audio", "narrator", "model"))
MAX_OPS = 256


@dataclass(frozen=True)
class HostAttestation:
    """Host-produced proof descriptor; constructing this is NEVER authentication."""
    grant_id: str
    owner_id: int
    main_sha: str
    stop_generation: str
    root_key: str
    scope: str
    expires_epoch: int
    max_operations: int
    owner_identity_verified: bool
    project_grant_verified: bool
    main_verified: bool
    transport_verified: bool
    root_verified: bool
    stop_generation_verified: bool
    owner_stop_engaged: bool
    grant_not_revoked: bool


class Hold(Exception):
    pass


def _validate(a: Any, now_epoch: int) -> None:
    if type(a) is not HostAttestation:
        raise Hold("HOST_PROOF_MISSING")
    if not (
        type(a.grant_id) is str and GRANT_ID.fullmatch(a.grant_id)
        and type(a.owner_id) is int and a.owner_id > 0
        and type(a.main_sha) is str and SHA40.fullmatch(a.main_sha)
        and type(a.stop_generation) is str and OPAQUE.fullmatch(a.stop_generation)
        and type(a.root_key) is str and ROOT.fullmatch(a.root_key)
        and type(a.scope) is str and a.scope in READ_SCOPES
        and type(a.expires_epoch) is int and now_epoch < a.expires_epoch <= now_epoch + 86400 * 365
        and type(a.max_operations) is int and 1 <= a.max_operations <= MAX_OPS
    ):
        raise Hold("GRANT_SCOPE_OR_EXPIRY_INVALID")
    if not all(x is True for x in (
        a.owner_identity_verified, a.project_grant_verified, a.main_verified,
        a.transport_verified, a.root_verified, a.stop_generation_verified,
        a.owner_stop_engaged, a.grant_not_revoked,
    )):
        raise Hold("GRANT_STOP_OR_TRANSPORT_UNVERIFIED")


def _binding(a: HostAttestation) -> str:
    d = [SCHEMA, TASK, REPO, a.grant_id, a.owner_id, a.main_sha,
         a.stop_generation, a.root_key, a.scope, a.expires_epoch, a.max_operations]
    return hashlib.sha256(json.dumps(d, separators=(",", ":")).encode()).hexdigest()


def _journal(path: Path, a: HostAttestation, b: str, index: int, op_id: str,
             *, consume: bool) -> None:
    if (type(path) is not type(Path(".")) or not path.is_absolute()
            or not path.parent.is_dir() or path.is_symlink()):
        raise Hold("JOURNAL_HOST_PATH_UNQUALIFIED")
    try:
        with closing(sqlite3.connect(str(path), timeout=3, isolation_level=None)) as db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            if consume:
                db.execute("CREATE TABLE IF NOT EXISTS grants "
                           "(grant_id TEXT PRIMARY KEY, binding TEXT NOT NULL)")
                db.execute("CREATE TABLE IF NOT EXISTS child_reads "
                           "(grant_id TEXT NOT NULL, seq INTEGER NOT NULL, "
                           "op_id TEXT NOT NULL, state TEXT NOT NULL, "
                           "PRIMARY KEY(grant_id, seq), UNIQUE(grant_id, op_id))")
                current = db.execute("SELECT binding FROM grants WHERE grant_id=?",
                                     (a.grant_id,)).fetchone()
                if current is None:
                    db.execute("INSERT INTO grants VALUES (?,?)", (a.grant_id, b))
                elif current != (b,):
                    db.execute("ROLLBACK")
                    raise Hold("GRANT_BINDING_DRIFT")
                next_seq = db.execute("SELECT COUNT(*) FROM child_reads WHERE grant_id=?",
                                      (a.grant_id,)).fetchone()[0]
                if index != next_seq:
                    db.execute("ROLLBACK")
                    raise Hold("CHILD_OUT_OF_ORDER_OR_REPLAY")
                try:
                    db.execute("INSERT INTO child_reads VALUES (?,?,?,'CONSUMED')",
                               (a.grant_id, index, op_id))
                except sqlite3.IntegrityError:
                    db.execute("ROLLBACK")
                    raise Hold("CHILD_REPLAY_BLOCKED") from None
            else:
                current = db.execute("SELECT binding FROM grants WHERE grant_id=?",
                                     (a.grant_id,)).fetchone()
                child = db.execute(
                    "SELECT op_id,state FROM child_reads WHERE grant_id=? AND seq=?",
                    (a.grant_id, index),
                ).fetchone()
                if current != (b,) or child != (op_id, "CONSUMED"):
                    db.execute("ROLLBACK")
                    raise Hold("JOURNAL_WITNESS_CHANGED")
            db.execute("COMMIT")
    except Hold:
        raise
    except (sqlite3.Error, OSError):
        raise Hold("JOURNAL_UNAVAILABLE") from None


def _trusted_call(fn: Callable[[], Any]) -> Any:
    try:
        return fn()
    except BaseException:
        raise Hold("HOST_CALLBACK_FAILED") from None


def _sanitized_metadata(response: Any, a: HostAttestation) -> dict[str, Any]:
    try:
        if type(response) is not dict or any(type(k) is not str for k in response):
            raise ValueError()
        scope = response.get("scope")
        fp = response.get("metadata_fingerprint_sha256")
        count = response.get("candidate_files")
        byte_count = response.get("candidate_bytes")
        if (type(scope) is not str or scope != a.scope
                or type(fp) is not str or SHA64.fullmatch(fp) is None
                or type(count) is not int or not 0 <= count <= 5000
                or type(byte_count) is not int or byte_count < 0):
            raise ValueError()
        return {"scope": a.scope, "metadata_fingerprint_sha256": fp,
                "candidate_files": count, "candidate_bytes": byte_count}
    except BaseException:
        raise Hold("METADATA_UNQUALIFIED") from None


def read_project_grant_child(
    *, host_verify: Callable[[], HostAttestation],
    host_read_metadata: Callable[[], dict[str, Any]],
    host_journal: Path, child_index: int, child_id: str,
    host_now_epoch: Callable[[], int] | None = None,
) -> dict[str, Any]:
    """Reserve exactly one ordered child under standing V6 grant, then read.

    Each admitted child is consumed even if the callback fails. Never emits
    private paths, secrets, audio or an actionable START approval. The H4 host
    must serialize STOP/lifecycle changes with this transaction externally.
    """
    block = {"schema": SCHEMA, "task_id": TASK, "status": "BLOCKED",
             "field_accepted": False, "worker_started": False,
             "approved_to_start": False, "approved_to_dispatch": False,
             "production_modified": False, "task_completed": False}
    try:
        if not callable(host_verify) or not callable(host_read_metadata):
            raise Hold("HOST_CALLBACK_MISSING")
        if (type(child_index) is not int or not 0 <= child_index < MAX_OPS
                or type(child_id) is not str or GRANT_ID.fullmatch(child_id) is None):
            raise Hold("CHILD_REQUEST_INVALID")
        if not callable(host_now_epoch) and host_now_epoch is not None:
            raise Hold("CLOCK_UNQUALIFIED")
        def now() -> int:
            value = _trusted_call(host_now_epoch or (lambda: int(time.time())))
            if type(value) is not int:
                raise Hold("CLOCK_UNQUALIFIED")
            return value
        first = _trusted_call(host_verify)
        _validate(first, now())
        if child_index >= first.max_operations:
            raise Hold("CHILD_SCOPE_EXCEEDED")
        fingerprint = _binding(first)
        _journal(host_journal, first, fingerprint, child_index, child_id, consume=True)
        prior = _trusted_call(host_verify)
        _validate(prior, now())
        if prior != first:
            raise Hold("STOP_OR_GRANT_CHANGED")
        _journal(host_journal, first, fingerprint, child_index, child_id, consume=False)
        candidate = _trusted_call(host_read_metadata)
        after = _trusted_call(host_verify)
        _validate(after, now())
        if after != first:
            raise Hold("STOP_OR_GRANT_CHANGED")
        _journal(host_journal, first, fingerprint, child_index, child_id, consume=False)
        safe = _sanitized_metadata(candidate, first)
        return {**block, "status": "SOURCE_ONLY_CHILD_ACCEPTED_UNATTESTED",
                "grant_reusable_for_remaining_children": True,
                "child_consumed": True, "child_index": child_index,
                "metadata": safe}
    except Hold as e:
        allowed = frozenset((
            "HOST_PROOF_MISSING", "GRANT_SCOPE_OR_EXPIRY_INVALID",
            "GRANT_STOP_OR_TRANSPORT_UNVERIFIED", "JOURNAL_HOST_PATH_UNQUALIFIED",
            "JOURNAL_UNAVAILABLE", "GRANT_BINDING_DRIFT",
            "CHILD_OUT_OF_ORDER_OR_REPLAY", "CHILD_REPLAY_BLOCKED",
            "JOURNAL_WITNESS_CHANGED", "HOST_CALLBACK_FAILED",
            "METADATA_UNQUALIFIED", "HOST_CALLBACK_MISSING",
            "CHILD_REQUEST_INVALID", "CLOCK_UNQUALIFIED",
            "CHILD_SCOPE_EXCEEDED", "STOP_OR_GRANT_CHANGED",
        ))
        val = e.args[0] if type(e) is Hold and len(e.args) == 1 and type(e.args[0]) is str else None
        return {**block, "reason": val if val in allowed else "HOST_CALLBACK_FAILED"}
    except BaseException:
        return {**block, "reason": "HOST_CALLBACK_FAILED"}
