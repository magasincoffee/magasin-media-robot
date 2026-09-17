from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .browser import open_and_probe
from .classifier import classify_auth_state, classify_page_state
from .evidence import make_page_signals
from .generation import _NetworkRecorder, _network_event_summary
from .models import DiscoveryConfig
from .runtime import build_runtime_paths

VOICE_BUTTONS = r"""
() => {
  const visible=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
  const text=e=>(e.innerText||e.textContent||'').replace(/\s+/g,' ').trim();
  return Array.from(document.querySelectorAll('button,[role="button"]')).filter(visible).map(e=>{const r=e.getBoundingClientRect();return {text:text(e),x:r.x,y:r.y,w:r.width,h:r.height}}).filter(x=>x.text);
}
"""

VOICE_DIALOG_STATE = r"""
() => {
  const visible=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
  const text=e=>(e?.innerText||e?.textContent||'').replace(/\s+/g,' ').trim();
  const dialog=Array.from(document.querySelectorAll('[role="dialog"]')).find(visible);
  if(!dialog) return {found:false,cards:[],pages:[],selects:[],count_text:null};
  const descRe=/^(Nam|Nữ|Trung tính)\s*·\s*/;
  const descriptors=Array.from(dialog.querySelectorAll('*')).filter(visible).filter(e=>e.childElementCount===0&&descRe.test(text(e)));
  const cards=[];
  for(const d of descriptors){
    let scope=d.parentElement;
    for(let i=0;i<6&&scope;i++,scope=scope.parentElement){
      const t=text(scope);
      if(t.length>420) continue;
      const leaves=Array.from(scope.querySelectorAll('*')).filter(visible).filter(e=>e.childElementCount===0).map(text).filter(Boolean);
      const names=leaves.filter(x=>!descRe.test(x)&&!['Dùng','☆','★','▶','►','›','‹'].includes(x)&&!/^[1-9]\d*$/.test(x)&&x.length<90);
      if(names.length){ cards.push({name:names[0],descriptor:text(d),use_available:leaves.includes('Dùng')}); break; }
    }
  }
  const pageButtons=Array.from(dialog.querySelectorAll('button')).filter(visible).map(e=>({text:text(e),disabled:e.disabled===true,aria_current:e.getAttribute('aria-current'),class_name:e.className||''})).filter(x=>/^\d+$/.test(x.text));
  const selects=Array.from(dialog.querySelectorAll('select')).map(e=>({value:e.value,options:Array.from(e.options||[]).map(o=>({text:text(o),value:o.value,selected:o.selected,disabled:o.disabled}))}));
  const countText=Array.from(dialog.querySelectorAll('*')).filter(visible).map(text).find(t=>/^\d+\s+giọng$/.test(t))||null;
  return {found:true,cards,pages:pageButtons,selects,count_text:countText};
}
"""

CONTROL_PROBE = r"""
() => {
  const visible=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
  const text=e=>(e?.innerText||e?.textContent||'').replace(/\s+/g,' ').trim();
  const all=Array.from(document.querySelectorAll('body *'));
  const inputs=Array.from(document.querySelectorAll('input,select')).map(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {tag:e.tagName.toLowerCase(),type:e.getAttribute('type'),value:e.value??null,min:e.getAttribute('min'),max:e.getAttribute('max'),step:e.getAttribute('step'),aria_label:e.getAttribute('aria-label'),aria_valuenow:e.getAttribute('aria-valuenow'),x:r.x,y:r.y,w:r.width,h:r.height,display:s.display,visibility:s.visibility,opacity:s.opacity,class_name:String(e.className||'').slice(0,180)}}).filter(x=>x.x>900||x.w===0||x.h===0);
  const candidates=[];
  for(const e of all){
    if(!visible(e)) continue;
    const r=e.getBoundingClientRect(); if(r.x<900||r.width<120||r.width>500||r.height<2||r.height>45) continue;
    const s=getComputedStyle(e); const cls=String(e.className||'');
    if(!cls && !e.getAttribute('role') && !e.getAttribute('aria-valuenow')) continue;
    candidates.push({tag:e.tagName.toLowerCase(),text:text(e).slice(0,100),role:e.getAttribute('role'),class_name:cls.slice(0,220),aria_valuenow:e.getAttribute('aria-valuenow'),aria_valuemin:e.getAttribute('aria-valuemin'),aria_valuemax:e.getAttribute('aria-valuemax'),x:r.x,y:r.y,w:r.width,h:r.height,background:s.backgroundColor,border_radius:s.borderRadius,cursor:s.cursor});
    if(candidates.length>=120) break;
  }
  const body=(document.body?.innerText||'').replace(/\s+/g,' ').trim();
  return {inputs,track_candidates:candidates,body_excerpt:body.slice(0,4500)};
}
"""

