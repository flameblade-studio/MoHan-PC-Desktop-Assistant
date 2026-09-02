from __future__ import annotations

lazy import math
lazy import struct
lazy import zlib
lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from enum import StrEnum
lazy from itertools import pairwise
lazy from pathlib import Path

# Re-exported from the centralized constants module for a single source of truth.
lazy from domain.constants import (
    BYTES_PER_PIXEL,
    BYTE_MAX,
    PNG_BIT_DEPTH,
    PNG_COLOR_TYPE_RGBA,
)

LANDMARK_COUNT = 21
JOINTS_PER_FINGER = 3
MAX_OCCLUDED_JOINTS = 2

# PNG decoding constraints (RFC 2083 / RGBA8 hand assets).
MAX_PNG_DIMENSION = 4096

# Skin-detection thresholds for hand silhouettes.
MIN_OPAQUE_ALPHA = 96
MIN_SKIN_RED = 80
SKIN_RED_GREEN_RATIO = 0.85
MIN_SKIN_CHANNEL_SPREAD = 10

# Finger-proportion bounds (ratio of each finger to the middle finger).
INDEX_TO_MIDDLE_MIN = 0.72
INDEX_TO_MIDDLE_MAX = 1.10
RING_TO_MIDDLE_MIN = 0.72
RING_TO_MIDDLE_MAX = 1.05
PINKY_TO_MIDDLE_MIN = 0.48
PINKY_TO_MIDDLE_MAX = 0.86

# Coverage / fusion thresholds.
MIN_COVERAGE = 0.35
MIN_BRIDGE_COVERAGE = 0.55
MAX_BRIDGE_LUMINANCE_SPREAD = 10.0
MIN_FUSED_SEPARATION = 6.0
MAX_UNEXPECTED_SKIN_PIXELS = 28
HAND_SPAN_THRESHOLD = 64.0

FINGERS = frozendict({
    "thumb": (1, 2, 3, 4),
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
})
BONES = ((0, 1), (0, 5), (0, 9), (0, 13), (0, 17)) + tuple(
    (indices[position], indices[position + 1])
    for indices in FINGERS.values()
    for position in range(3)
)


class HandAuditError(RuntimeError):
    pass


class IssueCode(StrEnum):
    INVALID_PNG = "invalid-png"
    INVALID_PROJECTION = "invalid-projection"
    MISSING_HAND = "missing-hand"
    DUPLICATE_HAND = "duplicate-hand"
    MISSING_DIGIT = "missing-digit"
    EXTRA_DIGIT = "extra-digit"
    THUMB_WRONG_SIDE = "thumb-wrong-side"
    JOINT_ORDER = "joint-order"
    FINGER_PROPORTION = "finger-proportion"
    MISSING_PIXEL_COVERAGE = "missing-pixel-coverage"
    FUSED_DIGITS = "fused-digits"
    INVALID_OCCLUSION = "invalid-occlusion"
    FALSE_OCCLUSION = "false-occlusion"


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Occluder:
    occluder_id: str
    rgb: tuple[int, int, int]
    tolerance: int = 12


@dataclass(frozen=True, slots=True)
class JointOcclusion:
    landmark_index: int
    occluder_id: str


@dataclass(frozen=True, slots=True)
class HandProjection:
    side: str
    landmarks: tuple[Point, ...]
    occlusions: tuple[JointOcclusion, ...] = ()
    enforce_screen_thumb_side: bool = True


@dataclass(frozen=True, slots=True)
class FingerEvidence:
    side: str
    finger: str
    visible_joints: int
    occluded_joints: int
    covered_joints: int
    length: float
    issues: tuple[IssueCode, ...]


@dataclass(frozen=True, slots=True)
class AuditIssue:
    code: IssueCode
    side: str | None
    finger: str | None
    landmark_index: int | None


@dataclass(frozen=True, slots=True)
class HandAuditReport:
    passed: bool
    issues: tuple[AuditIssue, ...]
    fingers: tuple[FingerEvidence, ...]
    # Checks that were deliberately not run for this asset, with the reason.
    # A skipped check is reported, never silently counted as a pass.
    skipped_checks: tuple[str, ...] = ()


EXTRA_DIGIT_SKIPPED_SKIN_BACKGROUND = "extra-digit:skin-background"


