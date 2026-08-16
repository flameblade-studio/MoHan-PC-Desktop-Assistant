from __future__ import annotations

lazy import math
lazy from dataclasses import dataclass
lazy from enum import StrEnum

lazy from domain.gesture_intent import HandSide

LANDMARKS_PER_HAND = 21


class AirInteractionKind(StrEnum):
    PINCH = "pinch"
    SWIPE_LEFT = "swipe-left"
    SWIPE_RIGHT = "swipe-right"
    HIGH_FIVE = "high-five"


@dataclass(frozen=True, slots=True)
class AirInteractionConfig:
    """Conservative thresholds for camera gestures.

    The detector emits intent only. Application actions remain behind the
    existing gesture action router and its user-configured bindings.
    """

    enabled: bool = True
    minimum_confidence: float = 0.72
    minimum_stable_frames: int = 2
    pinch_start_ratio: float = 0.46
    pinch_release_ratio: float = 0.70
    minimum_palm_span: float = 0.025
    swipe_distance: float = 0.18
    swipe_vertical_tolerance: float = 0.18
    swipe_window_seconds: float = 0.75
    high_five_palm_span: float = 0.17
    cooldown_seconds: float = 0.85

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise TypeError("air interaction enabled state must be boolean")
        if self.minimum_stable_frames < 1:
            raise ValueError("air interaction stable frames must be positive")
        if not 0.0 < self.minimum_confidence <= 1.0:
            raise ValueError("air interaction confidence is invalid")
        if not 0.0 < self.pinch_start_ratio < self.pinch_release_ratio:
            raise ValueError("pinch hysteresis thresholds are invalid")
        if not self.minimum_palm_span > 0.0:
            raise ValueError("minimum palm span must be positive")
        if not self.swipe_distance > 0.0:
            raise ValueError("swipe distance must be positive")
        if not self.swipe_vertical_tolerance > 0.0:
            raise ValueError("swipe vertical tolerance must be positive")
        if not self.swipe_window_seconds > 0.0:
            raise ValueError("swipe window must be positive")
        if not self.high_five_palm_span >= self.minimum_palm_span:
            raise ValueError("high-five palm span must cover the minimum span")
        if self.cooldown_seconds < 0.0:
            raise ValueError("air interaction cooldown cannot be negative")


@dataclass(frozen=True, slots=True)
class AirHandPoint:
    x: float
    y: float
    z: float = 0.0

    def __post_init__(self) -> None:
        if not all(math.isfinite(value) for value in (self.x, self.y, self.z)):
            raise ValueError("air hand landmark must be finite")
        if not 0.0 <= self.x <= 1.0 or not 0.0 <= self.y <= 1.0:
            raise ValueError("air hand landmark must be normalized")


@dataclass(frozen=True, slots=True)
class AirHandSample:
    side: HandSide
    confidence: float
    landmarks: tuple[AirHandPoint, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.side, HandSide):
            raise TypeError("air hand side must be canonical")
        if not math.isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("air hand confidence is invalid")
        if len(self.landmarks) != LANDMARKS_PER_HAND:
            raise ValueError("air hand landmark count is invalid")


@dataclass(frozen=True, slots=True)
class AirInteractionEvent:
    kind: AirInteractionKind
    observed_at: float
    confidence: float
    side: HandSide | None = None
    palm_scale: float = 0.0
    pinch_ratio: float = 1.0
    displacement_x: float = 0.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.observed_at):
            raise ValueError("air interaction time must be finite")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("air interaction confidence is invalid")
        if self.palm_scale < 0.0 or self.pinch_ratio < 0.0:
            raise ValueError("air interaction measurements cannot be negative")
        if not math.isfinite(self.displacement_x):
            raise ValueError("air interaction displacement must be finite")


@dataclass(frozen=True, slots=True)
class AirHandParameters:
    palm_scale: float
    pinch_ratio: float
    index_extension: float
    middle_extension: float

    def __post_init__(self) -> None:
        if self.palm_scale < 0.0 or self.pinch_ratio < 0.0:
            raise ValueError("air hand parameters cannot be negative")
        if not 0.0 <= self.index_extension <= 1.0:
            raise ValueError("index extension must be normalized")
        if not 0.0 <= self.middle_extension <= 1.0:
            raise ValueError("middle extension must be normalized")


@dataclass(frozen=True, slots=True)
class _HandMetrics:
    sample: AirHandSample
    palm_span: float
    pinch_ratio: float
    open_palm_score: float
    wrist: AirHandPoint


