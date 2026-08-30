from __future__ import annotations

lazy import time
lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from enum import IntEnum, StrEnum


class FramingMode(IntEnum):
    CLOSE = 0
    HALF = 1
    THREE_QUARTER = 2
    FULL_BODY = 3


# Framing modes that publish the composed v4 full-body photograph.  CLOSE and
# HALF keep the legacy half-body poses, so the expensive full-body composition
# must not run for them at all.
PUBLISHABLE_BODY_MODES = frozenset({FramingMode.THREE_QUARTER, FramingMode.FULL_BODY})


QUIET_CONCERN_THRESHOLD = 0.78
MIN_HEIGHT_PX = 560
MIN_WIDTH_PX = 420
FULL_BODY_HEIGHT_PX = 760


class FramingReason(StrEnum):
    DAILY_COMPANION = "daily-companion"
    QUIET_CONCERN = "quiet-concern"
    LARGE_GESTURE = "large-gesture"
    ARRIVAL = "arrival"
    OUTFIT_PREVIEW = "outfit-preview"
    TURNING_AWAY = "turning-away"
    SMALL_VIEWPORT = "small-viewport"
    SPEECH_HOLD = "speech-hold"
    RATE_LIMIT = "rate-limit"


@dataclass(frozen=True, slots=True)
class NormalizedRect:
    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        if not (
            0.0 <= self.left < self.right <= 1.0
            and 0.0 <= self.top < self.bottom <= 1.0
        ):
            raise ValueError("Normalized framing rectangle must be within 0..1.")

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    def contains(self, other: NormalizedRect) -> bool:
        return (
            self.left <= other.left
            and self.top <= other.top
            and self.right >= other.right
            and self.bottom >= other.bottom
        )


FRAMING_RECTS = frozendict(
    {
        FramingMode.CLOSE: NormalizedRect(0.25, 0.00, 0.75, 0.34),
        FramingMode.HALF: NormalizedRect(0.15, 0.00, 0.85, 0.57),
        FramingMode.THREE_QUARTER: NormalizedRect(0.08, 0.00, 0.92, 0.82),
        FramingMode.FULL_BODY: NormalizedRect(0.00, 0.00, 1.00, 1.00),
    }
)


@dataclass(frozen=True, slots=True)
class FramingContext:
    available_width_px: int
    available_height_px: int
    speech_active: bool = False
    mouth_closed: bool = True
    emotion_intensity: float = 0.0
    gesture_bounds: NormalizedRect | None = None
    owner_arrived: bool = False
    outfit_preview: bool = False
    turning_away: bool = False
    adaptive_enabled: bool = True

    def __post_init__(self) -> None:
        if self.available_width_px <= 0 or self.available_height_px <= 0:
            raise ValueError("Available desktop viewport must be positive.")
        if not 0.0 <= self.emotion_intensity <= 1.0:
            raise ValueError("Emotion intensity must be within 0..1.")


@dataclass(frozen=True, slots=True)
class FramingDecision:
    mode: FramingMode
    crop: NormalizedRect
    transition_ms: int
    held: bool
    reason: FramingReason


# Framing styles (owner ruling 2026-08-29, after the v4.5.1 "jumping between
# full body and half body" report): "steady" keeps the whole conversation
# session at the half-body shot and only relaxes after a quiet cooldown;
# "lively" is the original event-driven behaviour; "half-only" never leaves
# the half-body shot except for the outfit preview, which needs the full
# photograph to show the garment.
FRAMING_STYLES = ("steady", "lively", "half-only")
DEFAULT_FRAMING_STYLE = "steady"
STEADY_TRANSITION_GAP_SECONDS = 8.0
LIVELY_TRANSITION_GAP_SECONDS = 1.2
CONVERSATION_HOLD_SECONDS = 75.0


