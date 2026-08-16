from __future__ import annotations

lazy from collections.abc import Iterable
lazy from dataclasses import dataclass, replace
lazy from typing import Protocol, cast

lazy from application.behavior_director import (
    BehaviorInput,
    BodyPerformancePlan,
    BreathStyle,
    GazeTarget,
    TransitionStyle,
)
lazy from application.speech_performance import (
    SpeechEvent,
    SpeechEventKind,
    SpeechPerformanceDirective,
    SpeechPerformancePhase,
)
lazy from domain.character_pose import (
    CharacterPose,
    canonical_view_id,
    normalize_view_id,
)
lazy from domain.performance_preferences import PerformancePreferences


class PoseRegistryPort(Protocol):
    def get(self, pose_id: str) -> CharacterPose | None: ...

    def available(
        self,
        pose_id: str,
        available_corrections: Iterable[str],
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class PerformanceFrame:
    """One generation-checked atomic frame for every visual performance layer."""

    speech_generation: int
    behavior_generation: int
    event: SpeechEventKind
    phase: SpeechPerformancePhase
    pose: str
    view: str
    face: str | None
    left_hand: str
    right_hand: str
    gaze: GazeTarget
    breath: BreathStyle
    transition: TransitionStyle
    hold_ms: int
    viseme: str
    mouth_closed: bool
    body_energy: float
    gesture_beat: bool
    fallback: bool

    def __post_init__(self) -> None:
        if self.speech_generation < 0 or self.behavior_generation < 0:
            raise ValueError("Performance generations must not be negative.")
        if not 0.0 <= self.body_energy <= 1.0:
            raise ValueError("Body energy must be within 0..1.")
        if self.hold_ms < 0:
            raise ValueError("Frame hold must not be negative.")
        if self.mouth_closed and self.viseme != "CLOSED":
            raise ValueError("A closed mouth requires the CLOSED viseme.")
        if self.pose.startswith("back-") and (
            self.face is not None or self.gaze is not GazeTarget.AWAY
        ):
            raise ValueError("Back-facing frames cannot render face or user gaze.")


@dataclass(frozen=True, slots=True)
class CoordinationInput:
    event: SpeechEvent
    directive: SpeechPerformanceDirective
    behavior_generation: int
    context: BehaviorInput
    plan: BodyPerformancePlan
    available_corrections: Iterable[str]


_AUDIO_EVENTS = frozenset({
    SpeechEventKind.FIRST_AUDIO,
    SpeechEventKind.SEGMENT_BOUNDARY,
    SpeechEventKind.VISEME,
    SpeechEventKind.PAUSE,
    SpeechEventKind.FINAL_AUDIO,
})
_BACK_DEPTH = frozendict({
    "front-crossed": 0,
    "left-neutral": 1,
    "right-neutral": 1,
    "back-two-thirds-left": 2,
    "back-two-thirds-right": 2,
    "back-full": 3,
})


class PerformanceCoordinator:
    """Join speech, behaviour and authored pose availability without providers."""

    def __init__(self, registry: PoseRegistryPort) -> None:
        self._registry = registry
        self._speech_generation = -1
        self._behavior_generation = -1
        self._audio_active = False
        self._awaiting_closed_settle = False
        self._last_good: PerformanceFrame | None = None

    @property
    def last_known_good(self) -> PerformanceFrame | None:
        return self._last_good

    @staticmethod
    def apply_preferences(
        plan: BodyPerformancePlan,
        preferences: PerformancePreferences,
    ) -> BodyPerformancePlan:
        """Apply the one persisted preference model at the planning boundary."""

        if not isinstance(preferences, PerformancePreferences):
            raise TypeError("Performance preferences must use the canonical model.")
        candidate = plan
        if candidate.pose.startswith("back-") and (
            not preferences.view_360_enabled
            or not preferences.full_back_view_enabled
        ):
            candidate = replace(
                candidate,
                pose="front-crossed",
                view=canonical_view_id(0),
                face="neutral",
            )
        elif candidate.pose == "right-neutral" and not preferences.view_360_enabled:
            candidate = replace(
                candidate,
                pose="front-crossed",
                view=canonical_view_id(0),
            )
        return replace(
            candidate,
            left_hand=(
                candidate.left_hand
                if preferences.left_gestures_enabled
                else "relaxed"
            ),
            right_hand=(
                candidate.right_hand
                if preferences.right_gestures_enabled
                else "relaxed"
            ),
        )

    def coordinate(
        self,
        request: CoordinationInput | None = None,
        **legacy: object,
    ) -> PerformanceFrame | None:
        """Return None for stale input; otherwise return one complete safe frame."""

        value = self._coordination_input(request, legacy)
        event = value.event
        directive = value.directive
        behavior_generation = value.behavior_generation
        candidate = value.plan
        if not self._accept_generations(event, directive, behavior_generation):
            return None
        self._speech_generation = event.generation
        self._behavior_generation = behavior_generation
        self._update_audio_state(event.kind)
        existing_back = bool(
            self._last_good and self._last_good.pose.startswith("back-")
        )
        if self._audio_active or event.kind in _AUDIO_EVENTS:
            candidate = self._during_audio_plan(
                candidate,
                directive,
                existing_back=existing_back,
            )
        if event.kind is SpeechEventKind.MOUTH_CLOSED and self._awaiting_closed_settle:
            candidate = self._closed_settling_plan(candidate)
            self._awaiting_closed_settle = False

        try:
            candidate = replace(
                candidate,
                view=normalize_view_id(candidate.view),
            )
        except (TypeError, ValueError):
            return self._fallback_frame(event, directive, behavior_generation)

        pose = self._registry.get(candidate.pose)
        unavailable = (
            pose is None
            or not self._registry.available(
                candidate.pose,
                value.available_corrections,
            )
            or (
                (self._audio_active or event.kind in _AUDIO_EVENTS)
                and pose is not None
                and not pose.speech_safe
                and not (existing_back and candidate.pose.startswith("back-"))
            )
        )
        unsafe_transition = (
            self._last_good is not None
            and not self._safe_depth_transition(
                self._last_good.pose,
                candidate.pose,
            )
        )
        if unavailable or unsafe_transition:
            return self._fallback_frame(event, directive, behavior_generation)

        frame = self._performance_frame(value, candidate)
        self._last_good = frame
        return frame

    @staticmethod
    def _coordination_input(
        request: CoordinationInput | None,
        legacy: dict[str, object],
    ) -> CoordinationInput:
        if request is not None:
            if legacy:
                raise TypeError("Do not combine request and legacy arguments.")
            return request
        required = {
            "event",
            "directive",
            "behavior_generation",
            "context",
            "plan",
            "available_corrections",
        }
        if set(legacy) != required:
            missing = sorted(required - set(legacy))
            unexpected = sorted(set(legacy) - required)
            raise TypeError(
                f"Invalid coordination arguments; missing={missing}, "
                f"unexpected={unexpected}."
            )
        return CoordinationInput(
            cast("SpeechEvent", legacy["event"]),
            cast("SpeechPerformanceDirective", legacy["directive"]),
            int(cast("int", legacy["behavior_generation"])),
            cast("BehaviorInput", legacy["context"]),
            cast("BodyPerformancePlan", legacy["plan"]),
            cast("Iterable[str]", legacy["available_corrections"]),
        )

    def _accept_generations(
        self,
        event: SpeechEvent,
        directive: SpeechPerformanceDirective,
        behavior_generation: int,
    ) -> bool:
        return (
            event.generation == directive.generation
            and event.generation >= self._speech_generation
            and behavior_generation >= self._behavior_generation
        )

    def _update_audio_state(self, event: SpeechEventKind) -> None:
        if event is SpeechEventKind.FIRST_AUDIO:
            self._audio_active = True
        elif event in {SpeechEventKind.INTERRUPT, SpeechEventKind.FAILURE}:
            self._awaiting_closed_settle = self._audio_active
            self._audio_active = False
        elif event is SpeechEventKind.MOUTH_CLOSED:
            self._awaiting_closed_settle = (
                self._audio_active or self._awaiting_closed_settle
            )
            self._audio_active = False

    def _performance_frame(
        self,
        value: CoordinationInput,
        candidate: BodyPerformancePlan,
    ) -> PerformanceFrame:
        event = value.event
        directive = value.directive
        mouth_closed = self._mouth_closed(event)
        viseme = "CLOSED" if mouth_closed else str(event.viseme or "CLOSED").upper()
        face = None if candidate.pose.startswith("back-") else candidate.face
        gaze = GazeTarget.AWAY if candidate.pose.startswith("back-") else candidate.gaze
        gesture_beat = bool(
            directive.gesture_beat
            and event.kind in {SpeechEventKind.SEGMENT_BOUNDARY, SpeechEventKind.VISEME}
            and not candidate.pose.startswith("back-")
        )
        left_hand, right_hand = self._hands(candidate, gesture_beat)
        transition = candidate.transition
        if self._audio_active and self._is_large_turn(self._last_good, candidate):
            transition = TransitionStyle.HOLD
        return PerformanceFrame(
            event.generation,
            value.behavior_generation,
            event.kind,
            directive.phase,
            candidate.pose,
            candidate.view,
            face,
            left_hand,
            right_hand,
            gaze,
            candidate.breath,
            transition,
            candidate.hold_ms,
            viseme,
            mouth_closed,
            min(1.0, max(0.0, directive.body_energy)),
            gesture_beat,
            False,
        )

    def _during_audio_plan(
        self,
        candidate: BodyPerformancePlan,
        directive: SpeechPerformanceDirective,
        *,
        existing_back: bool,
    ) -> BodyPerformancePlan:
        if existing_back and self._last_good is not None:
            return BodyPerformancePlan(
                self._last_good.pose,
                self._last_good.view,
                "hidden",
                "relaxed",
                "relaxed",
                GazeTarget.AWAY,
                BreathStyle.SPEAKING,
                TransitionStyle.HOLD,
                max(1_200, candidate.hold_ms),
            )
        if (
            self._last_good is not None
            and self._is_large_turn(self._last_good, candidate)
        ):
            return BodyPerformancePlan(
                self._last_good.pose,
                self._last_good.view,
                candidate.face,
                self._last_good.left_hand,
                self._last_good.right_hand,
                self._last_good.gaze,
                BreathStyle.SPEAKING,
                TransitionStyle.HOLD,
                max(1_200, candidate.hold_ms),
            )
        if directive.hold_current_pose and self._last_good is not None:
            return BodyPerformancePlan(
                self._last_good.pose,
                self._last_good.view,
                candidate.face,
                candidate.left_hand,
                candidate.right_hand,
                self._last_good.gaze,
                BreathStyle.SPEAKING,
                TransitionStyle.HOLD,
                max(1_200, candidate.hold_ms),
            )
        return replace(candidate, breath=BreathStyle.SPEAKING)

    def _closed_settling_plan(
        self,
        candidate: BodyPerformancePlan,
    ) -> BodyPerformancePlan:
        if self._last_good is None:
            return replace(
                candidate,
                breath=BreathStyle.SETTLING,
                transition=TransitionStyle.HOLD,
                hold_ms=max(800, candidate.hold_ms),
            )
        return BodyPerformancePlan(
            self._last_good.pose,
            self._last_good.view,
            "hidden" if self._last_good.pose.startswith("back-") else "neutral",
            self._last_good.left_hand,
            self._last_good.right_hand,
            self._last_good.gaze,
            BreathStyle.SETTLING,
            TransitionStyle.HOLD,
            max(800, candidate.hold_ms),
        )

    def _fallback_frame(
        self,
        event: SpeechEvent,
        directive: SpeechPerformanceDirective,
        behavior_generation: int,
    ) -> PerformanceFrame | None:
        if self._last_good is None:
            return None
        mouth_closed = self._mouth_closed(event)
        frame = replace(
            self._last_good,
            speech_generation=event.generation,
            behavior_generation=behavior_generation,
            event=event.kind,
            phase=directive.phase,
            viseme=("CLOSED" if mouth_closed else str(event.viseme or "CLOSED").upper()),
            mouth_closed=mouth_closed,
            body_energy=min(1.0, max(0.0, directive.body_energy)),
            gesture_beat=False,
            transition=TransitionStyle.HOLD,
            fallback=True,
        )
        self._last_good = frame
        return frame

    def _hands(
        self,
        candidate: BodyPerformancePlan,
        gesture_beat: bool,
    ) -> tuple[str, str]:
        if gesture_beat or self._last_good is None:
            return candidate.left_hand, candidate.right_hand
        return self._last_good.left_hand, self._last_good.right_hand

    @staticmethod
    def _mouth_closed(event: SpeechEvent) -> bool:
        return event.kind in {
            SpeechEventKind.PREPARE,
            SpeechEventKind.MOUTH_CLOSED,
            SpeechEventKind.INTERRUPT,
            SpeechEventKind.FAILURE,
        } or (
            event.kind is SpeechEventKind.VISEME
            and event.viseme.upper() == "CLOSED"
            and event.level == 0.0
        )

    @staticmethod
    def _is_large_turn(
        previous: PerformanceFrame | None,
        candidate: BodyPerformancePlan,
    ) -> bool:
        if previous is None:
            return False
        previous_depth = _BACK_DEPTH.get(previous.pose, 0)
        candidate_depth = _BACK_DEPTH.get(candidate.pose, 0)
        return (
            previous_depth != candidate_depth
            and max(previous_depth, candidate_depth) >= 2
        )

    @staticmethod
    def _safe_depth_transition(previous_pose: str, next_pose: str) -> bool:
        return abs(
            _BACK_DEPTH.get(previous_pose, 0)
            - _BACK_DEPTH.get(next_pose, 0)
        ) <= 1
