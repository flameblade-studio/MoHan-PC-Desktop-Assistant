from __future__ import annotations

lazy import math
lazy from collections import deque
lazy from collections.abc import Mapping, Sequence
lazy from dataclasses import dataclass
lazy from enum import StrEnum
lazy from itertools import pairwise
lazy from operator import itemgetter

lazy from domain.constants import FLOAT_COMPARISON_EPSILON
lazy from domain.gesture_configuration import GestureLandmark, GestureSample
lazy from domain.gesture_intent import HandSide

# Hand-skeleton validation bounds.
LANDMARK_COUNT = 21
MIN_Z = -8.0
MAX_Z = 8.0
MIN_HAND_SCALE = 1e-6

# Static-gesture debounce thresholds.
MINIMUM_FRAMES = 3
MINIMUM_DURATION = 0.18
MIN_CONFIDENCE_LOWER_BOUND = 0.5
DEFAULT_MINIMUM_CONFIDENCE = 0.72

# Wave-gesture detection thresholds.
MIN_WAVE_MOVEMENT = 0.035
MIN_WAVE_REVERSALS = 2
MIN_WAVE_FRAMES = 4
SIGNIFICANT_WAVE_MOVEMENT = 0.018
MIN_SIGNIFICANT_MOVEMENTS = 3
MIN_WAVE_SPAN = 0.045

# Built-in gesture classification thresholds.
THUMB_EXTENDED_RATIO = 0.42
FULL_EXTENDED_FINGERS = 4
THUMB_UP_THRESHOLD = -0.72
THUMB_DOWN_THRESHOLD = 0.72
POINT_HORIZONTAL_THRESHOLD = 0.78


class GestureId(StrEnum):
    UNKNOWN = "unknown"
    OPEN_PALM = "open-palm"
    CLOSED_FIST = "closed-fist"
    THUMBS_UP = "thumbs-up"
    THUMBS_DOWN = "thumbs-down"
    POINT_LEFT = "point-left"
    POINT_RIGHT = "point-right"
    WAVE = "wave"


class RecognitionState(StrEnum):
    UNKNOWN = "unknown"
    CANDIDATE = "candidate"
    TRIGGERED = "triggered"
    COOLDOWN = "cooldown"


@dataclass(frozen=True, slots=True)
class HandSkeleton:
    observed_at: float
    side: HandSide
    landmarks: tuple[GestureLandmark, ...]

    def __post_init__(self) -> None:
        if not math.isfinite(self.observed_at):
            raise ValueError("Gesture observation time must be finite.")
        if not isinstance(self.side, HandSide):
            raise TypeError("Gesture hand side must be canonical.")
        if len(self.landmarks) != LANDMARK_COUNT:
            raise ValueError("Gesture recognition requires exactly 21 landmarks.")
        if any(
            not 0.0 <= coordinate <= 1.0
            for point in self.landmarks
            for coordinate in (point.x, point.y)
        ):
            raise ValueError("Gesture x/y landmarks must be normalized to [0, 1].")
        if any(
            not math.isfinite(point.z) or not MIN_Z <= point.z <= MAX_Z
            for point in self.landmarks
        ):
            raise ValueError("Gesture z landmarks must remain within [-8, 8].")
        if _hand_scale(self.landmarks) <= MIN_HAND_SCALE:
            raise ValueError("Gesture skeleton must have non-zero scale.")


@dataclass(frozen=True, slots=True)
class GestureRecognition:
    gesture_id: GestureId | str
    confidence: float
    state: RecognitionState
    side: HandSide

    def __post_init__(self) -> None:
        if not isinstance(self.gesture_id, (GestureId, str)):
            raise TypeError("Gesture identifier must be typed text.")
        if not math.isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Gesture confidence must be normalized.")
        if self.gesture_id is GestureId.UNKNOWN and abs(self.confidence) >= FLOAT_COMPARISON_EPSILON:
            raise ValueError("Unknown gestures cannot claim confidence.")

    @property
    def triggered(self) -> bool:
        return self.state is RecognitionState.TRIGGERED


@dataclass(frozen=True, slots=True)
class _WavePoint:
    observed_at: float
    wrist_x: float


@dataclass(slots=True)
class _CandidateSequence:
    gesture_id: GestureId | str
    started_at: float
    frames: int
    confidence: float


