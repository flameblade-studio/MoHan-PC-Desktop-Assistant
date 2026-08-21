from __future__ import annotations

lazy import math
lazy from collections.abc import Iterable, Mapping
lazy from dataclasses import dataclass
lazy from enum import StrEnum
lazy from itertools import pairwise

lazy from domain.character_body_profile import MOHAN_BODY_PROFILE
lazy from domain.character_pose import (
    CANONICAL_YAWS,
    ArmRig,
    BodySide,
    CharacterPose,
    HandPose,
    Point2D,
    PoseRegistry,
    audit_hand_anatomy,
    canonical_view_id,
    default_pose_registry,
)

FULL_BODY_RIG_SCHEMA_VERSION = 1
LEGACY_POSE_IDS = ("front-crossed", "left-neutral", "left-cheek-rest")
SOLE_LANDMARK_NAMES = frozenset(
    {"heel_outer", "heel_inner", "toe_inner", "toe_outer"}
)

# Safe limb-length and joint-angle ranges for the 2.5D body rig.
MIN_LIMB_LENGTH = 0.05
MAX_LIMB_LENGTH = 0.40
MIN_HIP_DEGREES = 55.0
MAX_HIP_DEGREES = 125.0
MIN_KNEE_DEGREES = -145.0
MAX_KNEE_DEGREES = 145.0
MIN_ANKLE_DEGREES = -55.0
MAX_ANKLE_DEGREES = 70.0
MIN_FOOT_CHAIN_LENGTH = 0.03
MIN_SOLE_AREA = 0.0002

# Foot-direction yaw boundaries (degrees).
FORWARD_YAW_LIMIT = 45
RIGHT_YAW_LIMIT = 135
LEFT_YAW_LIMIT = -135


class FootDirection(StrEnum):
    """Semantic facing of a foot in the authored 2.5D view."""

    FORWARD = "forward"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True, slots=True)
class BodyProportions:
    """Identity-locked normalized lengths for the official body rig."""

    root_to_pelvis: float
    pelvis_to_spine: float
    spine_to_chest: float
    chest_to_neck: float
    neck_to_head: float
    hip_half_width: float
    thigh_length: float
    shin_length: float
    foot_length: float
    toe_length: float

    def __post_init__(self) -> None:
        values = (
            self.root_to_pelvis,
            self.pelvis_to_spine,
            self.spine_to_chest,
            self.chest_to_neck,
            self.neck_to_head,
            self.hip_half_width,
            self.thigh_length,
            self.shin_length,
            self.foot_length,
            self.toe_length,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in values):
            raise ValueError("Body proportions must contain positive finite lengths.")


MOHAN_BODY_PROPORTIONS = BodyProportions(
    root_to_pelvis=0.025,
    pelvis_to_spine=0.115,
    spine_to_chest=0.155,
    chest_to_neck=0.105,
    neck_to_head=0.105,
    hip_half_width=0.075,
    thigh_length=0.245,
    shin_length=0.225,
    foot_length=0.105,
    toe_length=0.045,
)


@dataclass(frozen=True, slots=True)
class AxialRig:
    """Renderer-independent root-to-head chain in normalized canvas space."""

    root: Point2D
    pelvis: Point2D
    spine: Point2D
    chest: Point2D
    neck: Point2D
    head: Point2D

    def __post_init__(self) -> None:
        points = (self.root, self.pelvis, self.spine, self.chest, self.neck, self.head)
        if any(not _point_is_finite(point) for point in points):
            raise ValueError("Axial joints must be finite.")
        if not all(0.0 <= point.x <= 1.0 and 0.0 <= point.y <= 1.0 for point in points):
            raise ValueError("Axial joints must remain in normalized canvas space.")
        if any(upper.y >= lower.y for lower, upper in pairwise(points)):
            raise ValueError("Axial joints must progress upward from root to head.")


