from __future__ import annotations

lazy import time
lazy from collections.abc import Callable
lazy from dataclasses import dataclass, replace
lazy from enum import StrEnum


class SpeechPerformancePhase(StrEnum):
    IDLE = "idle"
    PREPARING = "preparing"
    SPEAKING = "speaking"
    PAUSING = "pausing"
    SETTLING = "settling"
    INTERRUPTED = "interrupted"


class SpeechEventKind(StrEnum):
    PREPARE = "prepare"
    FIRST_AUDIO = "first-audio"
    SEGMENT_BOUNDARY = "segment-boundary"
    VISEME = "viseme"
    PAUSE = "pause"
    FINAL_AUDIO = "final-audio"
    MOUTH_CLOSED = "mouth-closed"
    INTERRUPT = "interrupt"
    FAILURE = "failure"


@dataclass(frozen=True, slots=True)
class SpeechEvent:
    """Provider-neutral event; spoken text and secrets are never retained."""

    generation: int
    provider_id: str
    kind: SpeechEventKind
    timestamp: float
    level: float = 0.0
    viseme: str = "CLOSED"
    segment_index: int = 0
    estimated: bool = False


@dataclass(frozen=True, slots=True)
class SpeechPerformanceDirective:
    """Small body-performance controls consumed by the behaviour director."""

    generation: int
    phase: SpeechPerformancePhase
    body_energy: float
    breath: float
    emphasis: float
    gesture_beat: bool
    allow_large_turn: bool
    hold_current_pose: bool
    reason: str


@dataclass(frozen=True, slots=True)
class SpeechPerformanceSnapshot:
    generation: int = 0
    provider_id: str = ""
    phase: SpeechPerformancePhase = SpeechPerformancePhase.IDLE
    prepared_at: float = 0.0
    audio_started_at: float = 0.0
    last_event_at: float = 0.0
    last_boundary_at: float = 0.0
    segment_index: int = 0
    last_viseme: str = "CLOSED"
    last_level: float = 0.0
    mouth_closed: bool = True
    interrupted: bool = False


