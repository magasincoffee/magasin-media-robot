from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

PageState = Literal["TTS_READY", "LOGIN_REQUIRED", "ACCESS_BLOCKED", "UNKNOWN"]
RunStatus = Literal["CAPTURED", "LOGIN_REQUIRED", "ACCESS_BLOCKED", "UNKNOWN", "BROWSER_ERROR"]
AuthState = Literal["ANONYMOUS", "AUTHENTICATED_OR_HIDDEN", "UNKNOWN"]


@dataclass(frozen=True)
class RuntimePaths:
    root: Path
    profile_dir: Path
    logs_dir: Path
    screenshots_dir: Path
    reports_dir: Path
    downloads_dir: Path
    runs_dir: Path

    def create(self) -> None:
        for path in (
            self.root,
            self.profile_dir,
            self.logs_dir,
            self.screenshots_dir,
            self.reports_dir,
            self.downloads_dir,
            self.runs_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class DiscoveryConfig:
    tts_url: str = "https://voice.saydi.ai/vi/studio/tts/"
    headless: bool = False
    navigation_timeout_ms: int = 45_000
    settle_ms: int = 1_500
    viewport_width: int = 1440
    viewport_height: int = 1000
    chromium_executable_path: str | None = None
    login_wait_seconds: int = 0
    login_poll_ms: int = 2_000
    allow_generate: bool = False
    generation_timeout_ms: int = 60_000
    generation_poll_ms: int = 500
    generation_retry_after_reload_error: bool = False


@dataclass(frozen=True)
class PageSignals:
    url: str
    title: str
    visible_text: str
    has_password_input: bool = False
    has_textarea: bool = False
    has_contenteditable: bool = False
    button_texts: tuple[str, ...] = ()
    link_texts: tuple[str, ...] = ()


@dataclass(frozen=True)
class InteractiveElement:
    index: int
    tag: str
    role: str | None = None
    name: str | None = None
    text: str | None = None
    input_type: str | None = None
    placeholder: str | None = None
    aria_label: str | None = None
    test_id: str | None = None
    contenteditable: bool = False
    disabled: bool = False
    aria_selected: str | None = None
    aria_checked: str | None = None
    aria_valuenow: str | None = None
    aria_valuemin: str | None = None
    aria_valuemax: str | None = None


@dataclass
class DiscoveryReport:
    schema_version: str
    runner_version: str
    run_id: str
    started_at: str
    finished_at: str
    target_url: str
    final_url: str
    page_title: str
    page_state: PageState
    run_status: RunStatus
    screenshot_path: str | None
    dom_inventory_path: str | None
    element_count: int
    auth_state: AuthState = "UNKNOWN"
    surface_map_path: str | None = None
    selectors_path: str | None = None
    voice_catalog_path: str | None = None
    settings_catalog_path: str | None = None
    generation_lifecycle_path: str | None = None
    notes: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
