from __future__ import annotations

lazy import hashlib
lazy import json
lazy import math
lazy import struct
lazy import zlib
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath

lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id
lazy from domain.hand_asset_audit import (
    HandProjection,
    JointOcclusion,
    Occluder,
    Point,
    audit_hand_asset,
)

SIDECAR_SCHEMA_VERSION = 1
LANDMARK_COUNT = 21
HAND_SIDES = frozenset({"left", "right"})
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
ROI_LANDMARK_MARGIN = 3
ROI_GAP = 8


@dataclass(frozen=True, slots=True)
class HandAssetManifestEvidence:
    view_id: str
    yaw_degrees: int
    png_path: str
    sidecar_path: str
    width: int
    height: int
    png_sha256: str
    sidecar_sha256: str


@dataclass(frozen=True, slots=True)
class HandAssetEvidenceIssue:
    code: str
    side: str | None = None
    finger: str | None = None
    landmark_index: int | None = None


@dataclass(frozen=True, slots=True)
class HandAssetEvidenceResult:
    passed: bool
    view_id: str | None
    png_sha256: str | None
    sidecar_sha256: str | None
    issues: tuple[HandAssetEvidenceIssue, ...]
    visible_sides: frozenset[str] = frozenset()
    occluded_sides: frozenset[str] = frozenset()

    @property
    def problems(self) -> tuple[str, ...]:
        return tuple(issue.code for issue in self.issues)

    def to_json_bytes(self) -> bytes:
        payload = {
            "schema_version": 1,
            "passed": self.passed,
            "view_id": self.view_id,
            "png_sha256": self.png_sha256,
            "sidecar_sha256": self.sidecar_sha256,
            "issues": [
                {
                    "code": issue.code,
                    "side": issue.side,
                    "finger": issue.finger,
                    "landmark_index": issue.landmark_index,
                }
                for issue in self.issues
            ],
            "visible_sides": sorted(self.visible_sides),
            "occluded_sides": sorted(self.occluded_sides),
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class _VerifiedFiles:
    png: bytes
    sidecar: bytes
    png_sha256: str
    sidecar_sha256: str


def build_hand_asset_evidence(
    asset_root: Path,
    manifest: HandAssetManifestEvidence,
) -> HandAssetEvidenceResult:
    """Audit one real RGBA view without retaining paths or landmarks."""

    identity_issue = _validate_manifest_identity(manifest)
    if identity_issue is not None:
        return _failure(identity_issue)
    try:
        files = _verified_files(asset_root.resolve(), manifest)
    except _EvidenceFailure as error:
        return _failure(error.code, manifest.view_id, error.png_sha256, error.sidecar_sha256)
    try:
        width, height = _png_dimensions(files.png)
    except ValueError:
        return _failure("invalid_rgba_png", manifest.view_id, files.png_sha256, files.sidecar_sha256)
    if (width, height) != (manifest.width, manifest.height):
        return _failure("dimension_mismatch", manifest.view_id, files.png_sha256, files.sidecar_sha256)
    try:
        payload = _sidecar(files.sidecar, manifest, width, height)
        image = _decode_rgba(files.png, width, height)
        audit_png, projections, visible_sides, occluded_sides = _audit_canvas(
            payload,
            image,
            width,
            height,
        )
        occluders = _occluders(payload)
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError, zlib.error):
        return _failure("sidecar_invalid", manifest.view_id, files.png_sha256, files.sidecar_sha256)
    report = audit_hand_asset(
        audit_png,
        projections,
        occluders,
        allow_occluded_sides=occluded_sides,
    )
    issues = tuple(
        HandAssetEvidenceIssue(
            f"hand_{issue.code.value.replace('-', '_')}",
            issue.side,
            issue.finger,
            issue.landmark_index,
        )
        for issue in report.issues
    )
    complete_sides = visible_sides | occluded_sides == HAND_SIDES
    passed = report.passed and complete_sides
    return HandAssetEvidenceResult(
        passed,
        manifest.view_id,
        files.png_sha256,
        files.sidecar_sha256,
        tuple(dict.fromkeys(issues)),
        visible_sides,
        occluded_sides,
    )


