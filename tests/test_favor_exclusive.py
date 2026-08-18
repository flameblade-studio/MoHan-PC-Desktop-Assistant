from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.favor_exclusive import (
    FAVOR_DEVOTED_THRESHOLD,
    FAVOR_GROWTH_PER_GESTURE,
    FavorExclusiveState,
)


def test_favor_starts_at_zero() -> None:
    state = FavorExclusiveState()
    assert state.favor == 0.0
    assert not state.is_devoted


def test_gesture_grows_favor() -> None:
    state = FavorExclusiveState()
    before = state.favor
    state.note_gesture(now=0.0)
    assert state.favor - before == FAVOR_GROWTH_PER_GESTURE


def test_favor_is_bounded_at_one() -> None:
    state = FavorExclusiveState(favor=0.99)
    state.note_gesture(now=0.0)
    assert state.favor == 1.0


def test_favor_decays_slowly() -> None:
    state = FavorExclusiveState(favor=1.0)
    later = state.snapshot(now=30.0 * 24.0 * 60.0 * 60.0)
    assert 0.0 < later < 1.0


def test_devoted_threshold() -> None:
    assert FAVOR_DEVOTED_THRESHOLD == 0.7
    assert FavorExclusiveState(favor=0.71).is_devoted
    assert not FavorExclusiveState(favor=0.69).is_devoted


def test_tolerance_tracks_favor() -> None:
    state = FavorExclusiveState(favor=0.5)
    assert state.tolerance(now=0.0) == 0.5


def run() -> None:
    test_favor_starts_at_zero()
    test_gesture_grows_favor()
    test_favor_is_bounded_at_one()
    test_favor_decays_slowly()
    test_devoted_threshold()
    test_tolerance_tracks_favor()
    print("FAVOR_EXCLUSIVE_OK")


if __name__ == "__main__":
    run()
