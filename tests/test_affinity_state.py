from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.affinity_state import (
    AFFECTION_BOOST_PER_GESTURE,
    AFFINITY_ACQUAINTED,
    AFFINITY_CLOSE,
    AFFINITY_DEVOTED,
    AffinityState,
)


def test_affinity_grows_with_interaction() -> None:
    state = AffinityState()
    assert state.affinity == 0.0
    assert state.interaction_count == 0
    for _ in range(10):
        state.note_interaction(now=0.0)
    assert state.affinity > 0.0
    assert state.interaction_count == 10


def test_affinity_stage_progresses() -> None:
    state = AffinityState()
    assert state.snapshot(now=0.0).stage == "stranger"
    for _ in range(20):
        state.note_interaction(now=0.0)
    assert state.snapshot(now=0.0).stage in {"acquainted", "close"}


def test_jealousy_spikes_and_fades() -> None:
    state = AffinityState()
    assert state.jealousy == 0.0
    state.note_jealousy(now=0.0)
    assert state.jealousy > 0.5
    # Far in the future the jealousy has faded.
    assert state.snapshot(now=10_000.0).jealousy < 0.1


def test_jealousy_lingers_for_minutes() -> None:
    # A tsundere's pout must hold for several minutes, not vanish in a second.
    state = AffinityState()
    state.note_jealousy(now=0.0)
    # After two minutes the jealousy is still clearly present.
    assert state.snapshot(now=120.0).jealousy > 0.5
    # After ten minutes (one half-life) it has decayed but not to zero.
    later = state.snapshot(now=600.0).jealousy
    assert 0.2 < later < 0.5


def test_affection_boost_is_larger_than_routine_interaction() -> None:
    state = AffinityState()
    state.note_interaction(now=0.0)
    routine = state.affinity
    state.note_affection_boost(now=0.0)
    assert state.affinity - routine == AFFECTION_BOOST_PER_GESTURE


def test_affinity_decays_slowly_over_time() -> None:
    state = AffinityState()
    for _ in range(10):
        state.note_interaction(now=0.0)
    before = state.affinity
    # One week later, affinity has decayed but not to zero.
    later = state.snapshot(now=7.0 * 24.0 * 60.0 * 60.0).affinity
    assert 0.0 < later < before


def test_invalid_affinity_is_rejected() -> None:
    try:
        AffinityState(affinity=1.5)
    except ValueError:
        pass
    else:
        raise AssertionError("affinity above 1.0 must be rejected")


def run() -> None:
    test_affinity_grows_with_interaction()
    test_affinity_stage_progresses()
    test_jealousy_spikes_and_fades()
    test_jealousy_lingers_for_minutes()
    test_affection_boost_is_larger_than_routine_interaction()
    test_affinity_decays_slowly_over_time()
    test_invalid_affinity_is_rejected()
    print("AFFINITY_STATE_OK")


if __name__ == "__main__":
    run()