PAUSE_PROBE = r"""
() => {
  const visible=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
  const text=e=>(e?.innerText||e?.textContent||'').replace(/\s+/g,' ').trim();
  return Array.from(document.querySelectorAll('button,input,label,[role="button"],[role="switch"],[role="checkbox"]')).filter(visible).map(e=>{const r=e.getBoundingClientRect();return {tag:e.tagName.toLowerCase(),text:text(e).slice(0,120),type:e.getAttribute('type'),role:e.getAttribute('role'),checked:e.checked??null,aria_checked:e.getAttribute('aria-checked'),x:r.x,y:r.y,w:r.width,h:r.height}}).filter(x=>x.x>900);
}
"""


def _norm(v: str | None) -> str:
    return re.sub(r"\s+", " ", v or "").strip().lower()


def _is_tts_request(event: dict[str, Any]) -> bool:
    if event.get("kind") != "request": return False
    try: return urlsplit(str(event.get("url") or "")).path == "/api/tts"
    except Exception: return False


def _pick_voice(page: Any) -> str | None:
    excluded={"vi","en","cài ứng dụng","tạo giọng nói","thêm người nói","nhập kịch bản","phụ đề thành giọng nói","đang tắt","đang bật"}
    items=page.evaluate(VOICE_BUTTONS) or []
    good=[]
    for x in items:
        t=str(x.get('text') or '').strip(); xx=float(x.get('x') or 0); y=float(x.get('y') or 9999)
        if not t or _norm(t) in excluded or len(t)>100: continue
        if 180<=xx<=900 and 55<=y<=190: good.append(x)
    good.sort(key=lambda x:(abs(float(x.get('y') or 9999)-100),float(x.get('x') or 9999)))
    return str(good[0].get('text')) if good else None


def _dedupe_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out=[]; seen=set()
    for c in cards:
        key=(c.get('name'),c.get('descriptor'))
        if key in seen: continue
        seen.add(key); out.append(c)
    return out


