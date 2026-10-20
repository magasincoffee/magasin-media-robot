from saydivoice_discovery.d5_limits import classify_input_state, parse_counter


def test_parse_counter_with_thousands_separator() -> None:
    assert parse_counter("124 / 20,000") == (124, 20000)


def test_parse_counter_missing() -> None:
    assert parse_counter(None) == (None, None)
    assert parse_counter("no counter here") == (None, None)


def test_classify_empty_blocked() -> None:
    assert classify_input_state(0, 0, 20000, False) == "EMPTY_BLOCKED_UI"


def test_classify_regular_input_accepted() -> None:
    assert classify_input_state(19999, 19999, 20000, True) == "ACCEPTED_UI"


def test_classify_limit_accepted() -> None:
    assert classify_input_state(20000, 20000, 20000, True) == "LIMIT_ACCEPTED_UI"


def test_classify_limit_blocked() -> None:
    assert classify_input_state(20000, 20000, 20000, False) == "LIMIT_BLOCKED_UI"


def test_classify_over_limit_clamped() -> None:
    assert classify_input_state(20001, 20000, 20000, False) == "OVER_LIMIT_CLAMPED_UI"
    assert classify_input_state(20001, 20000, 20000, True) == "OVER_LIMIT_CLAMPED_UI"


def test_classify_ambiguous_when_no_clamp_observed() -> None:
    assert classify_input_state(20001, 20001, 20000, True) == "AMBIGUOUS"
