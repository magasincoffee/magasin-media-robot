from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from .browser import open_and_probe
from .classifier import classify_auth_state, classify_page_state
from .evidence import make_page_signals
from .models import DiscoveryConfig
from .runtime import build_runtime_paths, sanitize_error_message


TARGET_SNIPPET = "Chỉ đến khi gặp Chris Winfield"


def clean(v: str | None) -> str:
    return re.sub(r"\s+", " ", v or "").strip()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--chromium-executable", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()

    runtime = build_runtime_paths()
    runtime.create()
    cfg = DiscoveryConfig(
        chromium_executable_path=args.chromium_executable,
        headless=False,
        navigation_timeout_ms=60_000,
        settle_ms=2_000,
    )
    bundle = None
    try:
        raw, bundle, page = open_and_probe(cfg, runtime)
        signals = make_page_signals(raw)
        state = classify_page_state(signals)
        auth = classify_auth_state(signals, state)
        if state != "TTS_READY" or auth != "AUTHENTICATED_OR_HIDDEN":
            raise RuntimeError(f"Saydi session not ready: state={state} auth={auth}")

        network_events = []
        def on_response(resp):
            try:
                req = resp.request
                if req.resource_type in {"xhr", "fetch", "media"}:
                    network_events.append({
                        "method": req.method,
                        "url": resp.url.split("?", 1)[0],
                        "status": resp.status,
                        "content_type": (resp.headers or {}).get("content-type", ""),
                    })
            except Exception:
                pass
        page.on("response", on_response)

        history = page.get_by_text("Lịch sử", exact=True)
        if history.count() < 1:
            raise RuntimeError("History tab not found")
        history.first.click(timeout=5_000)
        page.wait_for_timeout(2_000)

        evidence_dir = runtime.runs_dir / "history_recover_latest"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(evidence_dir / "history_surface.png"), full_page=True)

        body = clean(page.locator("body").inner_text())
        probe = {
            "body_excerpt": body[:6000],
            "network_events": network_events[-30:],
        }
        (evidence_dir / "history_probe.json").write_text(
            json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps({"history_probe": probe}, ensure_ascii=False))
        if TARGET_SNIPPET not in body:
            raise RuntimeError("Latest target excerpt not visible in Saydi history")

        result = page.evaluate(
            r"""
(snippet) => {
  const norm=(v)=>(v||'').replace(/\s+/g,' ').trim();
  const vis=(e)=>{if(!e)return false;const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
  const nodes=Array.from(document.querySelectorAll('body *')).filter(vis)
    .filter(e=>norm(e.innerText||e.textContent).includes(snippet));
  for(const n of nodes){
    let p=n;
    for(let d=0; d<12 && p; d++, p=p.parentElement){
      const buttons=Array.from(p.querySelectorAll('button,[role="button"],a')).filter(vis);
      const dl=buttons.find(b=>/tải về|download/i.test(norm(b.innerText||b.textContent)) || /download/i.test(b.getAttribute('aria-label')||''));
      if(dl){
        dl.setAttribute('data-magasin-history-download','1');
        return {found:true, text:norm(p.innerText||p.textContent).slice(0,500)};
      }
    }
  }
  return {found:false};
}
""",
            TARGET_SNIPPET,
        )
        if not result.get("found"):
            raise RuntimeError("Download control for target history item not found")

        out = args.output.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        control = page.locator('[data-magasin-history-download="1"]').first
        with page.expect_download(timeout=20_000) as info:
            control.click(timeout=5_000)
        download = info.value
        download.save_as(str(out))
        data = out.read_bytes()
        if not data:
            raise RuntimeError("Recovered history download is empty")

        payload = {
            "schema_version": "1.0",
            "mode": "RECOVER_EXISTING_HISTORY_AUDIO_NO_GENERATE",
            "target_snippet": TARGET_SNIPPET,
            "generate_click_count": 0,
            "download_completed": True,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "output_path": str(out),
            "history_item_text": result.get("text"),
        }
        (evidence_dir / "history_recover.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({
            "gate": "FAIL_HISTORY_RECOVERY",
            "error": sanitize_error_message(f"{type(exc).__name__}: {exc}")
        }, ensure_ascii=False))
        return 1
    finally:
        if bundle:
            playwright, context = bundle
            try:
                context.close()
            finally:
                playwright.stop()


if __name__ == "__main__":
    raise SystemExit(main())
