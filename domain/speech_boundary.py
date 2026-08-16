from __future__ import annotations

lazy import math
lazy import threading
lazy from dataclasses import dataclass
lazy from enum import StrEnum

TICKS_PER_SECOND = 10_000_000


class SpeechTimingKind(StrEnum):
    WORD = "word"
    PUNCTUATION = "punctuation"
    SENTENCE = "sentence"
    VISEME = "viseme"


@dataclass(frozen=True, slots=True)
class SpeechTimingEvent:
    operation_id: int
    audio_offset_seconds: float
    duration_seconds: float
    kind: SpeechTimingKind
    estimated: bool
    cue_id: int | None = None


class SpeechTimingCollector:
    """Convert Azure callbacks into privacy-safe, deduplicated timing events."""

    def __init__(self, operation_id: int) -> None:
        if operation_id < 0:
            raise ValueError("operation_id must be non-negative")
        self.operation_id = operation_id
        self._seen: set[tuple[object, ...]] = set()
        self._lock = threading.Lock()

    def word_boundary(self, event: object) -> SpeechTimingEvent | None:
        offset = _ticks(getattr(event, "audio_offset", None))
        if offset is None:
            return None
        duration = _ticks(getattr(event, "duration", None))
        estimated = duration is None
        kind = _boundary_kind(getattr(event, "boundary_type", None))
        return self._unique(
            SpeechTimingEvent(
                self.operation_id,
                offset,
                0.0 if duration is None else duration,
                kind,
                estimated,
            )
        )

    def viseme(self, event: object) -> SpeechTimingEvent | None:
        offset = _ticks(getattr(event, "audio_offset", None))
        cue_id = getattr(event, "viseme_id", None)
        if offset is None or not isinstance(cue_id, int) or isinstance(cue_id, bool) or cue_id < 0:
            return None
        return self._unique(
            SpeechTimingEvent(
                self.operation_id,
                offset,
                0.0,
                SpeechTimingKind.VISEME,
                True,
                cue_id,
            )
        )

    def _unique(self, event: SpeechTimingEvent) -> SpeechTimingEvent | None:
        identity = (
            event.kind,
            event.audio_offset_seconds,
            event.duration_seconds,
            event.cue_id,
        )
        with self._lock:
            if identity in self._seen:
                return None
            self._seen.add(identity)
        return event


def _ticks(value: object) -> float | None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return None
    seconds = value / TICKS_PER_SECOND
    return seconds if math.isfinite(seconds) else None


def _boundary_kind(value: object) -> SpeechTimingKind:
    name = getattr(value, "name", value)
    normalized = str(name).rsplit(".", 1)[-1].lower()
    return {
        "punctuation": SpeechTimingKind.PUNCTUATION,
        "sentence": SpeechTimingKind.SENTENCE,
        "word": SpeechTimingKind.WORD,
    }.get(normalized, SpeechTimingKind.WORD)
