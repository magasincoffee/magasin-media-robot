from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .browser import open_and_probe
from .classifier import classify_auth_state, classify_page_state
from .evidence import make_page_signals
from .generation import DEFAULT_D3_SAMPLE
from .models import DiscoveryConfig
from .runtime import build_runtime_paths, sanitize_error_message


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _mark_latest_history_menu(page) -> str | None:
    return page.evaluate(
        r"""
        () => {
          const visible = (el) => {
            if (!el) return false;
            const s = getComputedStyle(el); const r = el.getBoundingClientRect();
            return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
          };
          const text = (el) => (el?.innerText || el?.textContent || '').replace(/\s+/g, ' ').trim();
          document.querySelectorAll('[data-d4-history-menu]').forEach(el => el.removeAttribute('data-d4-history-menu'));
          const stampRe = /^\d{1,2}:\d{2}:\d{2}\s+\d{1,2}\/\d{1,2}\/\d{4}$/;
          const stamps = Array.from(document.querySelectorAll('div,span,p'))
            .filter(visible)
            .filter(el => stampRe.test(text(el)))
            .filter(el => el.getBoundingClientRect().left > window.innerWidth * 0.55)
            .sort((a,b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
          if (!stamps.length) return null;
          const stamp = stamps[0];
          let p = stamp;
          for (let depth = 0; p && depth <= 7; depth++, p = p.parentElement) {
            const pr = p.getBoundingClientRect();
            const candidates = Array.from(p.querySelectorAll('button,[role="button"],[tabindex]')).filter(visible);
            if (candidates.length) {
              const rightmost = candidates.sort((a,b) => b.getBoundingClientRect().right - a.getBoundingClientRect().right)[0];
              if (rightmost.getBoundingClientRect().right >= pr.right - 80 || candidates.length === 1) {
                rightmost.setAttribute('data-d4-history-menu', '1');
                return text(stamp);
              }
            }
          }
          return null;
        }
        """
    )