@dataclass(frozen=True, slots=True)
class GestureTiming:
    cooldown_seconds: float = 1.0
    wave_window_seconds: float = 1.2
    minimum_frames: int = 3
    minimum_duration: float = 0.18

    def __post_init__(self) -> None:
        if self.cooldown_seconds < 0.0 or self.wave_window_seconds <= 0.0:
            raise ValueError("Gesture timing windows must be valid.")
        if self.minimum_frames < MINIMUM_FRAMES or self.minimum_duration < MINIMUM_DURATION:
            raise ValueError("Static gestures require at least 3 frames over 0.18 seconds.")


_FINGERS = ((5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20))
DEFAULT_GESTURE_TIMING = GestureTiming()


class GestureRecognizer:
    """Classify ephemeral hand skeletons without executing bound actions."""

    def __init__(
        self,
        custom_templates: Mapping[str, Sequence[GestureSample]] | None = None,
        *,
        minimum_confidence: float = 0.72,
        custom_max_distance: float = 0.18,
        timing: GestureTiming = DEFAULT_GESTURE_TIMING,
    ) -> None:
        if not MIN_CONFIDENCE_LOWER_BOUND <= minimum_confidence <= 1.0:
            raise ValueError("Minimum gesture confidence is invalid.")
        if custom_max_distance <= 0.0:
            raise ValueError("Gesture distance must be valid.")
        if not isinstance(timing, GestureTiming):
            raise TypeError("Gesture timing must be canonical.")
        self._minimum_confidence = minimum_confidence
        self._custom_max_distance = custom_max_distance
        self._timing = timing
        self._templates = _prepare_templates(custom_templates or {})
        self._wave: dict[HandSide, deque[_WavePoint]] = {
            side: deque() for side in HandSide
        }
        self._last_time: dict[HandSide, float] = {
            side: float("-inf") for side in HandSide
        }
        self._candidate: dict[HandSide, _CandidateSequence | None] = dict.fromkeys(HandSide)
        self._cooldown_until: dict[HandSide, float] = {
            side: float("-inf") for side in HandSide
        }

    @property
    def silence_requires_external_fusion(self) -> bool:
        """Silence remains owned by gesture_intent.SilenceGestureDetector."""

        return True

    def update(self, skeleton: HandSkeleton) -> GestureRecognition:
        if skeleton.observed_at <= self._last_time[skeleton.side]:
            self._reset_side(skeleton.side)
            return _unknown(skeleton.side)
        self._last_time[skeleton.side] = skeleton.observed_at
        if skeleton.observed_at < self._cooldown_until[skeleton.side]:
            self._reset_side(skeleton.side)
            return GestureRecognition(
                GestureId.UNKNOWN,
                0.0,
                RecognitionState.COOLDOWN,
                skeleton.side,
            )
        builtin = _classify_builtin(skeleton)
        wave = self._update_wave(skeleton, builtin)
        candidate = wave or self._classify_custom(skeleton) or builtin
        if candidate is None or candidate.confidence < self._minimum_confidence:
            self._candidate[skeleton.side] = None
            return _unknown(skeleton.side)
        if (
            candidate.gesture_id is GestureId.OPEN_PALM
            and self._wave_is_pending(skeleton.side)
        ):
            self._candidate[skeleton.side] = None
            return candidate
        if candidate.gesture_id is not GestureId.WAVE:
            debounced = self._debounce_static(skeleton, candidate)
            if debounced is not None:
                return debounced
        return self._trigger(skeleton, candidate)

    def cancel(self, side: HandSide | None = None) -> None:
        """Cancel pending observations for one hand or both hands."""

        sides = tuple(HandSide) if side is None else (side,)
        if side is not None and not isinstance(side, HandSide):
            raise TypeError("Cancelled hand side must be canonical.")
        for target in sides:
            self._reset_side(target)
            self._last_time[target] = float("-inf")

    def reset(self) -> None:
        self.cancel()
        for side in HandSide:
            self._cooldown_until[side] = float("-inf")

    def _debounce_static(
        self,
        skeleton: HandSkeleton,
        candidate: GestureRecognition,
    ) -> GestureRecognition | None:
        current = self._candidate[skeleton.side]
        if current is None or current.gesture_id != candidate.gesture_id:
            self._candidate[skeleton.side] = _CandidateSequence(
                candidate.gesture_id,
                skeleton.observed_at,
                1,
                candidate.confidence,
            )
            return candidate
        current.frames += 1
        current.confidence = min(current.confidence, candidate.confidence)
        if (
            current.frames < self._timing.minimum_frames
            or skeleton.observed_at - current.started_at
            < self._timing.minimum_duration
        ):
            return GestureRecognition(
                current.gesture_id,
                current.confidence,
                RecognitionState.CANDIDATE,
                skeleton.side,
            )
        return None

    def _wave_is_pending(self, side: HandSide) -> bool:
        history = tuple(self._wave[side])
        if len(history) < MINIMUM_FRAMES:
            return False
        movements = tuple(
            current.wrist_x - previous.wrist_x
            for previous, current in pairwise(history)
            if abs(current.wrist_x - previous.wrist_x) >= MIN_WAVE_MOVEMENT
        )
        return len(movements) >= MIN_WAVE_REVERSALS and any(
            left * right < 0.0 for left, right in pairwise(movements)
        )

    def _trigger(
        self,
        skeleton: HandSkeleton,
        candidate: GestureRecognition,
    ) -> GestureRecognition:
        self._cooldown_until[skeleton.side] = (
            skeleton.observed_at + self._timing.cooldown_seconds
        )
        self._reset_side(skeleton.side)
        return GestureRecognition(
            candidate.gesture_id,
            candidate.confidence,
            RecognitionState.TRIGGERED,
            skeleton.side,
        )

    def _reset_side(self, side: HandSide) -> None:
        self._wave[side].clear()
        self._candidate[side] = None

    def _update_wave(
        self,
        skeleton: HandSkeleton,
        builtin: GestureRecognition | None,
    ) -> GestureRecognition | None:
        history = self._wave[skeleton.side]
        if not _wave_palm_visible(skeleton, builtin):
            history.clear()
            return None
        history.append(_WavePoint(skeleton.observed_at, skeleton.landmarks[0].x))
        cutoff = skeleton.observed_at - self._timing.wave_window_seconds
        while history and history[0].observed_at < cutoff:
            history.popleft()
        if len(history) < MIN_WAVE_FRAMES:
            return None
        ordered = tuple(history)
        span = max(point.wrist_x for point in ordered) - min(
            point.wrist_x for point in ordered
        )
        if span < MIN_WAVE_SPAN:
            # A held open hand is not a wave.  Retain only enough recent
            # context to notice when it starts moving instead of keeping a
            # full sampling-window of identical skeletons indefinitely.
            while len(history) > 2:
                history.popleft()
            return None
        movements = tuple(
            current.wrist_x - previous.wrist_x
            for previous, current in pairwise(ordered)
        )
        # Webcam sampling is deliberately throttled; accept a natural wave
        # across four stable frames without requiring exaggerated arm swings.
        # Thresholds are kept forgiving so a casual side-to-side wave in front
        # of the camera reliably registers as a greeting.
        significant = tuple(value for value in movements if abs(value) >= SIGNIFICANT_WAVE_MOVEMENT)
        reversals = sum(
            left * right < 0.0
            for left, right in pairwise(significant)
        )
        if len(significant) >= MIN_SIGNIFICANT_MOVEMENTS and reversals >= 1 and span >= MIN_WAVE_SPAN:
            history.clear()
            return GestureRecognition(
                GestureId.WAVE,
                min(0.99, 0.82 + span),
                RecognitionState.CANDIDATE,
                skeleton.side,
            )
        return None

    def _classify_custom(
        self,
        skeleton: HandSkeleton,
    ) -> GestureRecognition | None:
        if not self._templates:
            return None
        normalized = _normalize(skeleton.landmarks, skeleton.side)
        scores = tuple(
            (
                gesture_id,
                min(_distance(normalized, sample) for sample in samples),
            )
            for gesture_id, samples in self._templates.items()
        )
        gesture_id, distance = min(scores, key=itemgetter(1, 0))
        confidence = max(0.0, 1.0 - distance / self._custom_max_distance)
        if distance > self._custom_max_distance or confidence < self._minimum_confidence:
            return None
        return GestureRecognition(
            gesture_id,
            confidence,
            RecognitionState.CANDIDATE,
            skeleton.side,
        )


