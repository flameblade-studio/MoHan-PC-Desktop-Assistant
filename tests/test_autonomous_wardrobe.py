from __future__ import annotations

lazy import sys
lazy from datetime import datetime, timedelta, timezone
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.autonomous_wardrobe import (
    AutonomousWardrobeDirector,
    WardrobeCandidate,
    WardrobeContext,
    thermal_band,
)
lazy from domain.outfit_pack import AutonomousStyleProfile


NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)


def profile(
    thermal: tuple[str, ...],
    weather: tuple[str, ...],
    moods: tuple[str, ...],
    occasions: tuple[str, ...] = ("everyday",),
    priority: int = 0,
) -> AutonomousStyleProfile:
    return AutonomousStyleProfile(
        frozenset(thermal),
        frozenset(weather),
        frozenset(moods),
        frozenset(occasions),
        priority,
    )


def context(**changes: object) -> WardrobeContext:
    values: dict[str, object] = {
        "observed_at": NOW,
        "temperature_c": 33.0,
        "weather": "clear",
        "mood": "cheerful",
        "occasion": "everyday",
        "current_outfit_id": "formal",
        "last_changed_at": NOW - timedelta(hours=8),
        "manual_lock_until": None,
    }
    values.update(changes)
    return WardrobeContext(**values)


def run() -> None:
    assert tuple(thermal_band(value) for value in (31, 26, 20, 14, 5)) == (
        "hot", "warm", "mild", "cool", "cold"
    )
    summer = WardrobeCandidate(
        "summer",
        profile(("hot",), ("clear", "indoor"), ("cheerful", "affectionate")),
    )
    reserved = WardrobeCandidate(
        "reserved",
        profile(("hot",), ("clear", "indoor"), ("reserved", "upset"), priority=5),
    )
    rain = WardrobeCandidate(
        "rain",
        profile(("hot", "warm"), ("rain", "storm"), ("calm", "focused")),
    )
    director = AutonomousWardrobeDirector()
    assert director.decide(context(), (summer, reserved, rain)).outfit_id == "summer"
    upset = director.decide(
        context(mood="upset"),
        (summer, reserved, rain),
    )
    assert upset.outfit_id == "reserved" and upset.changed
    locked = director.decide(
        context(manual_lock_until=NOW + timedelta(hours=2)),
        (summer, reserved, rain),
    )
    assert locked.outfit_id == "formal" and locked.reason == "manual-lock"
    cooling = director.decide(
        context(
            current_outfit_id="summer",
            last_changed_at=NOW - timedelta(minutes=10),
            mood="upset",
        ),
        (summer, reserved, rain),
    )
    assert cooling.outfit_id == "summer" and cooling.reason == "cooldown"
    urgent = director.decide(
        context(
            weather="rain",
            current_outfit_id="summer",
            last_changed_at=NOW - timedelta(minutes=10),
        ),
        (summer, reserved, rain),
    )
    assert urgent.outfit_id == "rain" and urgent.changed
    absent = director.decide(context(), ())
    assert absent.outfit_id == "formal" and absent.reason == "no-complete-match"
    print("AUTONOMOUS_WARDROBE_OK")


if __name__ == "__main__":
    run()
