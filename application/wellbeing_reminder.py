from __future__ import annotations

lazy import hashlib
lazy from collections.abc import Callable, Mapping
lazy from dataclasses import dataclass
lazy from datetime import datetime
lazy from enum import StrEnum

MAX_DAILY_REINFORCEMENTS = 8
MAX_ELIGIBILITY_PERCENT = 60


class WellbeingKind(StrEnum):
    MEAL = "meal"
    HYDRATION = "hydration"
    REST = "rest"
    PROLONGED_SITTING = "prolonged_sitting"


class ReminderStage(StrEnum):
    INITIAL = "initial"
    RESTRAINED_REINFORCEMENT = "restrained_reinforcement"


class ReminderResponse(StrEnum):
    NONE = "none"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    SNOOZED = "snoozed"
    DISMISSED = "dismissed"


class ReminderExpression(StrEnum):
    GENTLE = "gentle"
    CONCERNED = "concerned"
    RESTRAINED_TSUNDERE = "restrained_tsundere"
    QUIETLY_FIRM = "quietly_firm"


class ReminderGaze(StrEnum):
    USER = "user"
    NEAR_USER = "near_user"
    BRIEFLY_AWAY = "briefly_away"


class ReminderGesture(StrEnum):
    OPEN_HAND = "open_hand"
    OFFER_CUP = "offer_cup"
    GENTLE_PAUSE = "gentle_pause"
    INVITE_TO_RISE = "invite_to_rise"


class ReminderFraming(StrEnum):
    HALF = "half"
    CLOSE_CANDIDATE = "close_candidate"
    THREE_QUARTER = "three_quarter"


@dataclass(frozen=True, slots=True)
class WellbeingRule:
    kind: WellbeingKind
    reinforcement_delay_seconds: float
    same_kind_cooldown_seconds: float
    maximum_daily_reinforcements: int
    eligibility_percent: int
    reinforcement_expression: ReminderExpression
    reinforcement_gaze: ReminderGaze
    reinforcement_gesture: ReminderGesture
    reinforcement_framing: ReminderFraming

    def __post_init__(self) -> None:
        if self.reinforcement_delay_seconds < 5.0 * 60.0:
            raise ValueError("A wellbeing reinforcement must never be immediate.")
        if self.same_kind_cooldown_seconds < self.reinforcement_delay_seconds:
            raise ValueError("A wellbeing cooldown cannot be shorter than its delay.")
        if not 1 <= self.maximum_daily_reinforcements <= MAX_DAILY_REINFORCEMENTS:
            raise ValueError("Daily wellbeing reinforcement budget is invalid.")
        if not 1 <= self.eligibility_percent <= MAX_ELIGIBILITY_PERCENT:
            raise ValueError("A reinforcement must remain occasional.")


WELLBEING_RULES: Mapping[WellbeingKind, WellbeingRule] = frozendict(
    {
        WellbeingKind.MEAL: WellbeingRule(
            WellbeingKind.MEAL,
            15.0 * 60.0,
            3.0 * 60.0 * 60.0,
            2,
            38,
            ReminderExpression.RESTRAINED_TSUNDERE,
            ReminderGaze.USER,
            ReminderGesture.OPEN_HAND,
            ReminderFraming.CLOSE_CANDIDATE,
        ),
        WellbeingKind.HYDRATION: WellbeingRule(
            WellbeingKind.HYDRATION,
            12.0 * 60.0,
            90.0 * 60.0,
            3,
            28,
            ReminderExpression.CONCERNED,
            ReminderGaze.NEAR_USER,
            ReminderGesture.OFFER_CUP,
            ReminderFraming.CLOSE_CANDIDATE,
        ),
        WellbeingKind.REST: WellbeingRule(
            WellbeingKind.REST,
            10.0 * 60.0,
            2.0 * 60.0 * 60.0,
            2,
            32,
            ReminderExpression.RESTRAINED_TSUNDERE,
            ReminderGaze.BRIEFLY_AWAY,
            ReminderGesture.GENTLE_PAUSE,
            ReminderFraming.CLOSE_CANDIDATE,
        ),
        WellbeingKind.PROLONGED_SITTING: WellbeingRule(
            WellbeingKind.PROLONGED_SITTING,
            8.0 * 60.0,
            90.0 * 60.0,
            3,
            42,
            ReminderExpression.QUIETLY_FIRM,
            ReminderGaze.USER,
            ReminderGesture.INVITE_TO_RISE,
            ReminderFraming.THREE_QUARTER,
        ),
    }
)


@dataclass(frozen=True, slots=True)
class ReminderOccurrence:
    event_id: str
    kind: WellbeingKind
    initial_delivered_at: datetime | None = None
    response: ReminderResponse = ReminderResponse.NONE
    reinforcement_delivered_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("A reminder occurrence requires a stable event identifier.")
        if self.reinforcement_delivered_at is not None and self.initial_delivered_at is None:
            raise ValueError("A reminder cannot be reinforced before its first delivery.")
        if (
            self.initial_delivered_at is not None
            and self.reinforcement_delivered_at is not None
            and self.reinforcement_delivered_at < self.initial_delivered_at
        ):
            raise ValueError("Reminder delivery history is out of order.")


