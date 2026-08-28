from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass
lazy from datetime import datetime
lazy from typing import Protocol

lazy from application.outfit_reveal import OutfitRevealStateStore
lazy from application.wardrobe_service import WardrobeService
lazy from domain.autonomous_wardrobe import (
    AutonomousWardrobeDirector,
    WardrobeCandidate,
    WardrobeContext,
    WardrobeDecision,
)
lazy from domain.wardrobe_intuition import weight_for_thermal_bands

ACTIVE_OUTFIT_KEY = "active_outfit_id"
LAST_CHANGED_KEY = "wardrobe_last_changed_at"
MANUAL_LOCK_KEY = "wardrobe_manual_lock_until"
CURRENT_WEIGHT_KEY = "wardrobe_current_weight"


class WardrobeRuntimeSettingsPort(Protocol):
    def read(self, keys: tuple[str, ...]) -> Mapping[str, object]:
        raise NotImplementedError

    def write(self, values: Mapping[str, object]) -> None:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class WardrobeSituation:
    observed_at: datetime
    temperature_c: float
    weather: str
    mood: str
    occasion: str


class AutonomousWardrobeRuntime:
    """Apply one validated contextual ensemble and queue one natural reveal."""

    def __init__(
        self,
        service: WardrobeService,
        settings: WardrobeRuntimeSettingsPort,
        reveals: OutfitRevealStateStore,
        director: AutonomousWardrobeDirector | None = None,
    ) -> None:
        self._service = service
        self._settings = settings
        self._reveals = reveals
        self._director = director or AutonomousWardrobeDirector()

    def evaluate(self, situation: WardrobeSituation) -> WardrobeDecision:
        values = self._settings.read(
            (ACTIVE_OUTFIT_KEY, LAST_CHANGED_KEY, MANUAL_LOCK_KEY)
        )
        # Persist the observed weather so the companion's wardrobe intuition and
        # sensory synesthesia can read the same temperature/condition snapshot.
        self._settings.write(
            {
                "weather_temperature_c": situation.temperature_c,
                "weather_condition": situation.weather,
            }
        )
        current = str(values.get(ACTIVE_OUTFIT_KEY, "") or "").strip()
        if not current:
            current = self._service.selected_outfit(current)
        candidates = self._service.autonomous_candidates()
        decision = self._director.decide(
            WardrobeContext(
                observed_at=situation.observed_at,
                temperature_c=situation.temperature_c,
                weather=situation.weather,
                mood=situation.mood,
                occasion=situation.occasion,
                current_outfit_id=current,
                last_changed_at=_optional_datetime(values.get(LAST_CHANGED_KEY)),
                manual_lock_until=_optional_datetime(values.get(MANUAL_LOCK_KEY)),
            ),
            candidates,
        )
        self._persist_current_weight(decision.outfit_id, candidates)
        if not decision.changed:
            return decision
        self._service.apply(decision.outfit_id)
        self._settings.write(
            {
                ACTIVE_OUTFIT_KEY: decision.outfit_id,
                LAST_CHANGED_KEY: situation.observed_at.isoformat(),
            }
        )
        self._reveals.mark_pending(decision.outfit_id)
        return decision

    def _persist_current_weight(
        self,
        outfit_id: str,
        candidates: tuple[WardrobeCandidate, ...],
    ) -> None:
        """Record the worn outfit's weight for the comfort-complaint intuition.

        ``wardrobe_current_weight`` previously had no writer, so the
        too-hot/too-cold complaint could never trigger for autonomous outfits.
        The weight is derived from the outfit's own thermal-band profile.
        """
        profile = next(
            (
                candidate.profile
                for candidate in candidates
                if candidate.outfit_id == outfit_id
            ),
            None,
        )
        if profile is None:
            return
        self._settings.write(
            {
                CURRENT_WEIGHT_KEY: weight_for_thermal_bands(
                    profile.thermal_bands
                ).value
            }
        )


def _optional_datetime(value: object) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        raise ValueError("Saved wardrobe timestamp is invalid.") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Saved wardrobe timestamp must include a timezone.")
    return parsed
