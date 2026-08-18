from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.time_sovereignty import (
    BLINK_INTERVAL_ALERT,
    BLINK_INTERVAL_DROWSY,
    TimeSovereigntyState,
    is_late_night,
)


def test_late_night_window() -> None:
    assert is_late_night(2)
    assert is_late_night(3)
    assert is_late_night(4)
    assert not is_late_night(1)
    assert not is_late_night(5)
    assert not is_late_night(12)


def test_drowsiness_starts_alert() -> None:
    state = TimeSovereigntyState()
    assert state.drowsiness == 0.0
    assert state.blink_interval() == BLINK_INTERVAL_ALERT


def test_drowsiness_rises_during_late_night() -> None:
    state = TimeSovereigntyState()
    for step in range(200):
        state.update(hour=3, now=float(step))
    assert state.drowsiness > 0.5
    assert state.blink_interval() > BLINK_INTERVAL_ALERT


def test_drowsiness_eases_smoothly_without_snapping() -> None:
    state = TimeSovereigntyState()
    first = state.update(hour=3, now=0.0)
    assert first < 0.5, "drowsiness must ease in, not snap"


def test_drowsiness_decays_outside_late_night() -> None:
    state = TimeSovereigntyState()
    for step in range(200):
        state.update(hour=3, now=float(step))
    assert state.drowsiness > 0.5
    for step in range(400):
        state.update(hour=10, now=200.0 + float(step))
    assert state.drowsiness < 0.1
    assert state.blink_interval() < BLINK_INTERVAL_DROWSY


def test_blink_interval_stays_within_bounds() -> None:
    state = TimeSovereigntyState()
    for step in range(1000):
        state.update(hour=3, now=float(step))
    interval = state.blink_interval()
    assert BLINK_INTERVAL_ALERT <= interval <= BLINK_INTERVAL_DROWSY


def run() -> None:
    test_late_night_window()
    test_drowsiness_starts_alert()
    test_drowsiness_rises_during_late_night()
    test_drowsiness_eases_smoothly_without_snapping()
    test_drowsiness_decays_outside_late_night()
    test_blink_interval_stays_within_bounds()
    print("TIME_SOVEREIGNTY_OK")


if __name__ == "__main__":
    run()
