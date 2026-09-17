from __future__ import annotations

import argparse, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .browser import open_and_probe
from .classifier import classify_auth_state, classify_page_state
from .evidence import make_page_signals
from .models import DiscoveryConfig
from .runtime import build_runtime_paths, sanitize_error_message


def now() -> str: return datetime.now(timezone.utc).isoformat()
def norm(v: str | None) -> str: return re.sub(r"\s+", " ", v or "").strip()


def current_voice(page: Any) -> str | None:
    vals = page.evaluate(r"""
() => Array.from(document.querySelectorAll('button,[role="button"]'))
.filter(el=>{const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0})
.map(el=>(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim())
.filter(t=>t && t.length<140)
""") or []
    for v in vals:
        if '—' in v and 'giọng' in v.lower(): return norm(v)
    return next((norm(v) for v in vals if v.lower()=='tự động'), None)


def click_text(page: Any, text: str) -> bool:
    for loc in (page.get_by_role('button', name=text, exact=True), page.get_by_text(text, exact=True)):
        try:
            if loc.count(): loc.first.click(timeout=4000); return True
        except Exception: pass
    return False


def slider_probe(page: Any) -> list[dict[str, Any]]:
    return page.evaluate(r"""
() => {
 const vis=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
 const tx=e=>(e?.innerText||e?.textContent||'').replace(/\s+/g,' ').trim();
 return Array.from(document.querySelectorAll('[role="slider"],input[type="range"],[aria-valuenow]')).filter(vis).map((el,i)=>{
   let p=el.parentElement, ctx=''; for(let n=0;n<4&&p;n++,p=p.parentElement){ctx=tx(p); if(ctx.length>0&&ctx.length<500) break;}
   const r=el.getBoundingClientRect();
   return {index:i,tag:el.tagName.toLowerCase(),role:el.getAttribute('role'),type:el.getAttribute('type'),value:el.value??null,
     aria_valuenow:el.getAttribute('aria-valuenow'),aria_valuemin:el.getAttribute('aria-valuemin'),aria_valuemax:el.getAttribute('aria-valuemax'),
     aria_label:el.getAttribute('aria-label'),context:ctx.slice(0,420),x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width)};
 });
}
""")


def parse_cards(page: Any) -> list[dict[str, str]]:
    return page.evaluate(r"""
() => {
 const vis=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
 const clean=s=>(s||'').replace(/\s+/g,' ').trim();
 const action=Array.from(document.querySelectorAll('button')).filter(vis).filter(b=>['Dùng','Xóa','Xoá'].includes(clean(b.innerText||b.textContent)));
 const out=[];
 for(const b of action){
   let p=b.parentElement, best=null;
   for(let i=0;i<6&&p;i++,p=p.parentElement){
     const leaves=Array.from(p.querySelectorAll('*')).filter(vis).filter(e=>e.childElementCount===0).map(e=>clean(e.innerText||e.textContent)).filter(Boolean);
     const meta=leaves.find(t=>/\b(Nam|Nữ)\b/.test(t)&&/Tiếng Việt/.test(t));
     if(meta){ const name=leaves.find(t=>t!==meta&&!['Dùng','Xóa','Xoá','☆','★','▶','►'].includes(t)&&t.length>1&&t.length<100); best={name,metadata:meta,action:clean(b.innerText||b.textContent)}; break; }
   }
   if(best && best.name && !out.some(x=>x.name===best.name)) out.push(best);
 }
 return out;
}
""") or []


def popup_options(page: Any, label: str) -> list[str]:
    before=set(page.evaluate(r"""() => Array.from(document.querySelectorAll('body *')).filter(e=>e.childElementCount===0).map(e=>(e.innerText||e.textContent||'').replace(/\s+/g,' ').trim()).filter(Boolean)""") or [])
    if not click_text(page,label): return []
    page.wait_for_timeout(400)
    after=page.evaluate(r"""() => Array.from(document.querySelectorAll('body *')).filter(e=>e.childElementCount===0).map(e=>(e.innerText||e.textContent||'').replace(/\s+/g,' ').trim()).filter(Boolean)""") or []
    try: page.keyboard.press('Escape')
    except Exception: pass
    out=[]
    for x in after:
        x=norm(x)
        if x and x not in before and x!=label and len(x)<=100 and x not in out: out.append(x)
    return out


