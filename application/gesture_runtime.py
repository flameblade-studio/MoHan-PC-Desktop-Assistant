from __future__ import annotations

lazy import math
lazy from dataclasses import dataclass

lazy from application.gesture_action_router import (
    GestureActionDecision,
    GestureActionRouter,
    GestureTrigger,
)
lazy from application.gesture_recognizer import (
    GestureRecognition,
    GestureRecognizer,
    HandSkeleton,
)
lazy from domain.air_interaction import (
    AirHandPoint,
    AirHandSample,
    AirInteractionConfig,
    AirInteractionDetector,
    AirInteractionEvent,
)
lazy from domain.gesture_configuration import (
    GestureConfiguration,
    GestureLandmark,
    GestureSource,
)
lazy from domain.gesture_intent import (
    GestureFrame,
    GestureIntent,
    GestureState,
    HandLandmarks,
    HandSide,
    LipRegion,
    NormalizedPoint,
    SilenceGestureDetector,
)
lazy from infrastructure.hand_landmark_provider import Handedness, HandObservation


@dataclass(frozen=True, slots=True)
class GestureRuntimeResult:
    observed_at: float
    recognitions: tuple[GestureRecognition, ...]
    decision: GestureActionDecision | None = None
    air_interaction: AirInteractionEvent | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.observed_at):
            raise ValueError("Gesture runtime time must be finite.")
        if self.decision is not None and not self.decision.executable:
            raise ValueError("Gesture runtime may expose only executable decisions.")


