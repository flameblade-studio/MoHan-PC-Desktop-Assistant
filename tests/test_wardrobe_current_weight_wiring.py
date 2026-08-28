from __future__ import annotations

lazy import sys
lazy from datetime import UTC, datetime
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.autonomous_wardrobe_runtime import (
    AutonomousWardrobeRuntime,
    WardrobeSituation,
)
lazy from application.outfit_reveal import OutfitRevealStateStore
lazy from domain.autonomous_wardrobe import WardrobeCandidate, thermal_band
lazy from domain.constants import (
    DEFAULT_WEATHER_CONDITION,
    DEFAULT_WEATHER_TEMPERATURE_C,
)
lazy from domain.outfit_pack import WEATHER_TAGS, AutonomousStyleProfile
lazy from domain.wardrobe_intuition import (
    OutfitWeight,
    weight_for_thermal_bands,
)


class Settings:
    def __init__(self) -> None:
        self.values: dict[str, object] = {"active_outfit_id": "old"}

    def read(self, keys: tuple[str, ...]) -> dict[str, object]:
        return {key: self.values[key] for key in keys if key in self.values}

    def write(self, values) -> None:
        self.values.update(values)


class Wardrobe:
    def __init__(self, candidates: tuple[WardrobeCandidate, ...]) -> None:
        self.applied: list[str] = []
        self._candidates = candidates

    @staticmethod
    def selected_outfit(value: object) -> str:
        return str(value or "builtin")

    def autonomous_candidates(self) -> tuple[WardrobeCandidate, ...]:
        return self._candidates

    def apply(self, outfit_id: str) -> None:
        self.applied.append(outfit_id)


def _profile(bands: frozenset[str]) -> AutonomousStyleProfile:
    return AutonomousStyleProfile(
        bands,
        frozenset({"clear", "indoor"}),
        frozenset({"calm"}),
        frozenset({"everyday"}),
        10,
    )


def test_weight_for_thermal_bands_maps_extremes_and_versatility() -> None:
    assert weight_for_thermal_bands(frozenset({"hot"})) is OutfitWeight.LIGHT
    assert weight_for_thermal_bands(frozenset({"hot", "warm"})) is (
        OutfitWeight.LIGHT
    )
    assert weight_for_thermal_bands(frozenset({"cold"})) is OutfitWeight.WARM
    assert weight_for_thermal_bands(frozenset({"cool", "mild"})) is (
        OutfitWeight.WARM
    )
    assert weight_for_thermal_bands(frozenset({"warm", "mild"})) is (
        OutfitWeight.MODERATE
    )
    assert weight_for_thermal_bands(frozenset({"hot", "cold"})) is (
        OutfitWeight.MODERATE
    )


def test_runtime_persists_current_outfit_weight_on_change() -> None:
    settings = Settings()
    candidates = (WardrobeCandidate("modern-summer", _profile(frozenset({"hot"}))),)
    runtime = AutonomousWardrobeRuntime(
        Wardrobe(candidates),
        settings,
        OutfitRevealStateStore(settings),
    )
    decision = runtime.evaluate(
        WardrobeSituation(
            datetime(2027, 7, 1, 10, tzinfo=UTC), 33.0, "clear", "calm", "everyday"
        )
    )
    assert decision.changed
    assert settings.values["wardrobe_current_weight"] == "light"


def test_runtime_persists_weight_even_without_an_outfit_change() -> None:
    settings = Settings()
    settings.values["active_outfit_id"] = "winter-cloak"
    candidates = (
        WardrobeCandidate("winter-cloak", _profile(frozenset({"cold", "cool"}))),
    )
    runtime = AutonomousWardrobeRuntime(
        Wardrobe(candidates),
        settings,
        OutfitRevealStateStore(settings),
    )
    decision = runtime.evaluate(
        WardrobeSituation(
            datetime(2027, 1, 5, 10, tzinfo=UTC), 2.0, "clear", "calm", "everyday"
        )
    )
    assert not decision.changed
    assert settings.values["wardrobe_current_weight"] == "warm"


def test_weather_defaults_are_one_consistent_indoor_scene() -> None:
    expected_default_temperature_c = 24.0
    assert DEFAULT_WEATHER_CONDITION == "indoor"
    assert DEFAULT_WEATHER_CONDITION in WEATHER_TAGS
    assert DEFAULT_WEATHER_TEMPERATURE_C == expected_default_temperature_c
    assert thermal_band(DEFAULT_WEATHER_TEMPERATURE_C) == "warm"