def run(page: Any, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True,exist_ok=True)
    data={"schema_version":"1.1","mode":"D5A2_FULL_VOICE_STYLE_READ_ONLY","started_at":now(),"generate_clicked":False,"download_clicked":False}
    data['current_voice']=current_voice(page)
    data['sliders']=slider_probe(page)
    data['format_tabs']=page.evaluate(r"""() => Array.from(document.querySelectorAll('[role="tab"]')).map(e=>({text:(e.innerText||e.textContent||'').trim(),selected:e.getAttribute('aria-selected')})).filter(x=>['WAV','MP3','FLAC','OGG'].includes(x.text))""")
    data['settings_text']=page.evaluate(r"""() => ['Độ ổn định giọng','Biểu cảm','Tốc độ đọc','Ngắt nghỉ','Định dạng tệp'].map(k=>{const es=Array.from(document.querySelectorAll('*'));const e=es.find(x=>(x.innerText||x.textContent||'').trim()===k);return {label:k,parent:(e?.parentElement?.innerText||'').replace(/\s+/g,' ').trim().slice(0,300)}})""")
    page.screenshot(path=str(out_dir/'d5a2_main.png'),full_page=True)
    if not click_text(page,data['current_voice'] or 'Tự động'): raise RuntimeError('Could not open voice selector')
    page.wait_for_timeout(700)
    page.screenshot(path=str(out_dir/'d5a2_voice_page1.png'),full_page=True)
    data['filters']={
      'language': popup_options(page,'Tiếng Việt'),
      'gender': popup_options(page,'Tất cả giới tính'),
      'purpose': popup_options(page,'Tất cả mục đích'),
    }
    pages=[]; all_cards=[]
    for n in range(1,7):
        if n>1:
            loc=page.get_by_role('button',name=str(n),exact=True)
            if loc.count(): loc.last.click(timeout=4000); page.wait_for_timeout(500)
        cards=parse_cards(page)
        pages.append({'page':n,'cards':cards})
        for c in cards:
            if not any(x['name']==c['name'] for x in all_cards): all_cards.append(c)
    data['voice_pages']=pages; data['voices']=all_cards; data['voice_count_captured']=len(all_cards)
    data['metadata_dimensions']={
      'genders':sorted({(c['metadata'].split('·')[0].strip()) for c in all_cards if '·' in c['metadata']}),
      'regions':sorted({c['metadata'].split('·')[1].strip() for c in all_cards if len(c['metadata'].split('·'))>=4}),
      'purposes':sorted({'·'.join(c['metadata'].split('·')[3:]).strip() for c in all_cards if len(c['metadata'].split('·'))>=4}),
    }
    terms=['cảm xúc','tâm trạng','emotion','mood','tone','phong cách']
    body=page.locator('body').inner_text(timeout=3000).lower()
    data['explicit_emotion_control_hits']=[t for t in terms if t in body]
    data['finished_at']=now()
    try: page.keyboard.press('Escape')
    except Exception: pass
    out=out_dir/'d5a2_full.json'; out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); return out


def main(argv=None)->int:
    p=argparse.ArgumentParser(); p.add_argument('--runtime-root',type=Path); p.add_argument('--chromium-executable'); a=p.parse_args(argv)
    rt=build_runtime_paths(a.runtime_root) if a.runtime_root else build_runtime_paths(); rt.create(); cfg=DiscoveryConfig(headless=False,navigation_timeout_ms=60000,settle_ms=2500,chromium_executable_path=a.chromium_executable)
    bundle=None
    try:
        raw,bundle,page=open_and_probe(cfg,rt); sig=make_page_signals(raw); st=classify_page_state(sig); au=classify_auth_state(sig,st)
        if st!='TTS_READY' or au!='AUTHENTICATED_OR_HIDDEN': print(json.dumps({'gate':'FAIL_SESSION','state':st,'auth':au})); return 20
        out=run(page,rt.runs_dir/'d5a2_latest'); d=json.loads(out.read_text(encoding='utf-8'))
        print(json.dumps({'gate':'PASS','voices':d['voice_count_captured'],'sliders':len(d['sliders']),'emotion_hits':d['explicit_emotion_control_hits'],'generate_clicked':False,'download_clicked':False},ensure_ascii=False,indent=2)); return 0
    except Exception as e:
        print(json.dumps({'gate':'FAIL','error':sanitize_error_message(f'{type(e).__name__}: {e}')},ensure_ascii=False)); return 1
    finally:
        if bundle:
            pw,ctx=bundle
            try: ctx.close()
            finally: pw.stop()

if __name__=='__main__': raise SystemExit(main())
