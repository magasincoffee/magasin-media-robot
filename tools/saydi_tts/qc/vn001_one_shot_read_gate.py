"""SAYDI002-VN-001 offline/source-only one-shot read transaction.

Not a registered MCP tool or live H4 authority. A separately accepted trusted
host must own verify/read callbacks, the journal path, Windows no-follow
traversal, and the lifecycle lock. Never accept them from an Issue/request.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

SCHEMA = "MAGASIN_SAYDI_VN001_ONESHOT_READ_V1"
INVENTORY_SCHEMA = "saydi-vn001-v5-readonly-inventory-v1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
NONCE = re.compile(r"[0-9a-f]{32}\Z")
OPAQUE = re.compile(r"[A-Za-z0-9_.:-]{1,96}\Z")
ROOT = re.compile(r"[a-z0-9_-]{1,40}\Z")
SCOPES = frozenset(("audio", "checkpoint", "narrator", "model"))

@dataclass(frozen=True)
class TrustedWitness:
    """Output of independently trusted host verifier, NOT user input."""
    issue_id: int
    approval_id: int
    nonce: str
    main_sha: str
    stop_generation: str
    root_key: str
    scope: str
    owner_verified: bool
    approval_verified: bool
    exact_main_verified: bool
    transport_verified: bool
    root_verified: bool
    stop_generation_verified: bool
    owner_stop_engaged: bool

class GateHold(Exception):
    pass

def validate(w: Any) -> None:
    if type(w) is not TrustedWitness:
        raise GateHold("TRUSTED_WITNESS_MISSING")
    if (type(w.issue_id) is not int or w.issue_id < 1
        or type(w.approval_id) is not int or w.approval_id < 1
        or type(w.nonce) is not str or NONCE.fullmatch(w.nonce) is None
        or type(w.main_sha) is not str or SHA40.fullmatch(w.main_sha) is None
        or type(w.stop_generation) is not str or OPAQUE.fullmatch(w.stop_generation) is None
        or type(w.root_key) is not str or ROOT.fullmatch(w.root_key) is None
        or type(w.scope) is not str or w.scope not in SCOPES):
        raise GateHold("IDENTITY_INVALID")
    if not all(value is True for value in (
        w.owner_verified, w.approval_verified, w.exact_main_verified,
        w.transport_verified, w.root_verified, w.stop_generation_verified,
        w.owner_stop_engaged,
    )):
        raise GateHold("OWNER_STOP_OR_ROOT_UNVERIFIED")

def binding(w: TrustedWitness) -> str:
    parts = [w.issue_id, w.approval_id, w.nonce, w.main_sha,
             w.stop_generation, w.root_key, w.scope]
    return hashlib.sha256(json.dumps(parts, separators=(",", ":")).encode()).hexdigest()

def _journal(path: Path, w: TrustedWitness, digest: str, *, consume: bool) -> None:
    if not isinstance(path, Path) or not path.is_absolute() or not path.parent.is_dir():
        raise GateHold("JOURNAL_PATH_UNQUALIFIED")
    try:
        with closing(sqlite3.connect(str(path), timeout=3, isolation_level=None)) as db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            if consume:
                db.execute("CREATE TABLE IF NOT EXISTS used "
                           "(nonce TEXT PRIMARY KEY, approval INTEGER UNIQUE NOT NULL, "
                           "digest TEXT NOT NULL, state TEXT NOT NULL)")
                try:
                    db.execute("INSERT INTO used VALUES (?,?,?,'CONSUMED')",
                               (w.nonce, w.approval_id, digest))
                except sqlite3.IntegrityError:
                    db.execute("ROLLBACK")
                    raise GateHold("APPROVAL_ALREADY_CONSUMED") from None
            else:
                row = db.execute("SELECT approval,digest,state FROM used WHERE nonce=?",
                                 (w.nonce,)).fetchone()
                if row != (w.approval_id, digest, "CONSUMED"):
                    db.execute("ROLLBACK")
                    raise GateHold("JOURNAL_CHANGED_DURING_READ")
            db.execute("COMMIT")
    except GateHold:
        raise
    except (sqlite3.Error, OSError):
        raise GateHold("JOURNAL_UNAVAILABLE") from None

def _sanitize(data: Any, expected_scope: str) -> dict[str, Any]:
    if type(data) is not dict or data.get("schema") != INVENTORY_SCHEMA or data.get("scope") != expected_scope:
        raise GateHold("INVENTORY_RECEIPT_INVALID")
    n, total, fingerprint = (data.get("candidate_files"),
                             data.get("candidate_bytes"), data.get("metadata_fingerprint_sha256"))
    if (type(n) is not int or not 0 <= n <= 5000 or type(total) is not int or total < 0
        or type(fingerprint) is not str or SHA64.fullmatch(fingerprint) is None
        or data.get("mode") != "metadata" or data.get("individual_hashes") != []
        or data.get("hash_batch_offset") != 0):
        raise GateHold("INVENTORY_RECEIPT_INVALID")
    return {"schema": INVENTORY_SCHEMA, "scope": expected_scope,
            "candidate_files": n, "candidate_bytes": total,
            "metadata_fingerprint_sha256": fingerprint}

def guarded_read_once(
    *, trusted_verify: Callable[[], TrustedWitness],
    trusted_read_metadata: Callable[[], dict[str, Any]],
    trusted_journal_path: Path,
) -> dict[str, Any]:
    """Debit approval before reading; suppress receipts after any witness drift.

    This component can only return source/QA evidence. It grants no H4 field
    permission; a reviewed on-host binding is still required before use.
    """
    denied = {"schema": SCHEMA, "task_id": "SAYDI002-VN-001",
              "status": "BLOCKED", "approved_to_start": False,
              "approved_to_dispatch": False, "worker_started": False,
              "production_modified": False, "task_completed": False}
    try:
        if not callable(trusted_verify) or not callable(trusted_read_metadata):
            raise GateHold("TRUSTED_CALLBACKS_MISSING")
        before = trusted_verify()
        validate(before)
        digest = binding(before)
        _journal(trusted_journal_path, before, digest, consume=True)
        # Check immediately before protected metadata read, not just approval.
        pre = trusted_verify()
        validate(pre)
        if pre != before:
            raise GateHold("WITNESS_CHANGED")
        _journal(trusted_journal_path, before, digest, consume=False)
        candidate = trusted_read_metadata()
        # Check immediately after protected read and BEFORE releasing receipt.
        after = trusted_verify()
        validate(after)
        if after != before:
            raise GateHold("WITNESS_CHANGED")
        _journal(trusted_journal_path, before, digest, consume=False)
        clean = _sanitize(candidate, before.scope)
        return {**denied, "status": "SOURCE_ONLY_READ_UNATTESTED",
                "one_shot_consumed": True, "field_accepted": False,
                "metadata": clean}
    except GateHold as exc:
        return {**denied, "reason": str(exc)}
    except Exception:
        return {**denied, "reason": "UNQUALIFIED_HOST_OR_READ_FAILURE"}
