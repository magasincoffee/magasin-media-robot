import json
from pathlib import Path


CONTRACT_PATH = Path("contracts/saydivoice_contract_v1.json")


def _load():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_contract_identity_and_session_gate():
    c = _load()
    assert c["schema_version"] == "1.0"
    assert c["contract_id"] == "saydivoice-discovery-v1"
    assert c["target"]["tts_url"] == "https://voice.saydi.ai/vi/studio/tts/"
    assert c["session"]["required_page_state"] == "TTS_READY"
    assert c["session"]["required_auth_state"] == "AUTHENTICATED_OR_HIDDEN"
    assert c["session"]["profile_must_remain_local"] is True
    assert c["session"]["anonymous_session_is_production_supported"] is False


def test_locator_contract_freezes_high_value_controls():
    c = _load()["locator_policy"]
    assert c["priority"][:2] == ["test_id", "role_and_accessible_name"]
    assert c["editor"]["css"] == '[contenteditable="true"]'
    assert c["generate"] == {"role": "button", "name": "Tạo giọng nói", "exact": True}
    assert c["custom_sliders"]["stability_expression_index"] == 0
    assert c["custom_sliders"]["speed_index"] == 1
    assert set(c["format_tabs"]["observed"]) == {"WAV", "MP3", "FLAC", "OGG"}


def test_input_boundary_is_frozen_at_20000_without_provider_probe():
    c = _load()["input_boundary"]
    assert c["advertised_character_limit"] == 20_000
    assert c["effective_maximum_characters"] == 20_000
    assert c["empty_input"] == "GENERATE_DISABLED_UI"
    assert c["above_limit"] == "CLAMPED_AT_LIMIT_UI"
    assert c["d5c_tts_request_count"] == 0


def test_generation_and_download_have_separate_explicit_gates():
    c = _load()
    assert c["generation"]["explicit_authorization_required"] is True
    assert c["generation"]["default_max_generate_attempts"] == 1
    assert c["generation"]["download_during_d3"] is False
    assert c["generation"]["retry"]["implicit_retry"] is False
    assert c["download"]["explicit_authorization_required"] is True
    assert c["download"]["requires_generation_success_signal"] is True
    assert c["download"]["maximum_new_downloads_per_controlled_run"] == 1
    assert c["download"]["raw_audio_must_not_be_uploaded_to_github"] is True


def test_privacy_contract_excludes_sensitive_or_raw_payloads():
    c = _load()["privacy"]
    banned = set(c["never_persist"])
    assert {
        "editor_text",
        "credentials",
        "cookies",
        "localStorage",
        "sessionStorage",
        "authorization_headers",
        "request_bodies",
        "successful_response_bodies",
        "raw_html",
        "browser_profile",
        "raw_generated_audio_in_github_artifacts",
    } <= banned
    assert c["network_evidence"]["strip_query"] is True
    assert c["network_evidence"]["strip_fragment"] is True
    assert c["network_evidence"]["max_events"] == 180


def test_field_evidence_covers_authenticated_d3_d4_and_non_destructive_d5():
    e = _load()["field_evidence"]
    assert e["d3_generation_run"] == 35219033748
    assert e["d4_download_run"] == 35219638775
    assert e["d5b3_voice_roundtrip_run"] == 35230995883
    assert e["d5c_input_boundary_run"] == 35231771503
