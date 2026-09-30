from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from .analysis import AnalysisProvider, RuleBasedAnalysisProvider
from .contracts import VoiceRequest, VoiceResult, read_json, write_json
from .narration import choose_narration_profile, select_representative_passages
from .text_layers import build_text_layers
from .voice import VoiceProvider


STATE_FILE = "state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state(run_dir: Path) -> dict:
    path = run_dir / STATE_FILE
    return read_json(path) if path.exists() else {}


def _save_state(run_dir: Path, state: dict) -> None:
    state["updated_at"] = _now()
    write_json(run_dir / STATE_FILE, state)


def prepare_run(
    input_path: Path,
    run_dir: Path,
    analysis_provider: AnalysisProvider | None = None,
) -> dict:
    analysis_provider = analysis_provider or RuleBasedAnalysisProvider()
    raw = input_path.read_text(encoding="utf-8")
    layers = build_text_layers(raw)
    book = analysis_provider.analyze_book(layers.spoken_text)
    profile = choose_narration_profile(book)
    samples = select_representative_passages(layers.spoken_text, limit=3)
    if not samples:
        raise ValueError("no sample passage could be selected")

    input_sha = sha256(input_path.read_bytes()).hexdigest()
    run_id = sha256(f"{input_sha}|vertical-slice-v0.1".encode("utf-8")).hexdigest()[:20]
    run_dir.mkdir(parents=True, exist_ok=True)

    write_json(
        run_dir / "run_manifest.json",
        {
            "schema_version": "run-v0.1",
            "run_id": run_id,
            "created_at": _now(),
            "input_path": input_path.name,
            "input_sha256": input_sha,
        },
    )
    write_json(run_dir / "text_layers.json", asdict(layers))
    write_json(run_dir / "book_profile.json", asdict(book))
    write_json(
        run_dir / "narration_profile.json",
        {**asdict(profile), "fingerprint": profile.fingerprint},
    )
    write_json(run_dir / "sample_passages.json", [asdict(s) for s in samples])
    write_json(
        run_dir / "text_preview.json",
        {
            "run_id": run_id,
            "spoken_preview": samples[0].text,
            "narration_profile": profile.key,
            "narration_fingerprint": profile.fingerprint,
            "decision": "PENDING",
        },
    )
    state = {
        "schema_version": "state-v0.1",
        "run_id": run_id,
        "status": "TEXT_REVIEW_REQUIRED",
        "text_decision": "PENDING",
        "audio_decision": "NOT_AVAILABLE",
        "narration_fingerprint": profile.fingerprint,
        "created_at": _now(),
    }
    _save_state(run_dir, state)
    return state


def decide_text(run_dir: Path, decision: str) -> dict:
    decision = decision.upper()
    if decision not in {"APPROVE", "REJECT"}:
        raise ValueError("decision must be APPROVE or REJECT")
    state = _state(run_dir)
    if not state:
        raise FileNotFoundError("run state not found")
    state["text_decision"] = decision
    state["status"] = "TEXT_APPROVED" if decision == "APPROVE" else "TEXT_REJECTED"
    _save_state(run_dir, state)
    return state


def synthesize_sample(run_dir: Path, provider: VoiceProvider) -> VoiceResult:
    state = _state(run_dir)
    if state.get("status") not in {"TEXT_APPROVED", "AUDIO_REVIEW_REQUIRED", "SAMPLE_APPROVED"}:
        raise RuntimeError("text must be approved before sample synthesis")

    samples = read_json(run_dir / "sample_passages.json")
    sample = samples[0]
    provider_name = getattr(provider, "provider_name", provider.__class__.__name__)
    operation_id = sha256(
        (
            f"{state['run_id']}|{state['narration_fingerprint']}|"
            f"{sample['sample_id']}|{provider_name}"
        ).encode("utf-8")
    ).hexdigest()[:24]

    ledger_path = run_dir / "operations.json"
    ledger = read_json(ledger_path) if ledger_path.exists() else {}
    previous = ledger.get(operation_id)
    if previous and previous.get("status") == "SUCCESS":
        result = VoiceResult(**previous["result"])
        result.validate()
        return result
    if previous and previous.get("status") == "ATTEMPTING":
        raise RuntimeError("operation has ambiguous prior attempt; reconcile before retry")

    ledger[operation_id] = {"status": "ATTEMPTING", "started_at": _now()}
    write_json(ledger_path, ledger)

    output_path = run_dir / "audio" / f"{sample['sample_id']}.wav"
    request = VoiceRequest(
        operation_id=operation_id,
        sample_id=sample["sample_id"],
        text=sample["text"],
        narration_fingerprint=state["narration_fingerprint"],
        voice_key="default",
        output_path=str(output_path),
    )
    result = provider.generate(request)
    result.validate()

    ledger[operation_id] = {
        "status": result.status,
        "finished_at": _now(),
        "result": asdict(result),
    }
    write_json(ledger_path, ledger)
    write_json(run_dir / "voice_result.json", asdict(result))

    if result.status == "SUCCESS":
        state["status"] = "AUDIO_REVIEW_REQUIRED"
        state["audio_decision"] = "PENDING"
        state["voice_operation_id"] = operation_id
        _save_state(run_dir, state)
    return result


def decide_audio(run_dir: Path, decision: str) -> dict:
    decision = decision.upper()
    if decision not in {"APPROVE", "REJECT"}:
        raise ValueError("decision must be APPROVE or REJECT")
    state = _state(run_dir)
    if state.get("status") not in {"AUDIO_REVIEW_REQUIRED", "SAMPLE_APPROVED", "SAMPLE_REJECTED"}:
        raise RuntimeError("audio sample is not ready for review")
    state["audio_decision"] = decision
    state["status"] = "SAMPLE_APPROVED" if decision == "APPROVE" else "SAMPLE_REJECTED"
    _save_state(run_dir, state)
    return state
