from __future__ import annotations

lazy import math
lazy from dataclasses import dataclass
lazy from enum import StrEnum

HAND_LANDMARK_COUNT = 21
MIN_FRAMES = 2


class HandSide(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class GestureIntent(StrEnum):
    SILENCE_REQUEST = "silence-request"


class GestureState(StrEnum):
    IDLE = "idle"
    CANDIDATE = "candidate"
    COOLDOWN = "cooldown"
    TRIGGERED = "triggered"


@dataclass(frozen=True, slots=True)
class NormalizedPoint:
    x: float
    y: float

    def __post_init__(self) -> None:
        if not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in (self.x, self.y)):
            raise ValueError("Landmark coordinates must be finite and normalized.")

    def distance_to(self, other: NormalizedPoint) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


@dataclass(frozen=True, slots=True)
class LipRegion:
    center: NormalizedPoint
    width: float
    height: float

    def __post_init__(self) -> None:
        if not all(math.isfinite(value) and 0.0 < value <= 1.0 for value in (self.width, self.height)):
            raise ValueError("Lip region dimensions must be finite and positive.")

    def normalized_distance(self, point: NormalizedPoint) -> float:
        return math.hypot(
            (point.x - self.center.x) / self.width,
            (point.y - self.center.y) / self.height,
        )


@dataclass(frozen=True, slots=True)
class HandLandmarks:
    side: HandSide
    points: tuple[NormalizedPoint, ...]

    def __post_init__(self) -> None:
        if len(self.points) != HAND_LANDMARK_COUNT:
            raise ValueError("A hand observation must contain exactly 21 landmarks.")


@dataclass(frozen=True, slots=True)
class GestureFrame:
    observed_at: float
    lips: LipRegion | None
    hands: tuple[HandLandmarks, ...]
    tracking_valid: bool = True

    def __post_init__(self) -> None:
        if not math.isfinite(self.observed_at):
            raise ValueError("Gesture frame time must be finite.")
        if len({hand.side for hand in self.hands}) != len(self.hands):
            raise ValueError("A frame cannot contain duplicate hand sides.")


@dataclass(frozen=True, slots=True)
class GestureIntentDecision:
    state: GestureState
    intent: GestureIntent | None
    hand: HandSide | None
    confidence: float


class SilenceGestureDetector:
    """Debounce a visible finger-to-lips gesture into one local-only intent."""

    def __init__(
        self,
        *,
        minimum_frames: int = 3,
        minimum_duration: float = 0.20,
        cooldown: float = 2.0,
        lip_distance: float = 1.35,
    ) -> None:
        if minimum_frames < MIN_FRAMES:
            raise ValueError("minimum_frames must be at least two.")
        if minimum_duration <= 0.0 or cooldown < 0.0 or lip_distance <= 0.0:
            raise ValueError("Gesture timing and distance settings are invalid.")
        self._minimum_frames = minimum_frames
        self._minimum_duration = minimum_duration
        self._cooldown = cooldown
        self._lip_distance = lip_distance
        self._candidate_side: HandSide | None = None
        self._candidate_since: float | None = None
        self._candidate_frames = 0
        self._cooldown_until = -math.inf
        self._last_time = -math.inf

    def update(self, frame: GestureFrame) -> GestureIntentDecision:
        if frame.observed_at < self._last_time:
            raise ValueError("Gesture frames must be time ordered.")
        self._last_time = frame.observed_at
        if not frame.tracking_valid or frame.lips is None or not frame.hands:
            self.cancel()
            return GestureIntentDecision(GestureState.IDLE, None, None, 0.0)
        match = next(
            (
                (hand.side, confidence)
                for hand in frame.hands
                if (confidence := self._match_confidence(frame.lips, hand)) > 0.0
            ),
            None,
        )
        if match is None:
            self.cancel()
            return GestureIntentDecision(GestureState.IDLE, None, None, 0.0)
        side, confidence = match
        if frame.observed_at < self._cooldown_until:
            self.cancel()
            return GestureIntentDecision(
                GestureState.COOLDOWN,
                None,
                side,
                confidence,
            )
        if side is not self._candidate_side:
            self._candidate_side = side
            self._candidate_since = frame.observed_at
            self._candidate_frames = 1
        else:
            self._candidate_frames += 1
        candidate_since = self._candidate_since
        if candidate_since is None:
            raise RuntimeError("Gesture candidate time was not initialized.")
        elapsed = frame.observed_at - candidate_since
        if self._candidate_frames < self._minimum_frames or elapsed < self._minimum_duration:
            return GestureIntentDecision(GestureState.CANDIDATE, None, side, confidence)
        self._cooldown_until = frame.observed_at + self._cooldown
        self.cancel()
        return GestureIntentDecision(
            GestureState.TRIGGERED,
            GestureIntent.SILENCE_REQUEST,
            side,
            confidence,
        )

    def cancel(self) -> None:
        """Cancel only accumulated evidence; cooldown remains authoritative."""

        self._candidate_side = None
        self._candidate_since = None
        self._candidate_frames = 0

    def _match_confidence(self, lips: LipRegion, hand: HandLandmarks) -> float:
        wrist = hand.points[0]
        index_pip = hand.points[6]
        index_tip = hand.points[8]
        near_lips = lips.normalized_distance(index_tip)
        index_extended = index_tip.distance_to(wrist) > index_pip.distance_to(wrist) * 1.08
        folded = all(
            hand.points[tip].distance_to(wrist)
            <= hand.points[pip].distance_to(wrist) * 1.08
            for pip, tip in ((10, 12), (14, 16), (18, 20))
        )
        if near_lips > self._lip_distance or not index_extended or not folded:
            return 0.0
        # Geometry, folded-finger checks and temporal debounce already form a
        # strict fused classifier. Keep its calibrated confidence above the
        # generic action-router floor while preserving proximity ordering.
        proximity = 1.0 - near_lips / self._lip_distance
        return max(0.8, min(1.0, 0.8 + 0.2 * proximity))
