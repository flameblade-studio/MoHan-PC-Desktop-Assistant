from __future__ import annotations

lazy import struct
lazy import sys
lazy import zlib
lazy from itertools import pairwise
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from hand_asset_audit import (
    FINGERS,
    AuditIssue,
    HandProjection,
    IssueCode,
    JointOcclusion,
    Occluder,
    Point,
    _finger_proportions_valid,
    audit_hand_asset,
)

WIDTH, HEIGHT = 132, 72
SKIN = (214, 155, 126, 255)
SLEEVE = (30, 70, 130, 255)
FINGER_COUNT = 10
COVERED_JOINTS_PER_FINGER = 4


def _points(side: str) -> tuple[Point, ...]:
    if side == "left":
        wrist = Point(27, 61)
        bases = {"thumb": Point(47, 50), "index": Point(40, 49), "middle": Point(31, 48), "ring": Point(22, 49), "pinky": Point(13, 51)}
        tips = {"thumb": Point(56, 38), "index": Point(40, 25), "middle": Point(31, 21), "ring": Point(22, 26), "pinky": Point(13, 35)}
    else:
        wrist = Point(105, 61)
        bases = {"thumb": Point(85, 50), "index": Point(92, 49), "middle": Point(101, 48), "ring": Point(110, 49), "pinky": Point(119, 51)}
        tips = {"thumb": Point(76, 38), "index": Point(92, 25), "middle": Point(101, 21), "ring": Point(110, 26), "pinky": Point(119, 35)}
    result = [wrist]
    for finger in ("thumb", "index", "middle", "ring", "pinky"):
        base, tip = bases[finger], tips[finger]
        result.extend(Point(base.x + (tip.x - base.x) * step / 3, base.y + (tip.y - base.y) * step / 3) for step in range(4))
    return tuple(result)


def _disk(pixels: bytearray, point: Point, color: tuple[int, int, int, int], radius: int = 2) -> None:
    for y in range(round(point.y) - radius, round(point.y) + radius + 1):
        for x in range(round(point.x) - radius, round(point.x) + radius + 1):
            if 0 <= x < WIDTH and 0 <= y < HEIGHT and (x - point.x) ** 2 + (y - point.y) ** 2 <= radius**2:
                offset = (y * WIDTH + x) * 4
                pixels[offset : offset + 4] = bytes(color)


def _line(pixels: bytearray, start: Point, end: Point, color: tuple[int, int, int, int], radius: int = 1) -> None:
    steps = max(1, round(max(abs(end.x - start.x), abs(end.y - start.y))))
    for step in range(steps + 1):
        scale = step / steps
        _disk(pixels, Point(start.x + (end.x - start.x) * scale, start.y + (end.y - start.y) * scale), color, radius)


def _rgba(*, omit: tuple[str, str] | None = None, fused: bool = False, extra: bool = False, occluded: tuple[str, int] | None = None) -> tuple[bytes, tuple[HandProjection, ...]]:
    pixels = bytearray(WIDTH * HEIGHT * 4)
    projections = []
    for side in ("left", "right"):
        points = _points(side)
        _disk(pixels, points[0], SKIN, 3)
        for finger, indices in FINGERS.items():
            if omit == (side, finger):
                continue
            _line(pixels, points[0], points[indices[0]], SKIN)
            for first, second in pairwise(indices):
                _line(pixels, points[first], points[second], SKIN)
            for index in indices:
                _disk(pixels, points[index], SKIN)
        declarations = _draw_occlusion(pixels, points, side, occluded)
        projections.append(HandProjection(side, points, declarations))
        if fused:
            _draw_fused_digits(pixels, points)
    if extra:
        _line(pixels, Point(64, 60), Point(64, 30), SKIN, 2)
    return _png(pixels), tuple(projections)


def _draw_occlusion(
    pixels: bytearray,
    points: tuple[Point, ...],
    side: str,
    occluded: tuple[str, int] | None,
) -> tuple[JointOcclusion, ...]:
    if occluded is None or occluded[0] != side:
        return ()
    _disk(pixels, points[occluded[1]], SLEEVE, 3)
    return (JointOcclusion(occluded[1], "sleeve"),)


def _draw_fused_digits(pixels: bytearray, points: tuple[Point, ...]) -> None:
    for first_name, second_name in pairwise(("index", "middle", "ring", "pinky")):
        for position in (1, 2, 3):
            _line(
                pixels,
                points[FINGERS[first_name][position]],
                points[FINGERS[second_name][position]],
                SKIN,
                2,
            )


def _png(pixels: bytes) -> bytes:
    raw = b"".join(b"\0" + pixels[y * WIDTH * 4 : (y + 1) * WIDTH * 4] for y in range(HEIGHT))
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def _codes(report: object) -> set[IssueCode]:
    return {issue.code for issue in report.issues}


