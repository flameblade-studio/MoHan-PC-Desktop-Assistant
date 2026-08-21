from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.sword_soul_resonance import (
    AWAKENED_THRESHOLD,
    SwordSoulResonanceState,
)

AWAKENING_THRESHOLD = 0.6


def test_awakening_starts_at_zero() -> None:
    state = SwordSoulResonanceState()
    assert state.awakening == 0.0
    assert not state.is_awakened


def test_awakening_grows_with_days_and_commits() -> None:
    state = SwordSoulResonanceState(days=45.0, commits=150)
    assert 0.0 < state.awakening < 1.0


def test_awakening_is_monotonic() -> None:
    state = SwordSoulResonanceState()
    before = state.awakening
    state.update(days=90.0, commits=300)
    assert state.awakening >= before
    # Updating with smaller values must not regress.
    state.update(days=1.0, commits=1)
    assert state.awakening == 1.0


def test_awakened_threshold() -> None:
    assert AWAKENED_THRESHOLD == AWAKENING_THRESHOLD
    assert SwordSoulResonanceState(days=90.0, commits=300).is_awakened
    assert not SwordSoulResonanceState(days=10.0, commits=10).is_awakened


def test_gaze_linger_tracks_awakening() -> None:
    state = SwordSoulResonanceState(days=90.0, commits=300)
    assert state.gaze_linger() == 1.0


def run() -> None:
    test_awakening_starts_at_zero()
    test_awakening_grows_with_days_and_commits()
    test_awakening_is_monotonic()
    test_awakened_threshold()
    test_gaze_linger_tracks_awakening()
    print("SWORD_SOUL_RESONANCE_OK")


if __name__ == "__main__":
    run()