class AirInteractionDetector:
    """Turn stable 21-point observations into non-executable local events."""

    def __init__(self, config: AirInteractionConfig | None = None) -> None:
        self._config = config or AirInteractionConfig()
        self._last_time = -math.inf
        self._previous_wrist: dict[HandSide, tuple[float, float, float]] = {}
        self._pinch_candidates: dict[HandSide, int] = {}
        self._pinching: set[HandSide] = set()
        self._high_five_candidates = 0
        self._last_event_at: dict[AirInteractionKind, float] = {}

    @property
    def config(self) -> AirInteractionConfig:
        return self._config

    def update(
        self,
        observed_at: float,
        hands: tuple[AirHandSample, ...],
    ) -> AirInteractionEvent | None:
        if not math.isfinite(observed_at):
            raise ValueError("air interaction time must be finite")
        if observed_at < self._last_time:
            raise ValueError("air interaction frames must be time ordered")
        self._last_time = observed_at
        if not self._config.enabled or not hands:
            self._clear_transient_state()
            return None
        selected = _select_hands(hands)
        if not selected:
            self._clear_transient_state()
            return None
        metrics = tuple(_measure(hand) for hand in selected)
        candidates: list[AirInteractionEvent] = []
        high_five = self._high_five_event(observed_at, metrics)
        if high_five is not None:
            candidates.append(high_five)
        for item in metrics:
            pinch = self._pinch_event(observed_at, item)
            if pinch is not None:
                candidates.append(pinch)
            swipe = self._swipe_event(observed_at, item)
            if swipe is not None:
                candidates.append(swipe)
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda event: (
                event.confidence,
                _EVENT_PRIORITY[event.kind],
                event.kind.value,
            ),
        )

    def reset(self) -> None:
        self._last_time = -math.inf
        self._previous_wrist.clear()
        self._pinch_candidates.clear()
        self._pinching.clear()
        self._high_five_candidates = 0
        self._last_event_at.clear()

    def cancel(self) -> None:
        """Forget in-progress gestures while retaining no camera evidence."""

        self._previous_wrist.clear()
        self._pinch_candidates.clear()
        self._pinching.clear()
        self._high_five_candidates = 0

    def _high_five_event(
        self,
        observed_at: float,
        metrics: tuple[_HandMetrics, ...],
    ) -> AirInteractionEvent | None:
        qualifies = len(metrics) == 2 and all(
            item.sample.confidence >= self._config.minimum_confidence
            and item.palm_span >= self._config.high_five_palm_span
            and item.open_palm_score >= 0.55
            for item in metrics
        )
        self._high_five_candidates = (
            self._high_five_candidates + 1 if qualifies else 0
        )
        if self._high_five_candidates < self._config.minimum_stable_frames:
            return None
        self._high_five_candidates = 0
        confidence = min(
            1.0,
            sum(
                min(item.sample.confidence, item.open_palm_score)
                for item in metrics
            )
            / 2.0,
        )
        return self._emit(
            AirInteractionKind.HIGH_FIVE,
            observed_at,
            confidence,
            palm_scale=sum(item.palm_span for item in metrics) / 2.0,
        )

    def _pinch_event(
        self,
        observed_at: float,
        item: _HandMetrics,
    ) -> AirInteractionEvent | None:
        side = item.sample.side
        if item.sample.confidence < self._config.minimum_confidence:
            self._pinch_candidates.pop(side, None)
            self._pinching.discard(side)
            return None
        if item.pinch_ratio <= self._config.pinch_start_ratio:
            count = self._pinch_candidates.get(side, 0) + 1
            self._pinch_candidates[side] = count
            if side not in self._pinching and count >= self._config.minimum_stable_frames:
                self._pinching.add(side)
                return self._emit(
                    AirInteractionKind.PINCH,
                    observed_at,
                    min(1.0, item.sample.confidence),
                    side=side,
                    palm_scale=item.palm_span,
                    pinch_ratio=item.pinch_ratio,
                )
            return None
        if item.pinch_ratio >= self._config.pinch_release_ratio:
            self._pinch_candidates.pop(side, None)
            self._pinching.discard(side)
        return None

    def _swipe_event(
        self,
        observed_at: float,
        item: _HandMetrics,
    ) -> AirInteractionEvent | None:
        side = item.sample.side
        wrist = item.wrist
        previous = self._previous_wrist.get(side)
        self._previous_wrist[side] = (wrist.x, wrist.y, observed_at)
        if previous is None or item.sample.confidence < self._config.minimum_confidence:
            return None
        previous_x, previous_y, previous_at = previous
        elapsed = observed_at - previous_at
        displacement_x = wrist.x - previous_x
        displacement_y = abs(wrist.y - previous_y)
        if elapsed <= 0.0 or elapsed > self._config.swipe_window_seconds:
            return None
        if abs(displacement_x) < self._config.swipe_distance:
            return None
        if displacement_y > self._config.swipe_vertical_tolerance:
            return None
        kind = (
            AirInteractionKind.SWIPE_RIGHT
            if displacement_x > 0.0
            else AirInteractionKind.SWIPE_LEFT
        )
        confidence = min(
            1.0,
            item.sample.confidence
            * abs(displacement_x)
            / self._config.swipe_distance,
        )
        return self._emit(
            kind,
            observed_at,
            confidence,
            side=side,
            palm_scale=item.palm_span,
            displacement_x=displacement_x,
        )

    def _emit(
        self,
        kind: AirInteractionKind,
        observed_at: float,
        confidence: float,
        *,
        side: HandSide | None = None,
        palm_scale: float = 0.0,
        pinch_ratio: float = 1.0,
        displacement_x: float = 0.0,
    ) -> AirInteractionEvent | None:
        previous = self._last_event_at.get(kind, -math.inf)
        if observed_at - previous < self._config.cooldown_seconds:
            return None
        self._last_event_at[kind] = observed_at
        return AirInteractionEvent(
            kind,
            observed_at,
            max(0.0, min(1.0, confidence)),
            side,
            palm_scale,
            pinch_ratio,
            displacement_x,
        )

    def _clear_transient_state(self) -> None:
        self._previous_wrist.clear()
        self._pinch_candidates.clear()
        self._pinching.clear()
        self._high_five_candidates = 0