def _mark_download_menu_action(page) -> bool:
    return bool(page.evaluate(
        r"""
        () => {
          const visible = (el) => {
            if (!el) return false;
            const s = getComputedStyle(el); const r = el.getBoundingClientRect();
            return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
          };
          const text = (el) => (el?.innerText || el?.textContent || '').replace(/\s+/g, ' ').trim();
          document.querySelectorAll('[data-d4-download-target]').forEach(el => el.removeAttribute('data-d4-download-target'));
          const candidates = Array.from(document.querySelectorAll('button,[role="button"],[role="menuitem"],a,div'))
            .filter(visible)
            .filter(el => /^Tải về$/i.test(text(el)));
          if (!candidates.length) return false;
          candidates.sort((a,b) => {
            const ar = a.getBoundingClientRect(); const br = b.getBoundingClientRect();
            return (ar.width * ar.height) - (br.width * br.height);
          });
          candidates[0].setAttribute('data-d4-download-target', '1');
          return true;
        }
        """
    ))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Authorized D4 one-shot SaydiVoice download verification. Never invokes Generate.")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--chromium-executable", required=True)
    parser.add_argument("--timeout-ms", type=int, default=60_000)
    parser.add_argument("--allow-download", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.allow_download:
        print("D4_BLOCKED: --allow-download is required.", file=sys.stderr)
        return 12

    runtime = build_runtime_paths(args.runtime_root) if args.runtime_root else build_runtime_paths()
    runtime.create()
    run_id = "d4_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    evidence_dir = runtime.runs_dir / run_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    result_path = evidence_dir / "download_lifecycle.json"

    result = {
        "schema_version": "1.2",
        "mode": "D4_CONTROLLED_DOWNLOAD_ONLY",
        "started_at": _now(),
        "generate_clicked": False,
        "generation_attempt_count": 0,
        "download_authorized": True,
        "download_click_count": 0,
        "sample_text_length": len(DEFAULT_D3_SAMPLE),
        "sample_text_sha256": hashlib.sha256(DEFAULT_D3_SAMPLE.encode("utf-8")).hexdigest(),
        "status": "NOT_RUN",
    }

    cfg = DiscoveryConfig(
        headless=False,
        navigation_timeout_ms=max(5_000, args.timeout_ms),
        settle_ms=2_500,
        chromium_executable_path=args.chromium_executable,
        allow_generate=False,
    )

    browser_bundle = None
    try:
        raw, browser_bundle, page = open_and_probe(cfg, runtime)
        signals = make_page_signals(raw)
        state = classify_page_state(signals)
        auth = classify_auth_state(signals, state)
        result.update({"page_state": state, "auth_state": auth})
        if state != "TTS_READY" or auth != "AUTHENTICATED_OR_HIDDEN":
            raise RuntimeError(f"D4 requires authenticated TTS_READY session; state={state}, auth={auth}")

        page.screenshot(path=str(evidence_dir / "d4_before.png"), full_page=True)

        history = page.get_by_role("tab", name="Lịch sử", exact=True)
        if history.count() < 1:
            history = page.get_by_text("Lịch sử", exact=True)
        if history.count() < 1:
            raise RuntimeError("History control not found")
        history.first.click(timeout=5_000)
        page.wait_for_timeout(1_500)
        page.screenshot(path=str(evidence_dir / "d4_history.png"), full_page=True)

        newest_timestamp = _mark_latest_history_menu(page)
        if not newest_timestamp:
            raise RuntimeError("Could not bind the newest history item's overflow menu")
        menu = page.locator('[data-d4-history-menu="1"]')
        if menu.count() != 1:
            raise RuntimeError(f"Expected one newest-history overflow menu, found {menu.count()}")
        menu.click(timeout=5_000)
        page.wait_for_timeout(500)
        page.screenshot(path=str(evidence_dir / "d4_menu.png"), full_page=True)

        if not _mark_download_menu_action(page):
            raise RuntimeError("Newest history overflow menu did not expose a visible Tải về action")
        target = page.locator('[data-d4-download-target="1"]')
        if target.count() != 1:
            raise RuntimeError(f"D4 safety gate expected exactly one marked Download action; found {target.count()}")

        page.screenshot(path=str(evidence_dir / "d4_before_click.png"), full_page=True)
        with page.expect_download(timeout=30_000) as download_info:
            target.click(timeout=5_000)
        result["download_click_count"] = 1
        download = download_info.value
        suggested = Path(download.suggested_filename or "saydi-audio.bin").name
        suffix = Path(suggested).suffix.lower() or ".bin"
        saved_name = f"{run_id}{suffix}"
        saved_path = runtime.downloads_dir / saved_name
        download.save_as(str(saved_path))
        byte_count = saved_path.stat().st_size
        if byte_count <= 0:
            raise RuntimeError("Download event completed but saved file is empty")

        page.wait_for_timeout(500)
        page.screenshot(path=str(evidence_dir / "d4_after_click.png"), full_page=True)
        result.update({
            "status": "PASS",
            "target_mode": "newest_history_item_overflow_menu",
            "newest_history_timestamp": newest_timestamp,
            "suggested_filename": suggested,
            "saved_filename": saved_name,
            "extension": suffix,
            "byte_count": byte_count,
            "sha256": _sha256(saved_path),
            "download_failure": download.failure(),
            "saved_local_only": True,
            "audio_uploaded_to_github": False,
            "finished_at": _now(),
        })
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        result.update({
            "status": "FAIL",
            "error": sanitize_error_message(f"{type(exc).__name__}: {exc}"),
            "finished_at": _now(),
        })
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 31
    finally:
        if browser_bundle is not None:
            playwright, context = browser_bundle
            try:
                context.close()
            finally:
                playwright.stop()


if __name__ == "__main__":
    raise SystemExit(main())
