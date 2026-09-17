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


def visible_button_texts(page: Any) -> list[str]:
    return page.evaluate(r"""
() => Array.from(document.querySelectorAll('button,[role="button"]'))
.filter(el=>{const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0})
.map(el=>(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim())
.filter(Boolean)
""") or []


def current_voice(page: Any) -> str | None:
    vals=[clean(x) for x in visible_button_texts(page)]
    preferred=["Adam — Giọng hot tiktok","THEANH28 - Nữ","Tự động"]
    for p in preferred:
        if p in vals:return p
    for v in vals:
        low=v.lower()
        if len(v)<=120 and v not in {"Tạo giọng nói","Chọn giọng"} and ("giọng" in low or " - nữ" in low or " - nam" in low):
            return v
    return None


def selected_format(page: Any) -> str | None:
    vals=page.evaluate(r"""
() => Array.from(document.querySelectorAll('.fmt-tab')).map(el=>({t:(el.innerText||el.textContent||'').trim(),c:String(el.className||''),s:el.getAttribute('aria-selected')}))
""") or []
    for x in vals:
        if x.get('s')=='true' or 'active' in x.get('c','').split():
            return x.get('t')
    return None


def slider_state(page: Any) -> list[dict[str,Any]]:
    return page.evaluate(r"""
() => Array.from(document.querySelectorAll('.slider')).map((el,i)=>{
 const r=el.getBoundingClientRect(),f=el.querySelector('.slider-fill')?.getBoundingClientRect();
 return {index:i,width:r.width,ratio:(f&&r.width)?f.width/r.width:null};
})
""") or []


def text_exact(page: Any, label: str) -> bool:
    return bool(page.get_by_text(label, exact=True).count())


def section_text(page: Any, label: str) -> str:
    return page.evaluate(r"""
(label)=>{const n=s=>(s||'').replace(/\s+/g,' ').trim();const v=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};const a=Array.from(document.querySelectorAll('*')).find(e=>v(e)&&n(e.innerText||e.textContent)===label);if(!a)return '';const p=a.closest('.st-section')||a.parentElement;return n(p?.innerText||p?.textContent||'');}
""",label) or ''


def quota_text(page: Any) -> str | None:
    body = page.locator('body').inner_text()
    for pattern in [
        r"Còn\s+\d+\s+lượt\s+tạo\s+miễn\s+phí[^\r\n]*",
        r"\d[\d,\.]*\s*/\s*20,?000[^\r\n]*",
    ]:
        m = re.search(pattern, body, re.I)
        if m:
            return clean(m.group(0))
    return None


def run(page: Any,out_dir: Path)->Path:
    out_dir.mkdir(parents=True,exist_ok=True)
    buttons=visible_button_texts(page)
    generate=page.get_by_role('button',name='Tạo giọng nói',exact=True)
    editor=page.locator('[contenteditable="true"]')
    fmt=selected_format(page)
    sliders=slider_state(page)
    formats_present=[x for x in ['WAV','MP3','FLAC','OGG'] if page.locator('.fmt-tab').filter(has_text=re.compile(rf'^{re.escape(x)}$')).count()]
    data={
      'schema_version':'1.1','mode':'D6_AUTHENTICATED_GENERATION_PREFLIGHT','started_at':now(),
      'generate_clicked':False,'download_clicked':False,
      'voice':current_voice(page),
      'generate_present':generate.count()>0,
      'generate_enabled':bool(generate.count()>0 and generate.first.is_enabled()),
      'editor_present':editor.count()>0,
      'slider_count':len(sliders),'sliders':sliders,
      'stability_section':section_text(page,'Độ ổn định giọng'),
      'speed_section':section_text(page,'Tốc độ đọc'),
      'format':fmt,
      'formats_present':formats_present,
      'pause_present':text_exact(page,'Ngắt nghỉ'),
      'quota_text':quota_text(page),
      'quota_visibility':'VISIBLE' if quota_text(page) else 'NOT_VISIBLE_AUTH_SESSION',
      'button_sample':buttons[:25],
    }
    data['checks']={
      'voice':bool(data['voice']),
      'generate':bool(data['generate_present'] and data['generate_enabled']),
      'editor':bool(data['editor_present']),
      'sliders':len(sliders)>=2,
      'format':fmt in {'WAV','MP3','FLAC','OGG'} and len(formats_present)>=4,
      'pause':bool(data['pause_present']),
    }
    data['pass']=all(data['checks'].values())
    data['finished_at']=now()
    page.screenshot(path=str(out_dir/'d6_preflight.png'),full_page=True)
    out=out_dir/'d6_generation_preflight.json'
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    return out


def main(argv=None)->int:
    p=argparse.ArgumentParser();p.add_argument('--runtime-root',type=Path);p.add_argument('--chromium-executable');a=p.parse_args(argv)
    rt=build_runtime_paths(a.runtime_root) if a.runtime_root else build_runtime_paths();rt.create();bundle=None
    cfg=DiscoveryConfig(headless=False,navigation_timeout_ms=60_000,settle_ms=2_500,chromium_executable_path=a.chromium_executable)
    try:
        raw,bundle,page=open_and_probe(cfg,rt);sig=make_page_signals(raw);state=classify_page_state(sig);auth=classify_auth_state(sig,state)
        if state!='TTS_READY' or auth!='AUTHENTICATED_OR_HIDDEN':
            print(json.dumps({'gate':'FAIL_SESSION','state':state,'auth':auth},ensure_ascii=False));return 20
        out=run(page,rt.runs_dir/'d6_preflight_latest');d=json.loads(out.read_text(encoding='utf-8'))
        print(json.dumps({'gate':'PASS' if d['pass'] else 'FAIL_D6','checks':d['checks'],'voice':d['voice'],'format':d['format'],'formats_present':d['formats_present'],'quota_visibility':d['quota_visibility'],'quota_text':d['quota_text'],'generate_clicked':False,'download_clicked':False,'evidence':str(out)},ensure_ascii=False,indent=2))
        return 0 if d['pass'] else 25
    except Exception as exc:
        print(json.dumps({'gate':'FAIL','error':sanitize_error_message(f'{type(exc).__name__}: {exc}')},ensure_ascii=False));return 1
    finally:
        if bundle:
            pw,ctx=bundle
            try:ctx.close()
            finally:pw.stop()

if __name__=='__main__':raise SystemExit(main())
