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


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def pause_section(page: Any) -> dict[str, Any]:
    return page.evaluate(r"""
() => {
  const norm=s=>(s||'').replace(/\s+/g,' ').trim();
  const vis=e=>{if(!e)return false;const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
  const label=Array.from(document.querySelectorAll('*')).find(e=>vis(e)&&norm(e.innerText||e.textContent)==='Ngắt nghỉ');
  if(!label) return {found:false};
  const sec=label.closest('.st-section') || label.parentElement;
  const all=Array.from(sec.querySelectorAll('*'));
  const controls=all.filter(e=>vis(e)&&e.matches('input,button,select,textarea,[role="switch"],[role="slider"],[role="spinbutton"],[contenteditable="true"]')).map((el,i)=>({
    index:i,
    tag:el.tagName.toLowerCase(),
    type:el.getAttribute('type'),
    role:el.getAttribute('role'),
    text:norm(el.innerText||el.textContent).slice(0,160),
    value:('value' in el)?String(el.value):null,
    checked:('checked' in el)?Boolean(el.checked):null,
    disabled:('disabled' in el)?Boolean(el.disabled):null,
    min:el.getAttribute('min'),
    max:el.getAttribute('max'),
    step:el.getAttribute('step'),
    placeholder:el.getAttribute('placeholder'),
    aria_label:el.getAttribute('aria-label'),
    aria_checked:el.getAttribute('aria-checked'),
    aria_expanded:el.getAttribute('aria-expanded'),
    class_name:String(el.className||'').slice(0,220),
  }));
  return {
    found:true,
    text:norm(sec.innerText||sec.textContent),
    html_class:String(sec.className||''),
    controls,
    visible_input_count:controls.filter(x=>x.tag==='input').length,
    visible_button_texts:controls.filter(x=>x.tag==='button').map(x=>x.text),
  };
}
""") or {"found": False}


def find_pause_head(page: Any):
    # D8A found the collapsed header as button.dropdown.accordion-head.
    loc = page.locator('.st-section').filter(has_text='Ngắt nghỉ').locator('button.dropdown.accordion-head')
    if loc.count() > 0:
        return loc.first
    loc = page.locator('button.dropdown.accordion-head').filter(has_text=re.compile(r'Đang (tắt|bật)', re.I))
    if loc.count() > 0:
        return loc.first
    # Last resort: button in the nearest section around the exact label.
    label = page.get_by_text('Ngắt nghỉ', exact=True)
    if label.count() < 1:
        raise RuntimeError('Ngắt nghỉ section not found')
    return label.first.locator('xpath=ancestor-or-self::*[contains(@class,"st-section")][1]').locator('button').first


def run(page: Any, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        'schema_version': '1.0',
        'mode': 'D8B_PAUSE_CONTROLS_READ_ONLY_PROBE',
        'started_at': now(),
        'generate_clicked': False,
        'download_clicked': False,
        'settings_changed': False,
        'restore_errors': [],
    }

    before = pause_section(page)
    data['before'] = before
    if not before.get('found'):
        raise RuntimeError('Pause section missing')
    page.screenshot(path=str(out_dir/'01_pause_collapsed.png'), full_page=True)

    head = find_pause_head(page)
    head_text_before = clean(head.inner_text())
    data['head_text_before'] = head_text_before
    data['head_aria_expanded_before'] = head.get_attribute('aria-expanded')

    head.click(timeout=4_000)
    page.wait_for_timeout(700)
    expanded = pause_section(page)
    data['expanded'] = expanded
    data['head_text_after_open'] = clean(head.inner_text())
    data['head_aria_expanded_after_open'] = head.get_attribute('aria-expanded')
    page.screenshot(path=str(out_dir/'02_pause_expanded.png'), full_page=True)

    # This probe deliberately does not click any newly revealed toggle/value control.
    # Only the accordion header is toggled, so persistent TTS settings are untouched.
    try:
        head.click(timeout=4_000)
        page.wait_for_timeout(500)
    except Exception as exc:
        data['restore_errors'].append(sanitize_error_message(f'accordion close: {exc}'))

    final = pause_section(page)
    data['final'] = final
    data['head_text_final'] = clean(head.inner_text()) if head.count() else None
    data['head_aria_expanded_final'] = head.get_attribute('aria-expanded') if head.count() else None
    page.screenshot(path=str(out_dir/'03_pause_restored.png'), full_page=True)

    # Settings text/state should be unchanged. Expansion can alter visible controls,
    # therefore compare the collapsed section text and header text rather than DOM shape.
    data['restored'] = bool(
        not data['restore_errors']
        and clean(final.get('text')) == clean(before.get('text'))
        and data['head_text_final'] == head_text_before
    )
    data['revealed_more_controls'] = len(expanded.get('controls') or []) > len(before.get('controls') or [])
    data['pass'] = bool(data['restored'] and expanded.get('found'))
    data['finished_at'] = now()

    out = out_dir/'d8b_pause_probe.json'
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return out


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description='D8B read-only SaydiVoice pause controls probe')
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
        out=run(page,runtime.runs_dir/'d8b_latest')
        data=json.loads(out.read_text(encoding='utf-8'))
        print(json.dumps({
            'gate':'PASS' if data.get('pass') else 'FAIL_D8B',
            'before':data.get('before'),
            'expanded':data.get('expanded'),
            'restored':data.get('restored'),
            'revealed_more_controls':data.get('revealed_more_controls'),
            'generate_clicked':False,
            'download_clicked':False,
            'settings_changed':False,
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
