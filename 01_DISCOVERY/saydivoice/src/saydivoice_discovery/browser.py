from __future__ import annotations

from typing import Any

from .models import DiscoveryConfig, RuntimePaths

DOM_PROBE_SCRIPT = r"""
() => {
  const isVisible = (el) => {
    const s = window.getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
  };
  const textOf = (el) => (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 240);
  const interactiveSelector = [
    'button', 'a', 'input', 'textarea', 'select',
    '[role="button"]', '[role="combobox"]', '[role="slider"]', '[role="tab"]',
    '[role="textbox"]', '[contenteditable="true"]', '[aria-valuenow]'
  ].join(',');

  const all = Array.from(document.querySelectorAll(interactiveSelector)).filter(isVisible).slice(0, 400);
  const elements = all.map((el) => {
    const tag = el.tagName.toLowerCase();
    const contenteditable = el.getAttribute('contenteditable') === 'true' || el.isContentEditable === true;
    const isEditor = ['input', 'textarea', 'select'].includes(tag)
      || el.getAttribute('role') === 'textbox'
      || contenteditable;
    return {
      tag,
      role: el.getAttribute('role'),
      name: el.getAttribute('name'),
      text: isEditor ? '' : textOf(el),
      type: el.getAttribute('type'),
      placeholder: el.getAttribute('placeholder'),
      aria_label: el.getAttribute('aria-label'),
      test_id: el.getAttribute('data-testid') || el.getAttribute('data-test') || el.getAttribute('data-qa'),
      contenteditable,
      disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true',
      aria_selected: el.getAttribute('aria-selected'),
      aria_checked: el.getAttribute('aria-checked'),
      aria_valuenow: el.getAttribute('aria-valuenow'),
      aria_valuemin: el.getAttribute('aria-valuemin'),
      aria_valuemax: el.getAttribute('aria-valuemax')
    };
  });

  const buttonTexts = Array.from(document.querySelectorAll('button, [role="button"]'))
    .filter(isVisible).map(textOf).filter(Boolean).slice(0, 100);
  const linkTexts = Array.from(document.querySelectorAll('a'))
    .filter(isVisible).map(textOf).filter(Boolean).slice(0, 100);

  return {
    url: window.location.href,
    title: document.title || '',
    visible_text: (document.body?.innerText || '').replace(/\s+/g, ' ').slice(0, 6000),
    has_password_input: Array.from(document.querySelectorAll('input[type="password"]')).some(isVisible),
    has_textarea: Array.from(document.querySelectorAll('textarea')).some(isVisible),
    has_contenteditable: Array.from(document.querySelectorAll('[contenteditable="true"]')).some(isVisible),
    button_texts: buttonTexts,
    link_texts: linkTexts,
    elements
  };
}
"""


def probe_page(page: Any) -> dict[str, Any]:
    return page.evaluate(DOM_PROBE_SCRIPT)


def open_and_probe(config: DiscoveryConfig, paths: RuntimePaths) -> tuple[dict[str, Any], Any, Any]:
    """Open SaydiVoice and return probe data plus context/page for evidence capture."""
    from playwright.sync_api import sync_playwright

    playwright = sync_playwright().start()
    launch_kwargs: dict[str, Any] = {
        "user_data_dir": str(paths.profile_dir),
        "headless": config.headless,
        "accept_downloads": True,
        "downloads_path": str(paths.downloads_dir),
        "viewport": {"width": config.viewport_width, "height": config.viewport_height},
    }
    if config.chromium_executable_path:
        launch_kwargs["executable_path"] = config.chromium_executable_path

    try:
        context = playwright.chromium.launch_persistent_context(**launch_kwargs)
    except Exception:
        playwright.stop()
        raise

    try:
        context.set_default_timeout(config.navigation_timeout_ms)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(config.tts_url, wait_until="domcontentloaded", timeout=config.navigation_timeout_ms)
        page.wait_for_timeout(config.settle_ms)
        probe = probe_page(page)
        return probe, (playwright, context), page
    except Exception:
        try:
            context.close()
        finally:
            playwright.stop()
        raise
