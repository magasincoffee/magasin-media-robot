from saydivoice_discovery.generation import analyze_generation_trace


def snap(*, disabled=False, busy=None, audio=0, quota='Còn 3 lượt tạo miễn phí', alerts=None, controls=None):
    return {
        'at': 'x',
        'generate': {'text': 'Tạo giọng nói', 'disabled': disabled, 'aria_busy': busy},
        'audio_count': audio,
        'quota_text': quota,
        'alerts': alerts or [],
        'result_controls': controls or [],
    }


def test_generation_success_when_quota_decreases():
    trace = [snap(), snap(disabled=True), snap(quota='Còn 2 lượt tạo miễn phí')]
    result = analyze_generation_trace(trace)
    assert result['terminal_state'] == 'SUCCESS_SIGNAL'
    assert result['processing_observed'] is True
    assert result['quota_before'] == 3
    assert result['quota_after'] == 2


def test_generation_success_when_audio_appears():
    result = analyze_generation_trace([snap(audio=0), snap(audio=1)])
    assert result['terminal_state'] == 'SUCCESS_SIGNAL'
    assert result['audio_count_after'] == 1


def test_generation_error_ignores_preexisting_alert_but_captures_new_error():
    baseline = ['Không tải được giọng. Vui lòng tải lại trang.']
    trace = [snap(alerts=baseline), snap(disabled=True, alerts=baseline), snap(alerts=baseline + ['Tạo giọng thất bại. Vui lòng thử lại.'])]
    result = analyze_generation_trace(trace, baseline_alerts=baseline)
    assert result['terminal_state'] == 'ERROR'
    assert result['error_alerts'] == ['Tạo giọng thất bại. Vui lòng thử lại.']


def test_generation_processing_timeout_is_explicit():
    result = analyze_generation_trace([snap(), snap(disabled=True)])
    assert result['terminal_state'] == 'PROCESSING_OR_TIMEOUT'


def test_generation_no_signal_is_explicit():
    result = analyze_generation_trace([snap(), snap()])
    assert result['terminal_state'] == 'NO_TERMINAL_SIGNAL'