class CharacterFramingDirector:
    """Select a human-like shot while keeping one full-body identity source."""

    minimum_transition_gap_seconds = LIVELY_TRANSITION_GAP_SECONDS

    def __init__(
        self,
        clock: Callable[[], float] | None = None,
        *,
        initial_mode: FramingMode = FramingMode.HALF,
        style: str = DEFAULT_FRAMING_STYLE,
    ) -> None:
        self._clock = clock or time.monotonic
        self._mode = initial_mode
        self._last_change_at = float("-inf")
        self._pending: tuple[FramingMode, FramingReason] | None = None
        self._style = style if style in FRAMING_STYLES else DEFAULT_FRAMING_STYLE
        if self._style == "steady":
            self.minimum_transition_gap_seconds = STEADY_TRANSITION_GAP_SECONDS
        self._last_speech_at = float("-inf")

    @property
    def style(self) -> str:
        return self._style

    @property
    def mode(self) -> FramingMode:
        return self._mode

    def decide(self, context: FramingContext) -> FramingDecision:
        if not context.adaptive_enabled:
            return self._decision(self._mode, True, FramingReason.DAILY_COMPANION)

        requested, reason = self._requested(context)
        if self._style == "half-only" and not context.outfit_preview:
            # The owner asked for a completely still companion: everything but
            # the outfit preview stays at the half-body shot.
            requested, reason = FramingMode.HALF, FramingReason.DAILY_COMPANION
        fitted = self._fit_viewport(requested, context)
        if fitted != requested:
            reason = FramingReason.SMALL_VIEWPORT
        requested = fitted

        if context.speech_active:
            self._last_speech_at = float(self._clock())

        if context.speech_active and not context.mouth_closed:
            # Speech is fixed at the half-body shot.  Jump straight to HALF
            # instead of stepping through THREE_QUARTER, so a lingering
            # FULL_BODY (from an idle full-body view) or CLOSE never lingers
            # across the start of speech.  The companion must not speak a few
            # words in full-body before snapping back to half-body.
            # Remember the framing the policy actually wanted so the
            # mouth-closed branch below can restore it after speech; this
            # was the missing producer of ``_pending`` (the consumer existed
            # but nothing ever set it, so deferred restores never happened).
            if requested is not FramingMode.HALF:
                self._pending = (requested, reason)
            if self._mode is not FramingMode.HALF:
                self._mode = FramingMode.HALF
                self._last_change_at = float(self._clock())
                return self._decision(
                    self._mode,
                    False,
                    FramingReason.SPEECH_HOLD,
                )
            return self._decision(self._mode, True, FramingReason.SPEECH_HOLD)

        if context.mouth_closed and self._pending is not None:
            if (
                self._style == "steady"
                and float(self._clock()) - self._last_speech_at
                < CONVERSATION_HOLD_SECONDS
            ):
                # Conversation stickiness: between turns (the user typing, the
                # companion waiting) the shot stays half-body instead of
                # bouncing back to full body the moment the mouth closes.
                requested, reason = FramingMode.HALF, FramingReason.SPEECH_HOLD
            else:
                requested, reason = self._pending
                requested = self._fit_viewport(requested, context)
                self._pending = None

        now = float(self._clock())
        if (
            requested != self._mode
            and now - self._last_change_at < self.minimum_transition_gap_seconds
        ):
            return self._decision(self._mode, True, FramingReason.RATE_LIMIT)
        if requested != self._mode:
            self._mode = self._step_toward(self._mode, requested)
            self._last_change_at = now
            held = False
        else:
            held = True

        crop = self._crop_with_gesture(self._mode, context.gesture_bounds)
        mode = self._mode_for_crop(self._mode, crop)
        if mode != self._mode:
            self._mode = mode
            self._last_change_at = now
            held = False
        return FramingDecision(
            self._mode,
            crop,
            480 if held else 720,
            held,
            reason,
        )

    def _requested(
        self,
        context: FramingContext,
    ) -> tuple[FramingMode, FramingReason]:
        if context.outfit_preview:
            return FramingMode.FULL_BODY, FramingReason.OUTFIT_PREVIEW
        if context.turning_away:
            return FramingMode.FULL_BODY, FramingReason.TURNING_AWAY
        if context.owner_arrived:
            return FramingMode.FULL_BODY, FramingReason.ARRIVAL
        if context.gesture_bounds is not None and not FRAMING_RECTS[
            FramingMode.HALF
        ].contains(context.gesture_bounds):
            return FramingMode.THREE_QUARTER, FramingReason.LARGE_GESTURE
        if context.speech_active:
            # Speech is fixed at the half-body shot so the mouth and eyes stay
            # clearly readable.  Full-body is reserved for gestures, hand
            # actions, accessory reveals, and non-conversation idle time.
            return FramingMode.HALF, FramingReason.SPEECH_HOLD
        if context.emotion_intensity >= QUIET_CONCERN_THRESHOLD:
            return FramingMode.CLOSE, FramingReason.QUIET_CONCERN
        return FramingMode.HALF, FramingReason.DAILY_COMPANION

    @staticmethod
    def _fit_viewport(
        requested: FramingMode,
        context: FramingContext,
    ) -> FramingMode:
        if context.available_height_px < MIN_HEIGHT_PX or context.available_width_px < MIN_WIDTH_PX:
            return FramingMode.HALF
        if context.available_height_px < FULL_BODY_HEIGHT_PX and requested is FramingMode.FULL_BODY:
            return FramingMode.THREE_QUARTER
        return requested

    @staticmethod
    def _step_toward(current: FramingMode, requested: FramingMode) -> FramingMode:
        if abs(int(requested) - int(current)) <= 1:
            return requested
        return FramingMode(int(current) + (1 if requested > current else -1))

    @staticmethod
    def _crop_with_gesture(
        mode: FramingMode,
        gesture: NormalizedRect | None,
    ) -> NormalizedRect:
        crop = FRAMING_RECTS[mode]
        if gesture is None or crop.contains(gesture):
            return crop
        for candidate in (
            FramingMode.THREE_QUARTER,
            FramingMode.FULL_BODY,
        ):
            if FRAMING_RECTS[candidate].contains(gesture):
                return FRAMING_RECTS[candidate]
        return FRAMING_RECTS[FramingMode.FULL_BODY]

    @staticmethod
    def _mode_for_crop(
        current: FramingMode,
        crop: NormalizedRect,
    ) -> FramingMode:
        for mode, candidate in FRAMING_RECTS.items():
            if crop == candidate:
                return mode
        return current

    def _decision(
        self,
        mode: FramingMode,
        held: bool,
        reason: FramingReason,
    ) -> FramingDecision:
        return FramingDecision(mode, FRAMING_RECTS[mode], 480, held, reason)
