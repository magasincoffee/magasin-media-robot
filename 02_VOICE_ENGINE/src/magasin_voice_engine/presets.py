from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from .models import SUPPORTED_FORMATS

DEFAULT_VOICE = "Adam — Giọng hot tiktok"


@dataclass(frozen=True, slots=True)
class PauseProfile:
    enabled: bool = False
    dot_seconds: float = 0.45
    comma_seconds: float = 0.25
    semicolon_seconds: float = 0.30
    newline_seconds: float = 0.60


@dataclass(frozen=True, slots=True)
class VoicePreset:
    key: str
    label: str
    voice: str
    stability_ratio: float
    speed_ratio: float
    audio_format: str = "MP3"
    pause: PauseProfile = PauseProfile()
    intent: str = ""

    def validate(self) -> None:
        if not self.key.strip():
            raise ValueError("preset key is required")
        if not self.voice.strip():
            raise ValueError("voice is required")
        if not 0.0 <= self.stability_ratio <= 1.0:
            raise ValueError("stability_ratio must be between 0 and 1")
        if not 0.0 <= self.speed_ratio <= 1.0:
            raise ValueError("speed_ratio must be between 0 and 1")
        if self.audio_format.upper() not in SUPPORTED_FORMATS:
            raise ValueError(f"unsupported audio format: {self.audio_format}")


PRESETS: Mapping[str, VoicePreset] = {
    "tiktok_energetic": VoicePreset(
        key="tiktok_energetic",
        label="TikTok năng lượng",
        voice=DEFAULT_VOICE,
        stability_ratio=0.30,
        speed_ratio=0.65,
        pause=PauseProfile(enabled=False),
        intent="Nhanh, nhiều biểu cảm, phù hợp hook/video ngắn.",
    ),
    "review_natural": VoicePreset(
        key="review_natural",
        label="Review tự nhiên",
        voice=DEFAULT_VOICE,
        stability_ratio=0.50,
        speed_ratio=0.50,
        pause=PauseProfile(enabled=True),
        intent="Cân bằng biểu cảm và ổn định, nhịp nói tự nhiên.",
    ),
    "story_warm": VoicePreset(
        key="story_warm",
        label="Kể chuyện ấm",
        voice=DEFAULT_VOICE,
        stability_ratio=0.40,
        speed_ratio=0.35,
        pause=PauseProfile(
            enabled=True,
            dot_seconds=0.55,
            comma_seconds=0.30,
            semicolon_seconds=0.35,
            newline_seconds=0.70,
        ),
        intent="Chậm hơn, mềm và có khoảng nghỉ cho nội dung kể chuyện.",
    ),
    "news_stable": VoicePreset(
        key="news_stable",
        label="Thông tin ổn định",
        voice=DEFAULT_VOICE,
        stability_ratio=0.80,
        speed_ratio=0.50,
        pause=PauseProfile(enabled=True),
        intent="Đều, rõ, ít biến động cảm xúc.",
    ),
    "slow_emotional": VoicePreset(
        key="slow_emotional",
        label="Chậm cảm xúc",
        voice=DEFAULT_VOICE,
        stability_ratio=0.30,
        speed_ratio=0.35,
        pause=PauseProfile(
            enabled=True,
            dot_seconds=0.60,
            comma_seconds=0.35,
            semicolon_seconds=0.40,
            newline_seconds=0.75,
        ),
        intent="Nghiêng về biểu cảm, tốc độ chậm và khoảng nghỉ dài hơn.",
    ),
}


def get_preset(
    key: str,
    *,
    voice_override: str | None = None,
    format_override: str | None = None,
) -> VoicePreset:
    try:
        preset = PRESETS[key]
    except KeyError as exc:
        available = ", ".join(sorted(PRESETS))
        raise ValueError(f"unknown voice preset {key!r}; available: {available}") from exc

    if voice_override is not None:
        if not voice_override.strip():
            raise ValueError("voice_override must not be blank")
        preset = replace(preset, voice=voice_override.strip())
    if format_override is not None:
        fmt = format_override.upper()
        if fmt not in SUPPORTED_FORMATS:
            raise ValueError(f"unsupported format_override: {format_override}")
        preset = replace(preset, audio_format=fmt)

    preset.validate()
    return preset
