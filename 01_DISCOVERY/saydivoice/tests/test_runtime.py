from pathlib import Path

from saydivoice_discovery.runtime import build_runtime_paths, sanitize_error_message, sanitize_text, sanitize_url


def test_runtime_paths_stay_under_requested_root(tmp_path: Path):
    paths = build_runtime_paths(tmp_path)
    paths.create()
    assert paths.root == tmp_path / "saydivoice"
    assert paths.profile_dir.parent == paths.root
    assert paths.logs_dir.exists()
    assert paths.reports_dir.exists()
    assert paths.runs_dir.exists()


def test_sanitize_url_strips_query_and_fragment():
    assert sanitize_url("https://example.test/path?token=secret#frag") == "https://example.test/path"


def test_sanitize_text_masks_bearer_and_compacts_whitespace():
    value = "hello   bearer abcdefghijklmnop.qwerty   world"
    clean = sanitize_text(value)
    assert clean is not None
    assert "abcdef" not in clean
    assert "  " not in clean


def test_sanitize_text_masks_email():
    clean = sanitize_text("Profile: private@example.com")
    assert clean == "Profile: [REDACTED_EMAIL]"


def test_sanitize_error_strips_url_query_and_email():
    clean = sanitize_error_message("failed https://example.test/callback?code=secret user private@example.com")
    assert "secret" not in clean
    assert "private@example.com" not in clean
    assert "https://example.test/callback" in clean