def assert_valid_and_missing_digits() -> tuple[bytes, tuple[HandProjection, ...]]:
    valid_png, projections = _rgba()
    valid = audit_hand_asset(valid_png, projections)
    assert valid.passed
    assert len(valid.fingers) == FINGER_COUNT
    assert all(evidence.covered_joints == COVERED_JOINTS_PER_FINGER for evidence in valid.fingers)

    missing_png, missing_projection = _rgba(omit=("left", "pinky"))
    missing = audit_hand_asset(missing_png, missing_projection)
    assert not missing.passed
    assert IssueCode.MISSING_DIGIT in _codes(missing)
    return valid_png, projections


def assert_near_front_index_foreshortening_is_bounded() -> None:
    assert _finger_proportions_valid(
        {"thumb": 51.0, "index": 49.4, "middle": 46.0, "ring": 43.2, "pinky": 28.1}
    )
    assert not _finger_proportions_valid(
        {"thumb": 51.0, "index": 56.0, "middle": 46.0, "ring": 43.2, "pinky": 28.1}
    )


def assert_shape_and_occlusion_failures(
    valid_png: bytes,
    projections: tuple[HandProjection, ...],
) -> None:

    fused_png, fused_projection = _rgba(fused=True)
    assert IssueCode.FUSED_DIGITS in _codes(audit_hand_asset(fused_png, fused_projection))

    extra_png, extra_projection = _rgba(extra=True)
    assert IssueCode.EXTRA_DIGIT in _codes(audit_hand_asset(extra_png, extra_projection))

    wrong_side = list(projections)
    left = list(wrong_side[0].landmarks)
    left[4] = Point(5, left[4].y)
    wrong_side[0] = HandProjection("left", tuple(left))
    assert IssueCode.THUMB_WRONG_SIDE in _codes(audit_hand_asset(valid_png, tuple(wrong_side)))

    wrong_order = list(projections)
    right = list(wrong_order[1].landmarks)
    right[6], right[7] = right[7], right[6]
    wrong_order[1] = HandProjection("right", tuple(right))
    assert IssueCode.JOINT_ORDER in _codes(audit_hand_asset(valid_png, tuple(wrong_order)))

    occluded_png, occluded_projection = _rgba(occluded=("left", 7))
    occluded = audit_hand_asset(occluded_png, occluded_projection, (Occluder("sleeve", SLEEVE[:3]),))
    assert occluded.passed
    index = next(item for item in occluded.fingers if item.side == "left" and item.finger == "index")
    assert index.occluded_joints == 1

    thumb_base_png, thumb_base_projection = _rgba(occluded=("left", 1))
    thumb_base = audit_hand_asset(
        thumb_base_png,
        thumb_base_projection,
        (Occluder("sleeve", SLEEVE[:3]),),
    )
    assert thumb_base.passed

    index_base_png, index_base_projection = _rgba(occluded=("left", 5))
    index_base = audit_hand_asset(
        index_base_png,
        index_base_projection,
        (Occluder("sleeve", SLEEVE[:3]),),
    )
    assert IssueCode.INVALID_OCCLUSION in _codes(index_base)

    false = audit_hand_asset(valid_png, (HandProjection("left", projections[0].landmarks, (JointOcclusion(7, "sleeve"),)), projections[1]), (Occluder("sleeve", SLEEVE[:3]),))
    assert IssueCode.FALSE_OCCLUSION in _codes(false)

    unknown = audit_hand_asset(valid_png, (HandProjection("left", projections[0].landmarks, (JointOcclusion(7, "unknown"),)), projections[1]))
    assert IssueCode.INVALID_OCCLUSION in _codes(unknown)


def assert_invalid_inputs(
    valid_png: bytes,
    projections: tuple[HandProjection, ...],
) -> None:

    invalid_png = audit_hand_asset(b"not-a-png", projections)
    assert not invalid_png.passed
    assert invalid_png.issues == (AuditIssue(IssueCode.INVALID_PNG, None, None, None),)

    short_projection = audit_hand_asset(
        valid_png,
        (HandProjection("left", projections[0].landmarks[:-1]), projections[1]),
    )
    assert IssueCode.INVALID_PROJECTION in _codes(short_projection)


def run() -> None:
    valid_png, projections = assert_valid_and_missing_digits()
    assert_near_front_index_foreshortening_is_bounded()
    assert_shape_and_occlusion_failures(valid_png, projections)
    assert_invalid_inputs(valid_png, projections)
    print("HAND_ASSET_AUDIT_OK")


if __name__ == "__main__":
    run()
