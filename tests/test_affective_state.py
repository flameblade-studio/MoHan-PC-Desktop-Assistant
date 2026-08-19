from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.affective_state import (
    DEFAULT_RESIDUE_HALF_LIFE_SECONDS,
    RESIDUAL_EXPRESSION,
    AffectiveResidue,
    AffectiveState,
)


def test_residue_decays_exponentially_and_fades() -> None:
    state = AffectiveState()
    state.note_expression("shy", intensity=0.8, now=0.0)
    # Immediately after the shy expression, a softer shy residue lingers.
    assert state.residual_expression(now=0.0) == "shy_cute_front"
    # After one half-life the strength halves but is still above the floor.
    assert state.residual_expression(now=DEFAULT_RESIDUE_HALF_LIFE_SECONDS) == "shy_cute_front"
    # Far in the future the residue has fully faded.
    assert state.residual_expression(now=1_000.0) is None


def test_weak_expression_leaves_no_residue() -> None:
    state = AffectiveState()
    state.note_expression("happy", intensity=0.05, now=0.0)
    assert state.residual_expression(now=0.0) is None


def test_non_expressive_state_leaves_no_residue() -> None:
    state = AffectiveState()
    state.note_expression("idle", intensity=0.9, now=0.0)
    assert state.residual_expression(now=0.0) is None
    state.note_expression("speaking", intensity=0.9, now=0.0)
    assert state.residual_expression(now=0.0) is None


def test_new_expression_replaces_previous_residue() -> None:
    state = AffectiveState()
    state.note_expression("shy", intensity=0.8, now=0.0)
    state.note_expression("happy", intensity=0.9, now=1.0)
    assert state.residual_expression(now=1.0) == "gentle_smile_front"


def test_clear_removes_residue() -> None:
    state = AffectiveState()
    state.note_expression("worried", intensity=0.7, now=0.0)
    assert state.residual_expression(now=0.0) == "worried_front"
    state.clear()
    assert state.residual_expression(now=0.0) is None


def test_residue_strength_at_is_monotonic() -> None:
    residue = AffectiveResidue("gentle_smile_front", 1.0, 6.0, 0.0)
    early = residue.strength_at(1.0)
    late = residue.strength_at(5.0)
    assert 0.0 < late < early <= 1.0


def test_invalid_half_life_is_rejected() -> None:
    try:
        AffectiveState(half_life_seconds=0.0)
    except ValueError:
        pass
    else:
        raise AssertionError("zero half-life must be rejected")


def test_residual_mapping_covers_common_emotions() -> None:
    for emotion in ("happy", "shy", "worried", "proud", "surprised", "caught"):
        assert emotion in RESIDUAL_EXPRESSION


def run() -> None:
    test_residue_decays_exponentially_and_fades()
    test_weak_expression_leaves_no_residue()
    test_non_expressive_state_leaves_no_residue()
    test_new_expression_replaces_previous_residue()
    test_clear_removes_residue()
    test_residue_strength_at_is_monotonic()
    test_invalid_half_life_is_rejected()
    test_residual_mapping_covers_common_emotions()
    print("AFFECTIVE_STATE_OK")


if __name__ == "__main__":
    run()
