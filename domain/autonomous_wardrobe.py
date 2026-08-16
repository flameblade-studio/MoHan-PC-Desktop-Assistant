from __future__ import annotations

lazy from dataclasses import dataclass
lazy from datetime import datetime, timedelta, timezone

lazy from domain.outfit_pack import (
    MOOD_TAGS,
    OCCASION_TAGS,
    WEATHER_TAGS,
    AutonomousStyleProfile,
)

DEFAULT_CHANGE_COOLDOWN = timedelta(hours=6)
SPECIAL_OCCASIONS = frozenset({"birthday", "christmas", "valentines"})
PROTECTIVE_WEATHER = frozenset({"rain", "storm", "snow"})


@dataclass(frozen=True, slots=True)
class WardrobeCandidate:
    outfit_id: str
    profile: AutonomousStyleProfile


@dataclass(frozen=True, slots=True)
class WardrobeContext:
    observed_at: datetime
    temperature_c: float
    weather: str
    mood: str
    occasion: str
    current_outfit_id: str
    last_changed_at: datetime | None = None
    manual_lock_until: datetime | None = None


@dataclass(frozen=True, slots=True)
class WardrobeDecision:
    outfit_id: str
    changed: bool
    reason: str
    score: int


def thermal_band(temperature_c: float) -> str:
    if temperature_c >= 30.0:
        return "hot"
    if temperature_c >= 24.0:
        return "warm"
    if temperature_c >= 18.0:
        return "mild"
    if temperature_c >= 12.0:
        return "cool"
    return "cold"


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Wardrobe timestamps must include a timezone.")
    return value.astimezone(timezone.utc)


def _validate_context(context: WardrobeContext) -> None:
    _aware_utc(context.observed_at)
    if context.weather not in WEATHER_TAGS:
        raise ValueError("Unknown weather category.")
    if context.mood not in MOOD_TAGS:
        raise ValueError("Unknown companion mood.")
    if context.occasion not in OCCASION_TAGS:
        raise ValueError("Unknown wardrobe occasion.")
    if not -80.0 <= context.temperature_c <= 70.0:
        raise ValueError("Temperature is outside the supported range.")
    for value in (context.last_changed_at, context.manual_lock_until):
        if value is not None:
            _aware_utc(value)


def _weather_fit(profile: AutonomousStyleProfile, weather: str) -> bool:
    return weather in profile.weather or "indoor" in profile.weather


def _score(
    candidate: WardrobeCandidate,
    context: WardrobeContext,
    band: str,
) -> int:
    profile = candidate.profile
    score = profile.priority
    score += 40 if context.occasion in profile.occasions else 0
    score += 30 if context.weather in profile.weather else 5
    score += 20 if context.mood in profile.moods else 0
    score += 15 if band in profile.thermal_bands else 0
    score += 2 if candidate.outfit_id == context.current_outfit_id else 0
    return score


class AutonomousWardrobeDirector:
    """Choose a validated complete outfit without hidden fallback behavior."""

    def __init__(
        self,
        change_cooldown: timedelta = DEFAULT_CHANGE_COOLDOWN,
    ) -> None:
        if change_cooldown < timedelta(0):
            raise ValueError("Wardrobe cooldown cannot be negative.")
        self.change_cooldown = change_cooldown

    def decide(
        self,
        context: WardrobeContext,
        candidates: tuple[WardrobeCandidate, ...],
    ) -> WardrobeDecision:
        _validate_context(context)
        now = _aware_utc(context.observed_at)
        if (
            context.manual_lock_until is not None
            and now < _aware_utc(context.manual_lock_until)
        ):
            return WardrobeDecision(
                context.current_outfit_id,
                False,
                "manual-lock",
                0,
            )

        band = thermal_band(context.temperature_c)
        eligible = tuple(
            candidate
            for candidate in candidates
            if band in candidate.profile.thermal_bands
            and _weather_fit(candidate.profile, context.weather)
            and (
                context.occasion in candidate.profile.occasions
                or "everyday" in candidate.profile.occasions
            )
        )
        if not eligible:
            return WardrobeDecision(
                context.current_outfit_id,
                False,
                "no-complete-match",
                0,
            )

        ranked = sorted(
            (
                (_score(candidate, context, band), candidate.outfit_id)
                for candidate in eligible
            ),
            key=lambda item: (-item[0], item[1]),
        )
        score, selected = ranked[0]
        current = next(
            (
                candidate
                for candidate in candidates
                if candidate.outfit_id == context.current_outfit_id
            ),
            None,
        )
        urgent = (
            context.occasion in SPECIAL_OCCASIONS
            or context.weather in PROTECTIVE_WEATHER
            or current is None
            or band not in current.profile.thermal_bands
            or not _weather_fit(current.profile, context.weather)
        )
        cooling_down = (
            context.last_changed_at is not None
            and now - _aware_utc(context.last_changed_at) < self.change_cooldown
        )
        if cooling_down and not urgent:
            return WardrobeDecision(
                context.current_outfit_id,
                False,
                "cooldown",
                score,
            )
        return WardrobeDecision(
            selected,
            selected != context.current_outfit_id,
            "context-match",
            score,
        )
