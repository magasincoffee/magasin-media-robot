from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .browser import open_and_probe
from .classifier import classify_auth_state, classify_page_state
from .evidence import make_page_signals
from .models import DiscoveryConfig
from .runtime import build_runtime_paths, sanitize_error_message

STABILITY_SWEEP = [0.20, 0.40, 0.60, 0.80]
SPEED_SWEEP = [0.20, 0.35, 0.50, 0.65, 0.80]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slider_state(page: Any, index: int) -> dict[str, Any]:
    return page.evaluate(r"""
(index) => {
  const el=Array.from(document.querySelectorAll('.slider'))[index];
  if(!el) return {found:false};
  const r=el.getBoundingClientRect();
  const fill=el.querySelector('.slider-fill')?.getBoundingClientRect();
  const knob=el.querySelector('.slider-knob')?.getBoundingClientRect();
  return {
    found:true,
    width:r.width,
    ratio:(fill&&r.width)?fill.width/r.width:null,
    fill_width:fill?.width??null,
    knob_x:knob?.x??null,
  };
}
""", index)


def click_slider_ratio(page: Any, index: int, ratio: float) -> None:
    loc = page.locator('.slider').nth(index)
    box = loc.bounding_box()
    if not box:
        raise RuntimeError(f"slider {index} missing")
    ratio = max(0.04, min(0.96, ratio))
    page.mouse.click(box['x'] + box['width'] * ratio, box['y'] + max(1.0, box['height'] / 2))
    page.wait_for_timeout(650)


def section_text(page: Any, label: str) -> str:
    return page.evaluate(r"""
(label) => {
  const norm=s=>(s||'').replace(/\s+/g,' ').trim();
  const vis=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
  const node=Array.from(document.querySelectorAll('*')).find(e=>vis(e)&&norm(e.innerText||e.textContent)===label);
  if(!node) return '';
  const sec=node.closest('.st-section')||node.parentElement;
  return norm(sec?.innerText||sec?.textContent||'');
}
""", label) or ""


def selected_format(page: Any) -> str | None:
    values = page.evaluate(r"""
() => Array.from(document.querySelectorAll('.fmt-tab')).map(el=>({text:(el.innerText||el.textContent||'').trim(),cls:String(el.className||'')}))
""") or []
    for item in values:
        if 'active' in item.get('cls','').split():
            return item.get('text')
    return None


def pause_structure(page: Any) -> dict[str, Any]:
    return page.evaluate(r"""
() => {
  const norm=s=>(s||'').replace(/\s+/g,' ').trim();
  const vis=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
  const label=Array.from(document.querySelectorAll('*')).find(e=>vis(e)&&norm(e.innerText||e.textContent)==='Ngắt nghỉ');
  if(!label) return {found:false};
  const sec=label.closest('.st-section')||label.parentElement;
  const controls=Array.from(sec.querySelectorAll('input,button,select,[role="switch"],[role="slider"]')).filter(vis).map((el,i)=>({
    index:i,
    tag:el.tagName.toLowerCase(),
    type:el.getAttribute('type'),
    role:el.getAttribute('role'),
    text:norm(el.innerText||el.textContent).slice(0,120),
    value:('value' in el)?String(el.value):null,
    checked:('checked' in el)?Boolean(el.checked):null,
    min:el.getAttribute('min'),
    max:el.getAttribute('max'),
    step:el.getAttribute('step'),
    placeholder:el.getAttribute('placeholder'),
    aria_label:el.getAttribute('aria-label'),
    aria_checked:el.getAttribute('aria-checked'),
    class_name:String(el.className||'').slice(0,180),
  }));
  return {found:true,text:norm(sec.innerText||sec.textContent),controls};
}
""") or {"found": False}


