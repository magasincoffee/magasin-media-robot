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


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(v: str | None) -> str:
    return re.sub(r"\s+", " ", v or "").strip()


def current_voice(page: Any) -> str | None:
    values = page.evaluate(r"""
() => Array.from(document.querySelectorAll('button,[role="button"]'))
.filter(el=>{const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0})
.map(el=>(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim())
.filter(t=>t && t.length<140)
""") or []
    for v in values:
        if "—" in v and "giọng" in v.lower():
            return clean(v)
    for v in values:
        if v.lower() == "tự động":
            return clean(v)
    return None


def open_selector(page: Any, label: str) -> None:
    candidates = [
        page.get_by_role('button', name=label, exact=True),
        page.get_by_text(label, exact=True),
    ]
    for loc in candidates:
        try:
            if loc.count() > 0 and loc.first.is_visible():
                loc.first.click(timeout=4000)
                page.wait_for_timeout(700)
                return
        except Exception:
            pass
    raise RuntimeError(f"Could not open voice selector from {label!r}")


def visible_inputs(page: Any) -> list[dict[str, Any]]:
    return page.evaluate(r"""
() => Array.from(document.querySelectorAll('input')).filter(el=>{
 const s=getComputedStyle(el),r=el.getBoundingClientRect();
 return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0;
}).map((el,i)=>({index:i,placeholder:el.getAttribute('placeholder'),id:el.id||null,class_name:String(el.className||''),x:el.getBoundingClientRect().x,y:el.getBoundingClientRect().y,w:el.getBoundingClientRect().width}))
""") or []


def search_input(page: Any):
    # Critical: only visible inputs. The page also contains hidden translation/search inputs.
    loc = page.locator('input:visible')
    count = loc.count()
    if count < 1:
        raise RuntimeError('No visible input in voice dialog')
    for i in range(count):
        candidate = loc.nth(i)
        try:
            ph = (candidate.get_attribute('placeholder') or '').lower()
            if 'tìm' in ph or 'search' in ph or 'nhập' in ph:
                return candidate
        except Exception:
            pass
    return loc.last


def use_searched_voice(page: Any, query: str, expected_name: str) -> dict[str, Any]:
    info: dict[str, Any] = {"query": query, "expected": expected_name, "visible_inputs": visible_inputs(page)}
    inp = search_input(page)
    info['chosen_placeholder'] = inp.get_attribute('placeholder')
    inp.fill(query, timeout=4000)
    page.wait_for_timeout(800)
    info['body_hits'] = page.evaluate(r"""
(q) => {
 const clean=s=>(s||'').replace(/\s+/g,' ').trim();
 const vis=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
 return Array.from(document.querySelectorAll('*')).filter(vis).map(e=>clean(e.innerText||e.textContent)).filter(t=>t&&t.toLowerCase().includes(q.toLowerCase())&&t.length<180).slice(0,30);
}
""", query)
    clicked = page.evaluate(r"""
(args) => {
 const [query, expected] = args;
 const clean=s=>(s||'').replace(/\s+/g,' ').trim();
 const vis=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
 const nodes=Array.from(document.querySelectorAll('*')).filter(vis).filter(e=>{
   const t=clean(e.innerText||e.textContent);
   return t===expected || t.toLowerCase().includes(query.toLowerCase());
 }).sort((a,b)=>clean(a.innerText||a.textContent).length-clean(b.innerText||b.textContent).length);
 for(const n of nodes){
   let p=n;
   for(let depth=0;depth<8&&p;depth++,p=p.parentElement){
     const buttons=Array.from(p.querySelectorAll('button')).filter(vis);
     const use=buttons.find(b=>['Dùng','Sử dụng','Use'].includes(clean(b.innerText||b.textContent)));
     if(use){use.click();return {clicked:true,node:clean(n.innerText||n.textContent),button:clean(use.innerText||use.textContent)};}
   }
 }
 return {clicked:false};
}
""", [query, expected_name])
    info['click_result'] = clicked
    page.wait_for_timeout(1000)
    return info


