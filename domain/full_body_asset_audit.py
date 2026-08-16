from __future__ import annotations

lazy from collections import Counter
lazy from dataclasses import dataclass
lazy from statistics import median

lazy from domain.character_pose import CANONICAL_YAWS


@dataclass(frozen=True, slots=True)
class FullBodyViewEvidence:
    """Non-image evidence that one canonical view contains a complete body."""

    yaw_degrees: int
    canvas_width: int
    canvas_height: int
    left: int
    top: int
    right: int
    bottom: int
    center_of_mass_x: float
    center_of_mass_y: float
    left_sole_y: int | None
    right_sole_y: int | None
    crown_visible: bool
    left_leg_visible: bool
    right_leg_visible: bool
    left_foot_visible: bool
    right_foot_visible: bool
    left_sole_visible: bool
    right_sole_visible: bool
    limbs_unclipped: bool
    occluded_landmarks: frozenset[str] = frozenset()

    @property
    def occluded_sides(self) -> frozenset[str]:
        return frozenset(
            side
            for side in ("left", "right")
            if all(
                f"{side}_{part}" in self.occluded_landmarks
                for part in (
                    "hip",
                    "knee",
                    "ankle",
                    "heel",
                    "toe",
                    "sole",
                )
            )
        )

    @property
    def person_height(self) -> int:
        return self.bottom - self.top + 1


@dataclass(frozen=True, slots=True)
class FullBodyAuditPolicy:
    minimum_margin_pixels: int = 8
    minimum_margin_ratio: float = 0.01
    maximum_height_error_ratio: float = 0.01
    maximum_mirror_height_error_ratio: float = 0.01
    maximum_sole_difference_ratio: float = 0.01
    maximum_baseline_error_ratio: float = 0.01
    maximum_horizontal_balance_ratio: float = 0.20
    minimum_vertical_balance_ratio: float = 0.25
    maximum_vertical_balance_ratio: float = 0.75


DEFAULT_FULL_BODY_AUDIT_POLICY = FullBodyAuditPolicy()


@dataclass(frozen=True, slots=True)
class FullBodyAuditIssue:
    code: str
    yaw_degrees: int | None = None


@dataclass(frozen=True, slots=True)
class FullBodyAssetAuditReport:
    passed: bool
    issues: tuple[FullBodyAuditIssue, ...]

    @property
    def problems(self) -> tuple[str, ...]:
        return tuple(
            issue.code
            if issue.yaw_degrees is None
            else f"{issue.code}:{issue.yaw_degrees:+04d}"
            for issue in self.issues
        )


def audit_full_body_assets(
    views: tuple[FullBodyViewEvidence, ...],
    policy: FullBodyAuditPolicy = DEFAULT_FULL_BODY_AUDIT_POLICY,
) -> FullBodyAssetAuditReport:
    """Audit a complete 24-view body ring without retaining source assets."""

    issues: list[FullBodyAuditIssue] = []
    counts = Counter(view.yaw_degrees for view in views)
    for yaw in CANONICAL_YAWS:
        if counts[yaw] == 0:
            issues.append(FullBodyAuditIssue("missing_view", yaw))
        elif counts[yaw] > 1:
            issues.append(FullBodyAuditIssue("duplicate_view", yaw))
    if set(counts) - set(CANONICAL_YAWS):
        issues.append(FullBodyAuditIssue("noncanonical_view"))

    unique = {
        view.yaw_degrees: view
        for view in views
        if view.yaw_degrees in CANONICAL_YAWS and counts[view.yaw_degrees] == 1
    }
    ordered = tuple(unique[yaw] for yaw in CANONICAL_YAWS if yaw in unique)
    valid_geometry = [view for view in ordered if _audit_view(view, policy, issues)]

    if len(valid_geometry) == len(CANONICAL_YAWS):
        _audit_height_consistency(tuple(valid_geometry), policy, issues)
        _audit_baseline_consistency(tuple(valid_geometry), policy, issues)
        _audit_visible_limb_coverage(tuple(valid_geometry), issues)
    return FullBodyAssetAuditReport(not issues, tuple(issues))