def run(page: Any, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    original_stability = slider_state(page, 0)
    original_speed = slider_state(page, 1)
    original_format = selected_format(page)
    data: dict[str, Any] = {
        'schema_version': '1.0',
        'mode': 'D8A_REVERSIBLE_CONTROL_CALIBRATION',
        'started_at': now(),
        'generate_clicked': False,
        'download_clicked': False,
        'original': {
            'stability_slider': original_stability,
            'speed_slider': original_speed,
            'stability_section': section_text(page, 'Độ ổn định giọng'),
            'speed_section': section_text(page, 'Tốc độ đọc'),
            'format': original_format,
            'pause': pause_structure(page),
        },
        'stability_map': [],
        'speed_map': [],
        'restore_errors': [],
    }

    page.screenshot(path=str(out_dir/'d8a_before.png'), full_page=True)
    try:
        for ratio in STABILITY_SWEEP:
            click_slider_ratio(page, 0, ratio)
            data['stability_map'].append({
                'requested_ratio': ratio,
                'observed': slider_state(page, 0),
                'section_text': section_text(page, 'Độ ổn định giọng'),
            })

        click_slider_ratio(page, 0, float(original_stability.get('ratio') or 0.60))

        for ratio in SPEED_SWEEP:
            click_slider_ratio(page, 1, ratio)
            data['speed_map'].append({
                'requested_ratio': ratio,
                'observed': slider_state(page, 1),
                'section_text': section_text(page, 'Tốc độ đọc'),
            })
    except Exception as exc:
        data['probe_error'] = sanitize_error_message(f'{type(exc).__name__}: {exc}')
    finally:
        try:
            click_slider_ratio(page, 0, float(original_stability.get('ratio') or 0.60))
        except Exception as exc:
            data['restore_errors'].append(sanitize_error_message(f'stability: {exc}'))
        try:
            click_slider_ratio(page, 1, float(original_speed.get('ratio') or 0.50))
        except Exception as exc:
            data['restore_errors'].append(sanitize_error_message(f'speed: {exc}'))

    final_stability = slider_state(page, 0)
    final_speed = slider_state(page, 1)
    data['final'] = {
        'stability_slider': final_stability,
        'speed_slider': final_speed,
        'stability_section': section_text(page, 'Độ ổn định giọng'),
        'speed_section': section_text(page, 'Tốc độ đọc'),
        'format': selected_format(page),
        'pause': pause_structure(page),
    }

    def close_ratio(a: dict[str, Any], b: dict[str, Any]) -> bool:
        if not a.get('found') or not b.get('found'):
            return False
        return abs(float(a.get('ratio') or 0) - float(b.get('ratio') or 0)) < 0.03

    data['restored'] = bool(
        close_ratio(original_stability, final_stability)
        and close_ratio(original_speed, final_speed)
        and data['final']['format'] == original_format
        and not data['restore_errors']
    )
    data['pass'] = bool(
        len(data['stability_map']) == len(STABILITY_SWEEP)
        and len(data['speed_map']) == len(SPEED_SWEEP)
        and data['restored']
    )
    data['finished_at'] = now()
    page.screenshot(path=str(out_dir/'d8a_after_restored.png'), full_page=True)
    out = out_dir/'d8a_control_calibration.json'
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return out


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description='D8A reversible SaydiVoice control calibration map')
    parser.add_argument('--runtime-root', type=Path)
    parser.add_argument('--chromium-executable')
    args=parser.parse_args(argv)

    runtime=build_runtime_paths(args.runtime_root) if args.runtime_root else build_runtime_paths()
    runtime.create()
    cfg=DiscoveryConfig(headless=False,navigation_timeout_ms=60_000,settle_ms=2_500,chromium_executable_path=args.chromium_executable)
    bundle=None
    try:
        raw,bundle,page=open_and_probe(cfg,runtime)
        sig=make_page_signals(raw)
        state=classify_page_state(sig)
        auth=classify_auth_state(sig,state)
        if state!='TTS_READY' or auth!='AUTHENTICATED_OR_HIDDEN':
            print(json.dumps({'gate':'FAIL_SESSION','state':state,'auth':auth},ensure_ascii=False))
            return 20
        out=run(page,runtime.runs_dir/'d8a_latest')
        data=json.loads(out.read_text(encoding='utf-8'))
        print(json.dumps({
            'gate':'PASS' if data.get('pass') else 'FAIL_D8A',
            'restored':data.get('restored'),
            'stability_map':data.get('stability_map'),
            'speed_map':data.get('speed_map'),
            'pause':(data.get('original') or {}).get('pause'),
            'generate_clicked':False,
            'download_clicked':False,
            'evidence':str(out),
        },ensure_ascii=False,indent=2))
        return 0 if data.get('pass') else 25
    except Exception as exc:
        print(json.dumps({'gate':'FAIL','error':sanitize_error_message(f'{type(exc).__name__}: {exc}')},ensure_ascii=False))
        return 1
    finally:
        if bundle:
            pw,ctx=bundle
            try: ctx.close()
            finally: pw.stop()


if __name__=='__main__':
    raise SystemExit(main())
