from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from .browser import open_and_probe, probe_page
from .classifier import classify_auth_state, classify_page_state
from .generation import DEFAULT_D3_SAMPLE
from .models import DiscoveryConfig, PageSignals
from .runtime import build_runtime_paths, sanitize_error_message


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _visible_download_buttons(page):
    return page.get_by_role("button", name=re.compile(r"^\s*Tải về\s*$", re.I))


def _mark_best_download_for_sample(page) -> bool:
    return bool(page.evaluate(
        """
        (sample) => {
          const visible = (el) => {
            if (!el) return false;
            const s = getComputedStyle(el); const r = el.getBoundingClientRect();
            return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
          };
          const text = (el) => (el?.innerText || el?.textContent || '').replace(/\s+/g, ' ').trim();
          document.querySelectorAll('[data-d4-download-target]').forEach(el => el.removeAttribute('data-d4-download-target'));
          const buttons = Array.from(document.querySelectorAll('button,[role="button"],a'))
            .filter(visible)
            .filter(el => /^Tải về$/i.test(text(el)));
          if (!buttons.length) return false;
          if (buttons.length === 1) {
            buttons[0].setAttribute('data-d4-download-target', '1');
            return true;
          }
          const scored = [];
          for (const b of buttons) {
            let p = b;
            for (let depth = 0; p && depth <= 10; depth++, p = p.parentElement) {
              if (text(p).includes(sample)) {
                const r = p.getBoundingClientRect();
                scored.push({b, depth, area: Math.max(1, r.width * r.height)});
                break;
              }
            }
          }
          if (!scored.length) return false;
          scored.sort((a,b) => a.depth - b.depth || a.area - b.area);
          if (scored.length > 1 && scored[0].depth === scored[1].depth && Math.abs(scored[0].area - scored[1].area) < 1) return false;
          scored[0].b.setAttribute('data-d4-download-target', '1');
          return true;
        }
        """,
        DEFAULT_D3_SAMPLE,
    ))


def _try_select_history_sample(page) -> bool:
    return bool(page.evaluate(
        """
        (sample) => {
          const visible = (el) => {
            if (!el) return false;
            const s = getComputedStyle(el); const r = el.getBoundingClientRect();
            return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
          };
          const norm = (v) => (v || '').replace(/\s+/g, ' ').trim();
          document.querySelectorAll('[data-d4-history-target]').forEach(el => el.removeAttribute('data-d4-history-target'));
          const all = Array.from(document.querySelectorAll('div,li,button,[role="button"]')).filter(visible);
          const matches = all.filter(el => norm(el.innerText || el.textContent).includes(sample));
          const right = matches.filter(el => el.getBoundingClientRect().left >= window.innerWidth * 0.55);
          const pool = right.length ? right : matches;
          if (!pool.length) return false;
          pool.sort((a,b) => {
            const ta = norm(a.innerText || a.textContent).length;
            const tb = norm(b.innerText || b.textContent).length;
            const ra = a.getBoundingClientRect(); const rb = b.getBoundingClientRect();
            return ta - tb || (ra.width * ra.height) - (rb.width * rb.height);
          });
          pool[0].setAttribute('data-d4-history-target', '1');
          return true;
        }
        """,
        DEFAULT_D3_SAMPLE,
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
        "schema_version": "1.1",
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
        signals = _signals(raw)
        state = classify_page_state(signals)
        auth = classify_auth_state(signals, state)
        result.update({"page_state": state, "auth_state": auth})
        if state != "TTS_READY" or auth != "AUTHENTICATED_OR_HIDDEN":
            raise RuntimeError(f"D4 requires authenticated TTS_READY session; state={state}, auth={auth}")

        page.screenshot(path=str(evidence_dir / "d4_before.png"), full_page=True)

        target_mode = None
        if _mark_best_download_for_sample(page):
            target_mode = "current_player_or_unique_visible_download"
        else:
            history = page.get_by_role("tab", name="Lịch sử", exact=True)
            if history.count() < 1:
                history = page.get_by_text("Lịch sử", exact=True)
            if history.count() < 1:
                raise RuntimeError("History control not found and no safe Download target is visible")
            history.first.click(timeout=5_000)
            page.wait_for_timeout(1_500)
            page.screenshot(path=str(evidence_dir / "d4_history.png"), full_page=True)

            if _try_select_history_sample(page):
                page.locator('[data-d4-history-target="1"]').first.click(timeout=5_000)
                page.wait_for_timeout(1_000)

            if not _mark_best_download_for_sample(page):
                visible = _visible_download_buttons(page)
                if visible.count() == 1:
                    visible.first.evaluate("el => el.setAttribute('data-d4-download-target','1')")
                    target_mode = "history_unique_visible_download"
                else:
                    raise RuntimeError(f"Could not uniquely bind D4 target to the D3 sample; visible Download buttons={visible.count()}")
            else:
                target_mode = "history_sample_matched_download"

        target = page.locator('[data-d4-download-target="1"]')
        if target.count() != 1:
            raise RuntimeError(f"D4 safety gate expected exactly one marked Download control; found {target.count()}")

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
            "target_mode": target_mode,
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