@dataclass(frozen=True, slots=True)
class LegRig:
    """One hip-knee-ankle chain with conservative anatomical limits."""

    side: BodySide
    hip: Point2D
    thigh_length: float
    shin_length: float
    hip_degrees: float
    knee_degrees: float
    ankle_degrees: float

    def __post_init__(self) -> None:
        if not _point_is_finite(self.hip):
            raise ValueError("Hip anchor must be finite.")
        if not MIN_LIMB_LENGTH <= self.thigh_length <= MAX_LIMB_LENGTH:
            raise ValueError("Thigh length is outside the safe body range.")
        if not MIN_LIMB_LENGTH <= self.shin_length <= MAX_LIMB_LENGTH:
            raise ValueError("Shin length is outside the safe body range.")
        if not MIN_HIP_DEGREES <= self.hip_degrees <= MAX_HIP_DEGREES:
            raise ValueError("Hip rotation is outside its safe range.")
        if not MIN_KNEE_DEGREES <= self.knee_degrees <= MAX_KNEE_DEGREES:
            raise ValueError("Knee rotation is outside its safe range.")
        if not MIN_ANKLE_DEGREES <= self.ankle_degrees <= MAX_ANKLE_DEGREES:
            raise ValueError("Ankle rotation is outside its safe range.")

    @property
    def joints(self) -> frozendict[str, Point2D]:
        knee = _endpoint(self.hip, self.thigh_length, self.hip_degrees)
        ankle = _endpoint(
            knee,
            self.shin_length,
            self.hip_degrees + self.knee_degrees,
        )
        return frozendict({"hip": self.hip, "knee": knee, "ankle": ankle})


@dataclass(frozen=True, slots=True)
class FootRig:
    """Foot/toe chain plus explicit evidence that the complete sole exists."""

    side: BodySide
    ankle: Point2D
    foot: Point2D
    toe: Point2D
    direction: FootDirection
    sole_landmarks: Mapping[str, Point2D]

    def __post_init__(self) -> None:
        if set(self.sole_landmarks) != SOLE_LANDMARK_NAMES:
            raise ValueError("Foot must expose all four sole landmarks.")
        points = (self.ankle, self.foot, self.toe, *self.sole_landmarks.values())
        if any(not _point_is_finite(point) for point in points):
            raise ValueError("Foot geometry must be finite.")
        travel = Point2D(self.toe.x - self.ankle.x, self.toe.y - self.ankle.y)
        if _length(travel) < MIN_FOOT_CHAIN_LENGTH:
            raise ValueError("Foot and toe chain is collapsed.")
        if _dot(travel, _direction_vector(self.direction)) <= 0.0:
            raise ValueError("Foot geometry disagrees with its declared direction.")
        outline = tuple(self.sole_landmarks[name] for name in (
            "heel_outer",
            "heel_inner",
            "toe_inner",
            "toe_outer",
        ))
        if abs(_polygon_area(outline)) < MIN_SOLE_AREA:
            raise ValueError("Shoe sole is not fully visible as a usable surface.")


@dataclass(frozen=True, slots=True)
class FullBodyRigReport:
    valid: bool
    problems: tuple[str, ...]

    def require_valid(self) -> None:
        if not self.valid:
            raise ValueError("Invalid full-body rig: " + ", ".join(self.problems))


@dataclass(frozen=True, slots=True)
class CharacterFullBodyRig:
    """Complete 2.5D skeleton joined to the established arm and hand model."""

    rig_id: str
    source_pose_id: str
    body_profile_id: str
    yaw_degrees: int
    proportions: BodyProportions
    axial: AxialRig
    left_leg: LegRig
    right_leg: LegRig
    left_foot: FootRig
    right_foot: FootRig
    left_arm: ArmRig
    right_arm: ArmRig
    left_hand: HandPose
    right_hand: HandPose

    def __post_init__(self) -> None:
        audit_full_body_rig(self).require_valid()

    @property
    def joints(self) -> frozendict[str, Point2D]:
        return frozendict(
            {
                "root": self.axial.root,
                "pelvis": self.axial.pelvis,
                "spine": self.axial.spine,
                "chest": self.axial.chest,
                "neck": self.axial.neck,
                "head": self.axial.head,
                **{f"left_{name}": point for name, point in self.left_leg.joints.items()},
                **{f"right_{name}": point for name, point in self.right_leg.joints.items()},
                "left_foot": self.left_foot.foot,
                "left_toe": self.left_foot.toe,
                "right_foot": self.right_foot.foot,
                "right_toe": self.right_foot.toe,
                **{f"left_{name}": point for name, point in self.left_arm.joints.items()},
                **{f"right_{name}": point for name, point in self.right_arm.joints.items()},
            }
        )


