from __future__ import annotations

lazy from dataclasses import dataclass
lazy from enum import StrEnum

lazy from domain.character_framing import FramingMode, NormalizedRect


class EmotionValence(StrEnum):
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"


class FocusState(StrEnum):
    AVAILABLE = "available"
    FOCUSED = "focused"
    DEEP_FOCUS = "deep-focus"


class WellbeingReminderKind(StrEnum):
    MEAL = "meal"
    HYDRATION = "hydration"
    REST = "rest"
    PROLONGED_SITTING = "prolonged-sitting"


class FramingReasonCode(StrEnum):
    BASELINE_COMPANION = "baseline-companion"
    RETURNED_AFTER_ABSENCE = "returned-after-absence"
    SHORT_RETURN = "short-return"
    HIGH_INTIMACY = "high-intimacy"
    LOW_INTIMACY = "low-intimacy"
    POSITIVE_EMOTION = "positive-emotion"
    NEGATIVE_EMOTION = "negative-emotion"
    HIGH_EMOTION = "high-emotion"
    ANGRY_BACK_TURN = "angry-back-turn"
    SPEECH_ACTIVE = "speech-active"
    MOUTH_ACTIVE = "mouth-active"
    GESTURE_OUTSIDE_HALF = "gesture-outside-half"
    GESTURE_REQUIRES_FULL = "gesture-requires-full"
    WEAPON_OR_LARGE_PROP = "weapon-or-large-prop"
    OUTFIT_PREVIEW = "outfit-preview"
    USER_FOCUSED = "user-focused"
    USER_DEEP_FOCUS = "user-deep-focus"
    PROACTIVE_GREETING = "proactive-greeting"
    CLOSE_PRIVACY_ALLOWED = "close-privacy-allowed"
    CLOSE_PRIVACY_BLOCKED = "close-privacy-blocked"
    FULL_BODY_NOT_JUSTIFIED = "full-body-not-justified"
    CLOSE_RESTRAINED = "close-restrained"
    FIRST_WELLBEING_REMINDER = "first-wellbeing-reminder"
    REPEATED_WELLBEING_NUDGE = "repeated-wellbeing-nudge"
    REPEATED_MEAL_NUDGE = "repeated-meal-nudge"
    REPEATED_HYDRATION_NUDGE = "repeated-hydration-nudge"
    REPEATED_REST_NUDGE = "repeated-rest-nudge"
    REPEATED_PROLONGED_SITTING_NUDGE = "repeated-prolonged-sitting-nudge"
    WELLBEING_NUDGE_NOT_ELIGIBLE = "wellbeing-nudge-not-eligible"


@dataclass(frozen=True, slots=True)
class WellbeingReminderSnapshot:
    event_id: str
    kind: WellbeingReminderKind
    occurrence: int
    waiting_window_expired: bool
    acknowledged: bool
    snoozed: bool
    dismissed: bool
    in_meeting: bool
    fullscreen_active: bool
    proactive_care_allowed: bool
    variation_eligible: bool
    daily_limit: int
    daily_used: int
    category_limit: int
    category_used: int
    cooldown_seconds: float
    seconds_since_last_nudge: float

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("Wellbeing event ID must not be empty.")
        if self.occurrence < 1:
            raise ValueError("Reminder occurrence must be positive.")
        values = (
            self.daily_limit,
            self.daily_used,
            self.category_limit,
            self.category_used,
        )
        if any(value < 0 for value in values):
            raise ValueError("Reminder limits and usage must not be negative.")
        if self.cooldown_seconds < 0.0 or self.seconds_since_last_nudge < 0.0:
            raise ValueError("Reminder cooldown timing must not be negative.")