class _EvidenceFailure(RuntimeError):
    def __init__(
        self,
        code: str,
        png_sha256: str | None = None,
        sidecar_sha256: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.png_sha256 = png_sha256
        self.sidecar_sha256 = sidecar_sha256


def _verified_files(
    root: Path,
    manifest: HandAssetManifestEvidence,
) -> _VerifiedFiles:
    try:
        png_path = _resolve_asset(root, manifest.png_path, ".png")
        sidecar_path = _resolve_asset(root, manifest.sidecar_path, ".json")
        png = png_path.read_bytes()
        sidecar = sidecar_path.read_bytes()
    except (OSError, ValueError) as error:
        raise _EvidenceFailure("asset_path_invalid") from error
    png_hash = hashlib.sha256(png).hexdigest()
    sidecar_hash = hashlib.sha256(sidecar).hexdigest()
    if png_hash != manifest.png_sha256:
        raise _EvidenceFailure("png_hash_mismatch", png_hash, sidecar_hash)
    if sidecar_hash != manifest.sidecar_sha256:
        raise _EvidenceFailure("sidecar_hash_mismatch", png_hash, sidecar_hash)
    return _VerifiedFiles(png, sidecar, png_hash, sidecar_hash)


def _validate_manifest_identity(manifest: HandAssetManifestEvidence) -> str | None:
    if manifest.yaw_degrees not in CANONICAL_YAWS:
        return "noncanonical_yaw"
    if manifest.view_id != canonical_view_id(manifest.yaw_degrees):
        return "manifest_identity_mismatch"
    if manifest.width <= 0 or manifest.height <= 0:
        return "invalid_manifest_dimensions"
    if not _safe_hash(manifest.png_sha256) or not _safe_hash(manifest.sidecar_sha256):
        return "invalid_manifest_hash"
    return None


def _resolve_asset(root: Path, relative: str, suffix: str) -> Path:
    value = PurePosixPath(relative)
    if (
        not relative
        or value.is_absolute()
        or ".." in value.parts
        or "\\" in relative
        or value.suffix.lower() != suffix
    ):
        raise ValueError("unsafe_asset_path")
    resolved = (root / Path(*value.parts)).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("escaped_asset_root")
    return resolved


def _png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 33 or data[:8] != PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise ValueError("invalid_png")
    width, height, depth, color, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", data[16:29]
    )
    if (
        not 1 <= width <= 4096
        or not 1 <= height <= 4096
        or depth != 8
        or color != 6
        or compression
        or filtering
        or interlace
    ):
        raise ValueError("invalid_rgba_png")
    return width, height


def _decode_rgba(data: bytes, width: int, height: int) -> bytes:
    position = 8
    compressed = bytearray()
    while position < len(data):
        if position + 12 > len(data):
            raise ValueError("truncated_png")
        length = struct.unpack(">I", data[position : position + 4])[0]
        kind = data[position + 4 : position + 8]
        end = position + 8 + length
        if end + 4 > len(data):
            raise ValueError("truncated_png_chunk")
        payload = data[position + 8 : end]
        crc = struct.unpack(">I", data[end : end + 4])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise ValueError("png_crc_mismatch")
        position = end + 4
        if kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
    raw = zlib.decompress(compressed)
    stride = width * 4
    if len(raw) != height * (stride + 1):
        raise ValueError("png_scanline_mismatch")
    result = bytearray()
    previous = bytearray(stride)
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        current = bytearray(raw[cursor + 1 : cursor + stride + 1])
        cursor += stride + 1
        _unfilter(current, previous, filter_type)
        result.extend(current)
        previous = current
    return bytes(result)


