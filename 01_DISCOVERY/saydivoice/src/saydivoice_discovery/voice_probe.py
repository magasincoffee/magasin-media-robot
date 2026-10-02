from __future__ import annotations

import argparse
import json
from pathlib import Path

from .browser import open_and_probe
from .models import DiscoveryConfig
from .runtime import build_runtime_paths
from .voice_controls import current_voice, _open_voice_selector, _voice_search_input


LEAF_TEXT_SCRIPT = r"""
() => {
  const visible = (el) => {
    if (!el) return false;
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  };
  const unsafe = (el) => {
    if (!el) return true;
    if (el.matches?.('input[type="password"],textarea,[contenteditable="true"],[role="textbox"]')) return true;
    return !!el.closest?.('textarea,[contenteditable="true"],[role="textbox"]');
  };
  const textOf = (el) => (el.innerText || el.textContent || '').replace(/\s+/g,' ').trim();
  return Array.from(document.querySelectorAll('body *'))
    .filter(visible)
    .filter(el => !unsafe(el))
    .filter(el => el.childElementCount === 0)
    .map(el => textOf(el).slice(0,220))
    .filter(Boolean);
}
"""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--chromium-executable", required=True)
    p.add_argument("--query", default="MN")
    args = p.parse_args()

    paths = build_runtime_paths()
    paths.create()
    cfg = DiscoveryConfig(
        chromium_executable_path=args.chromium_executable,
        headless=False,
        navigation_timeout_ms=60_000,
        settle_ms=2_000,
    )
    bundle = None
    try:
        _, bundle, page = open_and_probe(cfg, paths)
        current = current_voice(page)
        if not current:
            raise RuntimeError("current voice button could not be resolved")
        _open_voice_selector(page, current)
        search = _voice_search_input(page)
        search.fill(args.query)
        page.wait_for_timeout(1200)

        texts = page.evaluate(LEAF_TEXT_SCRIPT) or []
        # Keep only concise, privacy-safe visible labels/descriptors.
        cleaned = []
        seen = set()
        for raw in texts:
            text = " ".join(str(raw).split())
            if not text or len(text) > 220:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(text)

        out_dir = paths.runs_dir / "voice_probe_latest"
        out_dir.mkdir(parents=True, exist_ok=True)
        screenshot = out_dir / "voice_probe.png"
        page.screenshot(path=str(screenshot), full_page=True)
        payload = {
            "schema_version": "1.0",
            "mode": "NON_GENERATIVE_VOICE_SEARCH",
            "query": args.query,
            "current_voice": current,
            "generate_clicked": False,
            "visible_labels": cleaned,
        }
        (out_dir / "voice_probe.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(payload, ensure_ascii=False))
        page.keyboard.press("Escape")
        return 0
    finally:
        if bundle is not None:
            playwright, context = bundle
            try:
                context.close()
            finally:
                playwright.stop()


if __name__ == "__main__":
    raise SystemExit(main())
