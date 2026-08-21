from __future__ import annotations

lazy import math
lazy from collections.abc import Iterable, Mapping
lazy from dataclasses import dataclass, replace
lazy from enum import StrEnum
lazy from itertools import pairwise

lazy from domain.character_body_profile import MOHAN_BODY_PROFILE
lazy from domain.constants import FLOAT_COMPARISON_EPSILON

POSE_SCHEMA_VERSION = 1
CANONICAL_YAW_STEP_DEGREES = 15
CANONICAL_YAWS = tuple(range(-180, 180, CANONICAL_YAW_STEP_DEGREES))

# 2.5D view and arm-rig angle/length bounds.
MIN_PITCH_DEGREES = -45
MAX_PITCH_DEGREES = 45
INTERPOLATION_MIDPOINT = 0.5
MIN_ARM_SEGMENT_LENGTH = 0.01
MAX_ARM_SEGMENT_LENGTH = 0.5
MIN_SHOULDER_DEGREES = -180.0
MAX_SHOULDER_DEGREES = 180.0
MIN_ELBOW_DEGREES = -165.0
MAX_ELBOW_DEGREES = 165.0
MIN_WRIST_DEGREES = -95.0
MAX_WRIST_DEGREES = 95.0

# Hand-anatomy audit thresholds.
MIN_FINGER_LENGTH = 0.05
FINGER_COUNT = 5
MIN_FINGER_ROOT_GAP = 0.01
MIN_THUMB_PINKY_SPAN = 0.20
MIN_THUMB_RATIO = 0.45
MAX_THUMB_RATIO = 0.90
LEGACY_VIEW_ALIASES = frozendict(
    {
        "front-000": 0,
        "left-030": -30,
        "right-030": 30,
        "left-045": -45,
        "right-045": 45,
        "back-left-120": -120,
        "back-right-120": 120,
        "back-180": -180,
    }
)
HAND_LANDMARK_NAMES = (
    "wrist",
    "thumb_cmc",
    "thumb_mcp",
    "thumb_ip",
    "thumb_tip",
    "index_mcp",
    "index_pip",
    "index_dip",
    "index_tip",
    "middle_mcp",
    "middle_pip",
    "middle_dip",
    "middle_tip",
    "ring_mcp",
    "ring_pip",
    "ring_dip",
    "ring_tip",
    "pinky_mcp",
    "pinky_pip",
    "pinky_dip",
    "pinky_tip",
)
FINGER_CHAINS = frozendict(
    {
        "thumb": ("thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_tip"),
        "index": ("index_mcp", "index_pip", "index_dip", "index_tip"),
        "middle": ("middle_mcp", "middle_pip", "middle_dip", "middle_tip"),
        "ring": ("ring_mcp", "ring_pip", "ring_dip", "ring_tip"),
        "pinky": ("pinky_mcp", "pinky_pip", "pinky_dip", "pinky_tip"),
    }
)
PALM_ROOT_ORDER = ("index_mcp", "middle_mcp", "ring_mcp", "pinky_mcp")


