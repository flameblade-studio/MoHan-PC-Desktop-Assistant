from __future__ import annotations

lazy import sys
lazy from datetime import UTC, datetime
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from application.autonomous_wardrobe_runtime import (
    AutonomousWardrobeRuntime,
    WardrobeSituation,
)
lazy from application.outfit_reveal import OutfitRevealStateStore
lazy from domain.autonomous_wardrobe import WardrobeCandidate
lazy from domain.outfit_pack import AutonomousStyleProfile


class Settings:
    def __init__(self) -> None:
        self.values: dict[str, object] = {
            "active_outfit_id": "old",
        }

    def read(self, keys: tuple[str, ...]) -> dict[str, object]:
        return {key: self.values[key] for key in keys if key in self.values}

    def write(self, values) -> None:
        self.values.update(values)


class Wardrobe:
    def __init__(self) -> None:
        self.applied: list[str] = []

    @staticmethod
    def selected_outfit(value: object) -> str:
        return str(value or "builtin")

    def autonomous_candidates(self) -> tuple[WardrobeCandidate, ...]:
        profile = AutonomousStyleProfile(
            frozenset({"hot"}),
            frozenset({"clear", "indoor"}),
            frozenset({"calm"}),
            frozenset({"everyday"}),
            10,
        )
        return (WardrobeCandidate("modern-summer", profile),)

    def apply(self, outfit_id: str) -> None:
        self.applied.append(outfit_id)


def run() -> None:
    settings = Settings()
    wardrobe = Wardrobe()
    runtime = AutonomousWardrobeRuntime(
        wardrobe,
        settings,
        OutfitRevealStateStore(settings),
    )
    decision = runtime.evaluate(
        WardrobeSituation(
            datetime(2027, 7, 1, 10, tzinfo=UTC),
            33.0,
            "clear",
            "calm",
            "everyday",
        )
    )
    assert decision.changed
    assert wardrobe.applied == ["modern-summer"]
    assert settings.values["active_outfit_id"] == "modern-summer"
    assert settings.values["wardrobe_reveal_pending_outfit_id"] == "modern-summer"
    print("AUTONOMOUS_WARDROBE_RUNTIME_OK")


if __name__ == "__main__":
    run()