@dataclass(frozen=True, slots=True)
class FramingPolicyContext:
    away_seconds: float
    returned_to_seat: bool
    intimacy: float
    emotion_intensity: float
    emotion_valence: EmotionValence
    angry_back_turn: bool
    speech_active: bool
    mouth_closed: bool
    gesture_bounds: NormalizedRect | None
    weapon_or_large_prop: bool
    outfit_preview: bool
    focus_state: FocusState
    proactive_greeting: bool
    close_framing_allowed: bool
    wellbeing_reminder: WellbeingReminderSnapshot | None = None

    def __post_init__(self) -> None:
        if self.away_seconds < 0.0:
            raise ValueError("Away time must not be negative.")
        if not 0.0 <= self.intimacy <= 1.0:
            raise ValueError("Intimacy must be within 0..1.")
        if not 0.0 <= self.emotion_intensity <= 1.0:
            raise ValueError("Emotion intensity must be within 0..1.")
        if self.speech_active and self.mouth_closed:
            raise ValueError("Active speech cannot report a closed mouth.")


@dataclass(frozen=True, slots=True)
class FramingProposal:
    mode: FramingMode
    score: float
    confidence: float
    reasons: tuple[FramingReasonCode, ...]
    hold_during_speech: bool

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("Framing score must be within 0..1.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Framing confidence must be within 0..1.")
        if not self.reasons:
            raise ValueError("Every framing proposal needs an audit reason.")


@dataclass(frozen=True, slots=True)
class FramingPolicyResult:
    proposals: tuple[FramingProposal, ...]

    def __post_init__(self) -> None:
        if tuple(proposal.mode for proposal in self.proposals) != tuple(FramingMode):
            raise ValueError("Policy output must contain all four framing modes in order.")

    @property
    def recommended(self) -> FramingProposal:
        return max(
            self.proposals,
            key=lambda proposal: (proposal.score, -int(proposal.mode)),
        )


_BASE_SCORES = frozendict({
    FramingMode.CLOSE: 0.18,
    FramingMode.HALF: 0.62,
    FramingMode.THREE_QUARTER: 0.42,
    FramingMode.FULL_BODY: 0.10,
})
_HALF_RECT = NormalizedRect(0.15, 0.00, 0.85, 0.57)
_THREE_QUARTER_RECT = NormalizedRect(0.08, 0.00, 0.92, 0.82)
_REPEATED_WELLBEING_FRAMING = frozendict({
    WellbeingReminderKind.MEAL: (
        FramingMode.CLOSE,
        0.58,
        FramingReasonCode.REPEATED_MEAL_NUDGE,
    ),
    WellbeingReminderKind.HYDRATION: (
        FramingMode.HALF,
        0.28,
        FramingReasonCode.REPEATED_HYDRATION_NUDGE,
    ),
    WellbeingReminderKind.REST: (
        FramingMode.CLOSE,
        0.54,
        FramingReasonCode.REPEATED_REST_NUDGE,
    ),
    WellbeingReminderKind.PROLONGED_SITTING: (
        FramingMode.THREE_QUARTER,
        0.42,
        FramingReasonCode.REPEATED_PROLONGED_SITTING_NUDGE,
    ),
})


def evaluate_framing_context(
    context: FramingPolicyContext,
) -> FramingPolicyResult:
    """Score four shots without switching, cooling down, or retaining state."""

    scores = dict(_BASE_SCORES)
    reasons: dict[FramingMode, list[FramingReasonCode]] = {
        mode: [FramingReasonCode.BASELINE_COMPANION]
        for mode in FramingMode
    }

    _score_return(context, scores, reasons)
    _score_relationship(context, scores, reasons)
    _score_emotion(context, scores, reasons)
    _score_body_requirements(context, scores, reasons)
    _score_attention(context, scores, reasons)
    _score_wellbeing_reminder(context, scores, reasons)
    _apply_close_restraint(context, scores, reasons)
    _apply_full_body_restraint(context, scores, reasons)

    bounded = {mode: _unit(score) for mode, score in scores.items()}
    confidence = _confidence(bounded)
    hold = context.speech_active and not context.mouth_closed
    return FramingPolicyResult(
        tuple(
            FramingProposal(
                mode,
                bounded[mode],
                confidence if bounded[mode] == max(bounded.values()) else _unit(confidence * 0.72),
                tuple(dict.fromkeys(reasons[mode])),
                hold,
            )
            for mode in FramingMode
        )
    )