@dataclass(frozen=True, slots=True)
class _Image:
    width: int
    height: int
    pixels: bytes

    def rgba(self, x: int, y: int) -> tuple[int, int, int, int]:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return 0, 0, 0, 0
        offset = (y * self.width + x) * 4
        return tuple(self.pixels[offset : offset + 4])  # type: ignore[return-value]


@dataclass(slots=True)
class _ProjectionAuditContext:
    image: _Image
    projection: HandProjection
    allowlist: dict[str, Occluder]
    issues: list[AuditIssue]
    occlusion_map: dict[int, str]


def _png(source: bytes | Path) -> _Image:
    try:
        data = Path(source).read_bytes() if isinstance(source, Path) else bytes(source)
        if len(data) > 32 * 1024 * 1024 or data[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError
        width, height, compressed = _png_chunks(data)
        return _Image(width, height, _decode_png_rows(compressed, width, height))
    except (OSError, ValueError, TypeError, struct.error, zlib.error, OverflowError):
        raise HandAuditError(IssueCode.INVALID_PNG) from None


def _png_chunks(data: bytes) -> tuple[int, int, bytes]:
    position, width, height = 8, 0, 0
    compressed = bytearray()
    while position < len(data):
        length = struct.unpack(">I", data[position : position + 4])[0]
        kind = data[position + 4 : position + 8]
        payload = data[position + 8 : position + 8 + length]
        expected = struct.unpack(">I", data[position + 8 + length : position + 12 + length])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected:
            raise ValueError
        position += 12 + length
        if kind == b"IHDR":
            width, height = _png_dimensions(payload)
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
    if not (1 <= width <= MAX_PNG_DIMENSION and 1 <= height <= MAX_PNG_DIMENSION):
        raise ValueError
    return width, height, bytes(compressed)


def _png_dimensions(payload: bytes) -> tuple[int, int]:
    width, height, depth, color, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", payload
    )
    if depth != PNG_BIT_DEPTH or color != PNG_COLOR_TYPE_RGBA or compression or filtering or interlace:
        raise ValueError
    return width, height


def _decode_png_rows(compressed: bytes, width: int, height: int) -> bytes:
    raw = zlib.decompress(compressed)
    stride = width * BYTES_PER_PIXEL
    if len(raw) != height * (stride + 1):
        raise ValueError
    rows, previous, cursor = bytearray(), bytearray(stride), 0
    for _ in range(height):
        filter_type = raw[cursor]
        current = bytearray(raw[cursor + 1 : cursor + 1 + stride])
        cursor += stride + 1
        _unfilter_row(current, previous, filter_type)
        rows.extend(current)
        previous = current
    return bytes(rows)


def _unfilter_row(current: bytearray, previous: bytearray, filter_type: int) -> None:
    if filter_type not in range(5):
        raise ValueError
    for index in range(len(current)):
        left = current[index - BYTES_PER_PIXEL] if index >= BYTES_PER_PIXEL else 0
        above = previous[index]
        upper_left = previous[index - BYTES_PER_PIXEL] if index >= BYTES_PER_PIXEL else 0
        predictors = (
            0,
            left,
            above,
            (left + above) // 2,
            _paeth(left, above, upper_left),
        )
        current[index] = (current[index] + predictors[filter_type]) & BYTE_MAX


