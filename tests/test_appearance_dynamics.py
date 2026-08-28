from __future__ import annotations

lazy import math
lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.appearance_dynamics import (
    IDENTITY_TRANSFORM,
    AppearanceDynamics,
    AppearanceDynamicsError,
    DynamicsConfiguration,
    DynamicsInput,
    DynamicsMode,
    MotionGroup,
    motion_group_for_slot,
)

EXPECTED_TICK_COUNT = 20
MAX_SUBSTEPS = 3
MOTION_GROUP_COUNT = 4
SCALE_Y_LOWER = 0.99
SCALE_Y_UPPER = 1.01


def _enabled(mode: DynamicsMode = DynamicsMode.FULL) -> DynamicsConfiguration:
    return DynamicsConfiguration(enabled=True, mode=mode)


def test_disabled_unavailable_and_static_modes_are_exact_fallbacks() -> None:
    engines = (
        AppearanceDynamics(),
        AppearanceDynamics(_enabled(), backend_available=False),
        AppearanceDynamics(_enabled(DynamicsMode.STATIC)),
    )
    for engine in engines:
        frame = engine.advance(DynamicsInput(10.0, motion_x=100.0, gravity_x=-50.0))
        assert frame.static_fallback
        assert frame.tick == 0
        assert all(transform == IDENTITY_TRANSFORM for transform in frame.transforms.values())


def test_fixed_step_sequence_is_reproducible() -> None:
    first = AppearanceDynamics(_enabled())
    second = AppearanceDynamics(_enabled())
    samples = tuple(
        DynamicsInput(1.0 / 60.0, motion_x=index / 20, motion_y=-index / 40)
        for index in range(20)
    )
    first_frames = tuple(first.advance(sample) for sample in samples)
    second_frames = tuple(second.advance(sample) for sample in samples)
    assert first_frames == second_frames
    assert first_frames[-1].tick == EXPECTED_TICK_COUNT
    assert first_frames[-1].for_group(MotionGroup.BODY) != IDENTITY_TRANSFORM
    assert first_frames[-1].for_group(MotionGroup.SLEEVE) != IDENTITY_TRANSFORM
    assert first_frames[-1].for_group(MotionGroup.HAIR) != IDENTITY_TRANSFORM
    assert first_frames[-1].for_group(MotionGroup.ACCESSORY) != IDENTITY_TRANSFORM


def test_dt_input_and_state_are_strictly_bounded() -> None:
    configuration = DynamicsConfiguration(
        enabled=True,
        fixed_step_seconds=0.01,
        maximum_dt_seconds=0.05,
        maximum_substeps=3,
    )
    engine = AppearanceDynamics(configuration)
    frame = engine.advance(
        DynamicsInput(10_000.0, motion_x=10_000.0, motion_y=-10_000.0)
    )
    assert frame.tick == MAX_SUBSTEPS
    assert engine.state_count == len(MotionGroup) == MOTION_GROUP_COUNT
    for _index in range(20_000):
        frame = engine.advance(DynamicsInput(0.01, motion_x=99.0, gravity_x=-99.0))
    limits = {
        MotionGroup.BODY: (2.0, 1.0),
        MotionGroup.SLEEVE: (8.0, 8.0),
        MotionGroup.HAIR: (10.0, 10.0),
        MotionGroup.ACCESSORY: (7.0, 12.0),
    }
    for group, (offset_limit, rotation_limit) in limits.items():
        transform = frame.for_group(group)
        assert abs(transform.offset_x) <= offset_limit
        assert abs(transform.offset_y) <= offset_limit + 1.2
        assert abs(transform.rotation_degrees) <= rotation_limit
        assert SCALE_Y_LOWER <= transform.scale_y <= SCALE_Y_UPPER
    assert engine.state_count == MOTION_GROUP_COUNT


def test_reduced_mode_and_reset_are_explicit() -> None:
    engine = AppearanceDynamics(_enabled(DynamicsMode.REDUCED))
    for _index in range(30):
        frame = engine.advance(DynamicsInput(1.0 / 60.0, motion_x=0.8))
    assert not frame.static_fallback
    assert frame.for_group(MotionGroup.BODY) != IDENTITY_TRANSFORM
    assert frame.for_group(MotionGroup.HAIR) != IDENTITY_TRANSFORM
    assert frame.for_group(MotionGroup.SLEEVE) == IDENTITY_TRANSFORM
    assert frame.for_group(MotionGroup.ACCESSORY) == IDENTITY_TRANSFORM
    reset = engine.reset()
    assert reset.static_fallback
    assert reset.tick == 0
    assert all(transform == IDENTITY_TRANSFORM for transform in reset.transforms.values())


def test_snapshot_restore_is_exact_and_rejects_wrong_types() -> None:
    engine = AppearanceDynamics(_enabled())
    for _index in range(12):
        engine.advance(DynamicsInput(1.0 / 60.0, motion_x=0.7))
    snapshot = engine.snapshot()
    expected = engine.advance(DynamicsInput(1.0 / 60.0, motion_y=-0.4))
    engine.restore(snapshot)
    assert engine.advance(DynamicsInput(1.0 / 60.0, motion_y=-0.4)) == expected
    try:
        engine.restore(object())  # type: ignore[arg-type]
    except AppearanceDynamicsError:
        pass
    else:
        raise AssertionError("invalid dynamics snapshot must fail closed")


def test_existing_pack_slots_work_without_new_metadata() -> None:
    expected = {
        "outerwear": MotionGroup.BODY,
        "sleeve-left": MotionGroup.SLEEVE,
        "bangs": MotionGroup.HAIR,
        "ponytail": MotionGroup.HAIR,
        "weapon": MotionGroup.ACCESSORY,
        "handheld": MotionGroup.ACCESSORY,
        "jewelry": MotionGroup.ACCESSORY,
        "foreground-effect": MotionGroup.ACCESSORY,
    }
    assert {slot: motion_group_for_slot(slot) for slot in expected} == expected
    frame = AppearanceDynamics(_enabled()).advance(DynamicsInput(1.0 / 60.0))
    assert frame.for_slot("legacy-unknown-slot") == IDENTITY_TRANSFORM


def test_invalid_timing_and_nonfinite_input_fail_closed() -> None:
    invalid_configurations = (
        {"fixed_step_seconds": 0.0},
        {"maximum_dt_seconds": 0.0},
        {"maximum_substeps": 0},
        {"maximum_substeps": 9},
        {"breathing_pixels": 4.1},
    )
    for changes in invalid_configurations:
        try:
            DynamicsConfiguration(**changes)
        except AppearanceDynamicsError:
            pass
        else:
            raise AssertionError("unsafe dynamics configuration must fail closed")
    for value in (-0.1, math.inf, math.nan):
        try:
            DynamicsInput(value)
        except AppearanceDynamicsError:
            pass
        else:
            raise AssertionError("unsafe dynamics input must fail closed")


if __name__ == "__main__":
    test_disabled_unavailable_and_static_modes_are_exact_fallbacks()
    test_fixed_step_sequence_is_reproducible()
    test_dt_input_and_state_are_strictly_bounded()
    test_reduced_mode_and_reset_are_explicit()
    test_existing_pack_slots_work_without_new_metadata()
    test_snapshot_restore_is_exact_and_rejects_wrong_types()
    test_invalid_timing_and_nonfinite_input_fail_closed()
    print("APPEARANCE_DYNAMICS_OK")
