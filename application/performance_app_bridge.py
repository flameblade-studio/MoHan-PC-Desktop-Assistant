from __future__ import annotations

lazy import random
lazy import time
lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from enum import StrEnum

lazy from application.behavior_director import BehaviorInput
lazy from application.body_pose_renderer import BodyPoseRenderer
lazy from application.performance_runtime import (
    AtomicPerformanceFrame,
    PerformanceContextEvent,
    PerformanceRuntime,
    RenderRequestFactory,
    RuntimeSpeechEvent,
)
lazy from application.speech_performance import (
    SpeechEvent,
    SpeechEventKind,
    SpeechPerformanceDirective,
)
lazy from domain.character_pose import PoseRegistry
lazy from domain.performance_preferences import PerformancePreferences


class BridgeDisposition(StrEnum):
    BYPASSED = "bypassed"
    STALE = "stale"
    DUPLICATE = "duplicate"
    THROTTLED = "throttled"
    FALLBACK = "fallback"
    EMITTED = "emitted"


@dataclass(frozen=True, slots=True)
class PerformanceBridgeInput:
    speech_event: SpeechEvent
    speech_directive: SpeechPerformanceDirective
    behavior_generation: int
    behavior: BehaviorInput
    preferences: PerformancePreferences
    available_corrections: frozenset[str]
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.behavior_generation < 0:
            raise ValueError("Behavior generation must not be negative.")


FrameCallback = Callable[[AtomicPerformanceFrame], None]


@dataclass(frozen=True, slots=True)
class PerformanceBridgeOptions:
    clock: Callable[[], float] | None = None
    rng: random.Random | None = None
    seed: int | None = None
    # Mouth cues are produced on the shared 50 Hz performance clock.  Keeping
    # the bridge at 20 Hz silently discarded most visemes before they reached
    # either layered renderer, making the new animation path look inert.
    minimum_render_interval_seconds: float = 0.02


class _ExistingSpeechPairTimeline:
    """Expose one already-normalized speech pair through the runtime protocol."""

    def __init__(self) -> None:
        self._pair: tuple[SpeechEvent, SpeechPerformanceDirective] | None = None

    def stage(
        self,
        event: SpeechEvent,
        directive: SpeechPerformanceDirective,
    ) -> None:
        self._pair = event, directive

    def prepare(self, _provider_id: str):
        return self._take(SpeechEventKind.PREPARE)

    def first_audio(self, _generation: int | None = None):
        return self._take(SpeechEventKind.FIRST_AUDIO)

    def segment_boundary(self, *_args: object, **_kwargs: object):
        return self._take(SpeechEventKind.SEGMENT_BOUNDARY)

    def viseme(self, *_args: object, **_kwargs: object):
        return self._take(SpeechEventKind.VISEME)

    def pause(self, **_kwargs: object):
        return self._take(SpeechEventKind.PAUSE)

    def final_audio(self, **_kwargs: object):
        return self._take(SpeechEventKind.FINAL_AUDIO)

    def mouth_closed(self, **_kwargs: object):
        return self._take(SpeechEventKind.MOUTH_CLOSED)

    def interrupt(self, *, failed: bool = False, **_kwargs: object):
        expected = SpeechEventKind.FAILURE if failed else SpeechEventKind.INTERRUPT
        return self._take(expected)

    def _take(
        self,
        expected: SpeechEventKind,
    ) -> tuple[SpeechEvent, SpeechPerformanceDirective] | None:
        pair = self._pair
        self._pair = None
        if pair is None or pair[0].kind is not expected:
            return None
        return pair


_RUNTIME_KIND = frozendict({
    SpeechEventKind.PREPARE: RuntimeSpeechEvent.PREPARE,
    SpeechEventKind.FIRST_AUDIO: RuntimeSpeechEvent.FIRST_AUDIO,
    SpeechEventKind.SEGMENT_BOUNDARY: RuntimeSpeechEvent.SEGMENT_BOUNDARY,
    SpeechEventKind.VISEME: RuntimeSpeechEvent.VISEME,
    SpeechEventKind.PAUSE: RuntimeSpeechEvent.PAUSE,
    SpeechEventKind.FINAL_AUDIO: RuntimeSpeechEvent.FINAL_AUDIO,
    SpeechEventKind.MOUTH_CLOSED: RuntimeSpeechEvent.MOUTH_CLOSED,
    SpeechEventKind.INTERRUPT: RuntimeSpeechEvent.INTERRUPT,
    SpeechEventKind.FAILURE: RuntimeSpeechEvent.FAILURE,
})
_UNTHROTTLED = frozenset({
    SpeechEventKind.PREPARE,
    SpeechEventKind.FIRST_AUDIO,
    SpeechEventKind.PAUSE,
    SpeechEventKind.FINAL_AUDIO,
    SpeechEventKind.MOUTH_CLOSED,
    SpeechEventKind.INTERRUPT,
    SpeechEventKind.FAILURE,
})