@dataclass(frozen=True, slots=True)
class WellbeingContext:
    local_now: datetime
    occurrence: ReminderOccurrence
    kind_enabled: bool
    proactive_enabled: bool
    user_present: bool
    focus_protected: bool = False
    meeting_active: bool = False
    fullscreen_active: bool = False
    speech_active: bool = False
    daily_reinforcement_count: int = 0
    last_same_kind_reinforcement_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.daily_reinforcement_count < 0:
            raise ValueError("Daily reinforcement count cannot be negative.")


@dataclass(frozen=True, slots=True)
class WellbeingCue:
    event_id: str
    kind: WellbeingKind
    stage: ReminderStage
    expression: ReminderExpression
    gaze: ReminderGaze
    gesture: ReminderGesture
    framing: ReminderFraming
    line_key: str
    reason_code: str


Eligibility = Callable[[str, WellbeingKind, int], bool]


class WellbeingReminderPolicy:
    """Advance every wellbeing reminder through one quiet, bounded lifecycle."""

    def __init__(
        self,
        *,
        rules: Mapping[WellbeingKind, WellbeingRule] = WELLBEING_RULES,
        eligibility: Eligibility | None = None,
    ) -> None:
        self._rules = frozendict(rules)
        if set(self._rules) != set(WellbeingKind):
            raise ValueError("Every wellbeing reminder kind requires one rule.")
        self._eligibility = eligibility or stable_reinforcement_eligibility

    def decide(self, context: WellbeingContext) -> WellbeingCue | None:
        occurrence = context.occurrence
        if (
            not self._may_interrupt(context)
            or occurrence.response is not ReminderResponse.NONE
        ):
            return None
        if occurrence.initial_delivered_at is None:
            return self._initial(occurrence)
        if occurrence.reinforcement_delivered_at is not None:
            return None
        rule = self._rules[occurrence.kind]
        if (
            not self._reinforcement_due(context, rule)
            or not self._eligibility(
                occurrence.event_id,
                occurrence.kind,
                rule.eligibility_percent,
            )
        ):
            return None
        return self._reinforcement(occurrence, rule)

    @staticmethod
    def _may_interrupt(context: WellbeingContext) -> bool:
        return (
            context.kind_enabled
            and context.proactive_enabled
            and context.user_present
            and not context.focus_protected
            and not context.meeting_active
            and not context.fullscreen_active
            and not context.speech_active
        )

    @staticmethod
    def _reinforcement_due(
        context: WellbeingContext,
        rule: WellbeingRule,
    ) -> bool:
        occurrence = context.occurrence
        initial_at = occurrence.initial_delivered_at
        if initial_at is None:
            return False
        if context.daily_reinforcement_count >= rule.maximum_daily_reinforcements:
            return False
        if (
            context.local_now - initial_at
        ).total_seconds() < rule.reinforcement_delay_seconds:
            return False
        last_at = context.last_same_kind_reinforcement_at
        return not (
            last_at is not None
            and (
                context.local_now - last_at
            ).total_seconds() < rule.same_kind_cooldown_seconds
        )

    @staticmethod
    def _initial(occurrence: ReminderOccurrence) -> WellbeingCue:
        gestures = {
            WellbeingKind.MEAL: ReminderGesture.OPEN_HAND,
            WellbeingKind.HYDRATION: ReminderGesture.OFFER_CUP,
            WellbeingKind.REST: ReminderGesture.GENTLE_PAUSE,
            WellbeingKind.PROLONGED_SITTING: ReminderGesture.INVITE_TO_RISE,
        }
        return WellbeingCue(
            occurrence.event_id,
            occurrence.kind,
            ReminderStage.INITIAL,
            ReminderExpression.GENTLE,
            ReminderGaze.NEAR_USER,
            gestures[occurrence.kind],
            ReminderFraming.HALF,
            f"wellbeing.{occurrence.kind.value}.initial",
            "wellbeing-first-reminder",
        )

    @staticmethod
    def _reinforcement(
        occurrence: ReminderOccurrence,
        rule: WellbeingRule,
    ) -> WellbeingCue:
        return WellbeingCue(
            occurrence.event_id,
            occurrence.kind,
            ReminderStage.RESTRAINED_REINFORCEMENT,
            rule.reinforcement_expression,
            rule.reinforcement_gaze,
            rule.reinforcement_gesture,
            rule.reinforcement_framing,
            f"wellbeing.{occurrence.kind.value}.restrained_reinforcement",
            "wellbeing-unanswered-reinforcement",
        )


def stable_reinforcement_eligibility(
    event_id: str,
    kind: WellbeingKind,
    eligibility_percent: int,
) -> bool:
    """Make occasional behavior stable across restarts and deterministic tests."""

    payload = f"mohan-wellbeing-v1\0{kind.value}\0{event_id}".encode()
    digest = hashlib.blake2s(payload, digest_size=4).digest()
    bucket = int.from_bytes(digest, "big") % 100
    return bucket < eligibility_percent
