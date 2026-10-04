from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Severity = Literal["INFO", "WARNING", "ERROR"]
QCStatus = Literal["PASS", "REPAIR", "REVIEW", "FAIL"]


@dataclass(frozen=True, slots=True)
class QualityPolicy:
    """Deterministic thresholds used by audiobook pronunciation/prosody QC."""

    asr_pass_similarity: float = 0.88
    asr_hard_fail_similarity: float = 0.72
    min_word_confidence: float = 0.68
    hard_fail_word_confidence: float = 0.45
    min_speaking_rate_wpm: float = 105.0
    max_speaking_rate_wpm: float = 185.0
    min_pause_ratio: float = 0.05
    max_pause_ratio: float = 0.34
    min_pitch_variation_semitones: float = 0.65
    max_clipping_ratio: float = 0.005
    max_auto_attempts: int = 2

    def validate(self) -> None:
        for name, value in (
            ("asr_pass_similarity", self.asr_pass_similarity),
            ("asr_hard_fail_similarity", self.asr_hard_fail_similarity),
            ("min_word_confidence", self.min_word_confidence),
            ("hard_fail_word_confidence", self.hard_fail_word_confidence),
            ("min_pause_ratio", self.min_pause_ratio),
            ("max_pause_ratio", self.max_pause_ratio),
            ("max_clipping_ratio", self.max_clipping_ratio),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0,1]")
        if self.asr_hard_fail_similarity >= self.asr_pass_similarity:
            raise ValueError("hard-fail ASR threshold must be below pass threshold")
        if self.hard_fail_word_confidence >= self.min_word_confidence:
            raise ValueError("hard-fail word confidence must be below review threshold")
        if self.min_speaking_rate_wpm <= 0 or self.max_speaking_rate_wpm <= self.min_speaking_rate_wpm:
            raise ValueError("invalid speaking-rate range")
        if self.max_pause_ratio <= self.min_pause_ratio:
            raise ValueError("invalid pause-ratio range")
        if self.min_pitch_variation_semitones < 0:
            raise ValueError("pitch variation threshold must be >= 0")
        if self.max_auto_attempts < 1:
            raise ValueError("max_auto_attempts must be >= 1")


@dataclass(frozen=True, slots=True)
class QualityObservation:
    """Measurements for exactly one rendered chunk/audio hash.

    The local worker is responsible for extracting these measurements. The core
    intentionally does not depend on a specific ASR, pitch tracker, or TTS model.
    """

    chunk_id: str
    audio_sha256: str
    attempt: int = 1
    asr_similarity: float | None = None
    min_word_confidence: float | None = None
    mean_word_confidence: float | None = None
    unclear_tokens: tuple[str, ...] = ()
    speaking_rate_wpm: float | None = None
    pause_ratio: float | None = None
    pitch_variation_semitones: float | None = None
    energy_variation_db: float | None = None
    clipping_ratio: float | None = None

    def validate(self) -> None:
        if not self.chunk_id.strip():
            raise ValueError("chunk_id is required")
        if len(self.audio_sha256) != 64:
            raise ValueError("audio_sha256 must be SHA-256 hex")
        if self.attempt < 1:
            raise ValueError("attempt must be >= 1")
        for name, value in (
            ("asr_similarity", self.asr_similarity),
            ("min_word_confidence", self.min_word_confidence),
            ("mean_word_confidence", self.mean_word_confidence),
            ("pause_ratio", self.pause_ratio),
            ("clipping_ratio", self.clipping_ratio),
        ):
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0,1]")
        if self.speaking_rate_wpm is not None and self.speaking_rate_wpm <= 0:
            raise ValueError("speaking_rate_wpm must be > 0")
        if self.pitch_variation_semitones is not None and self.pitch_variation_semitones < 0:
            raise ValueError("pitch_variation_semitones must be >= 0")


@dataclass(frozen=True, slots=True)
class QualityFinding:
    kind: str
    severity: Severity
    message: str
    tokens: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class QualityReport:
    chunk_id: str
    audio_sha256: str
    status: QCStatus
    pronunciation_status: Literal["PASS", "REPAIR", "REVIEW", "UNKNOWN"]
    prosody_status: Literal["PASS", "REPAIR", "REVIEW", "UNKNOWN"]
    acoustic_status: Literal["PASS", "REPAIR", "REVIEW", "UNKNOWN"]
    findings: tuple[QualityFinding, ...] = ()
    repair_actions: tuple[str, ...] = ()
    owner_review_required: bool = False
    metrics_missing: tuple[str, ...] = ()


def _missing(observation: QualityObservation) -> tuple[str, ...]:
    required = (
        "asr_similarity",
        "min_word_confidence",
        "speaking_rate_wpm",
        "pause_ratio",
        "pitch_variation_semitones",
        "clipping_ratio",
    )
    return tuple(name for name in required if getattr(observation, name) is None)


