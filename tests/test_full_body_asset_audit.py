from __future__ import annotations

lazy import sys
lazy from dataclasses import replace
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.character_pose import CANONICAL_YAWS
lazy from domain.full_body_asset_audit import FullBodyViewEvidence, audit_full_body_assets

REAR_YAW = -180


def evidence(yaw: int) -> FullBodyViewEvidence:
    return FullBodyViewEvidence(
        yaw_degrees=yaw,
        canvas_width=1000,
        canvas_height=1000,
        left=180,
        top=50,
        right=820,
        bottom=949,
        center_of_mass_x=500.0,
        center_of_mass_y=540.0,
        left_sole_y=949,
        right_sole_y=949,
        crown_visible=True,
        left_leg_visible=True,
        right_leg_visible=True,
        left_foot_visible=True,
        right_foot_visible=True,
        left_sole_visible=True,
        right_sole_visible=True,
        limbs_unclipped=True,
    )


def complete_ring() -> tuple[FullBodyViewEvidence, ...]:
    return tuple(evidence(yaw) for yaw in CANONICAL_YAWS)


def assert_complete_head_to_sole_ring_passes() -> None:
    report = audit_full_body_assets(complete_ring())
    assert report.passed
    assert report.issues == ()
    assert report.problems == ()


def assert_missing_duplicate_and_noncanonical_views_fail_closed() -> None:
    ring = complete_ring()
    report = audit_full_body_assets((*ring[:-1], ring[0], evidence(181)))
    assert "missing_view:+165" in report.problems
    assert "duplicate_view:-180" in report.problems
    assert "noncanonical_view" in report.problems


def assert_each_body_part_and_margin_is_a_hard_gate() -> None:
    cases = (
        ({"crown_visible": False}, "incomplete_head_to_sole"),
        ({"left_leg_visible": False}, "incomplete_head_to_sole"),
        ({"right_leg_visible": False}, "incomplete_head_to_sole"),
        ({"left_foot_visible": False}, "incomplete_head_to_sole"),
        ({"right_foot_visible": False}, "incomplete_head_to_sole"),
        ({"left_sole_visible": False}, "incomplete_head_to_sole"),
        ({"right_sole_visible": False}, "incomplete_head_to_sole"),
        ({"limbs_unclipped": False}, "limb_clipped"),
        ({"top": 2}, "unsafe_canvas_margin"),
    )
    for changes, code in cases:
        ring = list(complete_ring())
        ring[3] = replace(ring[3], **changes)
        report = audit_full_body_assets(tuple(ring))
        assert f"{code}:{CANONICAL_YAWS[3]:+04d}" in report.problems


def assert_height_median_and_mirror_limits_are_enforced() -> None:
    ring = list(complete_ring())
    positive = CANONICAL_YAWS.index(45)
    ring[positive] = replace(ring[positive], top=30)
    report = audit_full_body_assets(tuple(ring))
    assert "height_median_drift:+045" in report.problems
    assert "mirror_height_drift:+045" in report.problems
    assert "mirror_height_drift:-045" in report.problems


def assert_center_of_mass_and_foot_baselines_are_enforced() -> None:
    ring = list(complete_ring())
    ring[4] = replace(ring[4], center_of_mass_x=790.0)
    ring[5] = replace(ring[5], left_sole_y=920)
    ring[6] = replace(
        ring[6], top=62, bottom=961, left_sole_y=961, right_sole_y=961
    )
    report = audit_full_body_assets(tuple(ring))
    assert f"implausible_center_of_mass:{CANONICAL_YAWS[4]:+04d}" in report.problems
    assert f"unbalanced_sole_baseline:{CANONICAL_YAWS[5]:+04d}" in report.problems
    assert f"foot_baseline_drift:{CANONICAL_YAWS[6]:+04d}" in report.problems


def assert_invalid_geometry_fails_without_sensitive_output() -> None:
    ring = list(complete_ring())
    ring[0] = replace(ring[0], bottom=1001)
    report = audit_full_body_assets(tuple(ring))
    assert not report.passed
    assert "invalid_body_bounds:-180" in report.problems
    serialized = repr(report)
    for forbidden in ("canvas_width", "center_of_mass", "embedding", "rgba", "image"):
        assert forbidden not in serialized
    assert all(
        issue.yaw_degrees is None or issue.yaw_degrees in CANONICAL_YAWS
        for issue in report.issues
    )


def assert_rear_view_does_not_require_face_evidence() -> None:
    rear = complete_ring()[0]
    assert rear.yaw_degrees == REAR_YAW
    assert not hasattr(rear, "face_visible")
    assert audit_full_body_assets(complete_ring()).passed


def assert_explicitly_occluded_side_can_pass_without_fake_coordinates() -> None:
    ring = list(complete_ring())
    hidden = frozenset(
        f"left_{part}"
        for part in ("hip", "knee", "ankle", "heel", "toe", "sole")
    )
    ring[7] = replace(
        ring[7],
        left_leg_visible=False,
        left_foot_visible=False,
        left_sole_visible=False,
        left_sole_y=None,
        occluded_landmarks=hidden,
    )
    report = audit_full_body_assets(tuple(ring))
    assert report.passed


def run() -> None:
    assert_complete_head_to_sole_ring_passes()
    assert_missing_duplicate_and_noncanonical_views_fail_closed()
    assert_each_body_part_and_margin_is_a_hard_gate()
    assert_height_median_and_mirror_limits_are_enforced()
    assert_center_of_mass_and_foot_baselines_are_enforced()
    assert_invalid_geometry_fails_without_sensitive_output()
    assert_rear_view_does_not_require_face_evidence()
    assert_explicitly_occluded_side_can_pass_without_fake_coordinates()
    print("FULL_BODY_ASSET_AUDIT_OK")


if __name__ == "__main__":
    run()