def _unfilter(current: bytearray, previous: bytearray, filter_type: int) -> None:
    for index in range(len(current)):
        left = current[index - 4] if index >= 4 else 0
        above = previous[index]
        upper_left = previous[index - 4] if index >= 4 else 0
        if filter_type == 1:
            current[index] = (current[index] + left) & 255
        elif filter_type == 2:
            current[index] = (current[index] + above) & 255
        elif filter_type == 3:
            current[index] = (current[index] + (left + above) // 2) & 255
        elif filter_type == 4:
            estimate = left + above - upper_left
            candidates = (left, above, upper_left)
            current[index] = (
                current[index]
                + min(candidates, key=lambda value: abs(estimate - value))
            ) & 255
        elif filter_type != 0:
            raise ValueError("unsupported_png_filter")


def _copy_roi(
    source: tuple[bytes, int],
    target: bytearray,
    roi: _Roi,
    target_x: int,
    *,
    target_width: int,
) -> None:
    source_pixels, source_width = source
    row_bytes = roi.width * 4
    for row in range(roi.height):
        source_start = ((roi.y + row) * source_width + roi.x) * 4
        target_start = (row * target_width + target_x) * 4
        target[target_start : target_start + row_bytes] = source_pixels[
            source_start : source_start + row_bytes
        ]


def _encode_rgba(width: int, height: int, pixels: bytes) -> bytes:
    raw = b"".join(
        b"\0" + pixels[row * width * 4 : (row + 1) * width * 4]
        for row in range(height)
    )
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return (
        struct.pack(">I", len(payload))
        + body
        + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    )


def _sidecar(
    data: bytes,
    manifest: HandAssetManifestEvidence,
    width: int,
    height: int,
) -> dict[str, object]:
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("invalid_sidecar")
    if (
        payload.get("schema_version") != SIDECAR_SCHEMA_VERSION
        or payload.get("view_id") != manifest.view_id
        or payload.get("yaw_degrees") != manifest.yaw_degrees
        or payload.get("width") != width
        or payload.get("height") != height
    ):
        raise ValueError("sidecar_identity_mismatch")
    return payload


@dataclass(frozen=True, slots=True)
class _Roi:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


def _audit_canvas(
    payload: dict[str, object],
    image: bytes,
    width: int,
    height: int,
) -> tuple[bytes, tuple[HandProjection, ...], frozenset[str], frozenset[str]]:
    hands = payload.get("hands")
    if not isinstance(hands, list) or not 0 <= len(hands) <= 2:
        raise ValueError("visible_hand_required")
    parsed = tuple(_hand_with_roi(hand, width, height) for hand in hands)
    projections = tuple(item[0] for item in parsed)
    visible_sides = frozenset(projection.side for projection in projections)
    if len(visible_sides) != len(projections):
        raise ValueError("duplicate_visible_hand_side")
    occluded_sides = _occluded_hand_sides(payload, width, height)
    if visible_sides & occluded_sides:
        raise ValueError("duplicate_hand_side")
    if visible_sides | occluded_sides != HAND_SIDES:
        raise ValueError("hand_side_coverage_incomplete")
    rois = tuple(item[1] for item in parsed)
    if len(rois) == 2 and _intersects(rois[0], rois[1]):
        raise ValueError("hand_rois_overlap")
    protected = _protected_regions(payload, width, height)
    if any(_intersects(roi, region) for roi in rois for region in protected):
        raise ValueError("hand_roi_overlaps_protected_region")
    canvas_width = sum(roi.width for roi in rois) + ROI_GAP * max(0, len(rois) - 1)
    canvas_height = max((roi.height for roi in rois), default=1)
    canvas_width = max(canvas_width, 1)
    canvas = bytearray(canvas_width * canvas_height * 4)
    transformed = []
    offset_x = 0
    for projection, roi in parsed:
        _copy_roi((image, width), canvas, roi, offset_x, target_width=canvas_width)
        transformed.append(
            HandProjection(
                projection.side,
                tuple(
                    Point(point.x - roi.x + offset_x, point.y - roi.y)
                    for point in projection.landmarks
                ),
                projection.occlusions,
                projection.enforce_screen_thumb_side,
            )
        )
        offset_x += roi.width + ROI_GAP
    return (
        _encode_rgba(canvas_width, canvas_height, bytes(canvas)),
        tuple(transformed),
        visible_sides,
        occluded_sides,
    )


def _hand_with_roi(
    value: object,
    width: int,
    height: int,
) -> tuple[HandProjection, _Roi]:
    projection = _projection(value, width, height)
    if not isinstance(value, dict):
        raise TypeError("invalid_hand")
    roi = _roi(value.get("roi"), width, height)
    if not _roi_contains_landmarks(roi, projection.landmarks):
        raise ValueError("hand_roi_missing_landmarks")
    return projection, roi


def _projection(value: object, width: int, height: int) -> HandProjection:
    if not isinstance(value, dict) or value.get("side") not in {"left", "right"}:
        raise TypeError("invalid_hand")
    landmarks = value.get("landmarks")
    if not isinstance(landmarks, list) or len(landmarks) != LANDMARK_COUNT:
        raise ValueError("landmarks_required")
    points = tuple(_point(point, width, height) for point in landmarks)
    occlusions = value.get("occlusions", [])
    if not isinstance(occlusions, list):
        raise TypeError("invalid_occlusions")
    enforce_thumb_side = value.get("thumb_side_check", True)
    if not isinstance(enforce_thumb_side, bool):
        raise TypeError("invalid_thumb_side_check")
    declarations = tuple(_occlusion(item) for item in occlusions)
    if len({item.landmark_index for item in declarations}) != len(declarations):
        raise ValueError("duplicate_occlusion")
    return HandProjection(
        str(value["side"]),
        points,
        declarations,
        enforce_thumb_side,
    )


def _point(value: object, width: int, height: int) -> Point:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(
            not isinstance(item, (int, float))
            or isinstance(item, bool)
            or not math.isfinite(float(item))
            for item in value
        )
    ):
        raise TypeError("invalid_landmark")
    x, y = float(value[0]), float(value[1])
    if not 0 <= x < width or not 0 <= y < height:
        raise ValueError("landmark_out_of_range")
    return Point(x, y)


