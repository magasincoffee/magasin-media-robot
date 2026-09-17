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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(v: str | None) -> str:
    return re.sub(r"\s+", " ", v or "").strip()


def _current_voice(page: Any) -> str | None:
    values = page.evaluate(r"""
() => Array.from(document.querySelectorAll('button,[role="button"]'))
.filter(el => { const s=getComputedStyle(el), r=el.getBoundingClientRect(); return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0; })
.map(el => (el.innerText||el.textContent||'').replace(/\s+/g,' ').trim())
.filter(t => t && t.length < 140)
""") or []
    for value in values:
        if "—" in value and "giọng" in value.lower():
            return _clean(value)
    return next((_clean(v) for v in values if v.lower() == "tự động"), None)


def _section_text(page: Any, label: str) -> str:
    return page.evaluate(r"""
(label) => {
 const clean=s=>(s||'').replace(/\s+/g,' ').trim();
 const vis=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
 const lab=Array.from(document.querySelectorAll('*')).find(e=>vis(e)&&clean(e.innerText||e.textContent)===label);
 if(!lab) return '';
 const sec=lab.closest('.st-section') || lab.parentElement;
 return clean(sec?.innerText||sec?.textContent||'');
}
""", label) or ""


def _slider_state(page: Any, index: int) -> dict[str, Any]:
    return page.evaluate(r"""
(index) => {
 const sliders=Array.from(document.querySelectorAll('.slider'));
 const el=sliders[index]; if(!el) return {found:false};
 const fill=el.querySelector('.slider-fill'), knob=el.querySelector('.slider-knob');
 const r=el.getBoundingClientRect(), fr=fill?.getBoundingClientRect(), kr=knob?.getBoundingClientRect();
 return {found:true,x:r.x,y:r.y,width:r.width,fill_width:fr?.width??null,knob_x:kr?.x??null,ratio:(fr&&r.width)?fr.width/r.width:null};
}
""", index)


def _click_slider_ratio(page: Any, index: int, ratio: float) -> None:
    slider = page.locator('.slider').nth(index)
    box = slider.bounding_box()
    if not box:
        raise RuntimeError(f"Slider {index} not found")
    ratio = max(0.04, min(0.96, ratio))
    page.mouse.click(box['x'] + box['width'] * ratio, box['y'] + max(1.0, box['height'] / 2))
    page.wait_for_timeout(700)


def _selected_format(page: Any) -> str | None:
    vals = page.evaluate(r"""
() => Array.from(document.querySelectorAll('.fmt-tab')).map(el=>({text:(el.innerText||el.textContent||'').trim(),cls:String(el.className||'')}))
""") or []
    for item in vals:
        if "active" in item.get("cls", "").split():
            return item.get("text")
    return None


def _click_format(page: Any, fmt: str) -> bool:
    loc = page.get_by_role('tab', name=fmt, exact=True)
    if loc.count() < 1:
        loc = page.get_by_role('button', name=fmt, exact=True)
    if loc.count() < 1:
        return False
    loc.first.click(timeout=4_000)
    page.wait_for_timeout(500)
    return True


def _open_voice(page: Any, label: str) -> None:
    for loc in (page.get_by_role('button', name=label, exact=True), page.get_by_text(label, exact=True)):
        if loc.count():
            loc.first.click(timeout=4_000)
            page.wait_for_timeout(700)
            return
    raise RuntimeError(f"Could not open voice selector from {label!r}")


def _search_and_use_voice(page: Any, name: str) -> bool:
    search = page.locator('input[placeholder*="tìm" i]').first
    if search.count() < 1:
        search = page.locator('input').first
    if search.count() < 1:
        return False
    search.fill(name)
    page.wait_for_timeout(700)
    ok = page.evaluate(r"""
(name) => {
 const clean=s=>(s||'').replace(/\s+/g,' ').trim();
 const vis=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
 const exact=Array.from(document.querySelectorAll('*')).filter(vis).filter(e=>clean(e.innerText||e.textContent)===name);
 for(const n of exact){
   let p=n.parentElement;
   for(let i=0;i<7&&p;i++,p=p.parentElement){
     const buttons=Array.from(p.querySelectorAll('button')).filter(vis);
     const use=buttons.find(b=>['Dùng','Sử dụng'].includes(clean(b.innerText||b.textContent)));
     if(use){ use.click(); return true; }
   }
 }
 return false;
}
""", name)
    page.wait_for_timeout(900)
    return bool(ok)


