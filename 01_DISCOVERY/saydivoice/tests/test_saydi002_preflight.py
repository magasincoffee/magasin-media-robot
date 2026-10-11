"""Standard-library offline safety regression for SAYDI002-003 (no real browser)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from saydivoice_discovery.saydi002_preflight import (
    EXPECTED_HOST, PRESET, evaluate, run_preflight, main
)


def data():
    report={"page_state":"TTS_READY","auth_state":"AUTHENTICATED_OR_HIDDEN",
            "run_status":"CAPTURED","generation_lifecycle_path":None}
    voice={"opened":True,"closed_after_observation":True,"current_label":"Tự động",
           "options":[{"text":"SG - Chí Đạt"}]}
    settings={"settings":{
        "stability":{"found":True},"speed":{"found":True},"pause":{"found":True},
        "output_format":{"found":True,"options":["WAV","MP3","FLAC"]}}}
    return report,voice,settings


class PreflightContractTests(unittest.TestCase):
    def verdict(self,report=None,voice=None,settings=None,host=EXPECTED_HOST,**kwargs):
        a,b,c=data()
        return evaluate(a if report is None else report,
                        b if voice is None else voice,
                        c if settings is None else settings,
                        host=host,profile_exists=True,**kwargs)

    def test_clean_evidence_passes_without_generation_or_audio_approval(self):
        r=self.verdict()
        self.assertEqual(r["task_id"],"SAYDI002-003")
        self.assertEqual(r["preset"],PRESET)
        self.assertEqual(r["status"],"PASS")
        self.assertEqual(r["generate_clicks"],0)
        self.assertEqual(r["new_audio_files"],0)
        self.assertFalse(r["production_authorized"])
        self.assertFalse(r["owner_audio_approval"])

    def test_logged_out_blocks(self):
        a,b,c=data();a["page_state"]="LOGIN_REQUIRED"
        self.assertEqual(self.verdict(report=a)["status"],"BLOCKED_OR_REVIEW")

    def test_unknown_auth_blocks(self):
        a,b,c=data();a["auth_state"]="UNKNOWN"
        self.assertEqual(self.verdict(report=a)["status"],"BLOCKED_OR_REVIEW")

    def test_unknown_capture_status_blocks(self):
        a,b,c=data();a["run_status"]="UNKNOWN"
        self.assertEqual(self.verdict(report=a)["status"],"BLOCKED_OR_REVIEW")

    def test_generation_lifecycle_blocks(self):
        a,b,c=data();a["generation_lifecycle_path"]="C:/new_audio.json"
        r=self.verdict(report=a)
        self.assertEqual(r["status"],"BLOCKED_OR_REVIEW")
        self.assertIsNone(r["generate_clicks"])
        self.assertIsNone(r["new_audio_files"])

    def test_voice_missing_blocks(self):
        a,b,c=data();b["options"]=[{"text":"HN - Mai Phương"}]
        self.assertEqual(self.verdict(voice=b)["status"],"BLOCKED_OR_REVIEW")

    def test_voice_current_can_validate_without_selector(self):
        a,b,c=data();b["current_label"]="SG - Chí Đạt";b["options"]=[]
        self.assertEqual(self.verdict(voice=b)["status"],"PASS")

    def test_missing_stability_blocks(self):
        a,b,c=data();c["settings"]["stability"]["found"]=False
        self.assertEqual(self.verdict(settings=c)["status"],"BLOCKED_OR_REVIEW")

    def test_missing_speed_blocks(self):
        a,b,c=data();c["settings"]["speed"]["found"]=False
        self.assertEqual(self.verdict(settings=c)["status"],"BLOCKED_OR_REVIEW")

    def test_missing_pause_blocks(self):
        a,b,c=data();c["settings"]["pause"]["found"]=False
        self.assertEqual(self.verdict(settings=c)["status"],"BLOCKED_OR_REVIEW")

    def test_mp3_missing_blocks(self):
        a,b,c=data();c["settings"]["output_format"]["options"]=["WAV"]
        self.assertEqual(self.verdict(settings=c)["status"],"BLOCKED_OR_REVIEW")

    def test_wrong_host_cannot_open_browser(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); chrome=root/"chrome.exe";chrome.write_bytes(b"x")
            with patch("saydivoice_discovery.saydi002_preflight.run_discovery") as probe:
                with self.assertRaisesRegex(ValueError,"WRONG_HOST_NO_PROFILE_OPENED"):
                    run_preflight(host="DESKTOP-H4A16IL",chrome_path=chrome,
                                  evidence_path=root/"report.json")
                probe.assert_not_called()
            self.assertFalse((root/"report.json").exists())

    def test_recovered_profile_absent_cannot_open_browser(self):
        from saydivoice_discovery.models import RuntimePaths
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);chrome=root/"chrome.exe";chrome.write_bytes(b"x")
            app=root/"no_profile"
            paths=RuntimePaths(root=app,profile_dir=app/"browser_profile",
                               logs_dir=app/"logs",screenshots_dir=app/"shots",
                               reports_dir=app/"reports",downloads_dir=app/"downloads",
                               runs_dir=app/"runs")
            with patch("saydivoice_discovery.saydi002_preflight.build_runtime_paths",return_value=paths), \
                 patch("saydivoice_discovery.saydi002_preflight.run_discovery") as probe:
                with self.assertRaisesRegex(ValueError,"MISSING_RECOVERED_PROFILE"):
                    run_preflight(host=EXPECTED_HOST,chrome_path=chrome,
                                  evidence_path=root/"output.json")
                probe.assert_not_called()

    def test_private_fields_never_enter_sanitized_result(self):
        a,b,c=data()
        a["private_manuscript"]="NO_EXPORT_MANUSCRIPT"
        b["sample_text"]="NO_EXPORT_SCRIPT"
        c["password"]="NO_EXPORT_SECRET"
        encoded=json.dumps(self.verdict(report=a,voice=b,settings=c))
        for secret in ("NO_EXPORT_MANUSCRIPT","NO_EXPORT_SCRIPT","NO_EXPORT_SECRET"):
            self.assertNotIn(secret,encoded)

    def test_locked_profile_blocks(self):
        a,b,c=data()
        result=evaluate(a,b,c,host=EXPECTED_HOST,profile_exists=True,profile_locked=True)
        self.assertEqual(result["status"],"BLOCKED_OR_REVIEW")

    def test_default_command_is_non_executing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            code=main(["--chrome",str(root/"none.exe"),
                       "--output",str(root/"out.json")])
            self.assertEqual(code,0)
            self.assertFalse((root/"out.json").exists())


if __name__=="__main__":
    unittest.main(verbosity=2)
