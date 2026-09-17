from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .browser import open_and_probe
from .classifier import classify_auth_state, classify_page_state
from .evidence import make_page_signals
from .models import DiscoveryConfig
from .runtime import build_runtime_paths, sanitize_error_message


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(v: str | None) -> str:
    return re.sub(r"\s+", " ", v or "").strip()


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = _norm(value)
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            out.append(value)
    return out


LEAF_SCRIPT = r"""
(root) => {
  const visible = (el) => {
    if (!el) return false;
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  };
  const text = (el) => (el.innerText || el.textContent || '').replace(/\s+/g,' ').trim();
  const base = root || document.body;
  return Array.from(base.querySelectorAll('*'))
    .filter(visible)
    .filter(el => el.childElementCount === 0)
    .filter(el => !el.closest('textarea,[contenteditable="true"],[role="textbox"]'))
    .map(el => text(el).slice(0,180))
    .filter(Boolean);
}
"""


def _snapshot_leaf_texts(page: Any) -> list[str]:
    try:
        return _dedupe(page.evaluate(LEAF_SCRIPT, None) or [])
    except Exception:
        return []


def _delta(before: list[str], after: list[str]) -> list[str]:
    base = {x.lower() for x in before}
    return [x for x in after if x.lower() not in base]


def _click_exact(page: Any, text: str) -> bool:
    candidates = [
        page.get_by_role("button", name=text, exact=True),
        page.get_by_text(text, exact=True),
    ]
    for loc in candidates:
        try:
            if loc.count() > 0:
                loc.first.click(timeout=4_000)
                return True
        except Exception:
            pass
    return False


def _capture_popup_options(page: Any, label: str) -> list[str]:
    before = _snapshot_leaf_texts(page)
    if not _click_exact(page, label):
        return []
    page.wait_for_timeout(500)
    after = _snapshot_leaf_texts(page)
    options = _delta(before, after)
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    page.wait_for_timeout(150)
    generic = {"xóa", "xoá", "clear", "+", "-", "×", label.lower()}
    return [x for x in options if x.lower() not in generic and len(x) <= 100]


def _capture_main_settings(page: Any) -> dict[str, Any]:
    return page.evaluate(r"""
() => {
  const norm = v => (v || '').replace(/\s+/g,' ').trim();
  const visible = el => {
    if (!el) return false; const s=getComputedStyle(el), r=el.getBoundingClientRect();
    return s.display!=='none' && s.visibility!=='hidden' && r.width>0 && r.height>0;
  };
  const text = el => norm(el?.innerText || el?.textContent || '');
  const labels = ['Độ ổn định giọng','Biểu cảm','Tốc độ đọc','Ngắt nghỉ','Định dạng tệp'];
  const all = Array.from(document.querySelectorAll('body *')).filter(visible);
  const out = {};
  for (const label of labels) {
    const lab = all.find(el => text(el) === label);
    if (!lab) { out[label] = {found:false}; continue; }
    let scope = lab.parentElement, controls=[];
    for (let i=0;i<5 && scope;i++,scope=scope.parentElement) {
      controls = Array.from(scope.querySelectorAll('input,[role="slider"],[aria-valuenow],button,[role="button"],[role="tab"],select,[role="combobox"]')).filter(visible);
      if (controls.length) break;
    }
    out[label] = {
      found:true,
      text_hint:text(lab.parentElement || lab).slice(0,300),
      controls:controls.slice(0,12).map(el => ({
        tag:el.tagName?.toLowerCase()||null,
        role:el.getAttribute('role'),
        type:el.getAttribute('type'),
        text:text(el).slice(0,100),
        value:['range','number'].includes(el.getAttribute('type')) ? el.value : null,
        aria_valuenow:el.getAttribute('aria-valuenow'),
        aria_valuemin:el.getAttribute('aria-valuemin'),
        aria_valuemax:el.getAttribute('aria-valuemax'),
        aria_selected:el.getAttribute('aria-selected'),
        aria_checked:el.getAttribute('aria-checked'),
        aria_label:el.getAttribute('aria-label'),
      }))
    };
  }
  return out;
}
""")


def _find_current_voice(page: Any) -> str | None:
    try:
        vals = page.evaluate(r"""
() => Array.from(document.querySelectorAll('button,[role="button"]'))
 .filter(el => { const s=getComputedStyle(el),r=el.getBoundingClientRect(); return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0; })
 .map(el => (el.innerText||el.textContent||'').replace(/\s+/g,' ').trim())
 .filter(t => t && !['Tạo giọng nói','Cài ứng dụng'].includes(t))
""") or []
        for v in vals:
            if "—" in v or "giọng" in v.lower() or v.lower() == "tự động":
                if len(v) <= 120:
                    return _norm(v)
    except Exception:
        pass
    return None