def _score_return(context, scores, reasons) -> None:
    if not context.returned_to_seat:
        return
    if context.away_seconds >= 300.0:
        scores[FramingMode.THREE_QUARTER] += 0.24
        reasons[FramingMode.THREE_QUARTER].append(
            FramingReasonCode.RETURNED_AFTER_ABSENCE
        )
    else:
        scores[FramingMode.HALF] += 0.12
        reasons[FramingMode.HALF].append(FramingReasonCode.SHORT_RETURN)
    if context.proactive_greeting:
        scores[FramingMode.THREE_QUARTER] += 0.10
        reasons[FramingMode.THREE_QUARTER].append(
            FramingReasonCode.PROACTIVE_GREETING
        )


def _score_relationship(context, scores, reasons) -> None:
    if context.intimacy >= 0.72:
        scores[FramingMode.CLOSE] += 0.12
        scores[FramingMode.HALF] += 0.08
        reasons[FramingMode.CLOSE].append(FramingReasonCode.HIGH_INTIMACY)
    elif context.intimacy <= 0.25:
        scores[FramingMode.CLOSE] -= 0.16
        reasons[FramingMode.CLOSE].append(FramingReasonCode.LOW_INTIMACY)


def _score_emotion(context, scores, reasons) -> None:
    weighted = context.emotion_intensity
    if context.emotion_valence is EmotionValence.POSITIVE:
        scores[FramingMode.HALF] += 0.12 * weighted
        reasons[FramingMode.HALF].append(FramingReasonCode.POSITIVE_EMOTION)
    elif context.emotion_valence is EmotionValence.NEGATIVE:
        scores[FramingMode.HALF] += 0.08 * weighted
        reasons[FramingMode.HALF].append(FramingReasonCode.NEGATIVE_EMOTION)
    if weighted >= 0.78 and not context.angry_back_turn:
        scores[FramingMode.CLOSE] += 0.16
        reasons[FramingMode.CLOSE].append(FramingReasonCode.HIGH_EMOTION)
    if context.angry_back_turn:
        scores[FramingMode.THREE_QUARTER] += 0.48
        scores[FramingMode.FULL_BODY] += 0.22
        scores[FramingMode.CLOSE] -= 0.42
        reasons[FramingMode.THREE_QUARTER].append(
            FramingReasonCode.ANGRY_BACK_TURN
        )
        reasons[FramingMode.FULL_BODY].append(
            FramingReasonCode.ANGRY_BACK_TURN
        )
    if context.speech_active:
        for mode in FramingMode:
            reasons[mode].append(FramingReasonCode.SPEECH_ACTIVE)
            reasons[mode].append(FramingReasonCode.MOUTH_ACTIVE)


def _score_body_requirements(context, scores, reasons) -> None:
    gesture = context.gesture_bounds
    if gesture is not None and not _HALF_RECT.contains(gesture):
        scores[FramingMode.THREE_QUARTER] += 0.30
        reasons[FramingMode.THREE_QUARTER].append(
            FramingReasonCode.GESTURE_OUTSIDE_HALF
        )
        if not _THREE_QUARTER_RECT.contains(gesture):
            scores[FramingMode.FULL_BODY] += 0.68
            reasons[FramingMode.FULL_BODY].append(
                FramingReasonCode.GESTURE_REQUIRES_FULL
            )
    if context.weapon_or_large_prop:
        scores[FramingMode.FULL_BODY] += 0.68
        reasons[FramingMode.FULL_BODY].append(
            FramingReasonCode.WEAPON_OR_LARGE_PROP
        )
    if context.outfit_preview:
        scores[FramingMode.FULL_BODY] += 0.88
        reasons[FramingMode.FULL_BODY].append(
            FramingReasonCode.OUTFIT_PREVIEW
        )