class PerformanceAppBridge:
    """Narrow fail-closed boundary between the app and atomic performance runtime."""

    def __init__(
        self,
        registry: PoseRegistry,
        renderer: BodyPoseRenderer,
        render_request: RenderRequestFactory,
        publish: FrameCallback,
        **legacy_options: object,
    ) -> None:
        options = PerformanceBridgeOptions(**legacy_options)
        minimum_render_interval_seconds = options.minimum_render_interval_seconds
        if minimum_render_interval_seconds < 0.0:
            raise ValueError("Render interval must not be negative.")
        self._clock = options.clock or time.monotonic
        self._publish = publish
        self._minimum_interval = float(minimum_render_interval_seconds)
        self._preferences = PerformancePreferences()
        self._timeline = _ExistingSpeechPairTimeline()
        self._runtime = PerformanceRuntime(
            registry,
            renderer,
            render_request,
            preferences=lambda: self._preferences,
            clock=self._clock,
            rng=options.rng,
            seed=options.seed,
            timeline=self._timeline,  # type: ignore[arg-type]
        )
        self._last_input_signature: tuple[object, ...] | None = None
        self._last_frame_signature: tuple[object, ...] | None = None
        self._last_render_at = float("-inf")
        self._speech_generation = -1
        self._behavior_generation = -1
        self._last_good: AtomicPerformanceFrame | None = None

    @property
    def last_known_good(self) -> AtomicPerformanceFrame | None:
        return self._last_good

    def dispatch(self, value: PerformanceBridgeInput) -> BridgeDisposition:
        rejected = self._rejected_input(value)
        if rejected is not None:
            return rejected
        signature = self._input_signature(value)
        if signature == self._last_input_signature:
            return BridgeDisposition.DUPLICATE
        now = float(self._clock())
        if (
            value.speech_event.kind not in _UNTHROTTLED
            and now - self._last_render_at < self._minimum_interval
        ):
            return BridgeDisposition.THROTTLED

        return self._emit(value, signature, now)

    def _emit(
        self,
        value: PerformanceBridgeInput,
        signature: tuple[object, ...],
        now: float,
    ) -> BridgeDisposition:
        event = value.speech_event
        previous = self._last_good
        try:
            self._preferences = value.preferences
            self._timeline.stage(event, value.speech_directive)
            candidate = self._runtime.process(
                self._runtime_event(value),
                available_corrections=value.available_corrections,
            )
        except (LookupError, RuntimeError, TypeError, ValueError):
            return BridgeDisposition.FALLBACK
        if candidate is None or candidate is previous:
            return BridgeDisposition.FALLBACK

        frame_signature = self._frame_signature(candidate)
        if frame_signature == self._last_frame_signature:
            self._last_input_signature = signature
            return BridgeDisposition.DUPLICATE
        try:
            self._publish(candidate)
        except (OSError, RuntimeError, TypeError, ValueError):
            return BridgeDisposition.FALLBACK

        self._speech_generation = event.generation
        self._behavior_generation = value.behavior_generation
        self._last_input_signature = signature
        self._last_frame_signature = frame_signature
        self._last_render_at = now
        self._last_good = candidate
        return BridgeDisposition.EMITTED

    def _rejected_input(
        self,
        value: PerformanceBridgeInput,
    ) -> BridgeDisposition | None:
        if not value.enabled:
            return BridgeDisposition.BYPASSED
        event = value.speech_event
        if event.generation != value.speech_directive.generation:
            return BridgeDisposition.STALE
        if (
            event.generation < self._speech_generation
            or value.behavior_generation < self._behavior_generation
        ):
            return BridgeDisposition.STALE
        return None

    @staticmethod
    def _runtime_event(value: PerformanceBridgeInput) -> PerformanceContextEvent:
        event = value.speech_event
        behavior = value.behavior
        return PerformanceContextEvent(
            _RUNTIME_KIND[event.kind],
            event.provider_id,
            event.generation,
            value.behavior_generation,
            behavior.emotion,
            behavior.emotion_intensity,
            behavior.conversation_turn,
            behavior.user_in_gaze,
            behavior.user_present,
            behavior.away_seconds,
            behavior.current_pose,
            behavior.previous_action,
            behavior.proactive_performance_disabled,
            event.level,
            event.viseme,
            event.segment_index,
            value.speech_directive.emphasis,
        )

    @staticmethod
    def _input_signature(value: PerformanceBridgeInput) -> tuple[object, ...]:
        event = value.speech_event
        return (
            event.generation,
            event.kind,
            event.level,
            event.viseme,
            event.segment_index,
            event.estimated,
            value.speech_directive,
            value.behavior_generation,
            value.behavior,
            value.preferences,
            value.available_corrections,
        )

    @staticmethod
    def _frame_signature(frame: AtomicPerformanceFrame) -> tuple[object, ...]:
        performance = frame.performance
        body = frame.body
        return (
            performance.pose,
            performance.view,
            performance.face,
            performance.left_hand,
            performance.right_hand,
            performance.gaze,
            performance.breath,
            performance.transition,
            performance.viseme,
            performance.mouth_closed,
            performance.gesture_beat,
            body.width,
            body.height,
            body.rgba,
            body.view_ids,
            body.layer_order,
            body.articulation_active,
        )
