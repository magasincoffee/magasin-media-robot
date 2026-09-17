from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .browser import open_and_probe
from .classifier import classify_auth_state, classify_page_state
from .evidence import make_page_signals
from .models import DiscoveryConfig
from .runtime import build_runtime_paths, sanitize_error_message

ADAM = "Adam — Giọng hot tiktok"
ALT = "THEANH28 - Nữ"
KNOWN = (ADAM, ALT, "Tự động")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(v: str | None) -> str:
    return re.sub(r"\s+", " ", v or "").strip()


def _close_dialog(page: Any) -> None:
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    page.wait_for_timeout(400)


def _visible_main_exact(page: Any, label: str) -> bool:
    return bool(page.evaluate(r"""
(label) => {
  const norm=s=>(s||'').replace(/\s+/g,' ').trim();
  const vis=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
  const inDialog=e=>!!e.closest('[role="dialog"],dialog,.modal,.dialog,[class*="modal"],[class*="dialog"]');
  return Array.from(document.querySelectorAll('button,[role="button"],body *'))
    .some(e=>vis(e)&&!inDialog(e)&&norm(e.innerText||e.textContent)===label);
}
""", label))


def current_voice(page: Any) -> str | None:
    # Prefer the two voices involved in this recovery/roundtrip. This avoids
    # assuming the selected label must contain the Vietnamese word "giọng".
    for label in KNOWN:
        if _visible_main_exact(page, label):
            return label

    values = page.evaluate(r"""
() => Array.from(document.querySelectorAll('button,[role="button"]'))
.filter(el=>{const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0&&!el.closest('[role="dialog"],dialog,.modal,.dialog,[class*="modal"],[class*="dialog"]')})
.map(el=>(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim())
.filter(t=>t&&t.length<140)
""") or []
    for value in values:
        if "—" in value or " - " in value:
            low = value.lower()
            if any(x in low for x in ("giọng", "nữ", "nam")):
                return clean(value)
    return next((clean(v) for v in values if v.lower() == "tự động"), None)


def open_selector(page: Any, label: str) -> None:
    candidates = [
        page.get_by_role("button", name=label, exact=True),
        page.get_by_text(label, exact=True),
    ]
    for loc in candidates:
        try:
            for i in range(loc.count()):
                node = loc.nth(i)
                if node.is_visible():
                    node.click(timeout=4_000)
                    page.wait_for_timeout(700)
                    if page.locator('input:visible').count() > 0:
                        return
        except Exception:
            pass
    raise RuntimeError(f"Could not open voice selector from {label!r}")


def _search_input(page: Any):
    loc = page.locator('input:visible')
    if loc.count() < 1:
        raise RuntimeError("No visible search input in voice dialog")
    for i in range(loc.count()):
        candidate = loc.nth(i)
        placeholder = (candidate.get_attribute("placeholder") or "").lower()
        if any(k in placeholder for k in ("tìm", "search", "nhập")):
            return candidate
    return loc.last


def select_voice_in_open_dialog(page: Any, query: str, expected: str) -> dict[str, Any]:
    info: dict[str, Any] = {"query": query, "expected": expected}
    inp = _search_input(page)
    info["placeholder"] = inp.get_attribute("placeholder")
    inp.fill(query, timeout=4_000)
    page.wait_for_timeout(900)

    result = page.evaluate(r"""
(expected) => {
  const norm=s=>(s||'').replace(/\s+/g,' ').trim();
  const vis=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
  const exact=Array.from(document.querySelectorAll('*')).filter(vis).filter(e=>norm(e.innerText||e.textContent)===expected);
  for(const n of exact){
    let p=n;
    for(let depth=0;depth<9&&p;depth++,p=p.parentElement){
      const buttons=Array.from(p.querySelectorAll('button')).filter(vis);
      const use=buttons.find(b=>['Dùng','Sử dụng','Use'].includes(norm(b.innerText||b.textContent)));
      if(use){use.click();return {clicked:true,button:norm(use.innerText||use.textContent)};}
      const selected=buttons.find(b=>['Xóa','Xoá','Remove'].includes(norm(b.innerText||b.textContent)));
      if(selected){return {clicked:false,already_selected:true,button:norm(selected.innerText||selected.textContent)};}
    }
  }
  return {clicked:false,already_selected:false};
}
""", expected)
    info["result"] = result
    page.wait_for_timeout(1_000)
    return info


