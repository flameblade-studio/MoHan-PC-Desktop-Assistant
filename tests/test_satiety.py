from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.satiety import (
    BLINK_INTERVAL_FULL,
    BLINK_INTERVAL_STARVING,
    SATIETY_GAIN_PER_RATION,
    SATIETY_HUNGRY_THRESHOLD,
    SatietyState,
)

HUNGRY_THRESHOLD = 0.3


def test_satiety_starts_full() -> None:
    state = SatietyState()
    assert state.satiety == 1.0
    assert not state.is_hungry
    assert state.blink_interval(now=0.0) == BLINK_INTERVAL_FULL


def test_feeding_raises_satiety() -> None:
    state = SatietyState(satiety=0.5)
    before = state.satiety
    state.feed(now=0.0)
    assert state.satiety - before == SATIETY_GAIN_PER_RATION


def test_satiety_is_bounded_at_one() -> None:
    state = SatietyState(satiety=0.9)
    state.feed(now=0.0)
    assert state.satiety == 1.0


def test_satiety_decays_over_time() -> None:
    state = SatietyState(clock=lambda: 0.0, satiety=1.0)
    # One day later, satiety has decayed but not to zero.
    later = state.snapshot(now=24.0 * 60.0 * 60.0)
    assert 0.0 < later < 1.0


def test_hungry_state_slows_blink() -> None:
    state = SatietyState(satiety=0.1)
    assert state.is_hungry
    assert state.blink_interval(now=0.0) > BLINK_INTERVAL_FULL
    assert state.blink_interval(now=0.0) <= BLINK_INTERVAL_STARVING


def test_hungry_threshold() -> None:
    assert SATIETY_HUNGRY_THRESHOLD == HUNGRY_THRESHOLD
    assert SatietyState(satiety=0.29).is_hungry
    assert not SatietyState(satiety=0.31).is_hungry


def run() -> None:
    test_satiety_starts_full()
    test_feeding_raises_satiety()
    test_satiety_is_bounded_at_one()
    test_satiety_decays_over_time()
    test_hungry_state_slows_blink()
    test_hungry_threshold()
    print("SATIETY_OK")


if __name__ == "__main__":
    run()