def audit_full_body_rig(rig: CharacterFullBodyRig) -> FullBodyRigReport:
    """Fail-closed structural audit independent of rendering and providers."""

    checks = (
        (
            not rig.rig_id.strip() or not rig.source_pose_id.strip(),
            "missing_identifier",
        ),
        (rig.body_profile_id != MOHAN_BODY_PROFILE.profile_id, "body_profile"),
        (rig.yaw_degrees not in CANONICAL_YAWS, "canonical_yaw"),
        (rig.proportions != MOHAN_BODY_PROPORTIONS, "body_proportions"),
        (
            rig.left_leg.side is not BodySide.LEFT
            or rig.right_leg.side is not BodySide.RIGHT,
            "leg_side",
        ),
        (
            rig.left_foot.side is not BodySide.LEFT
            or rig.right_foot.side is not BodySide.RIGHT,
            "foot_side",
        ),
        (
            rig.left_arm.side is not BodySide.LEFT
            or rig.right_arm.side is not BodySide.RIGHT,
            "arm_side",
        ),
        (not _mirrored_anchors(rig), "mirror_consistency"),
        (
            rig.left_leg.thigh_length != rig.right_leg.thigh_length,
            "thigh_length",
        ),
        (
            rig.left_leg.shin_length != rig.right_leg.shin_length,
            "shin_length",
        ),
        (
            rig.left_foot.ankle != rig.left_leg.joints["ankle"],
            "left_foot_attachment",
        ),
        (
            rig.right_foot.ankle != rig.right_leg.joints["ankle"],
            "right_foot_attachment",
        ),
    )
    problems = [problem for failed, problem in checks if failed]
    hands = ((BodySide.LEFT, rig.left_hand), (BodySide.RIGHT, rig.right_hand))
    problems.extend(
        f"{side.value}_hand_anatomy"
        for side, hand in hands
        if not audit_hand_anatomy(hand, side).valid
    )
    return FullBodyRigReport(not problems, tuple(problems))


def adapt_character_pose(
    pose: CharacterPose,
    *,
    yaw_degrees: int | None = None,
) -> CharacterFullBodyRig:
    """Attach the official body and legs to one existing arm/hand pose."""

    yaw = _view_yaw(pose.view_id) if yaw_degrees is None else int(yaw_degrees)
    if yaw not in CANONICAL_YAWS:
        raise ValueError("Full-body rig yaw must use the canonical 15-degree grid.")
    root = Point2D(0.5, 0.51)
    pelvis = _vertical_offset(root, MOHAN_BODY_PROPORTIONS.root_to_pelvis)
    spine = _vertical_offset(pelvis, MOHAN_BODY_PROPORTIONS.pelvis_to_spine)
    chest = _vertical_offset(spine, MOHAN_BODY_PROPORTIONS.spine_to_chest)
    neck = _vertical_offset(chest, MOHAN_BODY_PROPORTIONS.chest_to_neck)
    axial = AxialRig(
        root=root,
        pelvis=pelvis,
        spine=spine,
        chest=chest,
        neck=neck,
        head=_vertical_offset(neck, MOHAN_BODY_PROPORTIONS.neck_to_head),
    )
    perspective = max(0.18, abs(math.cos(math.radians(yaw))))
    hip_offset = MOHAN_BODY_PROPORTIONS.hip_half_width * perspective
    left_leg = LegRig(
        BodySide.LEFT,
        Point2D(root.x - hip_offset, axial.pelvis.y),
        MOHAN_BODY_PROPORTIONS.thigh_length,
        MOHAN_BODY_PROPORTIONS.shin_length,
        88.0,
        2.0,
        0.0,
    )
    right_leg = LegRig(
        BodySide.RIGHT,
        Point2D(root.x + hip_offset, axial.pelvis.y),
        MOHAN_BODY_PROPORTIONS.thigh_length,
        MOHAN_BODY_PROPORTIONS.shin_length,
        92.0,
        -2.0,
        0.0,
    )
    direction = _foot_direction(yaw)
    return CharacterFullBodyRig(
        rig_id=f"{pose.pose_id}@{canonical_view_id(yaw)}",
        source_pose_id=pose.pose_id,
        body_profile_id=MOHAN_BODY_PROFILE.profile_id,
        yaw_degrees=yaw,
        proportions=MOHAN_BODY_PROPORTIONS,
        axial=axial,
        left_leg=left_leg,
        right_leg=right_leg,
        left_foot=_make_foot(BodySide.LEFT, left_leg.joints["ankle"], direction),
        right_foot=_make_foot(BodySide.RIGHT, right_leg.joints["ankle"], direction),
        left_arm=pose.left_arm,
        right_arm=pose.right_arm,
        left_hand=pose.left_hand,
        right_hand=pose.right_hand,
    )