def set_voice(page: Any, target: str) -> dict[str, Any]:
    before = current_voice(page)
    if before == target:
        return {"before": before, "target": target, "already_target": True, "verified": True}
    if not before:
        raise RuntimeError("Current voice could not be determined on main page")

    open_selector(page, before)
    query = "Adam" if target == ADAM else "THEANH28"
    action = select_voice_in_open_dialog(page, query, target)
    _close_dialog(page)
    after = current_voice(page)
    verified = after == target
    return {"before": before, "target": target, "action": action, "after": after, "verified": verified}


def run(page: Any, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "schema_version": "1.0",
        "mode": "D5B3_VOICE_RESTORE_AND_ROUNDTRIP",
        "started_at": now(),
        "generate_clicked": False,
        "download_clicked": False,
        "target_final_voice": ADAM,
        "restore_errors": [],
    }

    _close_dialog(page)
    data["initial_voice"] = current_voice(page)
    page.screenshot(path=str(out_dir / "01_initial.png"), full_page=True)

    try:
        # Recovery first: the previous diagnostic run may have left THEANH28 selected.
        data["recovery_to_adam"] = set_voice(page, ADAM)
        page.screenshot(path=str(out_dir / "02_after_recovery.png"), full_page=True)
        if current_voice(page) != ADAM:
            raise RuntimeError(f"Recovery to Adam failed; observed={current_voice(page)!r}")

        # Controlled roundtrip: Adam -> THEANH28 -> Adam.
        data["roundtrip_to_alt"] = set_voice(page, ALT)
        page.screenshot(path=str(out_dir / "03_after_alt.png"), full_page=True)
        if current_voice(page) != ALT:
            raise RuntimeError(f"Alternate voice verification failed; observed={current_voice(page)!r}")

        data["roundtrip_back_to_adam"] = set_voice(page, ADAM)
        page.screenshot(path=str(out_dir / "04_after_adam.png"), full_page=True)
        if current_voice(page) != ADAM:
            raise RuntimeError(f"Roundtrip restore failed; observed={current_voice(page)!r}")

        data["roundtrip_pass"] = True
    except Exception as exc:
        data["roundtrip_pass"] = False
        data["error"] = sanitize_error_message(f"{type(exc).__name__}: {exc}")
    finally:
        # Hard final invariant: best-effort restore Adam even when a diagnostic step fails.
        try:
            _close_dialog(page)
            if current_voice(page) != ADAM:
                data["final_restore"] = set_voice(page, ADAM)
        except Exception as exc:
            data["restore_errors"].append(sanitize_error_message(f"{type(exc).__name__}: {exc}"))
        _close_dialog(page)

    data["final_voice"] = current_voice(page)
    data["restored"] = data["final_voice"] == ADAM
    data["pass"] = bool(data.get("roundtrip_pass") and data["restored"] and not data["restore_errors"])
    data["finished_at"] = now()
    page.screenshot(path=str(out_dir / "05_final.png"), full_page=True)

    out = out_dir / "d5b3_voice_restore.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="D5B3 SaydiVoice recovery + reversible voice roundtrip")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--chromium-executable")
    args = parser.parse_args(argv)

    runtime = build_runtime_paths(args.runtime_root) if args.runtime_root else build_runtime_paths()
    runtime.create()
    cfg = DiscoveryConfig(
        headless=False,
        navigation_timeout_ms=60_000,
        settle_ms=2_500,
        chromium_executable_path=args.chromium_executable,
    )
    bundle = None
    try:
        raw, bundle, page = open_and_probe(cfg, runtime)
        signals = make_page_signals(raw)
        state = classify_page_state(signals)
        auth = classify_auth_state(signals, state)
        if state != "TTS_READY" or auth != "AUTHENTICATED_OR_HIDDEN":
            print(json.dumps({"gate": "FAIL_SESSION", "state": state, "auth": auth}, ensure_ascii=False))
            return 20

        out = run(page, runtime.runs_dir / "d5b3_latest")
        data = json.loads(out.read_text(encoding="utf-8"))
        print(json.dumps({
            "gate": "PASS" if data["pass"] else "FAIL_D5B3",
            "initial": data.get("initial_voice"),
            "final": data.get("final_voice"),
            "roundtrip_pass": data.get("roundtrip_pass"),
            "restored": data.get("restored"),
            "restore_errors": data.get("restore_errors"),
            "generate_clicked": False,
            "download_clicked": False,
            "evidence": str(out),
        }, ensure_ascii=False, indent=2))
        return 0 if data["pass"] else 25
    except Exception as exc:
        print(json.dumps({"gate": "FAIL", "error": sanitize_error_message(f"{type(exc).__name__}: {exc}")}, ensure_ascii=False))
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
