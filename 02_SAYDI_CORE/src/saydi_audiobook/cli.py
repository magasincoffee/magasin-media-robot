from __future__ import annotations

import argparse
from pathlib import Path

from .analysis import OllamaAnalysisProvider, RuleBasedAnalysisProvider
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
    return 1