class SpeechPerformanceTimeline:
    """Normalize every speech provider into one safe performance timeline.

    Providers may expose rich boundaries or only audio-derived visemes. The
    latter use restrained, rate-limited estimated segment beats so body motion
    remains synchronized without pretending exact word timing is available.
    """

    def __init__(
        self,
        clock: Callable[[], float] | None = None,
        *,
        estimated_segment_seconds: float = 0.72,
        minimum_gesture_gap_seconds: float = 0.48,
    ) -> None:
        if estimated_segment_seconds <= 0.0:
            raise ValueError("Estimated segment duration must be positive.")
        if minimum_gesture_gap_seconds <= 0.0:
            raise ValueError("Minimum gesture gap must be positive.")
        self._clock = clock or time.monotonic
        self.estimated_segment_seconds = float(estimated_segment_seconds)
        self.minimum_gesture_gap_seconds = float(minimum_gesture_gap_seconds)
        self._generation = 0
        self._last_gesture_at = 0.0
        self._has_rich_boundary = False
        self._snapshot = SpeechPerformanceSnapshot()

    @property
    def snapshot(self) -> SpeechPerformanceSnapshot:
        return self._snapshot

    def prepare(self, provider_id: str) -> tuple[SpeechEvent, SpeechPerformanceDirective]:
        provider = str(provider_id).strip()
        if not provider:
            raise ValueError("Speech provider identifier must not be empty.")
        now = self._now()
        self._generation += 1
        self._last_gesture_at = now - self.minimum_gesture_gap_seconds
        self._has_rich_boundary = False
        self._snapshot = SpeechPerformanceSnapshot(
            generation=self._generation,
            provider_id=provider,
            phase=SpeechPerformancePhase.PREPARING,
            prepared_at=now,
            last_event_at=now,
            mouth_closed=True,
        )
        event = self._event(SpeechEventKind.PREPARE, now)
        return event, self._directive(
            body_energy=0.10,
            breath=0.22,
            emphasis=0.0,
            gesture_beat=False,
            allow_large_turn=True,
            hold_current_pose=False,
            reason="speech_preparing",
        )

    def first_audio(
        self,
        generation: int | None = None,
    ) -> tuple[SpeechEvent, SpeechPerformanceDirective] | None:
        if not self._accepts(generation):
            return None
        now = self._now()
        if self._snapshot.phase is SpeechPerformancePhase.SPEAKING:
            return None
        self._snapshot = replace(
            self._snapshot,
            phase=SpeechPerformancePhase.SPEAKING,
            audio_started_at=now,
            last_event_at=now,
            mouth_closed=False,
        )
        return self._event(SpeechEventKind.FIRST_AUDIO, now), self._directive(
            body_energy=0.24,
            breath=0.36,
            emphasis=0.1,
            gesture_beat=False,
            allow_large_turn=False,
            hold_current_pose=True,
            reason="first_audio",
        )

    def segment_boundary(
        self,
        segment_index: int | None = None,
        *,
        emphasis: float = 0.45,
        generation: int | None = None,
    ) -> tuple[SpeechEvent, SpeechPerformanceDirective] | None:
        if not self._accepts(generation):
            return None
        self._ensure_audio_started()
        now = self._now()
        next_index = (
            self._snapshot.segment_index + 1
            if segment_index is None
            else max(self._snapshot.segment_index + 1, int(segment_index))
        )
        self._has_rich_boundary = True
        gesture = self._consume_gesture_window(now, emphasis)
        self._snapshot = replace(
            self._snapshot,
            phase=SpeechPerformancePhase.SPEAKING,
            last_event_at=now,
            last_boundary_at=now,
            segment_index=next_index,
        )
        bounded = _unit(emphasis)
        event = self._event(
            SpeechEventKind.SEGMENT_BOUNDARY,
            now,
            segment_index=next_index,
        )
        return event, self._directive(
            body_energy=0.22 + bounded * 0.28,
            breath=0.34,
            emphasis=bounded,
            gesture_beat=gesture,
            allow_large_turn=False,
            hold_current_pose=not gesture,
            reason="authored_segment_boundary",
        )

    def viseme(
        self,
        level: float,
        viseme: str,
        *,
        generation: int | None = None,
    ) -> tuple[SpeechEvent, SpeechPerformanceDirective] | None:
        if not self._accepts(generation):
            return None
        self._ensure_audio_started()
        now = self._now()
        bounded = _unit(level)
        normalized_viseme = str(viseme or "CLOSED").upper()
        estimated_boundary = self._should_estimate_boundary(now, bounded)
        next_index = self._snapshot.segment_index + int(estimated_boundary)
        gesture = estimated_boundary and self._consume_gesture_window(now, bounded)
        self._snapshot = replace(
            self._snapshot,
            phase=SpeechPerformancePhase.SPEAKING,
            last_event_at=now,
            last_boundary_at=(
                now if estimated_boundary else self._snapshot.last_boundary_at
            ),
            segment_index=next_index,
            last_viseme=normalized_viseme,
            last_level=bounded,
            mouth_closed=normalized_viseme == "CLOSED" and bounded == 0.0,
        )
        event = self._event(
            SpeechEventKind.VISEME,
            now,
            level=bounded,
            viseme=normalized_viseme,
            segment_index=next_index,
            estimated=estimated_boundary,
        )
        return event, self._directive(
            body_energy=0.18 + bounded * 0.28,
            breath=0.28 + bounded * 0.16,
            emphasis=bounded,
            gesture_beat=gesture,
            allow_large_turn=False,
            hold_current_pose=not gesture,
            reason=("audio_estimated_boundary" if estimated_boundary else "viseme"),
        )

    def pause(
        self,
        *,
        generation: int | None = None,
    ) -> tuple[SpeechEvent, SpeechPerformanceDirective] | None:
        if not self._accepts(generation):
            return None
        now = self._now()
        self._snapshot = replace(
            self._snapshot,
            phase=SpeechPerformancePhase.PAUSING,
            last_event_at=now,
        )
        return self._event(SpeechEventKind.PAUSE, now), self._directive(
            body_energy=0.08,
            breath=0.18,
            emphasis=0.0,
            gesture_beat=False,
            allow_large_turn=False,
            hold_current_pose=True,
            reason="speech_pause",
        )

    def final_audio(
        self,
        *,
        generation: int | None = None,
    ) -> tuple[SpeechEvent, SpeechPerformanceDirective] | None:
        if not self._accepts(generation):
            return None
        if self._snapshot.phase in {
            SpeechPerformancePhase.SETTLING,
            SpeechPerformancePhase.IDLE,
            SpeechPerformancePhase.INTERRUPTED,
        }:
            return None
        now = self._now()
        self._snapshot = replace(
            self._snapshot,
            phase=SpeechPerformancePhase.SETTLING,
            last_event_at=now,
            last_level=0.0,
        )
        return self._event(SpeechEventKind.FINAL_AUDIO, now), self._directive(
            body_energy=0.06,
            breath=0.16,
            emphasis=0.0,
            gesture_beat=False,
            allow_large_turn=False,
            hold_current_pose=True,
            reason="final_audio_settle",
        )

    def mouth_closed(
        self,
        *,
        generation: int | None = None,
    ) -> tuple[SpeechEvent, SpeechPerformanceDirective] | None:
        if not self._accepts(generation):
            return None
        if (
            self._snapshot.phase is SpeechPerformancePhase.IDLE
            and self._snapshot.mouth_closed
        ):
            return None
        now = self._now()
        self._snapshot = replace(
            self._snapshot,
            phase=SpeechPerformancePhase.IDLE,
            last_event_at=now,
            last_viseme="CLOSED",
            last_level=0.0,
            mouth_closed=True,
        )
        return self._event(SpeechEventKind.MOUTH_CLOSED, now), self._directive(
            body_energy=0.0,
            breath=0.12,
            emphasis=0.0,
            gesture_beat=False,
            allow_large_turn=True,
            hold_current_pose=False,
            reason="mouth_closed_handoff",
        )

    def interrupt(
        self,
        *,
        failed: bool = False,
        generation: int | None = None,
    ) -> tuple[SpeechEvent, SpeechPerformanceDirective] | None:
        if not self._accepts(generation):
            return None
        if self._snapshot.phase in {
            SpeechPerformancePhase.IDLE,
            SpeechPerformancePhase.INTERRUPTED,
        }:
            return None
        now = self._now()
        kind = SpeechEventKind.FAILURE if failed else SpeechEventKind.INTERRUPT
        self._snapshot = replace(
            self._snapshot,
            phase=SpeechPerformancePhase.INTERRUPTED,
            last_event_at=now,
            last_level=0.0,
            interrupted=True,
        )
        return self._event(kind, now), self._directive(
            body_energy=0.0,
            breath=0.10,
            emphasis=0.0,
            gesture_beat=False,
            allow_large_turn=False,
            hold_current_pose=True,
            reason=("speech_failure" if failed else "speech_interrupted"),
        )

    def _ensure_audio_started(self) -> None:
        if self._snapshot.phase is SpeechPerformancePhase.PREPARING:
            now = self._now()
            self._snapshot = replace(
                self._snapshot,
                phase=SpeechPerformancePhase.SPEAKING,
                audio_started_at=now,
                last_event_at=now,
                mouth_closed=False,
            )

    def _should_estimate_boundary(self, now: float, level: float) -> bool:
        if self._has_rich_boundary or level < 0.32:
            return False
        reference = self._snapshot.last_boundary_at or self._snapshot.audio_started_at
        return reference > 0.0 and now - reference >= self.estimated_segment_seconds

    def _consume_gesture_window(self, now: float, emphasis: float) -> bool:
        if emphasis < 0.42 or now - self._last_gesture_at < self.minimum_gesture_gap_seconds:
            return False
        self._last_gesture_at = now
        return True

    def _accepts(self, generation: int | None) -> bool:
        if self._snapshot.phase is SpeechPerformancePhase.IDLE and self._generation == 0:
            return False
        return generation is None or int(generation) == self._generation

    def _event(
        self,
        kind: SpeechEventKind,
        timestamp: float,
        **changes: object,
    ) -> SpeechEvent:
        return SpeechEvent(
            self._generation,
            self._snapshot.provider_id,
            kind,
            timestamp,
            **changes,
        )

    def _directive(self, **values: object) -> SpeechPerformanceDirective:
        return SpeechPerformanceDirective(
            generation=self._generation,
            phase=self._snapshot.phase,
            **values,
        )

    def _now(self) -> float:
        return float(self._clock())


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
