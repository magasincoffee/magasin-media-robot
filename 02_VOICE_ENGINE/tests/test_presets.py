import pytest

from magasin_voice_engine.models import MAX_TEXT_CHARS, VoiceRequest
from magasin_voice_engine.presets import PRESETS, get_preset


def test_all_presets_validate():
    assert {"tiktok_energetic", "review_natural", "story_warm", "news_stable", "slow_emotional"} <= set(PRESETS)
    for preset in PRESETS.values():
        preset.validate()


def test_tiktok_preset_matches_field_verified_policy():
    preset = get_preset("tiktok_energetic")
    assert preset.voice == "Adam — Giọng hot tiktok"
    assert preset.stability_ratio == pytest.approx(0.30)
    assert preset.speed_ratio == pytest.approx(0.65)
    assert preset.audio_format == "MP3"
    assert preset.pause.enabled is False


def test_preset_overrides_are_scoped_to_resolved_copy():
    original = get_preset("review_natural")
    overridden = get_preset("review_natural", voice_override="Voice X", format_override="wav")
    assert overridden.voice == "Voice X"
    assert overridden.audio_format == "WAV"
    assert original.voice != overridden.voice
    assert original.audio_format == "MP3"


def test_unknown_preset_is_rejected():
    with pytest.raises(ValueError, match="unknown voice preset"):
        get_preset("does-not-exist")


def test_request_rejects_empty_overlimit_and_unauthorized_download(tmp_path):
    with pytest.raises(ValueError, match="must not be empty"):
        VoiceRequest(text="   ", output_directory=tmp_path).validate()
    with pytest.raises(ValueError, match="exceeds"):
        VoiceRequest(text="x" * (MAX_TEXT_CHARS + 1), output_directory=tmp_path).validate()
    with pytest.raises(ValueError, match="requires allow_generate"):
        VoiceRequest(text="ok", output_directory=tmp_path, allow_download=True).validate()
