from saydivoice_discovery.classifier import classify_auth_state, classify_page_state
from saydivoice_discovery.models import PageSignals


def signals(**overrides):
    base = dict(
        url="https://voice.saydi.ai/vi/studio/tts/",
        title="SaydiVoice",
        visible_text="",
        has_password_input=False,
        has_textarea=False,
        has_contenteditable=False,
        button_texts=(),
        link_texts=(),
    )
    base.update(overrides)
    return PageSignals(**base)


def test_ready_requires_editor_and_ready_term():
    s = signals(has_textarea=True, button_texts=("Tạo giọng",))
    assert classify_page_state(s) == "TTS_READY"


def test_password_input_is_login_required():
    s = signals(has_password_input=True, visible_text="Đăng nhập")
    assert classify_page_state(s) == "LOGIN_REQUIRED"


def test_login_link_does_not_override_ready_editor():
    s = signals(has_contenteditable=True, button_texts=("Generate",), link_texts=("Đăng nhập",))
    assert classify_page_state(s) == "TTS_READY"


def test_blocked_has_priority():
    s = signals(has_password_input=True, visible_text="Verify you are human")
    assert classify_page_state(s) == "ACCESS_BLOCKED"


def test_unknown_when_evidence_is_insufficient():
    assert classify_page_state(signals(visible_text="SaydiVoice Studio")) == "UNKNOWN"


def test_auth_state_anonymous_when_ready_and_login_visible():
    s = signals(has_contenteditable=True, button_texts=("Tạo giọng nói", "Đăng nhập"))
    assert classify_auth_state(s, "TTS_READY") == "ANONYMOUS"


def test_auth_state_does_not_claim_identity_when_login_hidden():
    s = signals(has_contenteditable=True, button_texts=("Tạo giọng nói",))
    assert classify_auth_state(s, "TTS_READY") == "AUTHENTICATED_OR_HIDDEN"
