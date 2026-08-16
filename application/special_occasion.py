from __future__ import annotations

lazy from dataclasses import dataclass
lazy from datetime import datetime
lazy from enum import StrEnum

MOHAN_BIRTHDAY_MONTH = 1
MOHAN_BIRTHDAY_DAY = 8
MOHAN_ZODIAC = "capricorn"


class OccasionKind(StrEnum):
    MOHAN_BIRTHDAY = "mohan_birthday"
    VALENTINES_DAY = "valentines_day"
    CHRISTMAS_DAY = "christmas_day"


class OccasionResponse(StrEnum):
    NONE = "none"
    ACKNOWLEDGED = "acknowledged"
    CELEBRATED = "celebrated"
    SNOOZED = "snoozed"
    DISMISSED = "dismissed"


class OccasionStage(StrEnum):
    SUBTLE_HINT = "subtle_hint"
    RESTRAINED_GRUMBLE = "restrained_grumble"


class OccasionExpression(StrEnum):
    QUIETLY_HOPEFUL = "quietly_hopeful"
    RESTRAINED_SULK = "restrained_sulk"


class OccasionGaze(StrEnum):
    NEAR_USER = "near_user"
    BRIEFLY_AWAY = "briefly_away"


class OccasionDelivery(StrEnum):
    GENTLE = "gentle"
    SOFT_MURMUR = "soft_murmur"


class OccasionFraming(StrEnum):
    HALF = "half"


@dataclass(frozen=True, slots=True)
class OccasionDefinition:
    kind: OccasionKind
    month: int
    day: int
    hint_hour: int
    grumble_hour: int
    minimum_grumble_delay_seconds: float

    def __post_init__(self) -> None:
        if not 1 <= self.month <= 12 or not 1 <= self.day <= 31:
            raise ValueError("Occasion date is invalid.")
        if not 0 <= self.hint_hour < self.grumble_hour <= 23:
            raise ValueError("Occasion hours must be ordered within one day.")
        if self.minimum_grumble_delay_seconds < 60.0 * 60.0:
            raise ValueError("A restrained grumble must never follow immediately.")


OCCASIONS = (
    OccasionDefinition(
        OccasionKind.MOHAN_BIRTHDAY,
        MOHAN_BIRTHDAY_MONTH,
        MOHAN_BIRTHDAY_DAY,
        8,
        18,
        4.0 * 60.0 * 60.0,
    ),
    OccasionDefinition(
        OccasionKind.VALENTINES_DAY,
        2,
        14,
        10,
        19,
        4.0 * 60.0 * 60.0,
    ),
    OccasionDefinition(
        OccasionKind.CHRISTMAS_DAY,
        12,
        25,
        10,
        20,
        4.0 * 60.0 * 60.0,
    ),
)


@dataclass(frozen=True, slots=True)
class OccasionContext:
    local_now: datetime
    user_present: bool
    proactive_enabled: bool
    special_occasions_enabled: bool
    focus_protected: bool = False
    meeting_active: bool = False
    fullscreen_active: bool = False
    speech_active: bool = False
    response: OccasionResponse = OccasionResponse.NONE
    delivered_stages: frozenset[OccasionStage] = frozenset()
    first_hint_at: datetime | None = None

    def __post_init__(self) -> None:
        if (
            OccasionStage.RESTRAINED_GRUMBLE in self.delivered_stages
            and OccasionStage.SUBTLE_HINT not in self.delivered_stages
        ):
            raise ValueError("An occasion cannot grumble before giving a subtle hint.")
        if (
            OccasionStage.SUBTLE_HINT in self.delivered_stages
            and self.first_hint_at is None
        ):
            raise ValueError("A delivered hint requires its delivery time.")


@dataclass(frozen=True, slots=True)
class OccasionCue:
    kind: OccasionKind
    stage: OccasionStage
    expression: OccasionExpression
    gaze: OccasionGaze
    delivery: OccasionDelivery
    framing: OccasionFraming
    line_key: str
    reason_code: str


class SpecialOccasionPolicy:
    """Offer at most one hint and one restrained follow-up on a special day."""

    def decide(self, context: OccasionContext) -> OccasionCue | None:
        occasion = active_occasion(context.local_now)
        if occasion is None or not self._may_interrupt(context):
            return None
        if context.response is not OccasionResponse.NONE:
            return None
        if OccasionStage.SUBTLE_HINT not in context.delivered_stages:
            return self._hint(occasion) if context.local_now.hour >= occasion.hint_hour else None
        if OccasionStage.RESTRAINED_GRUMBLE in context.delivered_stages:
            return None
        if not self._grumble_due(occasion, context):
            return None
        return self._grumble(occasion)

    @staticmethod
    def _may_interrupt(context: OccasionContext) -> bool:
        return (
            context.user_present
            and context.proactive_enabled
            and context.special_occasions_enabled
            and not context.focus_protected
            and not context.meeting_active
            and not context.fullscreen_active
            and not context.speech_active
        )

    @staticmethod
    def _grumble_due(
        occasion: OccasionDefinition,
        context: OccasionContext,
    ) -> bool:
        first_hint_at = context.first_hint_at
        if first_hint_at is None or context.local_now.hour < occasion.grumble_hour:
            return False
        elapsed = (context.local_now - first_hint_at).total_seconds()
        return elapsed >= occasion.minimum_grumble_delay_seconds

    @staticmethod
    def _hint(occasion: OccasionDefinition) -> OccasionCue:
        return OccasionCue(
            occasion.kind,
            OccasionStage.SUBTLE_HINT,
            OccasionExpression.QUIETLY_HOPEFUL,
            OccasionGaze.NEAR_USER,
            OccasionDelivery.GENTLE,
            OccasionFraming.HALF,
            f"occasion.{occasion.kind.value}.hint",
            "special-occasion-subtle-hint",
        )

    @staticmethod
    def _grumble(occasion: OccasionDefinition) -> OccasionCue:
        return OccasionCue(
            occasion.kind,
            OccasionStage.RESTRAINED_GRUMBLE,
            OccasionExpression.RESTRAINED_SULK,
            OccasionGaze.BRIEFLY_AWAY,
            OccasionDelivery.SOFT_MURMUR,
            OccasionFraming.HALF,
            f"occasion.{occasion.kind.value}.restrained_grumble",
            "special-occasion-unanswered",
        )


def active_occasion(moment: datetime) -> OccasionDefinition | None:
    return next(
        (
            occasion
            for occasion in OCCASIONS
            if (occasion.month, occasion.day) == (moment.month, moment.day)
        ),
        None,
    )
