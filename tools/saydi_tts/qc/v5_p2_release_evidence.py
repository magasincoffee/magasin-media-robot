"""SAYDI P2: offline inventory of remaining release/cutover evidence.

This utility cannot authenticate real host or Owner witnesses. It never
starts, stops, deploys, renders, or marks any audio or SOT task as FINAL.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = 'saydi-v5-p2-release-evidence-inventory-v1'
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
RECEIPT_SOURCES = {
    'exact_head_ci': 'GITHUB_ACTIONS',
    'h4_targeted_regression': 'H4_LOCAL',
    'source_fidelity': 'H4_LOCAL',
    'independent_vietnamese_audio': 'H4_LOCAL',
    'worker_checkpoint_and_ram': 'H4_LOCAL',
    'off_after_reboot': 'H4_LOCAL',
    'owner_stop_start_durable': 'H4_LOCAL',
    'no_duplicate_repair_resume': 'H4_LOCAL',
    'rollback_rehearsal': 'H4_LOCAL',
    'owner_full_chapter_listening': 'OWNER_REVIEW',
    'parent_sot_authorization': 'GITHUB_MAIN',
}
HOST_REQUIRED = {key for key, value in RECEIPT_SOURCES.items() if value == 'H4_LOCAL'}
ALLOWED = {'PASS', 'FAIL', 'BLOCKED', 'NOT_RUN'}


def _hash(value: object, length: int) -> bool:
    return isinstance(value, str) and (HEX40 if length == 40 else HEX64).fullmatch(value) is not None


def evaluate(package: dict, expected_head: str, expected_sot_main: str) -> dict:
    """Inventory receipts; a signed/independent verifier remains mandatory.

    All PASS values here are *untrusted self-reports*. No return value
    authorizes deployment, chapter FINAL or worker START.
    """
    if not _hash(expected_head, 40) or not _hash(expected_sot_main, 40):
        raise ValueError('EXPECTED_COMMIT_SHA_INVALID')
    if not isinstance(package, dict) or package.get('schema') != SCHEMA:
        raise ValueError('EVIDENCE_SCHEMA_INVALID')
    if set(package) - {'schema', 'pr_head_sha', 'sot_main_sha', 'chapter', 'checkpoint_sha256',
                        'reference_sha256', 'receipts'}:
        raise ValueError('UNSAFE_PACKAGE_FIELDS')
    if package.get('pr_head_sha') != expected_head or package.get('sot_main_sha') != expected_sot_main:
        raise ValueError('STALE_PR_HEAD_OR_MAIN_SOT')
    if type(package.get('chapter')) is not int or package['chapter'] < 1:
        raise ValueError('INVALID_CHAPTER')
    for field in ('checkpoint_sha256', 'reference_sha256'):
        val = package.get(field)
        if val is not None and not _hash(val, 64):
            raise ValueError('INVALID_PROTECTED_FINGERPRINT')
    receipts = package.get('receipts')
    if not isinstance(receipts, list) or len(receipts) > len(RECEIPT_SOURCES):
        raise ValueError('INVALID_RECEIPT_LIST')
    observed = {}
    for r in receipts:
        if not isinstance(r, dict) or set(r) != {'gate', 'status', 'source', 'evidence_sha256'}:
            raise ValueError('INVALID_RECEIPT_SCHEMA')
        gate = r['gate']
        if not isinstance(gate, str) or gate not in RECEIPT_SOURCES or gate in observed:
            raise ValueError('UNKNOWN_OR_DUPLICATE_GATE')
        if r['status'] not in ALLOWED or r['source'] != RECEIPT_SOURCES[gate]:
            raise ValueError('RECEIPT_STATUS_OR_PROVENANCE_INVALID')
        if not _hash(r['evidence_sha256'], 64):
            raise ValueError('RECEIPT_DIGEST_INVALID')
        observed[gate] = r
    pending = []
    claimed_pass = []
    failed = []
    for gate in RECEIPT_SOURCES:
        r = observed.get(gate)
        if r is None or r['status'] in {'NOT_RUN', 'BLOCKED'}:
            pending.append(gate)
        elif r['status'] == 'FAIL':
            failed.append(gate)
        else:
            claimed_pass.append(gate)
    if not package.get('checkpoint_sha256'):
        pending.append('immutable_checkpoint_snapshot')
    if not package.get('reference_sha256'):
        pending.append('approved_narrator_reference')
    if failed:
        status = 'BLOCKED_FAILED_GATE'
    elif pending:
        status = 'BLOCKED_MISSING_EVIDENCE'
    else:
        status = 'RECEIPTS_SUBMITTED_UNVERIFIED'
    return {
        'schema': SCHEMA,
        'chapter': package['chapter'],
        'pr_head_sha': expected_head,
        'sot_main_sha': expected_sot_main,
        'requested_gate_count': len(RECEIPT_SOURCES),
        'receipt_count': len(receipts),
        'self_reported_pass_count': len(claimed_pass),
        'self_reported_failed_gates': failed,
        'pending_gates': pending,
        'h4_required_gates': sorted(HOST_REQUIRED),
        'status': status,
        'receipt_authenticity_verified': False,
        'independent_owner_identity_verified': False,
        'sot_authorization_verified': False,
        'exact_head_ci_verified': False,
        'chapter_technical_pass': False,
        'chapter_listening_accepted': False,
        'production_write_allowed': False,
        'worker_start_allowed': False,
        'automatic_merge_allowed': False,
        'chapter_final': False,
        'note': 'Receipt SHA values and PASS labels do not authenticate GitHub, local host or Owner; external verification is mandatory.',
    }


def write_new_report(output: Path, result: dict) -> None:
    if any(part.casefold() in {'chunks','owner_approved_natural_v5','stitch_cleaned'} for part in output.parts):
        raise ValueError('REFUSE_PRODUCTION_PATH')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main() -> int:
    p = argparse.ArgumentParser(description='SAYDI P2 read-only release evidence inventory')
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--expected-head', required=True)
    p.add_argument('--expected-sot-main', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--enable-p2-inventory', action='store_true')
    a = p.parse_args()
    if not a.enable_p2_inventory:
        print('SAYDI_P2_INVENTORY_DISABLED_DEFAULT')
        return 0
    package = json.loads(a.input.read_text(encoding='utf-8-sig'))
    result = evaluate(package, a.expected_head, a.expected_sot_main)
    write_new_report(a.output, result)
    print(json.dumps({'status': result['status'], 'pending_gates': len(result['pending_gates']),
                      'chapter_final': False, 'worker_start_allowed': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
