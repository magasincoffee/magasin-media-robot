from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .analysis import OllamaAnalysisProvider, RuleBasedAnalysisProvider
from .pronunciation import build_pronunciation_repair_plan, load_pronunciation_lexicon
from .prosody import get_prosody_envelope, resolve_owner_style_request
from .voice import WindowsSapiVoiceProvider
from .workflow import decide_audio, decide_text, prepare_run, synthesize_sample


def _analysis(args):
    if args.analysis == "rules":
        return RuleBasedAnalysisProvider()
    return OllamaAnalysisProvider(model=args.ollama_model, endpoint=args.ollama_endpoint)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="saydi-audiobook",
        description="SAYDI Audiobook vertical-slice runner",
    )
    sub = p.add_subparsers(dest="command", required=True)

    prep = sub.add_parser("prepare")
    prep.add_argument(
        "--input",
        required=True,
        type=Path,
        help="UTF-8 text fixture for SAYDI-002; PDF arrives in SAYDI-003",
    )
    prep.add_argument("--run-dir", required=True, type=Path)
    prep.add_argument("--analysis", choices=["rules", "ollama"], default="rules")
    prep.add_argument("--ollama-model", default="qwen3:8b")
    prep.add_argument(
        "--ollama-endpoint",
        default="http://127.0.0.1:11434/api/generate",
    )

    dt = sub.add_parser("decide-text")
    dt.add_argument("--run-dir", required=True, type=Path)
    dt.add_argument("--decision", required=True, choices=["approve", "reject"])

    syn = sub.add_parser("synthesize-sample")
    syn.add_argument("--run-dir", required=True, type=Path)
    syn.add_argument("--provider", choices=["windows-sapi"], default="windows-sapi")
    syn.add_argument("--rate", type=int, default=0)
    syn.add_argument("--voice-name", default=None)

    da = sub.add_parser("decide-audio")
    da.add_argument("--run-dir", required=True, type=Path)
    da.add_argument("--decision", required=True, choices=["approve", "reject"])

    pron = sub.add_parser(
        "pronunciation-preview",
        help="Build a local, non-destructive spoken-form repair proposal.",
    )
    pron.add_argument("--input", required=True, type=Path, help="UTF-8 text input")
    pron.add_argument(
        "--suspect",
        action="append",
        default=[],
        help="Suspect token/phrase from QC. Repeat for multiple values.",
    )
    pron.add_argument("--lexicon", type=Path, default=None)
    pron.add_argument("--output", type=Path, default=None, help="Optional JSON output path")

    profile = sub.add_parser(
        "profile-resolve",
        help="Resolve a simple Owner genre/style request to a versioned prosody profile.",
    )
    profile.add_argument("--style", default="")
    profile.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional UTF-8 book text used as deterministic fallback when style is unknown.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        state = prepare_run(args.input, args.run_dir, _analysis(args))
        print(f"run prepared: {state['run_id']} status={state['status']}")
        return 0
    if args.command == "decide-text":
        state = decide_text(args.run_dir, args.decision)
        print(f"text decision: {state['text_decision']} status={state['status']}")
        return 0
    if args.command == "synthesize-sample":
        provider = WindowsSapiVoiceProvider(rate=args.rate, voice_name=args.voice_name)
        result = synthesize_sample(args.run_dir, provider)
        print(
            f"voice result: {result.status} provider={result.provider} "
            f"path={result.local_audio_path}"
        )
        return 0 if result.status == "SUCCESS" else 2
    if args.command == "decide-audio":
        state = decide_audio(args.run_dir, args.decision)
        print(f"audio decision: {state['audio_decision']} status={state['status']}")
        return 0
    if args.command == "pronunciation-preview":
        source = args.input.read_text(encoding="utf-8")
        lexicon = load_pronunciation_lexicon(args.lexicon) if args.lexicon else None
        result = build_pronunciation_repair_plan(
            source,
            suspect_tokens=args.suspect,
            lexicon=lexicon,
        )
        payload = {
            "canonical_text": result.canonical_text,
            "spoken_text": result.spoken_text,
            "lexicon_version": result.lexicon_version,
            "changed": result.changed,
            "applied_overrides": [asdict(x) for x in result.applied_overrides],
            "unresolved_suspect_tokens": list(result.unresolved_suspect_tokens),
        }
        rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
            print(
                f"pronunciation preview written: {args.output} "
                f"overrides={len(result.applied_overrides)} "
                f"unresolved={len(result.unresolved_suspect_tokens)}"
            )
        else:
            print(rendered, end="")
        return 0
    if args.command == "profile-resolve":
        book_profile = None
        if args.input is not None:
            source = args.input.read_text(encoding="utf-8")
            book_profile = RuleBasedAnalysisProvider().analyze_book(source)
        resolution = resolve_owner_style_request(
            args.style,
            book_profile=book_profile,
        )
        envelope = get_prosody_envelope(resolution.profile_key)
        payload = {
            "requested_style": resolution.requested_style,
            "profile_key": resolution.profile_key,
            "resolution_source": resolution.source,
            "matched_aliases": list(resolution.matched_aliases),
            "prosody_profile_version": envelope.version,
            "prosody_profile_fingerprint": envelope.fingerprint,
            "envelope": asdict(envelope),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    return 1
