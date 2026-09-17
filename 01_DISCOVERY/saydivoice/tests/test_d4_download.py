from pathlib import Path

from saydivoice_discovery.d4_download import _sha256, build_parser


def test_d4_requires_explicit_download_flag_at_cli_contract_level():
    args = build_parser().parse_args(["--chromium-executable", "chrome.exe", "--allow-download"])
    assert args.allow_download is True
    assert not hasattr(args, "allow_generate")


def test_d4_download_is_not_authorized_by_default():
    args = build_parser().parse_args(["--chromium-executable", "chrome.exe"])
    assert args.allow_download is False


def test_sha256_file(tmp_path: Path):
    p = tmp_path / "a.bin"
    p.write_bytes(b"abc")
    assert _sha256(p) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
