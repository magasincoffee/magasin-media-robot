"""Offline SAYDI002-003 contract/safety tests: absolutely no live generation."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
import pytest

from saydivoice_discovery.saydi002_preflight import (
    EXPECTED_HOST, PRESET, evaluate, run_preflight, main,
)


def base():
    report = {
        "page_state": "TTS_READY", "auth_state": "AUTHENTICATED_OR_HIDDEN",
        "run_status": "CAPTURED", "generation_lifecycle_path": None
    }
    voice = {"opened": True, "closed_after_observation": True,
             "current_label": "Tự động",
             "options": [{"text": "SG - Chí Đạt"}]}
    settings = {"settings": {
        "stability": {"found": True}, "speed": {"found": True},
        "pause": {"found": True},
        "output_format": {"found": True, "options": ["WAV", "MP3", "FLAC"]}
    }}
    return report, voice, settings


def verdict(report=None,voice=None,settings=None,host=EXPECTED_HOST):
    a,b,c=base()
    return evaluate(a if report is None else report,
                    b if voice is None else voice,
                    c if settings is None else settings,
                    host=host, profile_exists=True)


def test_expected_profile_and_no_generate_pass():
    result=verdict()
    assert result["status"]=="PASS"
    assert result["task_id"]=="SAYDI002-003"
    assert result["preset"]==PRESET
    assert result["generate_clicks"]==0
    assert result["new_audio_files"]==0
    assert result["production_authorized"] is False
    assert result["owner_audio_approval"] is False


@pytest.mark.parametrize("field,wrong",[
    ("page_state","LOGIN_REQUIRED"),
    ("auth_state","ANONYMOUS"),
    ("run_status","UNKNOWN"),
    ("generation_lifecycle_path","C:\\a\\generation.json"),
])
def test_auth_or_generation_failure_blocks(field,wrong):
    report,voice,settings=base()
    report[field]=wrong
    result=verdict(report=report)
    assert result["status"]=="BLOCKED_OR_REVIEW"
    if field=="generation_lifecycle_path":
        assert result["generate_clicks"] is None
        assert result["new_audio_files"] is None


def test_missing_required_voice_blocks():
    a,b,c=base()
    b["options"]=[{"text":"HN - Mai Phương"}]
    assert verdict(voice=b)["status"]=="BLOCKED_OR_REVIEW"


def test_current_voice_alone_can_prove_presence():
    a,b,c=base()
    b["options"]=[]
    b["current_label"]="SG - Chí Đạt"
    assert verdict(voice=b)["status"]=="PASS"


@pytest.mark.parametrize("setting",["stability","speed","pause"])
def test_missing_control_blocks(setting):
    a,b,c=base()
    c["settings"][setting]["found"]=False
    assert verdict(settings=c)["status"]=="BLOCKED_OR_REVIEW"


def test_missing_mp3_blocks():
    a,b,c=base()
    c["settings"]["output_format"]["options"]=["WAV"]
    assert verdict(settings=c)["status"]=="BLOCKED_OR_REVIEW"


def test_host_mismatch_blocks_and_wont_open_browser(tmp_path):
    chrome=tmp_path/"chrome.exe"
    chrome.write_bytes(b"no execution")
    with patch("saydivoice_discovery.saydi002_preflight.run_discovery") as probe:
        with pytest.raises(ValueError,match="WRONG_HOST_NO_PROFILE_OPENED"):
            run_preflight(host="DESKTOP-H4A16IL",chrome_path=chrome,
                          evidence_path=tmp_path/"result.json")
        probe.assert_not_called()
    assert not (tmp_path/"result.json").exists()


def test_no_profile_on_correct_machine_refuses_before_browser(tmp_path):
    chrome=tmp_path/"chrome.exe"
    chrome.write_bytes(b"no execution")
    from saydivoice_discovery.models import RuntimePaths
    bogus=RuntimePaths(
        root=tmp_path/"private",
        profile_dir=tmp_path/"private"/"browser_profile",
        logs_dir=tmp_path/"private"/"logs",
        screenshots_dir=tmp_path/"private"/"shots",
        reports_dir=tmp_path/"private"/"reports",
        downloads_dir=tmp_path/"private"/"downloads",
        runs_dir=tmp_path/"private"/"runs",
    )
    with patch("saydivoice_discovery.saydi002_preflight.build_runtime_paths",return_value=bogus), \
         patch("saydivoice_discovery.saydi002_preflight.run_discovery") as probe:
        with pytest.raises(ValueError,match="MISSING_RECOVERED_PROFILE"):
            run_preflight(host=EXPECTED_HOST,chrome_path=chrome,evidence_path=tmp_path/"result.json")
        probe.assert_not_called()


def test_private_book_text_not_in_result():
    a,b,c=base()
    a["private_manuscript"]="Nội dung sách riêng của Owner"
    b["sample_text"]="SECRET CONTENT"
    c["password"]="untrusted"
    serialized=json.dumps(verdict(report=a,voice=b,settings=c),ensure_ascii=False)
    assert "Nội dung sách" not in serialized
    assert "SECRET CONTENT" not in serialized
    assert "password" not in serialized


def test_profile_locked_blocks():
    a,b,c=base()
    r=evaluate(a,b,c,host=EXPECTED_HOST,profile_exists=True,profile_locked=True)
    assert r["status"]=="BLOCKED_OR_REVIEW"


def test_default_cli_is_off(capsys,tmp_path):
    rc=main(["--chrome",str(tmp_path/"nonexistent.exe"),
             "--output",str(tmp_path/"out.json")])
    assert rc==0
    assert "DISABLED_DEFAULT" in capsys.readouterr().out
    assert not (tmp_path/"out.json").exists()