def evaluate_quality(
    observation: QualityObservation,
    policy: QualityPolicy | None = None,
) -> QualityReport:
    """Classify a chunk and produce a bounded repair plan.

    Automatic repair is intentionally limited to retry-safe narration changes.
    After the retry budget is exhausted the same defects require review rather
    than an infinite generation loop.
    """

    policy = policy or QualityPolicy()
    policy.validate()
    observation.validate()

    findings: list[QualityFinding] = []
    repair_actions: list[str] = []
    missing = _missing(observation)

    pronunciation = "UNKNOWN"
    pronunciation_bad = False
    pronunciation_hard = False

    if observation.asr_similarity is not None or observation.min_word_confidence is not None:
        pronunciation = "PASS"
        if (
            observation.asr_similarity is not None
            and observation.asr_similarity < policy.asr_hard_fail_similarity
        ) or (
            observation.min_word_confidence is not None
            and observation.min_word_confidence < policy.hard_fail_word_confidence
        ):
            pronunciation_bad = True
            pronunciation_hard = True
            pronunciation = "REPAIR"
            findings.append(
                QualityFinding(
                    kind="pronunciation_unclear",
                    severity="ERROR",
                    message="Speech recognition evidence indicates unclear or incorrect pronunciation.",
                    tokens=observation.unclear_tokens,
                )
            )
        elif (
            observation.asr_similarity is not None
            and observation.asr_similarity < policy.asr_pass_similarity
        ) or (
            observation.min_word_confidence is not None
            and observation.min_word_confidence < policy.min_word_confidence
        ) or observation.unclear_tokens:
            pronunciation_bad = True
            pronunciation = "REPAIR"
            findings.append(
                QualityFinding(
                    kind="pronunciation_suspect",
                    severity="WARNING",
                    message="One or more words are not sufficiently clear for automatic acceptance.",
                    tokens=observation.unclear_tokens,
                )
            )

    prosody = "UNKNOWN"
    prosody_bad = False
    prosody_reasons: list[str] = []
    if any(
        value is not None
        for value in (
            observation.speaking_rate_wpm,
            observation.pause_ratio,
            observation.pitch_variation_semitones,
        )
    ):
        prosody = "PASS"
        if observation.speaking_rate_wpm is not None:
            if observation.speaking_rate_wpm < policy.min_speaking_rate_wpm:
                prosody_reasons.append("pace_too_slow")
            elif observation.speaking_rate_wpm > policy.max_speaking_rate_wpm:
                prosody_reasons.append("pace_too_fast")
        if observation.pause_ratio is not None:
            if observation.pause_ratio < policy.min_pause_ratio:
                prosody_reasons.append("insufficient_pauses")
            elif observation.pause_ratio > policy.max_pause_ratio:
                prosody_reasons.append("excessive_pauses")
        if (
            observation.pitch_variation_semitones is not None
            and observation.pitch_variation_semitones < policy.min_pitch_variation_semitones
        ):
            prosody_reasons.append("flat_intonation")

        if prosody_reasons:
            prosody_bad = True
            prosody = "REPAIR"
            findings.append(
                QualityFinding(
                    kind="prosody_style_mismatch",
                    severity="WARNING",
                    message="Prosody is outside the accepted audiobook style envelope: "
                    + ", ".join(prosody_reasons),
                )
            )

    acoustic = "UNKNOWN"
    acoustic_bad = False
    if observation.clipping_ratio is not None:
        acoustic = "PASS"
        if observation.clipping_ratio > policy.max_clipping_ratio:
            acoustic_bad = True
            acoustic = "REPAIR"
            findings.append(
                QualityFinding(
                    kind="clipping",
                    severity="ERROR",
                    message="Clipping ratio exceeds the accepted threshold.",
                )
            )

    any_bad = pronunciation_bad or prosody_bad or acoustic_bad

    if any_bad:
        retry_allowed = observation.attempt < policy.max_auto_attempts
        if retry_allowed:
            if pronunciation_bad:
                repair_actions.extend(
                    (
                        "apply_pronunciation_lexicon_or_spoken_form",
                        "split_chunk_around_unclear_tokens",
                        "rerender_affected_chunk",
                    )
                )
            if prosody_bad:
                repair_actions.extend(
                    (
                        "adjust_pace_pause_or_sentence_segmentation",
                        "rerender_affected_chunk",
                    )
                )
            if acoustic_bad:
                repair_actions.append("rerender_affected_chunk")
            # preserve order but remove duplicate actions
            repair_actions = list(dict.fromkeys(repair_actions))
            status: QCStatus = "REPAIR"
            owner_review_required = False
        else:
            status = "REVIEW"
            owner_review_required = True
            pronunciation = "REVIEW" if pronunciation_bad else pronunciation
            prosody = "REVIEW" if prosody_bad else prosody
            acoustic = "REVIEW" if acoustic_bad else acoustic
            findings.append(
                QualityFinding(
                    kind="retry_budget_exhausted",
                    severity="WARNING",
                    message="Automatic repair budget is exhausted; human review or a voice/model change is required.",
                )
            )
    elif missing:
        status = "REVIEW"
        owner_review_required = True
        findings.append(
            QualityFinding(
                kind="metrics_incomplete",
                severity="WARNING",
                message="Required pronunciation/prosody metrics are missing; automatic acceptance is unsafe.",
            )
        )
    else:
        status = "PASS"
        owner_review_required = False

    if pronunciation_hard and observation.attempt >= policy.max_auto_attempts:
        status = "REVIEW"
        owner_review_required = True

    return QualityReport(
        chunk_id=observation.chunk_id,
        audio_sha256=observation.audio_sha256,
        status=status,
        pronunciation_status=pronunciation,
        prosody_status=prosody,
        acoustic_status=acoustic,
        findings=tuple(findings),
        repair_actions=tuple(repair_actions),
        owner_review_required=owner_review_required,
        metrics_missing=missing,
    )
