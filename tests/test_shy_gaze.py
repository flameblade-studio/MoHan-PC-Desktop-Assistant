from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.shy_gaze import (
    AVERSION_HOLD_SECONDS,
    AVERSION_OFFSET_X,
    AVERSION_OFFSET_Y,
    STARE_THRESHOLD_SECONDS,
    ShyGazeState,
)


def test_no_aversion_before_threshold() -> None:
    state = ShyGazeState()
    # The user looks for a moment, but not long enough to trigger shyness.
    assert state.update(gaze_confidence=0.9, now=0.0) is None
    assert state.update(gaze_confidence=0.9, now=STARE_THRESHOLD_SECONDS - 0.5) is None


def test_aversion_triggers_after_sustained_stare() -> None:
    state = ShyGazeState()
    state.update(gaze_confidence=0.9, now=0.0)
    offset = state.update(gaze_confidence=0.9, now=STARE_THRESHOLD_SECONDS)
    assert offset is not None
    x, y = offset
    # The offset is small and downward, never a large lateral eye-roll.
    assert abs(x) == AVERSION_OFFSET_X
    assert y == AVERSION_OFFSET_Y


def test_aversion_holds_for_three_seconds() -> None:
    state = ShyGazeState()
    state.update(gaze_confidence=0.9, now=0.0)
    trigger_at = STARE_THRESHOLD_SECONDS
    state.update(gaze_confidence=0.9, now=trigger_at)
    # Still averting shortly after the trigger.
    assert state.update(gaze_confidence=0.9, now=trigger_at + 1.0) is not None
    # Released after the hold duration.
    assert state.update(gaze_confidence=0.9, now=trigger_at + AVERSION_HOLD_SECONDS + 0.1) is None


def test_looking_away_resets_the_stare() -> None:
    state = ShyGazeState()
    state.update(gaze_confidence=0.9, now=0.0)
    # The user looks away before the threshold, resetting the timer.
    state.update(gaze_confidence=0.1, now=2.0)
    # A fresh stare must start over.
    assert state.update(gaze_confidence=0.9, now=3.0) is None
    assert state.update(gaze_confidence=0.9, now=3.0 + STARE_THRESHOLD_SECONDS - 0.5) is None


def test_aversion_alternates_sides() -> None:
    state = ShyGazeState()
    state.update(gaze_confidence=0.9, now=0.0)
    first = state.update(gaze_confidence=0.9, now=STARE_THRESHOLD_SECONDS)
    # Let the first aversion expire.
    state.update(gaze_confidence=0.9, now=STARE_THRESHOLD_SECONDS + AVERSION_HOLD_SECONDS + 0.1)
    # Trigger a second stare.
    state.update(gaze_confidence=0.9, now=STARE_THRESHOLD_SECONDS + AVERSION_HOLD_SECONDS + 0.2)
    second = state.update(
        gaze_confidence=0.9,
        now=STARE_THRESHOLD_SECONDS + AVERSION_HOLD_SECONDS + 0.2 + STARE_THRESHOLD_SECONDS,
    )
    assert first is not None and second is not None
    assert first[0] == -second[0]


def run() -> None:
    test_no_aversion_before_threshold()
    test_aversion_triggers_after_sustained_stare()
    test_aversion_holds_for_three_seconds()
    test_looking_away_resets_the_stare()
    test_aversion_alternates_sides()
    print("SHY_GAZE_OK")


if __name__ == "__main__":
    run()