class GestureRuntime:
    """Coordinate local hand recognition and intent routing without execution."""

    def __init__(self, *, air_interactions_enabled: bool = True) -> None:
        if type(air_interactions_enabled) is not bool:
            raise TypeError("air interaction enablement must be boolean.")
        self._fingerprint: tuple[object, ...] | None = None
        self._recognizer: GestureRecognizer | None = None
        self._router: GestureActionRouter | None = None
        self._silence = SilenceGestureDetector()
        self._air_interactions = AirInteractionDetector(
            config=AirInteractionConfig(
                enabled=air_interactions_enabled,
            )
        )
        self._configuration = GestureConfiguration()

    def update(
        self,
        observed_at: float,
        hands: tuple[HandObservation, ...],
        configuration: GestureConfiguration,
        *,
        lips: LipRegion | None = None,
    ) -> GestureRuntimeResult:
        if not math.isfinite(observed_at):
            raise ValueError("Gesture runtime time must be finite.")
        if not isinstance(configuration, GestureConfiguration):
            raise TypeError("Gesture runtime configuration must be canonical.")
        if any(not isinstance(hand, HandObservation) for hand in hands):
            raise TypeError("Gesture runtime hands must be typed observations.")
        self._configure(configuration)
        air_interaction = self._air_interaction(observed_at, hands, configuration)
        if not configuration.enabled or not hands:
            self.cancel()
            return GestureRuntimeResult(observed_at, ())

        silence, silence_active = self._silence_decision(observed_at, hands, lips)
        if silence_active:
            return GestureRuntimeResult(observed_at, (), silence, air_interaction)

        recognitions = tuple(
            recognition
            for hand in _stable_hands(hands)
            if (recognition := self._recognize(observed_at, hand)) is not None
        )
        triggered = tuple(result for result in recognitions if result.triggered)
        if not triggered:
            return GestureRuntimeResult(observed_at, recognitions, air_interaction=air_interaction)
        winner = min(
            triggered,
            key=lambda item: (
                -item.confidence,
                str(item.gesture_id),
                item.side.value,
            ),
        )
        router = self._router
        if router is None:
            return GestureRuntimeResult(observed_at, recognitions, air_interaction=air_interaction)
        routed = router.route(
            GestureTrigger(str(winner.gesture_id), winner.confidence, observed_at),
            configuration,
        )
        return GestureRuntimeResult(
            observed_at,
            recognitions,
            routed if routed.executable else None,
            air_interaction,
        )

    def cancel(self, side: HandSide | None = None) -> None:
        if self._recognizer is not None:
            self._recognizer.cancel(side)
        self._silence.cancel()
        self._air_interactions.cancel()

    def reset(self) -> None:
        if self._recognizer is not None:
            self._recognizer.reset()
        if self._router is not None:
            self._router.reset()
        self._silence = SilenceGestureDetector()
        self._air_interactions.reset()

    def _silence_decision(
        self,
        observed_at: float,
        hands: tuple[HandObservation, ...],
        lips: LipRegion | None,
    ) -> tuple[GestureActionDecision | None, bool]:
        router = self._router
        if router is None or lips is None:
            self._silence.cancel()
            return None, False
        if not self._configuration.definition("silence").enabled:
            self._silence.cancel()
            return None, False
        canonical_hands = tuple(
            HandLandmarks(
                side,
                tuple(NormalizedPoint(point.x, point.y) for point in hand.landmarks),
            )
            for hand in _stable_hands(hands)
            if (side := _hand_side(hand.handedness)) is not None
        )
        if not canonical_hands:
            self._silence.cancel()
            return None, False
        intent = self._silence.update(
            GestureFrame(observed_at, lips, canonical_hands, tracking_valid=True)
        )
        active = intent.state in {
            GestureState.CANDIDATE,
            GestureState.COOLDOWN,
            GestureState.TRIGGERED,
        }
        if intent.intent is not GestureIntent.SILENCE_REQUEST:
            return None, active
        routed = router.route(
            GestureTrigger("silence", intent.confidence, observed_at),
            self._configuration,
        )
        return (routed if routed.executable else None), True

    def _configure(self, configuration: GestureConfiguration) -> None:
        fingerprint = _configuration_fingerprint(configuration)
        if fingerprint == self._fingerprint:
            return
        templates = {
            definition.gesture_id: definition.samples
            for definition in configuration.definitions
            if definition.source is GestureSource.CUSTOM
            and definition.enabled
            and definition.samples
        }
        self._recognizer = GestureRecognizer(templates)
        self._router = GestureActionRouter()
        self._silence = SilenceGestureDetector()
        self._configuration = configuration
        self._fingerprint = fingerprint

    def _air_interaction(
        self,
        observed_at: float,
        hands: tuple[HandObservation, ...],
        configuration: GestureConfiguration,
    ) -> AirInteractionEvent | None:
        if not configuration.enabled:
            self._air_interactions.cancel()
            return None
        samples = tuple(
            AirHandSample(
                side,
                hand.confidence,
                tuple(
                    AirHandPoint(point.x, point.y, point.z)
                    for point in hand.landmarks
                ),
            )
            for hand in _stable_hands(hands)
            if (side := _hand_side(hand.handedness)) is not None
        )
        try:
            return self._air_interactions.update(observed_at, samples)
        except (TypeError, ValueError):
            self._air_interactions.cancel()
            return None

    def _recognize(
        self,
        observed_at: float,
        hand: HandObservation,
    ) -> GestureRecognition | None:
        side = _hand_side(hand.handedness)
        if side is None or self._recognizer is None:
            return None
        try:
            skeleton = HandSkeleton(
                observed_at,
                side,
                tuple(
                    GestureLandmark(point.x, point.y, point.z)
                    for point in hand.landmarks
                ),
            )
        except (TypeError, ValueError):
            self._recognizer.cancel(side)
            return None
        return self._recognizer.update(skeleton)


def _hand_side(handedness: Handedness) -> HandSide | None:
    if handedness is Handedness.LEFT:
        return HandSide.LEFT
    if handedness is Handedness.RIGHT:
        return HandSide.RIGHT
    return None


def _stable_hands(hands: tuple[HandObservation, ...]) -> tuple[HandObservation, ...]:
    by_side: dict[Handedness, HandObservation] = {}
    for hand in hands:
        current = by_side.get(hand.handedness)
        if current is None or hand.confidence > current.confidence:
            by_side[hand.handedness] = hand
    return tuple(
        sorted(
            by_side.values(),
            key=lambda hand: hand.handedness.value,
        )
    )


def _configuration_fingerprint(
    configuration: GestureConfiguration,
) -> tuple[object, ...]:
    definitions = tuple(
        (
            definition.gesture_id,
            definition.source.value,
            definition.enabled,
            definition.binding.action.value,
            definition.binding.custom_command,
            tuple(
                tuple((point.x, point.y, point.z) for point in sample.landmarks)
                for sample in definition.samples
            ),
        )
        for definition in configuration.definitions
    )
    return (configuration.enabled, definitions)