_EVENT_PRIORITY = {
    AirInteractionKind.HIGH_FIVE: 4,
    AirInteractionKind.PINCH: 3,
    AirInteractionKind.SWIPE_LEFT: 2,
    AirInteractionKind.SWIPE_RIGHT: 2,
}


def _select_hands(hands: tuple[AirHandSample, ...]) -> tuple[AirHandSample, ...]:
    by_side: dict[HandSide, AirHandSample] = {}
    for hand in hands:
        current = by_side.get(hand.side)
        if current is None or hand.confidence > current.confidence:
            by_side[hand.side] = hand
    return tuple(sorted(by_side.values(), key=lambda hand: hand.side.value))


def _measure(hand: AirHandSample) -> _HandMetrics:
    points = hand.landmarks
    palm_span = _distance(points[5], points[17])
    if palm_span < 1e-6:
        raise ValueError("air hand palm span is too small")
    pinch_ratio = _distance(points[4], points[8]) / palm_span
    extension_scores = tuple(
        _finger_extension(points, mcp, pip, tip)
        for mcp, pip, tip in ((5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20))
    )
    open_palm_score = sum(extension_scores) / len(extension_scores)
    return _HandMetrics(hand, palm_span, pinch_ratio, open_palm_score, points[0])


def measure_hand_parameters(hand: AirHandSample) -> AirHandParameters:
    """Expose stable hand controls without exposing detector state."""

    points = hand.landmarks
    metrics = _measure(hand)
    return AirHandParameters(
        metrics.palm_span,
        metrics.pinch_ratio,
        _finger_extension(points, 5, 6, 8),
        _finger_extension(points, 9, 10, 12),
    )


def _finger_extension(
    points: tuple[AirHandPoint, ...],
    mcp: int,
    pip: int,
    tip: int,
) -> float:
    wrist = points[0]
    pip_distance = _distance(points[pip], wrist)
    tip_distance = _distance(points[tip], wrist)
    length_score = _clamp((tip_distance / max(pip_distance, 1e-6) - 1.05) / 0.35)
    angle = _angle(points[tip], points[pip], points[mcp])
    angle_score = _clamp((angle - 2.0) / (math.pi - 2.0))
    return min(length_score, angle_score)


def _distance(first: AirHandPoint, second: AirHandPoint) -> float:
    return math.hypot(first.x - second.x, first.y - second.y)


def _angle(
    first: AirHandPoint,
    vertex: AirHandPoint,
    second: AirHandPoint,
) -> float:
    first_vector = (first.x - vertex.x, first.y - vertex.y)
    second_vector = (second.x - vertex.x, second.y - vertex.y)
    first_length = math.hypot(*first_vector)
    second_length = math.hypot(*second_vector)
    if first_length < 1e-6 or second_length < 1e-6:
        return 0.0
    cosine = (
        first_vector[0] * second_vector[0]
        + first_vector[1] * second_vector[1]
    ) / (first_length * second_length)
    return math.acos(max(-1.0, min(1.0, cosine)))


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
