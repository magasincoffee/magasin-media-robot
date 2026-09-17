from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


DEFAULT_VOICE = "Adam — Giọng hot tiktok"
SUPPORTED_FORMATS = frozenset({"WAV", "MP3", "FLAC", "OGG"})

# Field-calibrated on the authenticated SaydiVoice UI. These are reference
# points, not a claim that Saydi exposes a discrete emotion API.
CALIBRATED_STABILITY_POINTS: Mapping[float, float] = {
    0.20: 1.6,
    0.40: 2.2,
    0.60: 2.8,
    0.80: 3.4,
}

CALIBRATED_SPEED_POINTS: Mapping[float, float] = {
    0.20: 0.70,
    0.35: 0.85,
    0.50: 1.00,
    0.65: 1.15,
    0.80: 1.30,
}


@dataclass(frozen=True, slots=True)
class PauseProfile:
    enabled: bool = False
    dot_seconds: float = 0.45
    comma_seconds: float = 0.25
    semicolon_seconds: float = 0.30
    newline_seconds: float = 0.60

    def validate(self) -> None:
        for name, value in (
            ("dot_seconds", self.dot_seconds),
            ("comma_seconds", self.comma_seconds),
            ("semicolon_seconds", self.semicolon_seconds),
            ("newline_seconds", self.newline_seconds),
        ):
            if value < 0:
                raise ValueError(f"{name} must be >= 0")


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
        self.pause.validate()


# Application-level style presets. SaydiVoice itself was observed to expose
# voice choice, a Biểu cảm ↔ Ổn định axis, speed, pause controls and format;
# no separate Happy/Sad/Angry mood selector was observed. Therefore mood is
# represented here as a deterministic combination of those real controls.
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
        pause=PauseProfile(enabled=True, dot_seconds=0.55, comma_seconds=0.30, semicolon_seconds=0.35, newline_seconds=0.70),
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
        pause=PauseProfile(enabled=True, dot_seconds=0.60, comma_seconds=0.35, semicolon_seconds=0.40, newline_seconds=0.75),
        intent="Nghiêng về biểu cảm, tốc độ chậm và khoảng nghỉ dài hơn.",
    ),
}


def get_preset(key: str) -> VoicePreset:
    try:
        preset = PRESETS[key]
    except KeyError as exc:
        available = ", ".join(sorted(PRESETS))
        raise KeyError(f"unknown voice preset {key!r}; available: {available}") from exc
    preset.validate()
    return preset


def nearest_calibrated_stability(ratio: float) -> tuple[float, float]:
    key = min(CALIBRATED_STABILITY_POINTS, key=lambda x: abs(x - ratio))
    return key, CALIBRATED_STABILITY_POINTS[key]


def nearest_calibrated_speed(ratio: float) -> tuple[float, float]:
    key = min(CALIBRATED_SPEED_POINTS, key=lambda x: abs(x - ratio))
    return key, CALIBRATED_SPEED_POINTS[key]


def describe_preset(key: str) -> dict[str, object]:
    preset = get_preset(key)
    stability_ref_ratio, stability_ui = nearest_calibrated_stability(preset.stability_ratio)
    speed_ref_ratio, speed_ui = nearest_calibrated_speed(preset.speed_ratio)
    return {
        "key": preset.key,
        "label": preset.label,
        "voice": preset.voice,
        "stability_ratio": preset.stability_ratio,
        "nearest_stability_reference_ratio": stability_ref_ratio,
        "nearest_stability_ui_value": stability_ui,
        "speed_ratio": preset.speed_ratio,
        "nearest_speed_reference_ratio": speed_ref_ratio,
        "nearest_speed_multiplier": speed_ui,
        "format": preset.audio_format,
        "pause": {
            "enabled": preset.pause.enabled,
            "dot_seconds": preset.pause.dot_seconds,
            "comma_seconds": preset.pause.comma_seconds,
            "semicolon_seconds": preset.pause.semicolon_seconds,
            "newline_seconds": preset.pause.newline_seconds,
        },
        "intent": preset.intent,
    }
