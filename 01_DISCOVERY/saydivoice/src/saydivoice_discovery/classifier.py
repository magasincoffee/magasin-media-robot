from __future__ import annotations

from .models import AuthState, PageSignals, PageState

READY_TERMS = (
    "tạo giọng",
    "chuyển văn bản",
    "text to speech",
    "tts",
    "tạo audio",
    "generate",
)
LOGIN_TERMS = (
    "đăng nhập",
    "login",
    "sign in",
    "tiếp tục với google",
    "continue with google",
)
BLOCKED_TERMS = (
    "captcha",
    "verify you are human",
    "xác minh bạn là người",
    "access denied",
    "cloudflare",
    "unusual traffic",
)


def _haystack(signals: PageSignals) -> str:
    return " ".join(
        (
            signals.title,
            signals.visible_text,
            *signals.button_texts,
            *signals.link_texts,
        )
    ).lower()


def classify_page_state(signals: PageSignals) -> PageState:
    text = _haystack(signals)

    if any(term in text for term in BLOCKED_TERMS):
        return "ACCESS_BLOCKED"

    if signals.has_password_input:
        return "LOGIN_REQUIRED"

    editor_present = signals.has_textarea or signals.has_contenteditable
    ready_term_present = any(term in text for term in READY_TERMS)
    if editor_present and ready_term_present:
        return "TTS_READY"

    login_term_present = any(term in text for term in LOGIN_TERMS)
    if login_term_present and not editor_present:
        return "LOGIN_REQUIRED"

    return "UNKNOWN"


def classify_auth_state(signals: PageSignals, page_state: PageState) -> AuthState:
    """Describe what the current surface shows without guessing account identity."""
    text = _haystack(signals)
    login_visible = any(term in text for term in LOGIN_TERMS)
    if page_state == "TTS_READY" and login_visible:
        return "ANONYMOUS"
    if page_state == "TTS_READY" and not login_visible:
        return "AUTHENTICATED_OR_HIDDEN"
    return "UNKNOWN"