def run(page: Any, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    original = current_voice(page)
    data: dict[str, Any] = {
        "schema_version": "1.0",
        "mode": "D5B2_VOICE_ROUNDTRIP",
        "started_at": now(),
        "generate_clicked": False,
        "download_clicked": False,
        "original_voice": original,
        "alternate_voice": "THEANH28 - Nữ",
        "restore_errors": [],
    }
    if not original:
        raise RuntimeError('Original voice not detected')
    page.screenshot(path=str(out_dir/'before.png'), full_page=True)
    changed = False
    try:
        open_selector(page, original)
        page.screenshot(path=str(out_dir/'dialog_before_change.png'), full_page=True)
        data['change_action'] = use_searched_voice(page, 'THEANH28', data['alternate_voice'])
        data['voice_after_change'] = current_voice(page)
        changed = data['voice_after_change'] is not None and data['voice_after_change'] != original
        data['changed'] = changed
        page.screenshot(path=str(out_dir/'after_change.png'), full_page=True)
        if not changed:
            raise RuntimeError(f"Voice did not change; observed={data['voice_after_change']!r}")

        open_selector(page, data['voice_after_change'])
        data['restore_action'] = use_searched_voice(page, 'Adam', original)
        data['voice_after_restore'] = current_voice(page)
        data['restored'] = data['voice_after_restore'] == original
        if not data['restored']:
            raise RuntimeError(f"Voice did not restore; observed={data['voice_after_restore']!r}")
    except Exception as exc:
        data['error'] = sanitize_error_message(f"{type(exc).__name__}: {exc}")
        # Best effort restore only if the voice truly changed.
        try:
            try: page.keyboard.press('Escape')
            except Exception: pass
            current = current_voice(page)
            if current and current != original:
                open_selector(page, current)
                data['final_restore_action'] = use_searched_voice(page, 'Adam', original)
        except Exception as restore_exc:
            data['restore_errors'].append(sanitize_error_message(f"{type(restore_exc).__name__}: {restore_exc}"))
    finally:
        try: page.keyboard.press('Escape')
        except Exception: pass
        page.wait_for_timeout(300)

    data['final_voice'] = current_voice(page)
    data['restored'] = data['final_voice'] == original
    data['pass'] = bool(changed and data['restored'] and not data['restore_errors'])
    data['finished_at'] = now()
    page.screenshot(path=str(out_dir/'after_restored.png'), full_page=True)
    out=out_dir/'d5b2_voice_roundtrip.json'
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    return out


def main(argv=None)->int:
    p=argparse.ArgumentParser();p.add_argument('--runtime-root',type=Path);p.add_argument('--chromium-executable');a=p.parse_args(argv)
    rt=build_runtime_paths(a.runtime_root) if a.runtime_root else build_runtime_paths();rt.create()
    cfg=DiscoveryConfig(headless=False,navigation_timeout_ms=60_000,settle_ms=2500,chromium_executable_path=a.chromium_executable);bundle=None
    try:
        raw,bundle,page=open_and_probe(cfg,rt);sig=make_page_signals(raw);state=classify_page_state(sig);auth=classify_auth_state(sig,state)
        if state!='TTS_READY' or auth!='AUTHENTICATED_OR_HIDDEN':
            print(json.dumps({'gate':'FAIL_SESSION','state':state,'auth':auth},ensure_ascii=False));return 20
        out=run(page,rt.runs_dir/'d5b2_latest');d=json.loads(out.read_text(encoding='utf-8'))
        print(json.dumps({'gate':'PASS' if d['pass'] else 'FAIL_D5B2','original':d['original_voice'],'after_change':d.get('voice_after_change'),'final':d.get('final_voice'),'restored':d['restored'],'generate_clicked':False,'download_clicked':False,'evidence':str(out)},ensure_ascii=False,indent=2))
        return 0 if d['pass'] else 25
    except Exception as exc:
        print(json.dumps({'gate':'FAIL','error':sanitize_error_message(f'{type(exc).__name__}: {exc}')},ensure_ascii=False));return 1
    finally:
        if bundle:
            pw,ctx=bundle
            try:ctx.close()
            finally:pw.stop()

if __name__=='__main__':raise SystemExit(main())
