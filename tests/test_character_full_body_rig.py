from __future__ import annotations

lazy import sys
lazy from dataclasses import FrozenInstanceError, replace
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from character_full_body_rig import (
    LEGACY_POSE_IDS,
    MOHAN_BODY_PROPORTIONS,
    AxialRig,
    BodyProportions,
    FootDirection,
    FootRig,
    adapt_character_pose,
    adapt_legacy_pose_registry,
    audit_full_body_rig,
    compatible_yaws,
)
lazy from character_pose import BodySide, Point2D, default_pose_registry

LANDMARK_COUNT = 21
MIRROR_EPSILON = 1e-9
CANONICAL_YAW_COUNT = 24
REAR_YAW = -30


def _front_rig():
    pose = default_pose_registry().get("front-crossed")
    assert pose is not None
    return adapt_character_pose(pose)


def assert_complete_joint_contract_and_existing_limbs_are_reused() -> None:
    source = default_pose_registry().get("front-crossed")
    assert source is not None
    rig = adapt_character_pose(source)
    required = {
        "root",
        "pelvis",
        "spine",
        "chest",
        "neck",
        "head",
        "left_hip",
        "left_knee",
        "left_ankle",
        "left_foot",
        "left_toe",
        "right_hip",
        "right_knee",
        "right_ankle",
        "right_foot",
        "right_toe",
        "left_shoulder",
        "left_elbow",
        "left_wrist",
        "left_hand",
        "right_shoulder",
        "right_elbow",
        "right_wrist",
        "right_hand",
    }
    assert set(rig.joints) == required
    assert rig.left_arm is source.left_arm
    assert rig.right_arm is source.right_arm
    assert rig.left_hand is source.left_hand
    assert rig.right_hand is source.right_hand
    assert len(rig.left_hand.landmarks) == LANDMARK_COUNT
    assert len(rig.right_hand.landmarks) == LANDMARK_COUNT


def assert_fixed_proportions_and_frozen_models() -> None:
    rig = _front_rig()
    assert rig.proportions == MOHAN_BODY_PROPORTIONS
    assert rig.left_leg.thigh_length == rig.right_leg.thigh_length
    assert rig.left_leg.shin_length == rig.right_leg.shin_length
    try:
        rig.yaw_degrees = 15
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("Full-body rig must be immutable.")
    altered = replace(MOHAN_BODY_PROPORTIONS, thigh_length=0.25)
    try:
        replace(rig, proportions=altered)
    except ValueError as error:
        assert "body_proportions" in str(error)
    else:
        raise AssertionError("Official body proportions must not be replaceable.")


def assert_left_right_geometry_is_mirrored() -> None:
    for yaw in compatible_yaws():
        pose = default_pose_registry().get("front-crossed")
        assert pose is not None
        rig = adapt_character_pose(pose, yaw_degrees=yaw)
        center = rig.axial.root.x
        assert abs((center - rig.left_leg.hip.x) - (rig.right_leg.hip.x - center)) < MIRROR_EPSILON
        assert audit_full_body_rig(rig).valid


def assert_all_24_canonical_yaws_are_supported() -> None:
    assert compatible_yaws() == tuple(range(-180, 180, 15))
    assert len(compatible_yaws()) == CANONICAL_YAW_COUNT
    pose = default_pose_registry().get("front-crossed")
    assert pose is not None
    assert {adapt_character_pose(pose, yaw_degrees=yaw).yaw_degrees for yaw in compatible_yaws()} == set(compatible_yaws())
    try:
        adapt_character_pose(pose, yaw_degrees=7)
    except ValueError as error:
        assert "15-degree" in str(error)
    else:
        raise AssertionError("Noncanonical yaw must fail closed.")


def assert_joint_ranges_fail_closed() -> None:
    rig = _front_rig()
    for field, unsafe in (("hip_degrees", 126.0), ("knee_degrees", 146.0), ("ankle_degrees", 71.0)):
        try:
            replace(rig.left_leg, **{field: unsafe})
        except ValueError as error:
            assert "safe range" in str(error)
        else:
            raise AssertionError(f"Unsafe {field} must fail closed.")


def assert_foot_direction_and_complete_sole_are_validated() -> None:
    foot = _front_rig().left_foot
    assert foot.direction is FootDirection.FORWARD
    assert set(foot.sole_landmarks) == {
        "heel_outer",
        "heel_inner",
        "toe_inner",
        "toe_outer",
    }
    try:
        replace(foot, direction=FootDirection.BACK)
    except ValueError as error:
        assert "direction" in str(error)
    else:
        raise AssertionError("Contradictory foot direction must fail closed.")
    collapsed = {name: Point2D(0.4, 0.9) for name in foot.sole_landmarks}
    try:
        replace(foot, sole_landmarks=frozendict(collapsed))
    except ValueError as error:
        assert "fully visible" in str(error)
    else:
        raise AssertionError("Collapsed shoe sole must fail closed.")
    try:
        FootRig(
            BodySide.LEFT,
            foot.ankle,
            foot.foot,
            foot.toe,
            foot.direction,
            frozendict({"heel_outer": Point2D(0.0, 0.0)}),
        )
    except ValueError as error:
        assert "four sole" in str(error)
    else:
        raise AssertionError("Incomplete sole evidence must fail closed.")


def assert_legacy_three_views_adapt_without_mutation() -> None:
    source = default_pose_registry()
    before = source.poses
    adapted = adapt_legacy_pose_registry(source)
    assert tuple(adapted) == LEGACY_POSE_IDS
    assert source.poses == before
    assert adapted["front-crossed"].yaw_degrees == 0
    assert adapted["left-neutral"].yaw_degrees == REAR_YAW
    assert adapted["left-cheek-rest"].yaw_degrees == REAR_YAW
    assert all(audit_full_body_rig(rig).valid for rig in adapted.values())


def assert_axial_order_and_proportion_inputs_fail_closed() -> None:
    rig = _front_rig()
    try:
        AxialRig(
            rig.axial.root,
            rig.axial.pelvis,
            rig.axial.spine,
            rig.axial.chest,
            rig.axial.neck,
            Point2D(rig.axial.head.x, rig.axial.neck.y + 0.01),
        )
    except ValueError as error:
        assert "progress upward" in str(error)
    else:
        raise AssertionError("Reversed axial chain must fail closed.")
    try:
        BodyProportions(0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.2, 0.1, 0.0)
    except ValueError as error:
        assert "positive finite" in str(error)
    else:
        raise AssertionError("Collapsed body segment must fail closed.")


def run() -> None:
    assert_complete_joint_contract_and_existing_limbs_are_reused()
    assert_fixed_proportions_and_frozen_models()
    assert_left_right_geometry_is_mirrored()
    assert_all_24_canonical_yaws_are_supported()
    assert_joint_ranges_fail_closed()
    assert_foot_direction_and_complete_sole_are_validated()
    assert_legacy_three_views_adapt_without_mutation()
    assert_axial_order_and_proportion_inputs_fail_closed()


if __name__ == "__main__":
    run()