def _score_attention(context, scores, reasons) -> None:
    if context.focus_state is FocusState.FOCUSED:
        scores[FramingMode.HALF] += 0.16
        scores[FramingMode.CLOSE] -= 0.16
        reasons[FramingMode.HALF].append(FramingReasonCode.USER_FOCUSED)
    elif context.focus_state is FocusState.DEEP_FOCUS:
        scores[FramingMode.HALF] += 0.24
        scores[FramingMode.CLOSE] -= 0.30
        if not _full_body_required(context):
            scores[FramingMode.FULL_BODY] -= 0.12
        reasons[FramingMode.HALF].append(FramingReasonCode.USER_DEEP_FOCUS)


def _score_wellbeing_reminder(context, scores, reasons) -> None:
    reminder = context.wellbeing_reminder
    if reminder is None:
        return
    if reminder.occurrence == 1:
        scores[FramingMode.HALF] += 0.28
        scores[FramingMode.CLOSE] = 0.0
        reasons[FramingMode.HALF].append(
            FramingReasonCode.FIRST_WELLBEING_REMINDER
        )
        reasons[FramingMode.CLOSE].append(
            FramingReasonCode.FIRST_WELLBEING_REMINDER
        )
        return
    eligible = bool(
        reminder.waiting_window_expired
        and not reminder.acknowledged
        and not reminder.snoozed
        and not reminder.dismissed
        and context.focus_state is FocusState.AVAILABLE
        and not reminder.in_meeting
        and not reminder.fullscreen_active
        and context.close_framing_allowed
        and reminder.proactive_care_allowed
        and reminder.variation_eligible
        and reminder.daily_used < reminder.daily_limit
        and reminder.category_used < reminder.category_limit
        and reminder.seconds_since_last_nudge >= reminder.cooldown_seconds
    )
    if eligible:
        mode, boost, kind_reason = _REPEATED_WELLBEING_FRAMING[reminder.kind]
        scores[mode] += boost
        reasons[mode].extend(
            (FramingReasonCode.REPEATED_WELLBEING_NUDGE, kind_reason)
        )
        return
    scores[FramingMode.CLOSE] = min(scores[FramingMode.CLOSE], 0.04)
    scores[FramingMode.HALF] += 0.18
    reasons[FramingMode.CLOSE].append(
        FramingReasonCode.WELLBEING_NUDGE_NOT_ELIGIBLE
    )


def _apply_close_restraint(context, scores, reasons) -> None:
    if context.close_framing_allowed:
        reasons[FramingMode.CLOSE].append(
            FramingReasonCode.CLOSE_PRIVACY_ALLOWED
        )
    else:
        scores[FramingMode.CLOSE] = min(scores[FramingMode.CLOSE], 0.04)
        reasons[FramingMode.CLOSE].append(
            FramingReasonCode.CLOSE_PRIVACY_BLOCKED
        )
    if not (
        context.intimacy >= 0.72
        and context.emotion_intensity >= 0.62
        and context.close_framing_allowed
        and context.focus_state is FocusState.AVAILABLE
        and not context.angry_back_turn
    ):
        scores[FramingMode.CLOSE] -= 0.10
        reasons[FramingMode.CLOSE].append(FramingReasonCode.CLOSE_RESTRAINED)


def _apply_full_body_restraint(context, scores, reasons) -> None:
    if not _full_body_required(context):
        scores[FramingMode.FULL_BODY] = min(scores[FramingMode.FULL_BODY], 0.14)
        reasons[FramingMode.FULL_BODY].append(
            FramingReasonCode.FULL_BODY_NOT_JUSTIFIED
        )


def _full_body_required(context: FramingPolicyContext) -> bool:
    return bool(
        context.outfit_preview
        or context.weapon_or_large_prop
        or context.angry_back_turn
        or (
            context.gesture_bounds is not None
            and not _THREE_QUARTER_RECT.contains(context.gesture_bounds)
        )
    )


def _confidence(scores: dict[FramingMode, float]) -> float:
    ranked = sorted(scores.values(), reverse=True)
    margin = ranked[0] - ranked[1]
    evidence = ranked[0]
    return _unit(0.50 + margin * 0.55 + evidence * 0.16)


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
