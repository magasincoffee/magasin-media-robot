"""SAYDI002-VN-001 — pure SOURCE/QA contract for a future H4 one-shot gate.

No IO, network, global journal, Windows handles, MCP tool, scanner or worker.
All supplied "witnesses" are caller-forgeable here. Even a matched synthetic
contract NEVER establishes live STOP, Owner consent, replay durability or
permission to read protected V5 assets.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "MAGASIN_SAYDI_VN001_H4_ONESHOT_DRYRUN_V1"
WITNESS_SCHEMA = "MAGASIN_SAYDI_VN001_H4_STOP_WITNESS_SYNTHETIC_V1"
LEDGER_SCHEMA = "MAGASIN_SAYDI_VN001_REPLAY_LEDGER_SNAPSHOT_SYNTHETIC_V1"
OWNER_SCHEMA = "MAGASIN_SAYDI_VN001_GITHUB_OWNER_EVIDENCE_V1"
TASK = "SAYDI002-VN-001"
HOST = "DESKTOP-H4A16IL"
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
EXPECTED_OWNER_FIELDS = frozenset({
    "schema", "task_id", "status", "issue_number", "issue_id",
    "approval_comment_id", "issue_body_sha256", "approval_nonce_sha256",
    "main_sha_observed", "owner_claims_match", "github_live_https_observed",
    "owner_one_shot_consumed", "owner_issue_approval_verified_for_h4",
    "h4_stop_generation_verified", "h4_root_identity_verified",
    "replay_guard_verified", "can_read_v5", "approved_to_dispatch",
    "approved_to_start", "worker_started", "task_completed",
    "production_modified",
})
MAX_LEDGER_RECORDS = 128
STATES = frozenset({"RESERVED", "CONSUMED", "HOLD"})


class ContractHold(ValueError):
    """Fixed, privacy-safe refusal code."""


def _pos_int(value: Any) -> bool:
    return type(value) is int and 0 < value < 2**63


def _hex40(value: Any) -> bool:
    return type(value) is str and HEX40.fullmatch(value) is not None


def _hex64(value: Any) -> bool:
    return type(value) is str and HEX64.fullmatch(value) is not None


def _owner_receipt(value: Any, expected_main_sha: str) -> tuple[int, int, int, str]:
    if (
        type(value) is not dict
        or set(value) != EXPECTED_OWNER_FIELDS
        or value.get("schema") != OWNER_SCHEMA
        or value.get("task_id") != TASK
        or value.get("status") != "OWNER_INTENT_MATCHED_NON_EXECUTABLE"
        or value.get("main_sha_observed") != expected_main_sha
        or not _pos_int(value.get("issue_number"))
        or not _pos_int(value.get("issue_id"))
        or not _pos_int(value.get("approval_comment_id"))
        or not _hex64(value.get("issue_body_sha256"))
        or not _hex64(value.get("approval_nonce_sha256"))
        or value.get("owner_claims_match") is not True
        or value.get("github_live_https_observed") is not True
        or value.get("owner_one_shot_consumed") is not False
        or value.get("owner_issue_approval_verified_for_h4") is not False
        or value.get("h4_stop_generation_verified") is not False
        or value.get("h4_root_identity_verified") is not False
        or value.get("replay_guard_verified") is not False
        or value.get("can_read_v5") is not False
        or value.get("approved_to_start") is not False
        or value.get("approved_to_dispatch") is not False
        or value.get("worker_started") is not False
        or value.get("task_completed") is not False
        or value.get("production_modified") is not False
    ):
        raise ContractHold("OWNER_LIVE_INTENT_NOT_PROVEN")
    return (
        value["issue_number"], value["issue_id"],
        value["approval_comment_id"], value["approval_nonce_sha256"],
    )


def _stop_fixture(value: Any, expected_main_sha: str) -> None:
    if (
        type(value) is not dict
        or value.get("schema") != WITNESS_SCHEMA
        or value.get("host") != HOST
        or value.get("task_id") != TASK
        or value.get("expected_main_sha") != expected_main_sha
        or value.get("stop_present_before") is not True
        or value.get("stop_present_after") is not True
        or value.get("autostart_disabled_before") is not True
        or value.get("autostart_disabled_after") is not True
        or not _hex64(value.get("owner_generation_before"))
        or value.get("owner_generation_before") != value.get("owner_generation_after")
        or value.get("worker_started") is not False
        or value.get("production_modified") is not False
    ):
        raise ContractHold("H4_STOP_GENERATION_UNATTESTED")


def _ledger_fixture(value: Any, nonce_sha: str) -> None:
    if type(value) is not dict or set(value) != {"schema", "records"}:
        raise ContractHold("REPLAY_LEDGER_UNTRUSTED")
    if value["schema"] != LEDGER_SCHEMA or type(value["records"]) is not list:
        raise ContractHold("REPLAY_LEDGER_UNTRUSTED")
    records = value["records"]
    if len(records) > MAX_LEDGER_RECORDS:
        raise ContractHold("REPLAY_LEDGER_UNTRUSTED")
    seen: set[str] = set()
    for record in records:
        if (
            type(record) is not dict
            or set(record) != {"nonce_sha256", "state"}
            or not _hex64(record["nonce_sha256"])
            or type(record["state"]) is not str
            or record["state"] not in STATES
        ):
            raise ContractHold("REPLAY_LEDGER_UNTRUSTED")
        if record["nonce_sha256"] in seen:
            raise ContractHold("REPLAY_LEDGER_DUPLICATE_RECORD")
        seen.add(record["nonce_sha256"])
    if nonce_sha in seen:
        raise ContractHold("OWNER_ONE_SHOT_ALREADY_SEEN")


def inspect_one_shot_contract(
    *,
    expected_main_sha: str,
    owner_intent: Any,
    stop_witness: Any,
    ledger_snapshot: Any,
) -> dict[str, Any]:
    """Validate synthetic shape and replay semantics, NEVER authorize field IO.

    Caller-owned dictionaries do NOT authenticate Owner, STOP or a local
    durable replay journal. A production H4 adapter must own those witnesses
    and an atomic, access-controlled, fsync-verified reservation transaction,
    then separately revalidate immediately before its one read operation.
    """
    result = {
        "schema": SCHEMA, "task_id": TASK,
        "status": "BLOCKED", "reason": "FIELD_AUTHORITY_NOT_QUALIFIED",
        "synthetic_contract_consistent": False,
        "owner_issue_approval_verified_for_h4": False,
        "replay_guard_verified": False,
        "h4_stop_generation_verified": False,
        "h4_root_identity_verified": False,
        "real_v5_inventory_verified": False,
        "one_shot_consumed": False,
        "can_read_v5": False, "approved_to_dispatch": False,
        "approved_to_start": False, "worker_started": False,
        "task_completed": False, "production_modified": False,
    }
    try:
        if not _hex40(expected_main_sha):
            raise ContractHold("EXPECTED_MAIN_SHA_INVALID")
        _issue_num, _issue_id, _comment_id, nonce_sha = _owner_receipt(
            owner_intent, expected_main_sha
        )
        _stop_fixture(stop_witness, expected_main_sha)
        _ledger_fixture(ledger_snapshot, nonce_sha)
    except ContractHold as exc:
        return {**result, "reason": str(exc)}
    return {
        **result, "status": "SYNTHETIC_CONTRACT_MATCHED_UNATTESTED",
        "reason": "REQUIRES_DURABLE_H4_TRANSACTION_AND_OWNER_STOP",
        "synthetic_contract_consistent": True,
    }