def adapt_legacy_pose_registry(
    registry: PoseRegistry | None = None,
) -> frozendict[str, CharacterFullBodyRig]:
    """Adapt all three original views without mutating their pose registry."""

    source = default_pose_registry() if registry is None else registry
    rigs: dict[str, CharacterFullBodyRig] = {}
    for pose_id in LEGACY_POSE_IDS:
        pose = source.get(pose_id)
        if pose is None:
            raise ValueError(f"Legacy pose registry is missing {pose_id!r}.")
        rigs[pose_id] = adapt_character_pose(pose)
    return frozendict(rigs)


def compatible_yaws() -> tuple[int, ...]:
    """Return the complete immutable 24-view yaw contract."""

    return CANONICAL_YAWS


def _make_foot(side: BodySide, ankle: Point2D, direction: FootDirection) -> FootRig:
    unit = _direction_vector(direction)
    perpendicular = Point2D(-unit.y, unit.x)
    foot = Point2D(
        ankle.x + unit.x * MOHAN_BODY_PROPORTIONS.foot_length,
        ankle.y + unit.y * MOHAN_BODY_PROPORTIONS.foot_length,
    )
    toe = Point2D(
        foot.x + unit.x * MOHAN_BODY_PROPORTIONS.toe_length,
        foot.y + unit.y * MOHAN_BODY_PROPORTIONS.toe_length,
    )
    heel_center = Point2D(ankle.x + unit.x * 0.018, ankle.y + unit.y * 0.018)
    width = 0.022
    return FootRig(
        side,
        ankle,
        foot,
        toe,
        direction,
        frozendict(
            {
                "heel_outer": _offset(heel_center, perpendicular, width),
                "heel_inner": _offset(heel_center, perpendicular, -width),
                "toe_inner": _offset(toe, perpendicular, -width),
                "toe_outer": _offset(toe, perpendicular, width),
            }
        ),
    )


def _mirrored_anchors(rig: CharacterFullBodyRig) -> bool:
    center = rig.axial.root.x
    return math.isclose(
        center - rig.left_leg.hip.x,
        rig.right_leg.hip.x - center,
        abs_tol=1e-9,
    )


def _view_yaw(view_id: str) -> int:
    matches = tuple(yaw for yaw in CANONICAL_YAWS if view_id == canonical_view_id(yaw))
    if len(matches) != 1:
        raise ValueError("Character pose does not use a canonical yaw view.")
    return matches[0]


def _foot_direction(yaw: int) -> FootDirection:
    if -FORWARD_YAW_LIMIT <= yaw <= FORWARD_YAW_LIMIT:
        return FootDirection.FORWARD
    if FORWARD_YAW_LIMIT < yaw < RIGHT_YAW_LIMIT:
        return FootDirection.RIGHT
    if LEFT_YAW_LIMIT < yaw < -FORWARD_YAW_LIMIT:
        return FootDirection.LEFT
    return FootDirection.BACK


def _direction_vector(direction: FootDirection) -> Point2D:
    return {
        # Depth-facing feet are foreshortened in the 2.5D canvas.
        FootDirection.FORWARD: Point2D(0.0, 0.28),
        FootDirection.BACK: Point2D(0.0, -0.28),
        FootDirection.LEFT: Point2D(-1.0, 0.0),
        FootDirection.RIGHT: Point2D(1.0, 0.0),
    }[direction]


def _endpoint(origin: Point2D, length: float, degrees: float) -> Point2D:
    radians = math.radians(degrees)
    return Point2D(
        origin.x + length * math.cos(radians),
        origin.y + length * math.sin(radians),
    )


def _offset(origin: Point2D, direction: Point2D, distance: float) -> Point2D:
    return Point2D(origin.x + direction.x * distance, origin.y + direction.y * distance)


def _vertical_offset(origin: Point2D, distance: float) -> Point2D:
    return Point2D(origin.x, origin.y - distance)


def _length(vector: Point2D) -> float:
    return math.hypot(vector.x, vector.y)


def _dot(first: Point2D, second: Point2D) -> float:
    return first.x * second.x + first.y * second.y


def _point_is_finite(point: Point2D) -> bool:
    return math.isfinite(point.x) and math.isfinite(point.y)


def _polygon_area(points: Iterable[Point2D]) -> float:
    materialized = tuple(points)
    return 0.5 * sum(
        first.x * second.y - second.x * first.y
        for first, second in zip(materialized, (*materialized[1:], materialized[0]), strict=True)
    )