class BodySide(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class PalmFacing(StrEnum):
    CAMERA = "camera"
    CHARACTER = "character"
    INWARD = "inward"
    OUTWARD = "outward"
    EDGE = "edge"


@dataclass(frozen=True, slots=True)
class Point2D:
    """A renderer-independent point in normalized local or canvas space."""

    x: float
    y: float

    def translated(self, dx: float, dy: float) -> Point2D:
        return Point2D(self.x + float(dx), self.y + float(dy))


@dataclass(frozen=True, slots=True)
class ViewAnchor:
    """One authored, identity-locked 2.5D view used by an angle atlas."""

    view_id: str
    yaw_degrees: int
    pitch_degrees: int
    silhouette: str
    required_layers: frozenset[str]
    body_profile_id: str = MOHAN_BODY_PROFILE.profile_id

    def __post_init__(self) -> None:
        if not self.view_id.strip() or not self.silhouette.strip():
            raise ValueError("View identifiers must not be empty.")
        if self.yaw_degrees not in CANONICAL_YAWS:
            raise ValueError("View yaw must use the canonical 15-degree grid.")
        if not MIN_PITCH_DEGREES <= self.pitch_degrees <= MAX_PITCH_DEGREES:
            raise ValueError("2.5D view pitch must remain within -45..45 degrees.")
        if not self.required_layers:
            raise ValueError("Every view requires an authored correction layer set.")
        if self.body_profile_id != MOHAN_BODY_PROFILE.profile_id:
            raise ValueError("View targets a different body identity.")
        if self.view_id != canonical_view_id(
            self.yaw_degrees,
            self.pitch_degrees,
        ):
            raise ValueError("View identifier must match its canonical angle.")


@dataclass(frozen=True, slots=True)
class ViewBlend:
    """The two nearest authored views and their safe crossfade weight."""

    first: ViewAnchor
    second: ViewAnchor
    second_weight: float
    interpolated: bool
    reason: str


class ViewAtlas:
    """Resolve continuous yaw without pretending missing raster views exist."""

    def __init__(
        self,
        anchors: Iterable[ViewAnchor],
        *,
        maximum_interpolation_gap: int = CANONICAL_YAW_STEP_DEGREES,
    ) -> None:
        materialized = tuple(anchors)
        if not materialized:
            raise ValueError("A view atlas requires at least one authored view.")
        keyed = {(anchor.pitch_degrees, anchor.yaw_degrees): anchor for anchor in materialized}
        if len(keyed) != len(materialized):
            raise ValueError("View atlas contains a duplicate pitch/yaw anchor.")
        if maximum_interpolation_gap <= 0:
            raise ValueError("Maximum interpolation gap must be positive.")
        self._anchors = materialized
        self._by_angle = frozendict(keyed)
        self.maximum_interpolation_gap = int(maximum_interpolation_gap)

    @property
    def anchors(self) -> tuple[ViewAnchor, ...]:
        return self._anchors

    @property
    def pitch_bands(self) -> tuple[int, ...]:
        return tuple(sorted({anchor.pitch_degrees for anchor in self._anchors}))

    def missing_horizontal_ring(self, pitch_degrees: int = 0) -> tuple[int, ...]:
        available = {
            anchor.yaw_degrees
            for anchor in self._anchors
            if anchor.pitch_degrees == pitch_degrees
        }
        return tuple(yaw for yaw in CANONICAL_YAWS if yaw not in available)

    def has_complete_horizontal_ring(self, pitch_degrees: int = 0) -> bool:
        return not self.missing_horizontal_ring(pitch_degrees)

    def resolve(self, yaw_degrees: float, pitch_degrees: float = 0.0) -> ViewBlend:
        pitch = min(self.pitch_bands, key=lambda value: abs(value - pitch_degrees))
        ring = tuple(
            sorted(
                (
                    anchor
                    for anchor in self._anchors
                    if anchor.pitch_degrees == pitch
                ),
                key=lambda anchor: _positive_yaw(anchor.yaw_degrees),
            )
        )
        target = _positive_yaw(yaw_degrees)
        if len(ring) == 1:
            return ViewBlend(ring[0], ring[0], 0.0, False, "single_anchor")

        for index, first in enumerate(ring):
            second = ring[(index + 1) % len(ring)]
            start = _positive_yaw(first.yaw_degrees)
            end = _positive_yaw(second.yaw_degrees)
            if index == len(ring) - 1:
                end += 360.0
            adjusted_target = target + (360.0 if target < start else 0.0)
            if start <= adjusted_target <= end:
                return self._blend_or_nearest(
                    first,
                    second,
                    adjusted_target,
                    start,
                    end,
                )
        raise RuntimeError("Circular view resolution failed.")

    def _blend_or_nearest(
        self,
        first: ViewAnchor,
        second: ViewAnchor,
        target: float,
        start: float,
        end: float,
    ) -> ViewBlend:
        gap = end - start
        if gap <= 0.0:
            return ViewBlend(first, first, 0.0, False, "invalid_gap")
        weight = max(0.0, min(1.0, (target - start) / gap))
        if weight < FLOAT_COMPARISON_EPSILON:
            return ViewBlend(first, first, 0.0, False, "exact_anchor")
        if weight > 1.0 - FLOAT_COMPARISON_EPSILON:
            return ViewBlend(second, second, 0.0, False, "exact_anchor")
        if gap <= self.maximum_interpolation_gap:
            return ViewBlend(first, second, weight, True, "adjacent_crossfade")
        nearest = first if weight < INTERPOLATION_MIDPOINT else second
        return ViewBlend(nearest, nearest, 0.0, False, "authored_gap")


@dataclass(frozen=True, slots=True)
class ArmRig:
    """Independent shoulder, elbow and wrist chain for one arm."""

    side: BodySide
    shoulder: Point2D
    upper_arm_length: float
    forearm_length: float
    hand_length: float
    shoulder_degrees: float
    elbow_degrees: float
    wrist_degrees: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.shoulder.x <= 1.0 or not 0.0 <= self.shoulder.y <= 1.0:
            raise ValueError("Shoulder anchor must be inside normalized canvas space.")
        if not all(
            MIN_ARM_SEGMENT_LENGTH <= length <= MAX_ARM_SEGMENT_LENGTH
            for length in (
                self.upper_arm_length,
                self.forearm_length,
                self.hand_length,
            )
        ):
            raise ValueError("Arm segment lengths are outside safe 2.5D limits.")
        if not MIN_SHOULDER_DEGREES <= self.shoulder_degrees <= MAX_SHOULDER_DEGREES:
            raise ValueError("Shoulder rotation is outside its safe range.")
        if not MIN_ELBOW_DEGREES <= self.elbow_degrees <= MAX_ELBOW_DEGREES:
            raise ValueError("Elbow rotation is outside its safe range.")
        if not MIN_WRIST_DEGREES <= self.wrist_degrees <= MAX_WRIST_DEGREES:
            raise ValueError("Wrist rotation is outside its safe range.")

    @property
    def joints(self) -> frozendict[str, Point2D]:
        elbow = _endpoint(
            self.shoulder,
            self.upper_arm_length,
            self.shoulder_degrees,
        )
        wrist = _endpoint(
            elbow,
            self.forearm_length,
            self.shoulder_degrees + self.elbow_degrees,
        )
        hand = _endpoint(
            wrist,
            self.hand_length,
            self.shoulder_degrees + self.elbow_degrees + self.wrist_degrees,
        )
        return frozendict(
            {
                "shoulder": self.shoulder,
                "elbow": elbow,
                "wrist": wrist,
                "hand": hand,
            }
        )


@dataclass(frozen=True, slots=True)
class HandPose:
    """A complete 21-landmark hand shape plus orientation and grip intent."""

    pose_id: str
    landmarks: Mapping[str, Point2D]
    palm_facing: PalmFacing
    grip_slot: str | None = None

    def __post_init__(self) -> None:
        if set(self.landmarks) != set(HAND_LANDMARK_NAMES):
            raise ValueError("Hand pose must define all 21 canonical landmarks.")
        if not self.pose_id.strip():
            raise ValueError("Hand pose identifier must not be empty.")
        if any(
            not math.isfinite(value)
            for point in self.landmarks.values()
            for value in (point.x, point.y)
        ):
            raise ValueError("Hand landmarks must be finite.")

    def mirrored(self, pose_id: str) -> HandPose:
        return HandPose(
            pose_id,
            frozendict(
                {
                    name: Point2D(-point.x, point.y)
                    for name, point in self.landmarks.items()
                }
            ),
            self.palm_facing,
            self.grip_slot,
        )


@dataclass(frozen=True, slots=True)
class HandAnatomyReport:
    """Machine-verifiable hand topology used before visual acceptance."""

    valid: bool
    side: BodySide
    digit_count: int
    landmark_count: int
    finger_lengths: Mapping[str, float]
    problems: tuple[str, ...]

    def require_valid(self) -> None:
        if not self.valid:
            raise ValueError("Invalid hand anatomy: " + ", ".join(self.problems))


def audit_hand_anatomy(hand: HandPose, side: BodySide) -> HandAnatomyReport:
    """Validate five distinct, correctly ordered digits on a left/right hand.

    This validates the full hidden rig. Raster acceptance separately verifies
    that every finger expected to be visible is actually drawn and not fused.
    """

    problems: list[str] = []
    landmark_names = set(hand.landmarks)
    if landmark_names != set(HAND_LANDMARK_NAMES):
        problems.append("landmark_set")

    lengths = frozendict(
        {
            finger: _chain_length(hand.landmarks, chain)
            for finger, chain in FINGER_CHAINS.items()
        }
    )
    if any(length <= MIN_FINGER_LENGTH for length in lengths.values()):
        problems.append("collapsed_digit")
    if len({_quantized_tip(hand.landmarks[chain[-1]]) for chain in FINGER_CHAINS.values()}) != FINGER_COUNT:
        problems.append("duplicate_or_fused_tip")

    roots = tuple(hand.landmarks[name].x for name in PALM_ROOT_ORDER)
    root_direction = 1.0 if side is BodySide.LEFT else -1.0
    if any(
        (next_root - root) * root_direction <= MIN_FINGER_ROOT_GAP
        for root, next_root in pairwise(roots)
    ):
        problems.append("finger_root_order")

    thumb_tip = hand.landmarks["thumb_tip"].x
    pinky_tip = hand.landmarks["pinky_tip"].x
    if (pinky_tip - thumb_tip) * root_direction <= MIN_THUMB_PINKY_SPAN:
        problems.append("thumb_pinky_side")

    if lengths["middle"] + 0.03 < max(lengths["index"], lengths["ring"]):
        problems.append("middle_finger_length")
    if lengths["pinky"] >= min(lengths["index"], lengths["ring"]):
        problems.append("pinky_finger_length")
    if not MIN_THUMB_RATIO <= lengths["thumb"] / lengths["middle"] <= MAX_THUMB_RATIO:
        problems.append("thumb_finger_ratio")

    return HandAnatomyReport(
        not problems,
        side,
        len(FINGER_CHAINS),
        len(hand.landmarks),
        lengths,
        tuple(problems),
    )


@dataclass(frozen=True, slots=True)
class CharacterPose:
    """One atomic body pose; face articulation remains an independent layer."""

    pose_id: str
    view_id: str
    legacy_face_pose: str
    silhouette: str
    left_arm: ArmRig
    right_arm: ArmRig
    left_hand: HandPose
    right_hand: HandPose
    required_corrections: frozenset[str]
    speech_safe: bool
    tags: frozenset[str]

    def __post_init__(self) -> None:
        if self.left_arm.side is not BodySide.LEFT:
            raise ValueError("Left arm rig has the wrong side.")
        if self.right_arm.side is not BodySide.RIGHT:
            raise ValueError("Right arm rig has the wrong side.")
        if not self.required_corrections:
            raise ValueError("Photoreal poses require authored correction layers.")
        if not self.pose_id.strip() or not self.view_id.strip():
            raise ValueError("Pose identifiers must not be empty.")


class PoseRegistry:
    """Immutable pose registry so installed packs cannot mutate live state."""

    def __init__(self, poses: Iterable[CharacterPose]) -> None:
        materialized = tuple(poses)
        keyed = {pose.pose_id: pose for pose in materialized}
        if len(keyed) != len(materialized):
            raise ValueError("Pose registry contains duplicate identifiers.")
        if not keyed:
            raise ValueError("Pose registry must not be empty.")
        self._poses = frozendict(keyed)

    @property
    def poses(self) -> Mapping[str, CharacterPose]:
        return self._poses

    def get(self, pose_id: str) -> CharacterPose | None:
        return self._poses.get(str(pose_id))

    def with_pose(self, pose: CharacterPose) -> PoseRegistry:
        if pose.pose_id in self._poses:
            raise ValueError("Pose identifier is already registered.")
        return PoseRegistry((*self._poses.values(), pose))

    def available(
        self,
        pose_id: str,
        available_corrections: Iterable[str],
    ) -> bool:
        pose = self.get(pose_id)
        return bool(
            pose
            and pose.required_corrections.issubset(
                frozenset(available_corrections)
            )
        )


def default_pose_registry() -> PoseRegistry:
    """Map the original three raster poses into the new canonical system."""

    relaxed_left = relaxed_hand_pose("relaxed-left")
    relaxed_right = relaxed_left.mirrored("relaxed-right")
    common_left = ArmRig(
        BodySide.LEFT,
        Point2D(0.39, 0.39),
        0.145,
        0.135,
        0.075,
        105.0,
        -62.0,
        -10.0,
    )
    common_right = ArmRig(
        BodySide.RIGHT,
        Point2D(0.61, 0.39),
        0.145,
        0.135,
        0.075,
        75.0,
        62.0,
        10.0,
    )
    return PoseRegistry(
        (
            CharacterPose(
                "front-crossed",
                canonical_view_id(0),
                "front",
                "front-crossed",
                common_left,
                common_right,
                relaxed_left,
                relaxed_right,
                frozenset({"idle_front.png"}),
                True,
                frozenset({"legacy", "idle", "front"}),
            ),
            CharacterPose(
                "left-neutral",
                canonical_view_id(-30),
                "lean",
                "left-neutral",
                replace(common_left, shoulder_degrees=118.0, elbow_degrees=-28.0),
                replace(common_right, shoulder_degrees=62.0, elbow_degrees=35.0),
                relaxed_left,
                relaxed_right,
                frozenset({"idle_lean.png"}),
                True,
                frozenset({"legacy", "idle", "left-view"}),
            ),
            CharacterPose(
                "left-cheek-rest",
                canonical_view_id(-30),
                "cheek",
                "cheek-rest",
                replace(common_left, shoulder_degrees=-112.0, elbow_degrees=118.0),
                replace(common_right, shoulder_degrees=78.0, elbow_degrees=54.0),
                relaxed_left,
                relaxed_right,
                frozenset({"idle.png"}),
                True,
                frozenset({"legacy", "idle", "left-view", "cheek-rest"}),
            ),
            CharacterPose(
                "right-neutral",
                canonical_view_id(30),
                "front",
                "right-neutral",
                replace(common_left, shoulder_degrees=112.0, elbow_degrees=-32.0),
                replace(common_right, shoulder_degrees=68.0, elbow_degrees=31.0),
                relaxed_left,
                relaxed_right,
                frozenset({"pose-atlas-v4"}),
                True,
                frozenset({"v4", "idle", "right-view"}),
            ),
            CharacterPose(
                "back-two-thirds-left",
                canonical_view_id(-120),
                "front",
                "back-two-thirds-left",
                common_left,
                common_right,
                relaxed_left,
                relaxed_right,
                frozenset({"pose-atlas-v4"}),
                False,
                frozenset({"v4", "back-view", "left-view"}),
            ),
            CharacterPose(
                "back-two-thirds-right",
                canonical_view_id(120),
                "front",
                "back-two-thirds-right",
                common_left,
                common_right,
                relaxed_left,
                relaxed_right,
                frozenset({"pose-atlas-v4"}),
                False,
                frozenset({"v4", "back-view", "right-view"}),
            ),
            CharacterPose(
                "back-full",
                canonical_view_id(-180),
                "front",
                "back-full",
                common_left,
                common_right,
                relaxed_left,
                relaxed_right,
                frozenset({"pose-atlas-v4"}),
                False,
                frozenset({"v4", "back-view", "full-back"}),
            ),
        )
    )


def relaxed_hand_pose(pose_id: str = "relaxed") -> HandPose:
    """Return a neutral hand authored in a small wrist-local coordinate space."""

    points = (
        (0.00, 0.00),
        (-0.15, -0.05),
        (-0.28, -0.15),
        (-0.38, -0.27),
        (-0.46, -0.38),
        (-0.18, -0.28),
        (-0.21, -0.50),
        (-0.22, -0.66),
        (-0.22, -0.80),
        (-0.02, -0.31),
        (-0.02, -0.56),
        (-0.02, -0.74),
        (-0.02, -0.89),
        (0.13, -0.29),
        (0.16, -0.52),
        (0.18, -0.68),
        (0.20, -0.81),
        (0.25, -0.24),
        (0.31, -0.42),
        (0.35, -0.55),
        (0.38, -0.66),
    )
    return HandPose(
        pose_id,
        frozendict(
            {
                name: Point2D(*point)
                for name, point in zip(HAND_LANDMARK_NAMES, points, strict=True)
            }
        ),
        PalmFacing.CAMERA,
    )


def canonical_view_id(yaw_degrees: int, pitch_degrees: int = 0) -> str:
    if yaw_degrees not in CANONICAL_YAWS:
        raise ValueError("Yaw must use the canonical 15-degree grid.")
    return f"yaw{yaw_degrees:+04d}-pitch{pitch_degrees:+03d}"


def normalize_view_id(value: str, pitch_degrees: int = 0) -> str:
    """Migrate legacy readable aliases to one canonical angle identity."""

    text = str(value).strip()
    if text in LEGACY_VIEW_ALIASES:
        return canonical_view_id(LEGACY_VIEW_ALIASES[text], pitch_degrees)
    if text in {
        canonical_view_id(yaw, pitch_degrees) for yaw in CANONICAL_YAWS
    }:
        return text
    raise ValueError("Unknown or non-canonical view identifier.")


def _positive_yaw(value: float) -> float:
    return float(value) % 360.0


def _endpoint(origin: Point2D, length: float, degrees: float) -> Point2D:
    radians = math.radians(degrees)
    return Point2D(
        origin.x + math.cos(radians) * length,
        origin.y + math.sin(radians) * length,
    )


def _chain_length(
    landmarks: Mapping[str, Point2D],
    chain: tuple[str, ...],
) -> float:
    points = (landmarks["wrist"], *(landmarks[name] for name in chain))
    return sum(
        math.hypot(second.x - first.x, second.y - first.y)
        for first, second in pairwise(points)
    )


def _quantized_tip(point: Point2D) -> tuple[int, int]:
    return round(point.x * 100), round(point.y * 100)
