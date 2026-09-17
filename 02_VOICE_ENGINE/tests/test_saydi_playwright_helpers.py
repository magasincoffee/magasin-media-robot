from pathlib import Path

from magasin_voice_engine.models import FailureDisposition
from magasin_voice_engine.saydi_playwright import _http_disposition, _safe_filename, _unique_path


def test_safe_filename_strips_path_and_windows_reserved_characters():
    assert _safe_filename('../bad:name?.mp3') == 'bad_name_.mp3'
    assert _safe_filename('') == 'saydivoice.mp3'


def test_unique_path_never_overwrites_existing_file(tmp_path):
    first = tmp_path / 'voice.mp3'
    first.write_bytes(b'x')
    assert _unique_path(tmp_path, 'voice.mp3') == tmp_path / 'voice_1.mp3'


def test_http_disposition_maps_provider_failures():
    assert _http_disposition(401) == FailureDisposition.RE_AUTH
    assert _http_disposition(403) == FailureDisposition.RE_AUTH
    assert _http_disposition(429) == FailureDisposition.RETRY
    assert _http_disposition(500) == FailureDisposition.RETRY
    assert _http_disposition(413) == FailureDisposition.FIX_INPUT
    assert _http_disposition(422) == FailureDisposition.FIX_INPUT
    assert _http_disposition(418) == FailureDisposition.DO_NOT_RETRY
