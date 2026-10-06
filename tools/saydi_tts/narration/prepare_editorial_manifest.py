from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
CORE_SRC = REPO_ROOT / "02_SAYDI_CORE" / "src"
if str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))

from saydi_audiobook.editorial import editorial_manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile manuscript text into a pre-render SAYDI editorial manifest."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--must-check", action="append", default=[])
    parser.add_argument("--emphasis", action="append", default=[])
    parser.add_argument("--max-chars", type=int, default=150)
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    manifest = editorial_manifest(
        text,
        must_check_phrases=args.must_check,
        emphasis_phrases=args.emphasis,
        max_chars=args.max_chars,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    required = [
        seg["index"]
        for seg in manifest["segments"]
        if seg["pronunciation_qc_required"]
    ]
    print(f"Editorial units: {manifest['unit_count']}")
    print(f"Pronunciation MUST_CHECK units: {required}")
    print(f"Post-render QC required: {manifest['post_render_qc_required']}")
    print(f"Manifest: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