def _roi(value: object, width: int, height: int) -> _Roi:
    if (
        not isinstance(value, list)
        or len(value) != 4
        or any(not isinstance(item, int) or isinstance(item, bool) for item in value)
    ):
        raise TypeError("invalid_roi")
    roi = _Roi(*value)
    if (
        roi.x < 0
        or roi.y < 0
        or roi.width <= 0
        or roi.height <= 0
        or roi.right > width
        or roi.bottom > height
    ):
        raise ValueError("roi_out_of_range")
    return roi


def _roi_contains_landmarks(roi: _Roi, points: tuple[Point, ...]) -> bool:
    return all(
        roi.x + ROI_LANDMARK_MARGIN <= point.x < roi.right - ROI_LANDMARK_MARGIN
        and roi.y + ROI_LANDMARK_MARGIN <= point.y < roi.bottom - ROI_LANDMARK_MARGIN
        for point in points
    )


def _protected_regions(
    payload: dict[str, object],
    width: int,
    height: int,
) -> tuple[_Roi, ...]:
    values = payload.get("protected_regions")
    if not isinstance(values, list):
        raise TypeError("protected_regions_required")
    labels = []
    regions = []
    for value in values:
        if not isinstance(value, dict) or value.get("label") not in {"face", "body"}:
            raise TypeError("invalid_protected_region")
        labels.append(value["label"])
        regions.append(_roi(value.get("rect"), width, height))
    if set(labels) != {"face", "body"} or len(labels) != 2:
        raise ValueError("face_and_body_regions_required")
    return tuple(regions)


def _occluded_hand_sides(
    payload: dict[str, object],
    width: int,
    height: int,
) -> frozenset[str]:
    values = payload.get("occluded_hands", [])
    if not isinstance(values, list):
        raise TypeError("invalid_occluded_hands")
    sides = []
    for value in values:
        if not isinstance(value, dict) or value.get("side") not in HAND_SIDES:
            raise TypeError("invalid_occluded_hand")
        if value.get("status") != "occluded":
            raise ValueError("invalid_occluded_hand_status")
        reason = value.get("reason")
        occluder_id = value.get("occluder_id")
        if (
            not isinstance(reason, str)
            or not reason.strip()
            or not isinstance(occluder_id, str)
            or not occluder_id.strip()
        ):
            raise ValueError("invalid_occluded_hand_evidence")
        _roi(value.get("region"), width, height)
        sides.append(str(value["side"]))
    if len(set(sides)) != len(sides):
        raise ValueError("duplicate_occluded_hand_side")
    return frozenset(sides)


def _intersects(first: _Roi, second: _Roi) -> bool:
    return not (
        first.right <= second.x
        or second.right <= first.x
        or first.bottom <= second.y
        or second.bottom <= first.y
    )


def _occlusion(value: object) -> JointOcclusion:
    if not isinstance(value, dict):
        raise TypeError("invalid_occlusion")
    index = value.get("landmark_index")
    occluder_id = value.get("occluder_id")
    if (
        not isinstance(index, int)
        or isinstance(index, bool)
        or not 0 <= index < LANDMARK_COUNT
        or not isinstance(occluder_id, str)
        or not occluder_id.strip()
    ):
        raise ValueError("invalid_occlusion")
    return JointOcclusion(index, occluder_id)


def _occluders(payload: dict[str, object]) -> tuple[Occluder, ...]:
    values = payload.get("occluders", [])
    if not isinstance(values, list):
        raise TypeError("invalid_occluders")
    result = tuple(_occluder(value) for value in values)
    if len({item.occluder_id for item in result}) != len(result):
        raise ValueError("duplicate_occluder")
    return result


def _occluder(value: object) -> Occluder:
    if not isinstance(value, dict):
        raise TypeError("invalid_occluder")
    identifier = value.get("id")
    rgb = value.get("rgb")
    tolerance = value.get("tolerance", 12)
    if (
        not isinstance(identifier, str)
        or not identifier.strip()
        or not isinstance(rgb, list)
        or len(rgb) != 3
        or any(not isinstance(item, int) or isinstance(item, bool) or not 0 <= item <= 255 for item in rgb)
        or not isinstance(tolerance, int)
        or isinstance(tolerance, bool)
        or not 0 <= tolerance <= 255
    ):
        raise ValueError("invalid_occluder")
    return Occluder(identifier, tuple(rgb), tolerance)  # type: ignore[arg-type]


def _safe_hash(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _failure(
    code: str,
    view_id: str | None = None,
    png_sha256: str | None = None,
    sidecar_sha256: str | None = None,
) -> HandAssetEvidenceResult:
    return HandAssetEvidenceResult(
        False,
        view_id,
        png_sha256,
        sidecar_sha256,
        (HandAssetEvidenceIssue(code),),
    )
