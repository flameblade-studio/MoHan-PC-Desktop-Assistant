from __future__ import annotations

lazy import random
lazy import time
lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from enum import StrEnum
lazy from typing import Protocol, cast

lazy from application.behavior_director import (
    BehaviorDirector,
    BehaviorInput,
    SemanticEmotion,
    SpeechLifecycle,
)
lazy from application.body_pose_renderer import BodyPoseFrame, BodyPoseRenderer
lazy from application.performance_coordinator import (
    PerformanceCoordinator,
    PerformanceFrame,
)
lazy from application.speech_performance import (
    SpeechEvent,
    SpeechPerformanceDirective,
    SpeechPerformanceTimeline,
)
lazy from domain.character_pose import (
    CharacterPose,
    PoseRegistry,
    ViewBlend,
)
lazy from domain.performance_preferences import PerformancePreferences


class RuntimeSpeechEvent(StrEnum):
    PREPARE = "prepare"
    FIRST_AUDIO = "first_audio"
    SEGMENT_BOUNDARY = "segment_boundary"
    VISEME = "viseme"
    PAUSE = "pause"
    FINAL_AUDIO = "final_audio"
    MOUTH_CLOSED = "mouth_closed"
    INTERRUPT = "interrupt"
    FAILURE = "failure"


@dataclass(frozen=True, slots=True)
class PerformanceContextEvent:
    kind: RuntimeSpeechEvent
    provider_id: str
    speech_generation: int | None
    behavior_generation: int
    emotion: SemanticEmotion
    emotion_intensity: float
    conversation_turn: int
    user_in_gaze: bool
    user_present: bool
    away_seconds: float
    current_pose: str
    previous_action: str
    proactive_performance_disabled: bool = False
    level: float = 0.0
    viseme: str = "CLOSED"
    segment_index: int = 0
    emphasis: float = 0.45

    def __post_init__(self) -> None:
        if self.behavior_generation < 0:
            raise ValueError("Behavior generation must not be negative.")
        if not self.provider_id.strip():
            raise ValueError("Provider identifier must not be empty.")
        if not 0.0 <= self.level <= 1.0:
            raise ValueError("Speech level must be within 0..1.")


@dataclass(frozen=True, slots=True)
class AtomicPerformanceFrame:
    performance: PerformanceFrame
    body: BodyPoseFrame


@dataclass(frozen=True, slots=True)
class BodyRenderRequest:
    blend: ViewBlend
    first_pose: CharacterPose | None
    second_pose: CharacterPose | None


class RenderRequestFactory(Protocol):
    def __call__(
        self,
        frame: PerformanceFrame,
        registry: PoseRegistry,
    ) -> BodyRenderRequest | None: ...


PreferencesSource = Callable[[], PerformancePreferences]


@dataclass(frozen=True, slots=True)
class PerformanceRuntimeOptions:
    preferences: PreferencesSource | PerformancePreferences | None = None
    clock: Callable[[], float] | None = None
    rng: random.Random | None = None
    seed: int | None = None
    timeline: SpeechPerformanceTimeline | None = None
    director: BehaviorDirector | None = None
    coordinator: PerformanceCoordinator | None = None


