from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .models import RuntimePaths


def resolve_runtime_root() -> Path:
    """Return a local-only runtime root; never place browser profile data in Git."""
    override = os.environ.get("MAGASIN_MEDIA_ROBOT_HOME")
    if override:
        return Path(override).expanduser().resolve()

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "MAGASIN" / "MediaRobot"

    # Portable fallback for non-Windows developer/test environments.
    return Path.home() / ".magasin" / "MediaRobot"


def build_runtime_paths(root: Path | None = None) -> RuntimePaths:
    base = (root or resolve_runtime_root()) / "saydivoice"
    return RuntimePaths(
        root=base,
        profile_dir=base / "browser_profile",
        logs_dir=base / "logs",
        screenshots_dir=base / "screenshots",
        reports_dir=base / "reports",
        downloads_dir=base / "downloads",
        runs_dir=base / "runs",
    )


def sanitize_url(url: str) -> str:
    """Strip query/fragment to avoid persisting OAuth codes, tokens, or tracking data."""
    try:
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    except Exception:
        return ""


def sanitize_text(value: str | None, limit: int = 180) -> str | None:
    if value is None:
        return None
    compact = re.sub(r"\s+", " ", value).strip()
    compact = re.sub(r"(?i)bearer\s+[a-z0-9._~+/-]+=*", "[REDACTED_BEARER]", compact)
    compact = re.sub(r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}(?:\.[a-zA-Z0-9_-]{10,})?\b", "[REDACTED_JWT]", compact)
    compact = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[REDACTED_EMAIL]", compact)
    return compact[:limit]


def sanitize_error_message(value: str, limit: int = 500) -> str:
    """Redact common secrets and remove query/fragment parts from URLs in errors."""
    safe = sanitize_text(value, limit=5000) or ""
    safe = re.sub(
        r"https?://[^\s\"']+",
        lambda m: sanitize_url(m.group(0)),
        safe,
    )
    return safe[:limit]
