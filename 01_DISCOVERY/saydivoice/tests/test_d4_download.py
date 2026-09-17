from pathlib import Path

from saydivoice_discovery.d4_download import _safe_suggested_filename, _sha256_file, build_parser


def test_d4_requires_explicit_flags_at_cli_contract_level():
    args = build_parser().parse_args(["--allow-generate", "--allow-download"])
    assert args.allow_generate is True
    assert args.allow_download is True


def test_safe_suggested_filename_strips_path_and_control_chars():
    assert _safe_suggested_filename("../audio\nname.mp3") == "audio_name.mp3"


def test_sha256_file(tmp_path: Path):
    p = tmp_path / "a.bin"
    p.write_bytes(b"abc")
    assert _sha256_file(p) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
