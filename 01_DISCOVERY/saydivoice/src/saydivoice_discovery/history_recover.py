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

        target_voice = "SG - Chí Đạt"
        voice_item = page.get_by_text(target_voice, exact=True).first
        if voice_item.count() < 1:
            raise RuntimeError("Latest SG - Chí Đạt history item not visible")

        history_json = page.evaluate(
            r"""
async () => {
  const r = await fetch('/api/library/history', {credentials:'include'});
  if(!r.ok) return {__fetch_error__: r.status};
  return await r.json();
}
"""
        )

        def find_target_records(value):
            found = []
            if isinstance(value, dict):
                scalar_text = " ".join(
                    str(v) for v in value.values()
                    if isinstance(v, (str, int, float, bool))
                )
                if target_voice in scalar_text:
                    found.append(value)
                for child in value.values():
                    found.extend(find_target_records(child))
            elif isinstance(value, list):
                for child in value:
                    found.extend(find_target_records(child))
            return found

        records = find_target_records(history_json)
        safe_records = []
        candidate_urls = []
        for rec in records:
            safe = {}
            for key, value in rec.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    low_key = str(key).lower()
                    if isinstance(value, str) and (value.startswith("http://") or value.startswith("https://")):
                        safe[key] = value.split("?", 1)[0]
                        if any(tok in low_key for tok in ("url", "audio", "file", "download", "src")):
                            candidate_urls.append(value)
                    elif "token" not in low_key and "secret" not in low_key and "auth" not in low_key:
                        safe[key] = value
            safe_records.append(safe)

        (evidence_dir / "history_target_records.json").write_text(
            json.dumps(safe_records[:10], ensure_ascii=False, indent=2), encoding="utf-8"
        )

        out = args.output.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        async_fetch_script = r"""
async (url) => {
  try {
    const r = await fetch(url, {credentials:'include'});
    if(!r.ok) return {ok:false,status:r.status};
    const buf = await r.arrayBuffer();
    const bytes = new Uint8Array(buf);
    let binary = '';
    const chunk = 0x8000;
    for(let i=0;i<bytes.length;i+=chunk){
      binary += String.fromCharCode(...bytes.subarray(i, i+chunk));
    }
    return {ok:true,status:r.status,content_type:r.headers.get('content-type')||'',b64:btoa(binary)};
  } catch(e) {
    return {ok:false,error:String(e)};
  }
}
"""

        recovered = None
        import base64
        for url in candidate_urls:
            fetched = page.evaluate(async_fetch_script, url)
            if fetched.get("ok") and fetched.get("b64"):
                raw_audio = base64.b64decode(fetched["b64"])
                if len(raw_audio) > 1000:
                    out.write_bytes(raw_audio)
                    recovered = {
                        "method": "history_api_url",
                        "content_type": fetched.get("content_type"),
                        "source_url": url.split("?", 1)[0],
                    }
                    break

        if recovered is None:
            # History cards expose an overflow "..." menu. Open the menu for the
            # newest SG - Chí Đạt row and download the existing audio from there.
            tagged = page.evaluate(
                r"""
(targetVoice) => {
  const norm=(v)=>(v||'').replace(/\s+/g,' ').trim();
  const vis=(e)=>{if(!e)return false;const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
  const nodes=Array.from(document.querySelectorAll('body *')).filter(vis)
    .filter(e=>norm(e.innerText||e.textContent)===targetVoice);
  for(const n of nodes){
    let p=n;
    for(let d=0; d<10 && p; d++, p=p.parentElement){
      const buttons=Array.from(p.querySelectorAll('button,[role="button"]')).filter(vis);
      const menu=buttons.find(b=>{
        const txt=norm(b.innerText||b.textContent);
        const aria=norm(b.getAttribute('aria-label')||'');
        return txt==='...' || txt==='…' || /more|thêm|tuỳ chọn|tùy chọn|menu/i.test(aria);
      });
      if(menu){
        menu.setAttribute('data-magasin-history-menu','1');
        return {found:true,row_text:norm(p.innerText||p.textContent).slice(0,300)};
      }
    }
  }
  return {found:false};
}
""",
                target_voice,
            )
            if tagged.get("found"):
                page.locator('[data-magasin-history-menu="1"]').first.click(timeout=5_000)
                page.wait_for_timeout(500)

                menu_text = clean(page.locator("body").inner_text())
                (evidence_dir / "history_menu_body.txt").write_text(menu_text[:6000], encoding="utf-8")

                download_control = page.get_by_text(re.compile(r"^Tải(?: về| xuống)?$", re.I)).first
                if download_control.count() < 1:
                    download_control = page.get_by_role("button", name=re.compile(r"Tải|Download", re.I)).first
                if download_control.count() > 0:
                    try:
                        with page.expect_download(timeout=20_000) as info:
                            download_control.click(timeout=5_000)
                        download = info.value
                        download.save_as(str(out))
                        if out.exists() and out.stat().st_size > 1000:
                            recovered = {
                                "method": "history_overflow_menu_download",
                                "row_text": tagged.get("row_text"),
                            }
                    except Exception:
                        # Some menu actions navigate/fetch without a browser download event.
                        page.wait_for_timeout(800)

            if recovered is None and tagged.get("found"):
                # Final non-generative fallback: after opening the row menu, look for
                # an audio element/source associated with the selected history state.
                audio_srcs = page.eval_on_selector_all(
                    "audio", "els => els.map(e => e.currentSrc || e.src || '').filter(Boolean)"
                )
                for src in reversed(audio_srcs):
                    fetched = page.evaluate(async_fetch_script, src)
                    if fetched.get("ok") and fetched.get("b64"):
                        raw_audio = base64.b64decode(fetched["b64"])
                        if len(raw_audio) > 1000:
                            out.write_bytes(raw_audio)
                            recovered = {
                                "method": "history_menu_audio_element",
                                "content_type": fetched.get("content_type"),
                                "source_url": src.split("?", 1)[0],
                            }
                            break

        if recovered is None or not out.exists():
            raise RuntimeError("Existing SG - Chí Đạt history audio could not be recovered without regeneration")

        data = out.read_bytes()
        if not data:
            raise RuntimeError("Recovered history audio is empty")

        payload = {
            "schema_version": "1.0",
            "mode": "RECOVER_EXISTING_HISTORY_AUDIO_NO_GENERATE",
            "target_snippet": TARGET_SNIPPET,
            "generate_click_count": 0,
            "download_completed": True,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "output_path": str(out),
            "recovery": recovered,
            "history_records_matched": len(records),
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
