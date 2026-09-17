from saydivoice_discovery.generation import (
    _network_event_summary,
    _safe_error_json,
    _safe_network_url,
    analyze_generation_trace,
    classify_session_bootstrap,
    should_retry_after_reload,
)


def snap(*, disabled=False, busy=None, audio=0, quota="Còn 3 lượt tạo miễn phí", alerts=None, controls=None, generate=True, cancel=None):
    return {
        "at": "x",
        "generate": {"text": "Tạo giọng nói", "disabled": disabled, "aria_busy": busy} if generate else None,
        "cancel_controls": cancel or [],
        "audio_count": audio,
        "quota_text": quota,
        "alerts": alerts or [],
        "result_controls": controls or [],
    }


def test_generation_success_when_quota_decreases():
    result = analyze_generation_trace([snap(), snap(disabled=True), snap(quota="Còn 2 lượt tạo miễn phí")])
    assert result["terminal_state"] == "SUCCESS_SIGNAL"
    assert result["processing_observed"] is True
    assert result["quota_before"] == 3
    assert result["quota_after"] == 2


def test_generation_success_when_audio_appears():
    result = analyze_generation_trace([snap(audio=0), snap(audio=1)])
    assert result["terminal_state"] == "SUCCESS_SIGNAL"
    assert result["audio_count_after"] == 1


def test_generation_error_ignores_preexisting_alert_but_captures_new_error():
    baseline = ["Không tải được giọng. Vui lòng tải lại trang."]
    trace = [snap(alerts=baseline), snap(disabled=True, alerts=baseline), snap(alerts=baseline + ["Tạo giọng thất bại. Vui lòng thử lại."])]
    result = analyze_generation_trace(trace, baseline_alerts=baseline)
    assert result["terminal_state"] == "ERROR"
    assert result["error_alerts"] == ["Tạo giọng thất bại. Vui lòng thử lại."]


def test_generation_processing_detects_cancel_or_generate_disappearing():
    result = analyze_generation_trace([snap(), snap(generate=False, cancel=["Hủy"]), snap(alerts=["Không tải được giọng. Vui lòng tải lại trang."])])
    assert result["terminal_state"] == "ERROR"
    assert result["processing_observed"] is True


def test_reload_retry_only_for_explicit_reload_error():
    reload_error = analyze_generation_trace([snap(), snap(alerts=["Không tải được giọng. Vui lòng tải lại trang."])])
    ordinary_error = analyze_generation_trace([snap(), snap(alerts=["Tạo giọng thất bại. Vui lòng thử lại."])])
    assert should_retry_after_reload(reload_error) is True
    assert should_retry_after_reload(ordinary_error) is False


def test_generation_processing_timeout_is_explicit():
    assert analyze_generation_trace([snap(), snap(disabled=True)])["terminal_state"] == "PROCESSING_OR_TIMEOUT"


def test_generation_no_signal_is_explicit():
    assert analyze_generation_trace([snap(), snap()])["terminal_state"] == "NO_TERMINAL_SIGNAL"


def test_network_summary_reports_only_safe_failure_metadata():
    events = [
        {"kind": "response", "url": "https://api.example.test/tts", "status": 500},
        {"kind": "response", "url": "https://api.example.test/voices", "status": 401},
        {"kind": "request_failed", "url": "https://cdn.example.test/audio"},
    ]
    result = _network_event_summary(events)
    assert result["event_count"] == 3
    assert result["request_failed_count"] == 1
    assert result["http_error_count"] == 2
    assert result["http_error_statuses"] == [401, 500]


def test_network_url_strips_query_and_fragment():
    assert _safe_network_url("https://voice.example.test/api/tts?token=secret#x") == "https://voice.example.test/api/tts"


def test_session_preflight_classifies_forbidden_start_as_blocking():
    events = [
        {"kind": "response", "url": "https://voice.saydi.ai/api/session/start", "status": 403},
        {"kind": "response", "url": "https://voice.saydi.ai/api/samples", "status": 401},
    ]
    result = classify_session_bootstrap(events)
    assert result["state"] == "SESSION_START_FORBIDDEN"
    assert result["blocking"] is True
    assert result["session_start_statuses"] == [403]


def test_session_preflight_allows_successful_session_start():
    result = classify_session_bootstrap([
        {"kind": "response", "url": "https://voice.saydi.ai/api/session/start", "status": 200},
        {"kind": "response", "url": "https://voice.saydi.ai/api/samples", "status": 200},
    ])
    assert result["state"] == "SESSION_STARTED"
    assert result["blocking"] is False


def test_safe_error_json_only_keeps_allowlisted_fields():
    payload = {
        "error": "forbidden",
        "message": "challenge failed",
        "token": "SECRET",
        "session_id": "SECRET2",
        "detail": {"code": "CF_BLOCK", "authorization": "SECRET3"},
    }
    assert _safe_error_json(payload) == {
        "error": "forbidden",
        "message": "challenge failed",
        "detail": {"code": "CF_BLOCK"},
    }