class PerformanceRuntime:
    """Provider-neutral facade for one atomic, fail-closed performance frame."""

    def __init__(
        self,
        registry: PoseRegistry,
        renderer: BodyPoseRenderer,
        render_request: RenderRequestFactory,
        **legacy_options: object,
    ) -> None:
        options = self._runtime_options(legacy_options)
        rng = options.rng
        seed = options.seed
        if rng is not None and seed is not None:
            raise ValueError("Inject either rng or seed, not both.")
        self.registry = registry
        self.renderer = renderer
        self.render_request = render_request
        selected_preferences = options.preferences or PerformancePreferences()
        self._preferences = (
            selected_preferences
            if callable(selected_preferences)
            else lambda: selected_preferences
        )
        shared_clock = options.clock or time.monotonic
        shared_rng = rng or random.Random(seed)
        self.timeline = options.timeline or SpeechPerformanceTimeline(clock=shared_clock)
        self.director = options.director or BehaviorDirector(
            clock=shared_clock,
            rng=shared_rng,
        )
        self.coordinator = options.coordinator or PerformanceCoordinator(registry)
        self._last_good: AtomicPerformanceFrame | None = None

    @staticmethod
    def _runtime_options(values: dict[str, object]) -> PerformanceRuntimeOptions:
        allowed = set(PerformanceRuntimeOptions.__dataclass_fields__)
        unexpected = sorted(set(values) - allowed)
        if unexpected:
            raise TypeError(f"Unexpected runtime options: {unexpected}.")
        return PerformanceRuntimeOptions(
            preferences=cast(
                "PreferencesSource | PerformancePreferences | None",
                values.get("preferences"),
            ),
            clock=cast("Callable[[], float] | None", values.get("clock")),
            rng=cast("random.Random | None", values.get("rng")),
            seed=cast("int | None", values.get("seed")),
            timeline=cast(
                "SpeechPerformanceTimeline | None",
                values.get("timeline"),
            ),
            director=cast("BehaviorDirector | None", values.get("director")),
            coordinator=cast(
                "PerformanceCoordinator | None",
                values.get("coordinator"),
            ),
        )

    @property
    def last_known_good(self) -> AtomicPerformanceFrame | None:
        return self._last_good

    def process(
        self,
        event: PerformanceContextEvent,
        *,
        available_corrections: frozenset[str],
    ) -> AtomicPerformanceFrame | None:
        """Process one typed event; every failure preserves the last full frame."""

        try:
            candidate = self._candidate(event, available_corrections)
        except (LookupError, RuntimeError, TypeError, ValueError):
            candidate = None
        if candidate is not None:
            self._last_good = candidate
        return self._last_good

    def _candidate(
        self,
        event: PerformanceContextEvent,
        available_corrections: frozenset[str],
    ) -> AtomicPerformanceFrame | None:
        speech = self._speech(event)
        if speech is None:
            return None
        speech_event, directive = speech
        behavior_context = self._behavior_context(event, directive)
        plan = self.coordinator.apply_preferences(
            self.director.direct(behavior_context),
            self._preferences(),
        )
        performance = self.coordinator.coordinate(
            event=speech_event,
            directive=directive,
            behavior_generation=event.behavior_generation,
            context=behavior_context,
            plan=plan,
            available_corrections=available_corrections,
        )
        if performance is None or (performance.fallback and self._last_good is not None):
            return None
        request = self.render_request(performance, self.registry)
        if request is None:
            return None
        previous_body = self.renderer.current_frame
        body = self.renderer.render(
            self.renderer.begin_transition(),
            request.blend,
            request.first_pose,
            request.second_pose,
        )
        if body == previous_body and previous_body.generation != 0:
            # Speech articulation is a performance-only update: the authored
            # body photograph commonly remains byte-identical while viseme,
            # mouth-closed state and continuous face controls change.  Dropping
            # the atomic frame here disconnects audio cues from the layered
            # full-body renderer and leaves the mouth frozen.  Deduplicate only
            # when both halves of the atomic frame are unchanged.
            if (
                self._last_good is not None
                and performance == self._last_good.performance
            ):
                return None
            body = previous_body
        return AtomicPerformanceFrame(performance, body)

    def _speech(
        self,
        event: PerformanceContextEvent,
    ) -> tuple[SpeechEvent, SpeechPerformanceDirective] | None:
        generation = event.speech_generation
        if event.kind is RuntimeSpeechEvent.PREPARE:
            return self.timeline.prepare(event.provider_id)
        if event.kind is RuntimeSpeechEvent.SEGMENT_BOUNDARY:
            return self.timeline.segment_boundary(
                event.segment_index,
                emphasis=event.emphasis,
                generation=generation,
            )
        if event.kind is RuntimeSpeechEvent.VISEME:
            return self.timeline.viseme(
                event.level,
                event.viseme,
                generation=generation,
            )
        simple_events = {
            RuntimeSpeechEvent.FIRST_AUDIO: lambda: self.timeline.first_audio(
                generation
            ),
            RuntimeSpeechEvent.PAUSE: lambda: self.timeline.pause(
                generation=generation
            ),
            RuntimeSpeechEvent.FINAL_AUDIO: lambda: self.timeline.final_audio(
                generation=generation
            ),
            RuntimeSpeechEvent.MOUTH_CLOSED: lambda: self.timeline.mouth_closed(
                generation=generation
            ),
            RuntimeSpeechEvent.INTERRUPT: lambda: self.timeline.interrupt(
                generation=generation
            ),
        }
        if event.kind is RuntimeSpeechEvent.FAILURE:
            return self.timeline.interrupt(failed=True, generation=generation)
        handler = simple_events.get(event.kind)
        if handler is None:
            raise AssertionError("Unhandled runtime speech event.")
        return handler()

    @staticmethod
    def _behavior_context(
        event: PerformanceContextEvent,
        directive: SpeechPerformanceDirective,
    ) -> BehaviorInput:
        lifecycle = {
            "preparing": SpeechLifecycle.STARTING,
            "speaking": SpeechLifecycle.SPEAKING,
            "pausing": SpeechLifecycle.SPEAKING,
            "settling": SpeechLifecycle.ENDING,
            "interrupted": SpeechLifecycle.ENDING,
            "idle": SpeechLifecycle.IDLE,
        }[directive.phase.value]
        return BehaviorInput(
            lifecycle,
            event.emotion,
            event.emotion_intensity,
            event.conversation_turn,
            event.user_in_gaze,
            event.user_present,
            event.away_seconds,
            event.current_pose,
            event.previous_action,
            event.proactive_performance_disabled,
        )