def _classify_builtin(skeleton: HandSkeleton) -> GestureRecognition | None:
    points = skeleton.landmarks
    fingers = tuple(_finger_extended(points, *indices) for indices in _FINGERS)
    thumb_vector = (points[4].x - points[2].x, points[4].y - points[2].y)
    thumb_length = math.hypot(*thumb_vector)
    scale = _hand_scale(points)
    thumb_extended = thumb_length / scale >= THUMB_EXTENDED_RATIO
    extended_count = sum(fingers)
    if extended_count == FULL_EXTENDED_FINGERS and thumb_extended:
        return _candidate(GestureId.OPEN_PALM, 0.94, skeleton.side)
    if extended_count == 0 and not thumb_extended:
        return _candidate(GestureId.CLOSED_FIST, 0.92, skeleton.side)
    if extended_count == 0 and thumb_extended:
        vertical = thumb_vector[1] / max(thumb_length, 1e-9)
        if vertical <= THUMB_UP_THRESHOLD:
            return _candidate(GestureId.THUMBS_UP, abs(vertical), skeleton.side)
        if vertical >= THUMB_DOWN_THRESHOLD:
            return _candidate(GestureId.THUMBS_DOWN, abs(vertical), skeleton.side)
    if fingers == (True, False, False, False) and not thumb_extended:
        vector_x = points[8].x - points[5].x
        vector_y = points[8].y - points[5].y
        length = math.hypot(vector_x, vector_y)
        horizontal = abs(vector_x) / max(length, 1e-9)
        if horizontal >= POINT_HORIZONTAL_THRESHOLD:
            gesture_id = GestureId.POINT_LEFT if vector_x < 0.0 else GestureId.POINT_RIGHT
            return _candidate(gesture_id, horizontal, skeleton.side)
    return None