def _paeth(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    candidates = (left, above, upper_left)
    return min(candidates, key=lambda value: abs(estimate - value))


def _distance(first: Point, second: Point) -> float:
    return math.hypot(first.x - second.x, first.y - second.y)


def _near_color(pixel: tuple[int, int, int, int], rgb: tuple[int, int, int], tolerance: int) -> bool:
    return pixel[3] >= MIN_OPAQUE_ALPHA and max(abs(pixel[index] - rgb[index]) for index in range(3)) <= tolerance


def _coverage(
    image: _Image,
    point: Point,
    predicate: Callable[[tuple[int, int, int, int]], bool],
    radius: int = 2,
) -> float:
    matches, total = 0, 0
    for y in range(round(point.y) - radius, round(point.y) + radius + 1):
        for x in range(round(point.x) - radius, round(point.x) + radius + 1):
            if (x - point.x) ** 2 + (y - point.y) ** 2 <= radius**2:
                total += 1
                matches += predicate(image.rgba(x, y))
    return matches / max(1, total)


def _skin(pixel: tuple[int, int, int, int]) -> bool:
    red, green, blue, alpha = pixel
    return (
        alpha >= MIN_OPAQUE_ALPHA
        and red >= MIN_SKIN_RED
        and red > blue
        and red >= green * SKIN_RED_GREEN_RATIO
        and max(red, green, blue) - min(red, green, blue) >= MIN_SKIN_CHANNEL_SPREAD
    )


def _segment_distance(point: Point, first: Point, second: Point) -> float:
    dx, dy = second.x - first.x, second.y - first.y
    if dx == dy == 0:
        return _distance(point, first)
    scale = max(0.0, min(1.0, ((point.x - first.x) * dx + (point.y - first.y) * dy) / (dx * dx + dy * dy)))
    return _distance(point, Point(first.x + scale * dx, first.y + scale * dy))


def _projection_issues(projection: HandProjection) -> list[AuditIssue]:
    if projection.side not in {"left", "right"} or len(projection.landmarks) != LANDMARK_COUNT:
        return [AuditIssue(IssueCode.INVALID_PROJECTION, projection.side, None, None)]
    if any(not math.isfinite(value) for point in projection.landmarks for value in (point.x, point.y)):
        return [AuditIssue(IssueCode.INVALID_PROJECTION, projection.side, None, None)]
    return []


def audit_hand_asset(
    png: bytes | Path,
    projections: tuple[HandProjection, ...],
    occluders: tuple[Occluder, ...] = (),
    allow_occluded_sides: frozenset[str] = frozenset(),
    skin_background: bool = False,
) -> HandAuditReport:
    """Audit one hand canvas.

    ``skin_background`` declares that the pixels around the hand are
    legitimately skin (bare forearm, bare thigh behind a hanging hand).  The
    extra-digit heuristic counts skin inside the hand ROI that no skeleton
    bone explains; it was calibrated on a long-sleeved body where that skin
    could only be a sixth finger.  Against a bare body it flags the forearm
    and thigh on most views, so under the declaration it is not run and the
    skip is reported in ``skipped_checks`` for a human to cover.
    """

    try:
        image = _png(png)
    except HandAuditError:
        issue = AuditIssue(IssueCode.INVALID_PNG, None, None, None)
        return HandAuditReport(False, (issue,), ())
    issues: list[AuditIssue] = []
    allowlist = {item.occluder_id: item for item in occluders}
    _audit_hand_counts(projections, allow_occluded_sides, issues)
    if len(allowlist) != len(occluders):
        issues.append(AuditIssue(IssueCode.INVALID_OCCLUSION, None, None, None))
    fingers: list[FingerEvidence] = []
    valid_point_sets: list[tuple[Point, ...]] = []
    for projection in projections:
        projection_errors = _projection_issues(projection)
        issues.extend(projection_errors)
        if projection_errors:
            continue
        valid_point_sets.append(projection.landmarks)
        fingers.extend(_audit_projection(image, projection, allowlist, issues))
    skipped: tuple[str, ...] = ()
    if skin_background:
        skipped = (EXTRA_DIGIT_SKIPPED_SKIN_BACKGROUND,)
    elif valid_point_sets and _unexpected_skin_pixels(image, valid_point_sets) > MAX_UNEXPECTED_SKIN_PIXELS:
        issues.append(AuditIssue(IssueCode.EXTRA_DIGIT, None, None, None))
    unique = tuple(dict.fromkeys(issues))
    return HandAuditReport(not unique, unique, tuple(fingers), skipped)


def _audit_hand_counts(
    projections: tuple[HandProjection, ...],
    allow_occluded_sides: frozenset[str],
    issues: list[AuditIssue],
) -> None:
    sides = [projection.side for projection in projections]
    for side in ("left", "right"):
        count = sides.count(side)
        if count == 0 and side not in allow_occluded_sides:
            issues.append(AuditIssue(IssueCode.MISSING_HAND, side, None, None))
        elif count > 1:
            issues.append(AuditIssue(IssueCode.DUPLICATE_HAND, side, None, None))


def _audit_projection(
    image: _Image,
    projection: HandProjection,
    allowlist: dict[str, Occluder],
    issues: list[AuditIssue],
) -> tuple[FingerEvidence, ...]:
    points = projection.landmarks
    occlusion_map = {
        item.landmark_index: item.occluder_id for item in projection.occlusions
    }
    if len(occlusion_map) != len(projection.occlusions):
        issues.append(AuditIssue(IssueCode.INVALID_OCCLUSION, projection.side, None, None))
    context = _ProjectionAuditContext(
        image,
        projection,
        allowlist,
        issues,
        occlusion_map,
    )
    if projection.enforce_screen_thumb_side:
        _audit_thumb_side(projection, issues)
    lengths = {
        finger: _distance(points[indices[0]], points[indices[-1]])
        for finger, indices in FINGERS.items()
    }
    if not _finger_proportions_valid(lengths):
        issues.append(AuditIssue(IssueCode.FINGER_PROPORTION, projection.side, None, None))
    evidence = tuple(
        _audit_finger(context, finger, indices, lengths[finger])
        for finger, indices in FINGERS.items()
    )
    _audit_fused_digits(image, projection, issues)
    return evidence


def _audit_thumb_side(projection: HandProjection, issues: list[AuditIssue]) -> None:
    points = projection.landmarks
    palm_center = sum(points[index].x for index in (5, 9, 13, 17)) / 4
    wrong = (
        projection.side == "left" and points[4].x <= palm_center
    ) or (
        projection.side == "right" and points[4].x >= palm_center
    )
    if wrong:
        issues.append(AuditIssue(IssueCode.THUMB_WRONG_SIDE, projection.side, "thumb", 4))


def _finger_proportions_valid(lengths: dict[str, float]) -> bool:
    middle = lengths["middle"]
    return (
        middle >= lengths["index"] * 0.92
        and middle >= lengths["ring"] * 0.95
        # A near-front relaxed hand can foreshorten its middle finger slightly
        # more than its index finger in a two-dimensional projection.
        and INDEX_TO_MIDDLE_MIN <= lengths["index"] / middle <= INDEX_TO_MIDDLE_MAX
        and RING_TO_MIDDLE_MIN <= lengths["ring"] / middle <= RING_TO_MIDDLE_MAX
        and PINKY_TO_MIDDLE_MIN <= lengths["pinky"] / middle <= PINKY_TO_MIDDLE_MAX
    )


def _audit_finger(
    context: _ProjectionAuditContext,
    finger: str,
    indices: tuple[int, ...],
    length: float,
) -> FingerEvidence:
    projection = context.projection
    issues = context.issues
    occlusion_map = context.occlusion_map
    points = projection.landmarks
    finger_issues: list[IssueCode] = []
    radial = [_distance(points[0], points[index]) for index in indices]
    # Coordinates are integer pixels.  A one-pixel tie or reversal is not
    # enough to reject an otherwise supported, naturally relaxed finger.
    if any(current + 1.5 < previous for previous, current in pairwise(radial)):
        _record_issue(issues, finger_issues, IssueCode.JOINT_ORDER, projection.side, finger)
    occluded = [index for index in indices if index in occlusion_map]
    if (
        len(occluded) > MAX_OCCLUDED_JOINTS
        or indices[-1] in occluded
        or (indices[0] in occluded and finger != "thumb")
    ):
        _record_issue(issues, finger_issues, IssueCode.INVALID_OCCLUSION, projection.side, finger)
    covered = sum(
        _audit_joint(context, points[index], index, finger, finger_issues)
        for index in indices
    )
    if covered + len(occluded) < JOINTS_PER_FINGER:
        _record_issue(issues, finger_issues, IssueCode.MISSING_DIGIT, projection.side, finger)
    return FingerEvidence(
        projection.side,
        finger,
        4 - len(occluded),
        len(occluded),
        covered,
        length,
        tuple(dict.fromkeys(finger_issues)),
    )


def _audit_joint(
    context: _ProjectionAuditContext,
    point: Point,
    index: int,
    finger: str,
    finger_issues: list[IssueCode],
) -> int:
    code = _joint_issue(
        context.image,
        point,
        index,
        context.occlusion_map,
        context.allowlist,
    )
    if code is None:
        return 1
    context.issues.append(AuditIssue(code, context.projection.side, finger, index))
    finger_issues.append(code)
    return 0


def _joint_issue(
    image: _Image,
    point: Point,
    index: int,
    occlusion_map: dict[int, str],
    allowlist: dict[str, Occluder],
) -> IssueCode | None:
    if index not in occlusion_map:
        return None if _coverage(image, point, _skin) >= MIN_COVERAGE else IssueCode.MISSING_PIXEL_COVERAGE
    occluder = allowlist.get(occlusion_map[index])
    if occluder is None:
        return IssueCode.INVALID_OCCLUSION
    covered = _coverage(
        image,
        point,
        lambda pixel: _near_color(pixel, occluder.rgb, occluder.tolerance),
    )
    return None if covered >= MIN_COVERAGE else IssueCode.FALSE_OCCLUSION


def _record_issue(
    issues: list[AuditIssue],
    finger_issues: list[IssueCode],
    code: IssueCode,
    side: str,
    finger: str,
) -> None:
    issues.append(AuditIssue(code, side, finger, None))
    finger_issues.append(code)


def _audit_fused_digits(
    image: _Image,
    projection: HandProjection,
    issues: list[AuditIssue],
) -> None:
    ordered = ("index", "middle", "ring", "pinky")
    for first_name, second_name in pairwise(ordered):
        bridges = sum(
            _finger_bridge(image, projection.landmarks, first_name, second_name, position)
            for position in (1, 2, 3)
        )
        separations = tuple(
            _distance(
                projection.landmarks[FINGERS[first_name][position]],
                projection.landmarks[FINGERS[second_name][position]],
            )
            for position in (1, 2, 3)
        )
        # When 21-point evidence itself puts adjacent fingers within six
        # pixels, a closed relaxed hand is ambiguous rather than malformed.
        # Still reject a connected silhouette whose independently separated
        # fingers have fused together.
        if bridges == JOINTS_PER_FINGER and min(separations) >= MIN_FUSED_SEPARATION:
            issues.append(
                AuditIssue(
                    IssueCode.FUSED_DIGITS,
                    projection.side,
                    f"{first_name}/{second_name}",
                    None,
                )
            )


def _finger_bridge(
    image: _Image,
    points: tuple[Point, ...],
    first_name: str,
    second_name: str,
    position: int,
) -> bool:
    first = points[FINGERS[first_name][position]]
    second = points[FINGERS[second_name][position]]
    samples = tuple(
        Point(
            first.x + (second.x - first.x) * step / 8,
            first.y + (second.y - first.y) * step / 8,
        )
        for step in range(9)
    )
    if not all(_coverage(image, sample, _skin, 1) >= MIN_BRIDGE_COVERAGE for sample in samples[1:-1]):
        return False
    luminance = tuple(_luminance(image.rgba(round(sample.x), round(sample.y))) for sample in samples)
    return max(luminance) - min(luminance) < MAX_BRIDGE_LUMINANCE_SPREAD


def _luminance(pixel: tuple[int, int, int, int]) -> float:
    red, green, blue, _alpha = pixel
    return red * 0.2126 + green * 0.7152 + blue * 0.0722


def _unexpected_skin_pixels(
    image: _Image,
    point_sets: list[tuple[Point, ...]],
) -> int:
    if not point_sets:
        return 0
    allowances = tuple(_hand_skeleton_allowance(points) for points in point_sets)
    margin = max(allowances)
    left = max(0, math.floor(min(point.x for points in point_sets for point in points) - margin))
    right = min(image.width - 1, math.ceil(max(point.x for points in point_sets for point in points) + margin))
    top = max(0, math.floor(min(point.y for points in point_sets for point in points) - margin))
    bottom = min(image.height - 1, math.ceil(max(point.y for points in point_sets for point in points) + margin))
    return sum(
        _skin(image.rgba(x, y))
        and min(
            _segment_distance(Point(x, y), points[first], points[second]) - allowance
            for points, allowance in zip(point_sets, allowances, strict=False)
            for first, second in BONES
        ) > 0
        for y in range(top, bottom + 1)
        for x in range(left, right + 1)
    )


def _hand_skeleton_allowance(points: tuple[Point, ...]) -> float:
    hand_span = _distance(points[0], points[12])
    # A relaxed side-view hand overlaps its finger silhouettes more than an
    # open-palm pose.  Keep the allowance proportional to the measured hand
    # span so that it covers the legitimate palm contour without concealing a
    # separate extra digit.
    scale = 0.165 if hand_span >= HAND_SPAN_THRESHOLD else 0.14
    return max(3.5, min(18.0, hand_span * scale))