def _scroll_dialog_and_collect(page: Any) -> list[str]:
    collected: list[str] = []
    for _ in range(18):
        collected.extend(_snapshot_leaf_texts(page))
        moved = page.evaluate(r"""
() => {
  const title = Array.from(document.querySelectorAll('*')).find(el => (el.innerText||el.textContent||'').trim()==='Chọn giọng');
  if (!title) return false;
  const roots=[]; let p=title.parentElement;
  for(let i=0;i<6&&p;i++,p=p.parentElement) roots.push(p);
  const modal = roots.find(x => x.querySelector('input[placeholder*="tìm"]')) || roots[roots.length-1];
  const nodes = [modal, ...Array.from(modal?.querySelectorAll('*')||[])];
  const scrollable = nodes.filter(el => el && el.scrollHeight > el.clientHeight + 40)
    .sort((a,b)=>(b.scrollHeight-b.clientHeight)-(a.scrollHeight-a.clientHeight))[0];
  if (!scrollable) return false;
  const before=scrollable.scrollTop;
  scrollable.scrollTop = Math.min(scrollable.scrollTop + Math.max(300, scrollable.clientHeight*0.8), scrollable.scrollHeight);
  return scrollable.scrollTop > before + 2;
}
""")
        page.wait_for_timeout(250)
        if not moved:
            break
    generic = {
        "chọn giọng","khám phá","đã chọn","giọng của tôi","yêu thích","xóa","xoá",
        "tất cả ngôn ngữ","tất cả giới tính","tất cả mục đích"
    }
    cleaned = []
    for x in _dedupe(collected):
        k=x.lower()
        if k in generic or len(x)>150 or re.fullmatch(r"\d+\s+giọng", k):
            continue
        if "nhập để tìm kiếm" in k:
            continue
        cleaned.append(x)
    return cleaned


def run_d5a(page: Any, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema_version":"1.0",
        "mode":"D5A_VOICE_STYLE_READ_ONLY_DISCOVERY",
        "started_at":_now(),
        "generate_clicked":False,
        "download_clicked":False,
    }
    payload["current_voice"] = _find_current_voice(page)
    payload["main_settings"] = _capture_main_settings(page)
    page.screenshot(path=str(out_dir / "d5a_main.png"), full_page=True)

    current = payload["current_voice"] or "Tự động"
    opened = _click_exact(page, current)
    if not opened and current != "Tự động":
        opened = _click_exact(page, "Tự động")
    payload["voice_dialog_opened"] = opened
    if opened:
        page.wait_for_timeout(700)
        page.screenshot(path=str(out_dir / "d5a_voice_dialog.png"), full_page=True)
        payload["voice_surface_labels"] = _scroll_dialog_and_collect(page)
        payload["voice_filters"] = {
            "language": _capture_popup_options(page, "Tất cả ngôn ngữ"),
            "gender": _capture_popup_options(page, "Tất cả giới tính"),
            "purpose": _capture_popup_options(page, "Tất cả mục đích"),
        }
        payload["style_keyword_hits"] = [
            x for x in payload["voice_surface_labels"]
            if any(k in x.lower() for k in ["cảm xúc","tâm trạng","phong cách","tone","mood","emotion","mục đích","giọng"])
        ]
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
    payload["finished_at"] = _now()
    out = out_dir / "d5a_voice_style.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def build_parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(description="SaydiVoice D5A read-only voice/style discovery")
    p.add_argument("--runtime-root", type=Path)
    p.add_argument("--chromium-executable")
    return p


def main(argv: list[str] | None=None) -> int:
    args=build_parser().parse_args(argv)
    runtime=build_runtime_paths(args.runtime_root) if args.runtime_root else build_runtime_paths()
    runtime.create()
    cfg=DiscoveryConfig(headless=False,navigation_timeout_ms=60_000,settle_ms=2_500,chromium_executable_path=args.chromium_executable)
    bundle=None
    try:
        raw,bundle,page=open_and_probe(cfg,runtime)
        signals=make_page_signals(raw)
        state=classify_page_state(signals); auth=classify_auth_state(signals,state)
        if state!="TTS_READY" or auth!="AUTHENTICATED_OR_HIDDEN":
            print(json.dumps({"gate":"FAIL_SESSION","page_state":state,"auth_state":auth},ensure_ascii=False)); return 20
        out=run_d5a(page,runtime.runs_dir / "d5a_latest")
        data=json.loads(out.read_text(encoding="utf-8"))
        print(json.dumps({"gate":"PASS","evidence":str(out),"current_voice":data.get("current_voice"),"voice_dialog_opened":data.get("voice_dialog_opened"),"labels":len(data.get("voice_surface_labels") or []),"generate_clicked":False,"download_clicked":False},ensure_ascii=False,indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"gate":"FAIL","error":sanitize_error_message(f"{type(exc).__name__}: {exc}")},ensure_ascii=False)); return 1
    finally:
        if bundle is not None:
            playwright,context=bundle
            try: context.close()
            finally: playwright.stop()


if __name__=="__main__":
    raise SystemExit(main())