def _wave_palm_visible(
    skeleton: HandSkeleton,
    builtin: GestureRecognition | None,
) -> bool:
    """Accept a natural waving hand even when the thumb is partly tucked."""

    if builtin is not None and builtin.gesture_id is GestureId.OPEN_PALM:
        return True
    points = skeleton.landmarks
    return all(_finger_extended(points, *indices) for indices in _FINGERS)


def _finger_extended(
    points: tuple[GestureLandmark, ...],
    base: int,
    middle: int,
    tip: int,
) -> bool:
    wrist = points[0]
    return _point_distance(wrist, points[tip]) > _point_distance(
        wrist, points[middle]
    ) * 1.18 and _point_distance(points[base], points[tip]) > _point_distance(
        points[base], points[middle]
    ) * 1.18


def _candidate(
    gesture_id: GestureId,
    confidence: float,
    side: HandSide,
) -> GestureRecognition:
    return GestureRecognition(
        gesture_id,
        confidence,
        RecognitionState.CANDIDATE,
        side,
    )


def _unknown(side: HandSide) -> GestureRecognition:
    return GestureRecognition(
        GestureId.UNKNOWN,
        0.0,
        RecognitionState.UNKNOWN,
        side,
    )


def _prepare_templates(
    templates: Mapping[str, Sequence[GestureSample]],
) -> dict[str, tuple[tuple[tuple[float, float, float], ...], ...]]:
    prepared = {}
    for gesture_id, samples in templates.items():
        identifier = gesture_id.strip()
        if not identifier.startswith("custom:") or not samples:
            raise ValueError("Custom templates require a custom identifier and samples.")
        prepared[identifier] = tuple(
            _normalize(sample.landmarks, HandSide.RIGHT) for sample in samples
        )
    return prepared


def _normalize(
    points: tuple[GestureLandmark, ...],
    side: HandSide,
) -> tuple[tuple[float, float, float], ...]:
    origin = points[0]
    scale = _hand_scale(points)
    mirror = -1.0 if side is HandSide.LEFT else 1.0
    return tuple(
        (
            (point.x - origin.x) * mirror / scale,
            (point.y - origin.y) / scale,
            (point.z - origin.z) / scale,
        )
        for point in points
    )


def _hand_scale(points: tuple[GestureLandmark, ...]) -> float:
    wrist = points[0]
    return max(_point_distance(wrist, point) for point in points)


def _point_distance(left: GestureLandmark, right: GestureLandmark) -> float:
    return math.dist((left.x, left.y, left.z), (right.x, right.y, right.z))


def _distance(
    left: tuple[tuple[float, float, float], ...],
    right: tuple[tuple[float, float, float], ...],
) -> float:
    return sum(map(math.dist, left, right, strict=True)) / len(left)