def _snapshot(page: Any) -> dict[str, Any]:
    return {
        "voice": _current_voice(page),
        "stability_section": _section_text(page, "Độ ổn định giọng"),
        "stability_slider": _slider_state(page, 0),
        "speed_section": _section_text(page, "Tốc độ đọc"),
        "speed_slider": _slider_state(page, 1),
        "format": _selected_format(page),
    }


def _close_modal(page: Any) -> None:
    try:
        page.keyboard.press('Escape')
        page.wait_for_timeout(250)
    except Exception:
        pass


def run(page: Any, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "schema_version": "1.0",
        "mode": "D5B_REVERSIBLE_CONTROL_VERIFICATION",
        "started_at": _now(),
        "generate_clicked": False,
        "download_clicked": False,
        "tests": {},
        "restore_errors": [],
    }
    original = _snapshot(page)
    data["original"] = original
    page.screenshot(path=str(out_dir / 'd5b_before.png'), full_page=True)

    orig_voice = original.get("voice")
    orig_stab = float((original.get("stability_slider") or {}).get("ratio") or 0.60)
    orig_speed = float((original.get("speed_slider") or {}).get("ratio") or 0.50)
    orig_fmt = original.get("format") or 'MP3'

    try:
        # Voice roundtrip using a known alternate catalog entry.
        voice_test = {"alternate": "THEANH28 - Nữ", "before": orig_voice}
        try:
            if not orig_voice:
                raise RuntimeError("Current voice unavailable")
            _open_voice(page, orig_voice)
            changed = _search_and_use_voice(page, voice_test["alternate"])
            if not changed:
                raise RuntimeError("Alternate voice could not be selected")
            voice_test["after_change"] = _current_voice(page)
            _open_voice(page, voice_test["after_change"] or voice_test["alternate"])
            restored = _search_and_use_voice(page, orig_voice)
            if not restored:
                raise RuntimeError("Original voice could not be restored")
            voice_test["after_restore"] = _current_voice(page)
            voice_test["pass"] = bool(voice_test["after_change"] != orig_voice and voice_test["after_restore"] == orig_voice)
        except Exception as exc:
            voice_test["error"] = sanitize_error_message(f"{type(exc).__name__}: {exc}")
            voice_test["pass"] = False
            _close_modal(page)
            if orig_voice and _current_voice(page) != orig_voice:
                try:
                    current = _current_voice(page)
                    if current:
                        _open_voice(page, current)
                        _search_and_use_voice(page, orig_voice)
                except Exception as restore_exc:
                    data["restore_errors"].append(sanitize_error_message(f"voice: {restore_exc}"))
        data["tests"]["voice_roundtrip"] = voice_test

        # Stability / expression axis roundtrip.
        stab_test = {"before": _snapshot(page)}
        try:
            test_ratio = 0.30 if abs(orig_stab - 0.30) > 0.10 else 0.75
            _click_slider_ratio(page, 0, test_ratio)
            stab_test["after_change"] = _snapshot(page)
            _click_slider_ratio(page, 0, orig_stab)
            stab_test["after_restore"] = _snapshot(page)
            changed_text = stab_test["after_change"]["stability_section"] != stab_test["before"]["stability_section"]
            restored_text = stab_test["after_restore"]["stability_section"] == stab_test["before"]["stability_section"]
            restored_ratio = abs((stab_test["after_restore"]["stability_slider"].get("ratio") or 0)-orig_stab) < 0.03
            stab_test["pass"] = bool(changed_text and restored_text and restored_ratio)
        except Exception as exc:
            stab_test["error"] = sanitize_error_message(f"{type(exc).__name__}: {exc}")
            stab_test["pass"] = False
            try: _click_slider_ratio(page, 0, orig_stab)
            except Exception as restore_exc: data["restore_errors"].append(sanitize_error_message(f"stability: {restore_exc}"))
        data["tests"]["stability_expression_roundtrip"] = stab_test

        # Speed roundtrip.
        speed_test = {"before": _snapshot(page)}
        try:
            test_ratio = 0.72 if abs(orig_speed - 0.72) > 0.10 else 0.28
            _click_slider_ratio(page, 1, test_ratio)
            speed_test["after_change"] = _snapshot(page)
            _click_slider_ratio(page, 1, orig_speed)
            speed_test["after_restore"] = _snapshot(page)
            changed_text = speed_test["after_change"]["speed_section"] != speed_test["before"]["speed_section"]
            restored_text = speed_test["after_restore"]["speed_section"] == speed_test["before"]["speed_section"]
            restored_ratio = abs((speed_test["after_restore"]["speed_slider"].get("ratio") or 0)-orig_speed) < 0.03
            speed_test["pass"] = bool(changed_text and restored_text and restored_ratio)
        except Exception as exc:
            speed_test["error"] = sanitize_error_message(f"{type(exc).__name__}: {exc}")
            speed_test["pass"] = False
            try: _click_slider_ratio(page, 1, orig_speed)
            except Exception as restore_exc: data["restore_errors"].append(sanitize_error_message(f"speed: {restore_exc}"))
        data["tests"]["speed_roundtrip"] = speed_test

        # Format roundtrip.
        fmt_test = {"before": _selected_format(page), "alternate": "WAV" if orig_fmt != "WAV" else "FLAC"}
        try:
            if not _click_format(page, fmt_test["alternate"]):
                raise RuntimeError("Alternate format tab not found")
            fmt_test["after_change"] = _selected_format(page)
            if not _click_format(page, orig_fmt):
                raise RuntimeError("Original format tab not found")
            fmt_test["after_restore"] = _selected_format(page)
            fmt_test["pass"] = bool(fmt_test["after_change"] == fmt_test["alternate"] and fmt_test["after_restore"] == orig_fmt)
        except Exception as exc:
            fmt_test["error"] = sanitize_error_message(f"{type(exc).__name__}: {exc}")
            fmt_test["pass"] = False
            try: _click_format(page, orig_fmt)
            except Exception as restore_exc: data["restore_errors"].append(sanitize_error_message(f"format: {restore_exc}"))
        data["tests"]["format_roundtrip"] = fmt_test

    finally:
        # Final best-effort restore of every tested setting.
        try:
            if _current_voice(page) != orig_voice and orig_voice:
                current = _current_voice(page)
                if current:
                    _open_voice(page, current)
                    _search_and_use_voice(page, orig_voice)
        except Exception as exc:
            data["restore_errors"].append(sanitize_error_message(f"final_voice: {exc}"))
        try: _click_slider_ratio(page, 0, orig_stab)
        except Exception as exc: data["restore_errors"].append(sanitize_error_message(f"final_stability: {exc}"))
        try: _click_slider_ratio(page, 1, orig_speed)
        except Exception as exc: data["restore_errors"].append(sanitize_error_message(f"final_speed: {exc}"))
        try: _click_format(page, orig_fmt)
        except Exception as exc: data["restore_errors"].append(sanitize_error_message(f"final_format: {exc}"))

    data["final"] = _snapshot(page)
    data["restored"] = (
        data["final"].get("voice") == original.get("voice")
        and data["final"].get("stability_section") == original.get("stability_section")
        and data["final"].get("speed_section") == original.get("speed_section")
        and data["final"].get("format") == original.get("format")
    )
    data["all_tests_pass"] = all(bool(v.get("pass")) for v in data["tests"].values()) and data["restored"] and not data["restore_errors"]
    data["finished_at"] = _now()
    page.screenshot(path=str(out_dir / 'd5b_after_restored.png'), full_page=True)
    out = out_dir / 'd5b_control_roundtrip.json'
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return out


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description='D5B reversible SaydiVoice control verification')
    p.add_argument('--runtime-root', type=Path); p.add_argument('--chromium-executable'); a=p.parse_args(argv)
    rt=build_runtime_paths(a.runtime_root) if a.runtime_root else build_runtime_paths(); rt.create()
    cfg=DiscoveryConfig(headless=False,navigation_timeout_ms=60_000,settle_ms=2_500,chromium_executable_path=a.chromium_executable)
    bundle=None
    try:
        raw,bundle,page=open_and_probe(cfg,rt); signals=make_page_signals(raw); state=classify_page_state(signals); auth=classify_auth_state(signals,state)
        if state!='TTS_READY' or auth!='AUTHENTICATED_OR_HIDDEN':
            print(json.dumps({'gate':'FAIL_SESSION','state':state,'auth':auth},ensure_ascii=False)); return 20
        out=run(page,rt.runs_dir/'d5b_latest'); d=json.loads(out.read_text(encoding='utf-8'))
        print(json.dumps({'gate':'PASS' if d['all_tests_pass'] else 'FAIL_D5B','tests':{k:v.get('pass') for k,v in d['tests'].items()},'restored':d['restored'],'restore_errors':d['restore_errors'],'generate_clicked':False,'download_clicked':False,'evidence':str(out)},ensure_ascii=False,indent=2))
        return 0 if d['all_tests_pass'] else 25
    except Exception as exc:
        print(json.dumps({'gate':'FAIL','error':sanitize_error_message(f'{type(exc).__name__}: {exc}')},ensure_ascii=False)); return 1
    finally:
        if bundle:
            pw,ctx=bundle
            try: ctx.close()
            finally: pw.stop()

if __name__=='__main__': raise SystemExit(main())
