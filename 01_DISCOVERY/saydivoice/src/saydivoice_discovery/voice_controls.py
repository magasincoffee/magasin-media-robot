from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from .voice_presets import PauseProfile, VoicePreset


_PAUSE_VALUE_PATTERNS = {
    "dot_seconds": r"Dấu chấm\s*[•.]?\s*[−-]\s*([0-9]+(?:\.[0-9]+)?)s",
    "comma_seconds": r"Dấu phẩy\s*,?\s*[−-]\s*([0-9]+(?:\.[0-9]+)?)s",
    "semicolon_seconds": r"Dấu chấm phẩy\s*;?\s*[−-]\s*([0-9]+(?:\.[0-9]+)?)s",
    "newline_seconds": r"Xuống dòng\s*¶?\s*[−-]\s*([0-9]+(?:\.[0-9]+)?)s",
}


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_pause_values(text: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for key, pattern in _PAUSE_VALUE_PATTERNS.items():
        match = re.search(pattern, clean(text), re.IGNORECASE)
        if not match:
            raise ValueError(f"pause value {key} not found")
        values[key] = float(match.group(1))
    return values


def _range_state_by_label(page: Any, label: str) -> dict[str, Any]:
    return page.evaluate(
        r"""
(label) => {
  const norm=(v)=>(v||'').replace(/\s+/g,' ').trim().toLowerCase();
  const textOf=(el)=>(el?.innerText||el?.textContent||'').replace(/\s+/g,' ').trim();
  const visible=(el)=>{
    if(!el) return false;
    const s=getComputedStyle(el),r=el.getBoundingClientRect();
    return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0;
  };
  const all=Array.from(document.querySelectorAll('body *')).filter(visible);
  const labelEl=all.find(el=>norm(textOf(el))===norm(label));
  if(!labelEl) return {found:false,label};

  let scope=labelEl.parentElement;
  let input=null;
  for(let depth=0; depth<6 && scope; depth++,scope=scope.parentElement){
    const ranges=Array.from(scope.querySelectorAll('input[type="range"]')).filter(visible);
    if(ranges.length===1){ input=ranges[0]; break; }
  }
  if(!input) return {found:false,label,reason:'range-not-found'};

  const min=Number(input.min || 0);
  const max=Number(input.max || 1);
  const value=Number(input.value);
  const stepRaw=input.step;
  const step=(stepRaw && stepRaw!=='any') ? Number(stepRaw) : null;
  const ratio=(Number.isFinite(min)&&Number.isFinite(max)&&Number.isFinite(value)&&max>min)
    ? (value-min)/(max-min) : null;
  return {
    found:true,
    label,
    ratio,
    value,
    min,
    max,
    step:Number.isFinite(step)?step:null,
    source:'label-range-input'
  };
}
""",
        label,
    )


def slider_state(page: Any, index: int) -> dict[str, Any]:
    label = "Độ ổn định giọng" if index == 0 else "Tốc độ đọc"
    return _range_state_by_label(page, label)


def set_slider_ratio(page: Any, index: int, ratio: float, *, tolerance: float = 0.06) -> dict[str, Any]:
    ratio = max(0.0, min(1.0, float(ratio)))
    label = "Độ ổn định giọng" if index == 0 else "Tốc độ đọc"

    result = page.evaluate(
        r"""
({label,ratio}) => {
  const norm=(v)=>(v||'').replace(/\s+/g,' ').trim().toLowerCase();
  const textOf=(el)=>(el?.innerText||el?.textContent||'').replace(/\s+/g,' ').trim();
  const visible=(el)=>{
    if(!el) return false;
    const s=getComputedStyle(el),r=el.getBoundingClientRect();
    return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0;
  };
  const all=Array.from(document.querySelectorAll('body *')).filter(visible);
  const labelEl=all.find(el=>norm(textOf(el))===norm(label));
  if(!labelEl) return {ok:false,error:'label-not-found',label};

  let scope=labelEl.parentElement;
  let input=null;
  for(let depth=0; depth<6 && scope; depth++,scope=scope.parentElement){
    const ranges=Array.from(scope.querySelectorAll('input[type="range"]')).filter(visible);
    if(ranges.length===1){ input=ranges[0]; break; }
  }
  if(!input) return {ok:false,error:'range-not-found',label};

  const min=Number(input.min || 0);
  const max=Number(input.max || 1);
  const stepRaw=input.step;
  const step=(stepRaw && stepRaw!=='any') ? Number(stepRaw) : null;
  if(!Number.isFinite(min)||!Number.isFinite(max)||max<=min){
    return {ok:false,error:'invalid-range',label,min,max};
  }

  let target=min + ratio*(max-min);
  if(Number.isFinite(step) && step>0){
    target=min + Math.round((target-min)/step)*step;
    target=Math.max(min,Math.min(max,target));
  }

  const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')?.set;
  if(setter) setter.call(input,String(target));
  else input.value=String(target);
  input.dispatchEvent(new Event('input',{bubbles:true}));
  input.dispatchEvent(new Event('change',{bubbles:true}));

  return {ok:true,label,target,min,max,step:Number.isFinite(step)?step:null};
}
""",
        {"label": label, "ratio": ratio},
    )
    if not result.get("ok"):
        raise RuntimeError(f"slider {label!r} could not be set: {result}")

    page.wait_for_timeout(500)
    state = _range_state_by_label(page, label)
    observed = state.get("ratio")
    if not state.get("found") or observed is None or abs(float(observed) - ratio) > tolerance:
        raise RuntimeError(f"slider {label!r} did not reach requested ratio {ratio}: {state}")
    return state


def selected_format(page: Any) -> str | None:
    items = page.evaluate(
        r"""
() => Array.from(document.querySelectorAll('.fmt-tab')).map(el=>({
  text:(el.innerText||el.textContent||'').trim(),
  cls:String(el.className||'')
}))
"""
    ) or []
    for item in items:
        if "active" in item.get("cls", "").split():
            return clean(item.get("text"))
    return None


def set_format(page: Any, audio_format: str) -> str:
    target = audio_format.upper()
    if selected_format(page) == target:
        return target
    loc = page.locator(".fmt-tab").filter(has_text=target)
    if loc.count() < 1:
        raise RuntimeError(f"format {target} missing")
    loc.first.click(timeout=4_000)
    page.wait_for_timeout(350)
    observed = selected_format(page)
    if observed != target:
        raise RuntimeError(f"format did not change to {target}; observed={observed!r}")
    return observed


def current_voice(page: Any, preferred: tuple[str, ...] = ()) -> str | None:
    values = page.evaluate(
        r"""
() => Array.from(document.querySelectorAll('button,[role="button"]'))
.filter(el=>{
  const s=getComputedStyle(el),r=el.getBoundingClientRect();
  return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0
    && !el.closest('[role="dialog"],dialog,.modal,.dialog,[class*="modal"],[class*="dialog"]');
})
.map(el=>(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim())
.filter(Boolean)
"""
    ) or []
    normalized = [clean(v) for v in values]
    for name in preferred:
        if name in normalized:
            return name
    for value in normalized:
        low = value.lower()
        if len(value) <= 140 and value not in {"Tạo giọng nói", "Chọn giọng"} and (
            "giọng" in low or " - nữ" in low or " - nam" in low
        ):
            return value
    return next((v for v in normalized if v.lower() == "tự động"), None)


def _open_voice_selector(page: Any, label: str) -> None:
    for loc in (page.get_by_role("button", name=label, exact=True), page.get_by_text(label, exact=True)):
        for i in range(loc.count()):
            node = loc.nth(i)
            try:
                if node.is_visible():
                    node.click(timeout=4_000)
                    page.wait_for_timeout(500)
                    if page.locator("input:visible").count() > 0:
                        return
            except Exception:
                continue
    raise RuntimeError(f"could not open voice selector from {label!r}")


def _voice_search_input(page: Any):
    loc = page.locator("input:visible")
    if loc.count() < 1:
        raise RuntimeError("voice selector search input missing")
    for i in range(loc.count()):
        candidate = loc.nth(i)
        placeholder = (candidate.get_attribute("placeholder") or "").lower()
        if any(token in placeholder for token in ("tìm", "search", "nhập")):
            return candidate
    return loc.last


def set_voice(page: Any, target: str) -> str:
    before = current_voice(page, (target,))
    if before == target:
        return target
    if not before:
        raise RuntimeError("current voice unavailable")
    _open_voice_selector(page, before)
    search = _voice_search_input(page)
    query = target.split("—", 1)[0].split(" - ", 1)[0].strip()
    search.fill(query, timeout=4_000)
    page.wait_for_timeout(650)
    result = page.evaluate(
        r"""
(target) => {
  const norm=s=>(s||'').replace(/\s+/g,' ').trim();
  const vis=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
  const exact=Array.from(document.querySelectorAll('*')).filter(vis).filter(e=>norm(e.innerText||e.textContent)===target);
  for(const n of exact){
    let p=n;
    for(let depth=0;depth<9&&p;depth++,p=p.parentElement){
      const buttons=Array.from(p.querySelectorAll('button')).filter(vis);
      const use=buttons.find(b=>['Dùng','Sử dụng','Use'].includes(norm(b.innerText||b.textContent)));
      if(use){use.click();return true;}
      const selected=buttons.find(b=>['Xóa','Xoá','Remove'].includes(norm(b.innerText||b.textContent)));
      if(selected){return true;}
    }
  }
  return false;
}
""",
        target,
    )
    if not result:
        raise RuntimeError(f"voice {target!r} could not be selected")
    page.wait_for_timeout(650)
    page.keyboard.press("Escape")
    page.wait_for_timeout(350)
    after = current_voice(page, (target,))
    if after != target:
        raise RuntimeError(f"voice selection not verified; expected={target!r}, observed={after!r}")
    return after


def _pause_section(page: Any):
    label = page.get_by_text("Ngắt nghỉ", exact=True)
    if label.count() < 1:
        raise RuntimeError("pause section missing")
    return label.first.locator("xpath=ancestor-or-self::*[contains(concat(' ', normalize-space(@class), ' '), ' st-section ')][1]")


def ensure_pause_expanded(page: Any) -> Any:
    section = _pause_section(page)
    head = section.locator("button.dropdown.accordion-head").first
    if head.count() < 1:
        raise RuntimeError("pause accordion head missing")
    if (head.get_attribute("aria-expanded") or "false").lower() != "true":
        head.click(timeout=4_000)
        page.wait_for_timeout(300)
    return section


def read_pause_profile(page: Any) -> PauseProfile:
    section = ensure_pause_expanded(page)
    checkbox = section.locator('input.brk-enable[type="checkbox"]').first
    if checkbox.count() < 1:
        raise RuntimeError("pause enable checkbox missing")
    values = parse_pause_values(section.inner_text())
    return PauseProfile(enabled=checkbox.is_checked(), **values)


def set_pause_enabled(page: Any, enabled: bool) -> PauseProfile:
    section = ensure_pause_expanded(page)
    checkbox = section.locator('input.brk-enable[type="checkbox"]').first
    if checkbox.count() < 1:
        raise RuntimeError("pause enable checkbox missing")
    if checkbox.is_checked() != bool(enabled):
        checkbox.click(timeout=4_000)
        page.wait_for_timeout(300)
    observed = read_pause_profile(page)
    if observed.enabled != bool(enabled):
        raise RuntimeError(f"pause enable state mismatch: {observed.enabled}")
    return observed


def apply_preset(page: Any, preset: VoicePreset, *, configure_pause_enable: bool = True) -> dict[str, object]:
    preset.validate()
    voice = set_voice(page, preset.voice)
    stability = set_slider_ratio(page, 0, preset.stability_ratio)
    speed = set_slider_ratio(page, 1, preset.speed_ratio)
    audio_format = set_format(page, preset.audio_format)
    pause = read_pause_profile(page)
    if configure_pause_enable:
        pause = set_pause_enabled(page, preset.pause.enabled)
    return {
        "voice": voice,
        "stability": stability,
        "speed": speed,
        "format": audio_format,
        "pause": asdict(pause),
        "pause_timings_requested": asdict(preset.pause),
        "pause_timing_write_supported": False,
    }
