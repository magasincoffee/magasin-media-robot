from __future__ import annotations

import argparse, json, re
from pathlib import Path
from typing import Any

from .browser import open_and_probe
from .classifier import classify_auth_state, classify_page_state
from .evidence import make_page_signals
from .models import DiscoveryConfig
from .runtime import build_runtime_paths, sanitize_error_message

LABELS=['Độ ổn định giọng','Biểu cảm','Tốc độ đọc','Ngắt nghỉ','Định dạng tệp']

PROBE=r"""
(labels) => {
 const clean=s=>(s||'').replace(/\s+/g,' ').trim();
 const vis=e=>{if(!e)return false;const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
 const all=Array.from(document.querySelectorAll('body *'));
 const rec=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {tag:e.tagName.toLowerCase(),text:clean(e.innerText||e.textContent).slice(0,180),role:e.getAttribute('role'),type:e.getAttribute('type'),aria_label:e.getAttribute('aria-label'),aria_valuenow:e.getAttribute('aria-valuenow'),tabindex:e.getAttribute('tabindex'),class_name:String(e.className||'').slice(0,220),x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height),cursor:s.cursor,position:s.position};};
 const out={};
 for(const label of labels){
  const lab=all.find(e=>vis(e)&&clean(e.innerText||e.textContent)===label);
  if(!lab){out[label]={found:false};continue;}
  let root=lab.parentElement;
  while(root&&root.parentElement){const r=root.getBoundingClientRect();if(r.width>300&&r.height>55&&r.height<360)break;root=root.parentElement;}
  const cand=Array.from((root||lab.parentElement).querySelectorAll('*')).filter(vis).filter(e=>{
    const s=getComputedStyle(e),r=e.getBoundingClientRect();
    return e!==lab && (e.matches('input,button,[role],[tabindex]') || s.cursor==='pointer' || s.cursor==='grab' || s.cursor==='ew-resize' || (r.height<=40&&r.width>=80));
  }).slice(0,80).map(rec);
  out[label]={found:true,label:rec(lab),root:rec(root||lab.parentElement),candidates:cand};
 }
 out['all_range_like']=all.filter(vis).filter(e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return e.matches('input[type="range"],[role="slider"],[aria-valuenow]')||s.cursor==='grab'||s.cursor==='ew-resize'||(r.width>140&&r.height<=20&&r.x>window.innerWidth*0.55)}).slice(0,100).map(rec);
 return out;
}
"""

def main(argv=None)->int:
 p=argparse.ArgumentParser();p.add_argument('--chromium-executable');p.add_argument('--runtime-root',type=Path);a=p.parse_args(argv)
 rt=build_runtime_paths(a.runtime_root) if a.runtime_root else build_runtime_paths();rt.create();cfg=DiscoveryConfig(headless=False,navigation_timeout_ms=60000,settle_ms=2500,chromium_executable_path=a.chromium_executable);bundle=None
 try:
  raw,bundle,page=open_and_probe(cfg,rt);sig=make_page_signals(raw);st=classify_page_state(sig);au=classify_auth_state(sig,st)
  if st!='TTS_READY' or au!='AUTHENTICATED_OR_HIDDEN':print(json.dumps({'gate':'FAIL_SESSION','state':st,'auth':au}));return 20
  data={'mode':'D5A3_CONTROL_DOM_READ_ONLY','generate_clicked':False,'download_clicked':False,'controls':page.evaluate(PROBE,LABELS)}
  outdir=rt.runs_dir/'d5a3_latest';outdir.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(outdir/'d5a3_controls.png'),full_page=True);out=outdir/'d5a3_controls.json';out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps({'gate':'PASS','evidence':str(out),'range_like':len(data['controls'].get('all_range_like') or []),'generate_clicked':False,'download_clicked':False},ensure_ascii=False,indent=2));return 0
 except Exception as e:
  print(json.dumps({'gate':'FAIL','error':sanitize_error_message(f'{type(e).__name__}: {e}')},ensure_ascii=False));return 1
 finally:
  if bundle:
   pw,ctx=bundle
   try:ctx.close()
   finally:pw.stop()

if __name__=='__main__':raise SystemExit(main())
