from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .browser import open_and_probe, probe_page
from .classifier import classify_auth_state, classify_page_state
from .models import DiscoveryConfig, PageSignals
from .runtime import build_runtime_paths


def _signals(raw: dict) -> PageSignals:
    return PageSignals(
        url=str(raw.get("url") or ""),
        title=str(raw.get("title") or ""),
        visible_text=str(raw.get("visible_text") or ""),
        has_password_input=bool(raw.get("has_password_input")),
        has_textarea=bool(raw.get("has_textarea")),
        has_contenteditable=bool(raw.get("has_contenteditable")),
        button_texts=tuple(str(x) for x in raw.get("button_texts") or []),
        link_texts=tuple(str(x) for x in raw.get("link_texts") or []),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="One-time interactive SaydiVoice login bootstrap for the persistent local Playwright profile."
    )
    parser.add_argument("--runtime-root", type=Path, help="Override MAGASIN MediaRobot runtime root.")
    parser.add_argument("--timeout-ms", type=int, default=60_000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runtime = build_runtime_paths(args.runtime_root) if args.runtime_root else build_runtime_paths()
    runtime.create()
    cfg = DiscoveryConfig(
        headless=False,
        navigation_timeout_ms=max(5_000, args.timeout_ms),
        settle_ms=2_000,
    )

    print("\n=== MAGASIN SaydiVoice — One-time Browser Profile Setup ===")
    print(f"Profile local: {runtime.profile_dir}")
    print("1) Dang nhap SaydiVoice trong cua so Chromium vua mo.")
    print("2) Neu Google/OTP/CAPTCHA xuat hien, tu hoan tat tren trinh duyet.")
    print("3) Khi quay lai trang TTS va khong con nut Dang nhap, quay lai cua so nay.")
    print("4) Nhan ENTER de kiem tra va luu profile.\n")

    browser_bundle = None
    try:
        _raw, browser_bundle, page = open_and_probe(cfg, runtime)
        try:
            input("Nhan ENTER sau khi da dang nhap xong... ")
        except EOFError:
            print("ERROR: Can chay script nay tu Windows desktop/terminal tuong tac.", file=sys.stderr)
            return 12

        page.reload(wait_until="domcontentloaded", timeout=cfg.navigation_timeout_ms)
        page.wait_for_timeout(2_000)
        raw = probe_page(page)
        signals = _signals(raw)
        state = classify_page_state(signals)
        auth = classify_auth_state(signals, state)
        print(f"Page state: {state}")
        print(f"Auth state: {auth}")
        if state != "TTS_READY" or auth != "AUTHENTICATED_OR_HIDDEN":
            print("Profile chua duoc xac nhan dang nhap. Khong xoa profile; co the chay lai setup.")
            return 11
        print("PASS: Profile SaydiVoice da dang nhap va se duoc GitHub self-hosted runner tai su dung.")
        return 0
    finally:
        if browser_bundle is not None:
            playwright, context = browser_bundle
            try:
                context.close()
            finally:
                playwright.stop()


if __name__ == "__main__":
    raise SystemExit(main())