def _audit_view(
    view: FullBodyViewEvidence,
    policy: FullBodyAuditPolicy,
    issues: list[FullBodyAuditIssue],
) -> bool:
    yaw = view.yaw_degrees
    valid_canvas = view.canvas_width > 0 and view.canvas_height > 0
    valid_bounds = (
        valid_canvas
        and 0 <= view.left <= view.right < view.canvas_width
        and 0 <= view.top <= view.bottom < view.canvas_height
    )
    if not valid_bounds:
        issues.append(FullBodyAuditIssue("invalid_body_bounds", yaw))
        return False

    margin = max(
        policy.minimum_margin_pixels,
        round(min(view.canvas_width, view.canvas_height) * policy.minimum_margin_ratio),
    )
    if min(
        view.left,
        view.top,
        view.canvas_width - 1 - view.right,
        view.canvas_height - 1 - view.bottom,
    ) < margin:
        issues.append(FullBodyAuditIssue("unsafe_canvas_margin", yaw))

    required_evidence = (
        view.crown_visible,
        _side_evidence_is_present(view, "left", view.left_leg_visible),
        _side_evidence_is_present(view, "right", view.right_leg_visible),
        _side_evidence_is_present(view, "left", view.left_foot_visible),
        _side_evidence_is_present(view, "right", view.right_foot_visible),
        _side_evidence_is_present(view, "left", view.left_sole_visible),
        _side_evidence_is_present(view, "right", view.right_sole_visible),
    )
    if not all(required_evidence):
        issues.append(FullBodyAuditIssue("incomplete_head_to_sole", yaw))
    if not view.limbs_unclipped:
        issues.append(FullBodyAuditIssue("limb_clipped", yaw))

    sole_tolerance = max(1.0, view.person_height * policy.maximum_sole_difference_ratio)
    visible_soles = tuple(
        sole_y
        for sole_y in (view.left_sole_y, view.right_sole_y)
        if sole_y is not None
    )
    soles_inside = bool(visible_soles) and all(
        view.top <= sole_y <= view.bottom for sole_y in visible_soles
    )
    if not soles_inside:
        issues.append(FullBodyAuditIssue("invalid_sole_baseline", yaw))
    elif len(visible_soles) == 2 and (
        abs(visible_soles[0] - visible_soles[1]) > sole_tolerance
        or max(visible_soles) != view.bottom
    ):
        issues.append(FullBodyAuditIssue("unbalanced_sole_baseline", yaw))
    elif len(visible_soles) == 1 and visible_soles[0] != view.bottom:
        issues.append(FullBodyAuditIssue("unbalanced_sole_baseline", yaw))

    center_x = (view.left + view.right) / 2
    horizontal_tolerance = (
        (view.right - view.left + 1) * policy.maximum_horizontal_balance_ratio
    )
    vertical_ratio = (view.center_of_mass_y - view.top) / view.person_height
    if (
        not view.left <= view.center_of_mass_x <= view.right
        or abs(view.center_of_mass_x - center_x) > horizontal_tolerance
        or not policy.minimum_vertical_balance_ratio
        <= vertical_ratio
        <= policy.maximum_vertical_balance_ratio
    ):
        issues.append(FullBodyAuditIssue("implausible_center_of_mass", yaw))
    return True


def _audit_height_consistency(
    views: tuple[FullBodyViewEvidence, ...],
    policy: FullBodyAuditPolicy,
    issues: list[FullBodyAuditIssue],
) -> None:
    heights = {view.yaw_degrees: view.person_height for view in views}
    median_height = float(median(heights.values()))
    for yaw, height in heights.items():
        if _relative_error(height, median_height) > policy.maximum_height_error_ratio:
            issues.append(FullBodyAuditIssue("height_median_drift", yaw))
    for yaw in CANONICAL_YAWS:
        mirror = -yaw
        if yaw <= 0 or mirror not in heights:
            continue
        pair_reference = (heights[yaw] + heights[mirror]) / 2
        if (
            abs(heights[yaw] - heights[mirror]) / pair_reference
            > policy.maximum_mirror_height_error_ratio
        ):
            issues.extend(
                (
                    FullBodyAuditIssue("mirror_height_drift", yaw),
                    FullBodyAuditIssue("mirror_height_drift", mirror),
                )
            )


def _audit_baseline_consistency(
    views: tuple[FullBodyViewEvidence, ...],
    policy: FullBodyAuditPolicy,
    issues: list[FullBodyAuditIssue],
) -> None:
    baselines = {view.yaw_degrees: view.bottom for view in views}
    reference = float(median(baselines.values()))
    for view in views:
        tolerance = max(1.0, view.canvas_height * policy.maximum_baseline_error_ratio)
        if abs(view.bottom - reference) > tolerance:
            issues.append(FullBodyAuditIssue("foot_baseline_drift", view.yaw_degrees))


def _relative_error(value: float, reference: float) -> float:
    return abs(value - reference) / reference if reference else float("inf")


def _side_evidence_is_present(
    view: FullBodyViewEvidence,
    side: str,
    visible: bool,
) -> bool:
    return visible or side in view.occluded_sides


def _audit_visible_limb_coverage(
    views: tuple[FullBodyViewEvidence, ...],
    issues: list[FullBodyAuditIssue],
) -> None:
    requirements = (
        ("left_leg_visible", "missing_left_leg_visibility"),
        ("right_leg_visible", "missing_right_leg_visibility"),
        ("left_foot_visible", "missing_left_foot_visibility"),
        ("right_foot_visible", "missing_right_foot_visibility"),
    )
    for attribute, code in requirements:
        if not any(getattr(view, attribute) for view in views):
            issues.append(FullBodyAuditIssue(code))