def run(page: Any, evidence_dir: Path) -> Path:
    evidence_dir.mkdir(parents=True,exist_ok=True)
    test=page.context.new_page(); rec=_NetworkRecorder(); rec.attach(test)
    try:
        test.goto(page.url,wait_until='domcontentloaded',timeout=45000); test.wait_for_timeout(1600)
        mark=rec.mark(); controls=test.evaluate(CONTROL_PROBE) or {}
        voice=_pick_voice(test); pages_data=[]; all_cards=[]; filters={}; count_text=None
        if voice:
            loc=test.get_by_role('button',name=voice,exact=True)
            if loc.count()<1: loc=test.locator('button:visible').filter(has_text=voice)
            if loc.count()>0:
                loc.first.click(timeout=4000); test.wait_for_timeout(700)
                first=test.evaluate(VOICE_DIALOG_STATE) or {}
                count_text=first.get('count_text')
                for sel in first.get('selects') or []:
                    opts=sel.get('options') or []; labels=[_norm(str(o.get('text') or '')) for o in opts]
                    if any('tất cả ngôn ngữ' in x for x in labels): filters['language']=opts
                    elif any('tất cả giới tính' in x for x in labels): filters['gender']=opts
                    elif any('tất cả mục đích' in x for x in labels): filters['purpose']=opts
                page_nums=sorted({int(p['text']) for p in first.get('pages') or [] if str(p.get('text','')).isdigit()}) or [1]
                for n in page_nums:
                    if n!=1:
                        p=test.get_by_role('button',name=str(n),exact=True)
                        if p.count()<1: p=test.locator('[role="dialog"] button:visible').filter(has_text=str(n))
                        if p.count()>0:
                            p.first.click(timeout=3500); test.wait_for_timeout(650)
                    state=test.evaluate(VOICE_DIALOG_STATE) or {}
                    cards=_dedupe_cards(state.get('cards') or [])
                    pages_data.append({'page':n,'card_count':len(cards),'cards':cards})
                    all_cards.extend(cards)
                all_cards=_dedupe_cards(all_cards)
                test.screenshot(path=str(evidence_dir/'d5a2_voice_catalog.png'),full_page=True)
                test.keyboard.press('Escape'); test.wait_for_timeout(200)

        pause_before=test.evaluate(PAUSE_PROBE) or []
        pause_opened=False; pause_after=[]
        for label in ('Đang tắt','Đang bật'):
            b=test.get_by_role('button',name=label,exact=True)
            if b.count()>0:
                b.first.click(timeout=3000); test.wait_for_timeout(350); pause_opened=True; pause_after=test.evaluate(PAUSE_PROBE) or []; test.keyboard.press('Escape'); break
        test.screenshot(path=str(evidence_dir/'d5a2_controls.png'),full_page=True)

        rec.finalize_error_details(); events=rec.since(mark); tts=[e for e in events if _is_tts_request(e)]
        payload={
            'schema_version':'1.0','mode':'D5A2_FULL_VOICE_CATALOG_AND_CONTROL_PROBE','captured_at':datetime.now(timezone.utc).isoformat(),
            'voice_current':voice,'voice_count_text':count_text,'catalog_pages':pages_data,'catalog_voice_count':len(all_cards),'voices':all_cards,
            'filters':filters,'control_probe':controls,'pause_opened':pause_opened,'pause_controls_before':pause_before,'pause_controls_open':pause_after,
            'tts_request_count':len(tts),'network_summary':_network_event_summary(events),
            'privacy_note':'Read-only UI metadata only; no editor values, cookies, auth headers, request/response bodies, storage or credentials are persisted.',
            'notes':['No voice card Dùng button is clicked. Pagination and pause expansion are observation-only. No Generate or Download action is clicked.']
        }
        out=evidence_dir/'d5a2_catalog_controls.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8'); return out
    finally:
        try:test.close()
        except Exception:pass


def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--runtime-root',type=Path); ap.add_argument('--chromium-executable'); args=ap.parse_args(argv)
    runtime=build_runtime_paths(args.runtime_root) if args.runtime_root else build_runtime_paths(); runtime.create()
    cfg=DiscoveryConfig(headless=False,navigation_timeout_ms=60000,settle_ms=2500,chromium_executable_path=args.chromium_executable)
    bundle=None
    try:
        raw,bundle,page=open_and_probe(cfg,runtime); sig=make_page_signals(raw); state=classify_page_state(sig); auth=classify_auth_state(sig,state)
        if state!='TTS_READY' or auth!='AUTHENTICATED_OR_HIDDEN': print(json.dumps({'gate':'FAIL_SESSION','page_state':state,'auth_state':auth},ensure_ascii=False)); return 20
        out=run(page,runtime.runs_dir/'d5a2_catalog_controls_latest'); data=json.loads(out.read_text(encoding='utf-8'))
        passed=data.get('catalog_voice_count',0)>0 and data.get('tts_request_count',1)==0
        print(json.dumps({'gate':'PASS' if passed else 'REVIEW','evidence':str(out),'voice_count_text':data.get('voice_count_text'),'catalog_voice_count':data.get('catalog_voice_count'),'pages':[x.get('card_count') for x in data.get('catalog_pages',[])],'pause_opened':data.get('pause_opened'),'tts_request_count':data.get('tts_request_count')},ensure_ascii=False,indent=2)); return 0 if passed else 25
    finally:
        if bundle is not None:
            pw,ctx=bundle
            try:ctx.close()
            finally:pw.stop()

if __name__=='__main__': raise SystemExit(main())
