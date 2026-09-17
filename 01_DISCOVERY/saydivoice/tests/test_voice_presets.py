from __future__ import annotations

import pytest

from saydivoice_discovery.voice_presets import (
    CALIBRATED_SPEED_POINTS,
    CALIBRATED_STABILITY_POINTS,
    PRESETS,
    PauseProfile,
    VoicePreset,
    describe_preset,
    get_preset,
    nearest_calibrated_speed,
    nearest_calibrated_stability,
)


def test_all_builtin_presets_validate() -> None:
    assert PRESETS
    for preset in PRESETS.values():
        preset.validate()


def test_field_calibration_reference_points_are_stable() -> None:
    assert CALIBRATED_STABILITY_POINTS == {0.20: 1.6, 0.40: 2.2, 0.60: 2.8, 0.80: 3.4}
    assert CALIBRATED_SPEED_POINTS == {0.20: 0.70, 0.35: 0.85, 0.50: 1.00, 0.65: 1.15, 0.80: 1.30}


def test_review_preset_uses_real_pause_defaults() -> None:
    preset = get_preset("review_natural")
    assert preset.pause.enabled is True
    assert preset.pause.dot_seconds == 0.45
    assert preset.pause.comma_seconds == 0.25
    assert preset.pause.semicolon_seconds == 0.30
    assert preset.pause.newline_seconds == 0.60


def test_describe_preset_exposes_nearest_calibrated_values() -> None:
    desc = describe_preset("tiktok_energetic")
    assert desc["nearest_stability_reference_ratio"] in {0.20, 0.40}
    assert desc["nearest_speed_reference_ratio"] == 0.65
    assert desc["nearest_speed_multiplier"] == 1.15


def test_nearest_calibration_helpers() -> None:
    assert nearest_calibrated_stability(0.61) == (0.60, 2.8)
    assert nearest_calibrated_speed(0.79) == (0.80, 1.30)


def test_invalid_preset_rejected() -> None:
    bad = VoicePreset(
        key="bad",
        label="Bad",
        voice="Adam",
        stability_ratio=1.5,
        speed_ratio=0.5,
    )
    with pytest.raises(ValueError):
        bad.validate()


def test_negative_pause_rejected() -> None:
    pause = PauseProfile(enabled=True, dot_seconds=-0.1)
    with pytest.raises(ValueError):
        pause.validate()


def test_unknown_preset_lists_available_keys() -> None:
    with pytest.raises(KeyError, match="available"):
        get_preset("missing")
