from __future__ import annotations

lazy import sys
lazy from dataclasses import replace
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from character_pose import (
    CANONICAL_YAWS,
    HAND_LANDMARK_NAMES,
    ArmRig,
    BodySide,
    Point2D,
    PoseRegistry,
    ViewAnchor,
    ViewAtlas,
    audit_hand_anatomy,
    canonical_view_id,
    default_pose_registry,
    normalize_view_id,
    relaxed_hand_pose,
)


def _view(yaw: int) -> ViewAnchor:
    return ViewAnchor(
        canonical_view_id(yaw),
        yaw,
        0,
        f"silhouette-{yaw:+04d}",
        frozenset({f"body-{yaw:+04d}.png", f"hair-{yaw:+04d}.png"}),
    )


def assert_original_three_pose_compatibility() -> None:
    registry = default_pose_registry()
    assert tuple(registry.poses) == (
        "front-crossed",
        "left-neutral",
        "left-cheek-rest",
    )
    assert registry.get("front-crossed").legacy_face_pose == "front"
    assert registry.get("left-neutral").legacy_face_pose == "lean"
    assert registry.get("left-cheek-rest").legacy_face_pose == "cheek"
    assert registry.get("front-crossed").view_id == canonical_view_id(0)
    assert registry.get("left-neutral").view_id == canonical_view_id(-30)
    assert all(pose.speech_safe for pose in registry.poses.values())
    assert registry.available("front-crossed", {"idle_front.png"})
    assert not registry.available("front-crossed", ())


def assert_complete_360_degree_atlas() -> None:
    atlas = ViewAtlas(tuple(_view(yaw) for yaw in CANONICAL_YAWS))
    assert len(atlas.anchors) == 24
    assert atlas.has_complete_horizontal_ring()
    assert atlas.missing_horizontal_ring() == ()
    assert atlas.resolve(0).first.yaw_degrees == 0
    assert atlas.resolve(-180).first.yaw_degrees == -180
    between = atlas.resolve(7.5)
    assert between.interpolated
    assert between.first.yaw_degrees == 0
    assert between.second.yaw_degrees == 15
    assert between.second_weight == 0.5
    wrap = atlas.resolve(172.5)
    assert wrap.interpolated
    assert wrap.first.yaw_degrees == 165
    assert wrap.second.yaw_degrees == -180
    assert normalize_view_id("front-000") == canonical_view_id(0)
    assert normalize_view_id("left-030") == canonical_view_id(-30)
    assert normalize_view_id("right-030") == canonical_view_id(30)
    assert normalize_view_id("back-180") == canonical_view_id(-180)
    assert normalize_view_id(canonical_view_id(165)) == canonical_view_id(165)


def assert_missing_angles_never_fake_a_turn() -> None:
    sparse = ViewAtlas((_view(0), _view(-180)))
    assert not sparse.has_complete_horizontal_ring()
    assert len(sparse.missing_horizontal_ring()) == 22
    result = sparse.resolve(90)
    assert not result.interpolated
    assert result.reason == "authored_gap"
    assert result.first is result.second


def assert_independent_arm_kinematics() -> None:
    registry = default_pose_registry()
    pose = registry.get("front-crossed")
    original_right = pose.right_arm.joints
    moved_left = replace(
        pose.left_arm,
        shoulder_degrees=35.0,
        elbow_degrees=80.0,
        wrist_degrees=-30.0,
    )
    changed = replace(pose, pose_id="left-wave", left_arm=moved_left)
    expanded = registry.with_pose(changed)
    assert expanded.get("left-wave").left_arm.joints != pose.left_arm.joints
    assert expanded.get("left-wave").right_arm.joints == original_right
    assert isinstance(expanded, PoseRegistry)


def assert_left_and_right_hands_have_correct_five_digits() -> None:
    left = relaxed_hand_pose("left")
    right = left.mirrored("right")
    for hand, side in ((left, BodySide.LEFT), (right, BodySide.RIGHT)):
        report = audit_hand_anatomy(hand, side)
        report.require_valid()
        assert report.valid
        assert report.digit_count == 5
        assert report.landmark_count == 21
        assert set(hand.landmarks) == set(HAND_LANDMARK_NAMES)
        assert report.finger_lengths["middle"] >= report.finger_lengths["index"]
        assert report.finger_lengths["middle"] >= report.finger_lengths["ring"]
        assert report.finger_lengths["pinky"] < report.finger_lengths["index"]
        assert report.finger_lengths["pinky"] < report.finger_lengths["ring"]


def assert_wrong_thumb_side_and_fused_fingers_are_rejected() -> None:
    left = relaxed_hand_pose("left")
    wrong_side = audit_hand_anatomy(left, BodySide.RIGHT)
    assert not wrong_side.valid
    assert "finger_root_order" in wrong_side.problems
    assert "thumb_pinky_side" in wrong_side.problems

    fused_landmarks = dict(left.landmarks)
    fused_landmarks["pinky_tip"] = fused_landmarks["ring_tip"]
    fused = replace(left, pose_id="fused", landmarks=frozendict(fused_landmarks))
    fused_report = audit_hand_anatomy(fused, BodySide.LEFT)
    assert not fused_report.valid
    assert "duplicate_or_fused_tip" in fused_report.problems


def assert_joint_bounds_fail_closed() -> None:
    try:
        ArmRig(
            BodySide.LEFT,
            Point2D(0.5, 0.5),
            0.1,
            0.1,
            0.05,
            0.0,
            0.0,
            100.0,
        )
    except ValueError as exc:
        assert "Wrist" in str(exc)
    else:
        raise AssertionError("Unsafe wrist angle was accepted.")


def run() -> None:
    assert_original_three_pose_compatibility()
    assert_complete_360_degree_atlas()
    assert_missing_angles_never_fake_a_turn()
    assert_independent_arm_kinematics()
    assert_left_and_right_hands_have_correct_five_digits()
    assert_wrong_thumb_side_and_fused_fingers_are_rejected()
    assert_joint_bounds_fail_closed()
    print("CHARACTER_POSE_OK")


if __name__ == "__main__":
    run()
