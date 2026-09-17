from saydivoice_discovery.profile_setup import build_parser


def test_profile_setup_accepts_installed_chrome_executable() -> None:
    args = build_parser().parse_args([
        "--chromium-executable",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ])
    assert args.chromium_executable.endswith("chrome.exe")
