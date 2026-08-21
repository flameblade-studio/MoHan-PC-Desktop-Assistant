from __future__ import annotations

lazy import importlib
lazy import json
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Protocol

lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id
lazy from domain.full_body_asset_audit import FullBodyViewEvidence

SIDECAR_SCHEMA_VERSION = 2
SUPPORTED_SIDECAR_VERSIONS = frozenset({1, SIDECAR_SCHEMA_VERSION})
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_RGBA_COLOR_TYPE = 6
PNG_HEADER_LENGTH = 26
POINT_DIMENSIONS = 2
REQUIRED_LANDMARKS = frozenset(
    {
        "crown",
        "left_hip",
        "left_knee",
        "left_ankle",
        "left_heel",
        "left_toe",
        "left_sole",
        "right_hip",
        "right_knee",
        "right_ankle",
        "right_heel",
        "right_toe",
        "right_sole",
    }
)


@dataclass(frozen=True, slots=True)
class FullBodyAssetManifestView:
    view_id: str
    yaw_degrees: int
    canvas_width: int
    canvas_height: int


@dataclass(frozen=True, slots=True)
class FullBodyEvidencePolicy:
    minimum_margin_pixels: int = 8
    minimum_margin_ratio: float = 0.01


DEFAULT_FULL_BODY_EVIDENCE_POLICY = FullBodyEvidencePolicy()


@dataclass(frozen=True, slots=True)
class DecodedRgba:
    width: int
    height: int
    rgba: bytes


class RgbaDecoder(Protocol):
    def decode(self, path: Path) -> DecodedRgba: ...


@dataclass(frozen=True, slots=True)
class FullBodyEvidenceIssue:
    code: str
    yaw_degrees: int | None = None


@dataclass(frozen=True, slots=True)
class FullBodyAssetEvidenceResult:
    passed: bool
    evidence: FullBodyViewEvidence | None
    issues: tuple[FullBodyEvidenceIssue, ...]

    @property
    def problems(self) -> tuple[str, ...]:
        return tuple(
            issue.code
            if issue.yaw_degrees is None
            else f"{issue.code}:{issue.yaw_degrees:+04d}"
            for issue in self.issues
        )


class ImageBackendUnavailable(RuntimeError):
    pass


def build_full_body_asset_evidence(
    png_path: Path,
    sidecar_path: Path,
    manifest: FullBodyAssetManifestView,
    *,
    decoder: RgbaDecoder | None = None,
    policy: FullBodyEvidencePolicy = DEFAULT_FULL_BODY_EVIDENCE_POLICY,
) -> FullBodyAssetEvidenceResult:
    """Convert one real PNG and a safe sidecar into non-image audit evidence."""

    yaw = manifest.yaw_degrees if manifest.yaw_degrees in CANONICAL_YAWS else None
    issue, sidecar, image = _load_evidence_inputs(
        png_path, sidecar_path, manifest, decoder
    )
    if issue is not None or sidecar is None or image is None:
        return _failure(issue or "invalid_evidence_input", yaw)
    issue, bounds, landmarks, occluded = _validate_visual_evidence(
        image, sidecar, policy
    )
    if issue is not None or bounds is None or landmarks is None:
        return _failure(issue or "invalid_visual_evidence", yaw)

    left, top, right, bottom = bounds
    limbs_unclipped = _limbs_clear_canvas_edges(landmarks, image.width, image.height)
    center_x, center_y = _alpha_center_of_mass(image)
    evidence = FullBodyViewEvidence(
        yaw_degrees=manifest.yaw_degrees,
        canvas_width=image.width,
        canvas_height=image.height,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        center_of_mass_x=center_x,
        center_of_mass_y=center_y,
        left_sole_y=_landmark_y(landmarks, "left_sole"),
        right_sole_y=_landmark_y(landmarks, "right_sole"),
        crown_visible=_point_matches_top(landmarks["crown"], top),
        left_leg_visible=_complete_side(landmarks, "left"),
        right_leg_visible=_complete_side(landmarks, "right"),
        left_foot_visible=_complete_foot(landmarks, "left"),
        right_foot_visible=_complete_foot(landmarks, "right"),
        left_sole_visible="left_sole" in landmarks,
        right_sole_visible="right_sole" in landmarks,
        limbs_unclipped=limbs_unclipped,
        occluded_landmarks=occluded,
    )
    return FullBodyAssetEvidenceResult(True, evidence, ())


def _load_evidence_inputs(
    png_path: Path,
    sidecar_path: Path,
    manifest: FullBodyAssetManifestView,
    decoder: RgbaDecoder | None,
) -> tuple[str | None, dict[str, object] | None, DecodedRgba | None]:
    issue = _validate_asset_identity(png_path, manifest)
    sidecar: dict[str, object] | None = None
    image: DecodedRgba | None = None
    try:
        if issue is None:
            sidecar = _load_sidecar(sidecar_path)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        issue = "invalid_sidecar"
    if issue is None and sidecar is not None:
        issue = _validate_sidecar_identity(sidecar, manifest)
    if issue is None and not _is_native_rgba_png(png_path):
        issue = "not_native_rgba_png"
    if issue is None:
        issue, image = _decode_image(png_path, decoder)
    if issue is None and image is not None and (image.width, image.height) != (
        manifest.canvas_width,
        manifest.canvas_height,
    ):
        issue = "canvas_mismatch"
    if (
        issue is None
        and image is not None
        and len(image.rgba) != image.width * image.height * 4
    ):
        issue = "invalid_rgba_buffer"
    return issue, sidecar, image


def _decode_image(
    png_path: Path,
    decoder: RgbaDecoder | None,
) -> tuple[str | None, DecodedRgba | None]:
    try:
        return None, (decoder or _available_decoder()).decode(png_path)
    except ImageBackendUnavailable:
        return "image_backend_unavailable", None
    except (OSError, RuntimeError, TypeError, ValueError):
        return "png_decode_failed", None


def _validate_visual_evidence(
    image: DecodedRgba,
    sidecar: dict[str, object],
    policy: FullBodyEvidencePolicy,
) -> tuple[
    str | None,
    tuple[int, int, int, int] | None,
    dict[str, tuple[int, int]] | None,
    frozenset[str],
]:
    bounds = _alpha_bounds(image)
    landmarks, occluded = _parse_landmarks(sidecar, image.width, image.height)
    issue = _visual_evidence_issue(image, bounds, landmarks, policy)
    return issue, bounds, landmarks, occluded


def _visual_evidence_issue(
    image: DecodedRgba,
    bounds: tuple[int, int, int, int] | None,
    landmarks: dict[str, tuple[int, int]] | None,
    policy: FullBodyEvidencePolicy,
) -> str | None:
    checks = (
        (bounds is None, "empty_alpha"),
        (not _has_real_transparency(image.rgba), "missing_true_transparency"),
        (
            bounds is not None
            and not _has_safe_margin(bounds, image.width, image.height, policy),
            "unsafe_subject_margin",
        ),
        (landmarks is None, "invalid_landmarks"),
        (
            landmarks is not None and not _landmarks_touch_subject(landmarks, image),
            "landmark_outside_subject",
        ),
        (
            landmarks is not None
            and not _limbs_clear_canvas_edges(landmarks, image.width, image.height),
            "limb_touches_canvas_edge",
        ),
    )
    return next((code for failed, code in checks if failed), None)


def _validate_asset_identity(
    png_path: Path,
    manifest: FullBodyAssetManifestView,
) -> str | None:
    if manifest.yaw_degrees not in CANONICAL_YAWS:
        return "noncanonical_yaw"
    expected_id = canonical_view_id(manifest.yaw_degrees)
    if manifest.view_id != expected_id:
        return "manifest_identity_mismatch"
    if png_path.suffix.lower() != ".png" or png_path.stem != expected_id:
        return "filename_identity_mismatch"
    if manifest.canvas_width <= 0 or manifest.canvas_height <= 0:
        return "invalid_manifest_canvas"
    return None


def _load_sidecar(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Sidecar root must be an object.")
    return payload


def _is_native_rgba_png(path: Path) -> bool:
    try:
        header = path.read_bytes()[:PNG_HEADER_LENGTH]
    except OSError:
        return False
    return (
        len(header) == PNG_HEADER_LENGTH
        and header[:8] == PNG_SIGNATURE
        and header[12:16] == b"IHDR"
        and header[25] == PNG_RGBA_COLOR_TYPE
    )


def _validate_sidecar_identity(
    sidecar: dict[str, object],
    manifest: FullBodyAssetManifestView,
) -> str | None:
    if sidecar.get("schema_version") not in SUPPORTED_SIDECAR_VERSIONS:
        return "unsupported_sidecar_version"
    if sidecar.get("view_id") != manifest.view_id:
        return "sidecar_identity_mismatch"
    yaw = sidecar.get("yaw_degrees")
    if isinstance(yaw, bool) or yaw != manifest.yaw_degrees:
        return "sidecar_identity_mismatch"
    return None


def _parse_landmarks(
    sidecar: dict[str, object],
    width: int,
    height: int,
) -> tuple[dict[str, tuple[int, int]] | None, frozenset[str]]:
    raw = sidecar.get("landmarks")
    if not isinstance(raw, dict):
        return None, frozenset()
    occluded = _parse_occluded_landmarks(sidecar)
    if occluded is None or set(raw) | occluded != REQUIRED_LANDMARKS:
        return None, frozenset()
    if set(raw) & occluded:
        return None, frozenset()
    if "crown" not in raw:
        return None, frozenset()
    result: dict[str, tuple[int, int]] = {}
    for name, point in raw.items():
        if (
            not isinstance(name, str)
            or not isinstance(point, list)
            or len(point) != POINT_DIMENSIONS
            or any(isinstance(value, bool) or not isinstance(value, int) for value in point)
        ):
            return None, frozenset()
        x, y = point
        if not 0 <= x < width or not 0 <= y < height:
            return None, frozenset()
        result[name] = (x, y)
    return result, occluded


def _parse_occluded_landmarks(sidecar: dict[str, object]) -> frozenset[str] | None:
    values = sidecar.get("occluded_landmarks", [])
    if not isinstance(values, list):
        return None
    names: list[str] = []
    for value in values:
        if not isinstance(value, dict):
            return None
        name = value.get("name")
        reason = value.get("reason")
        occluder_id = value.get("occluder_id")
        if (
            not isinstance(name, str)
            or name not in REQUIRED_LANDMARKS
            or not isinstance(reason, str)
            or not reason.strip()
            or not isinstance(occluder_id, str)
            or not occluder_id.strip()
        ):
            return None
        names.append(name)
    if len(set(names)) != len(names):
        return None
    return frozenset(names)


def _available_decoder() -> RgbaDecoder:
    try:
        importlib.import_module("PIL.Image")
    except ImportError:
        try:
            importlib.import_module("PySide6.QtGui")
        except ImportError as error:
            raise ImageBackendUnavailable from error
        return _QtRgbaDecoder()
    return _PillowRgbaDecoder()


class _PillowRgbaDecoder:
    def decode(self, path: Path) -> DecodedRgba:
        image_module = importlib.import_module("PIL.Image")
        with image_module.open(path) as source:
            if source.format != "PNG" or source.mode != "RGBA":
                raise ValueError("A native RGBA PNG is required.")
            image = source.copy()
        return DecodedRgba(image.width, image.height, image.tobytes("raw", "RGBA"))


class _QtRgbaDecoder:
    def decode(self, path: Path) -> DecodedRgba:
        qt_gui = importlib.import_module("PySide6.QtGui")
        source = qt_gui.QImage(str(path))
        if source.isNull() or not source.hasAlphaChannel():
            raise ValueError("A readable PNG with alpha is required.")
        image = source.convertToFormat(qt_gui.QImage.Format.Format_RGBA8888)
        size = image.width() * image.height() * 4
        return DecodedRgba(image.width(), image.height(), bytes(image.bits()[:size]))


def _alpha_bounds(image: DecodedRgba) -> tuple[int, int, int, int] | None:
    visible = [
        (index % image.width, index // image.width)
        for index in range(image.width * image.height)
        if image.rgba[index * 4 + 3]
    ]
    if not visible:
        return None
    xs = tuple(point[0] for point in visible)
    ys = tuple(point[1] for point in visible)
    return min(xs), min(ys), max(xs), max(ys)


def _has_real_transparency(rgba: bytes) -> bool:
    alpha = rgba[3::4]
    return bool(alpha) and min(alpha) == 0 and max(alpha) > 0


def _has_safe_margin(
    bounds: tuple[int, int, int, int],
    width: int,
    height: int,
    policy: FullBodyEvidencePolicy,
) -> bool:
    left, top, right, bottom = bounds
    margin = max(
        policy.minimum_margin_pixels,
        round(min(width, height) * policy.minimum_margin_ratio),
    )
    return min(left, top, width - 1 - right, height - 1 - bottom) >= margin


def _landmarks_touch_subject(
    landmarks: dict[str, tuple[int, int]],
    image: DecodedRgba,
) -> bool:
    return all(
        image.rgba[(y * image.width + x) * 4 + 3] > 0
        for x, y in landmarks.values()
    )


def _limbs_clear_canvas_edges(
    landmarks: dict[str, tuple[int, int]],
    width: int,
    height: int,
) -> bool:
    limb_names = set(landmarks) - {"crown"}
    return all(
        0 < landmarks[name][0] < width - 1 and 0 < landmarks[name][1] < height - 1
        for name in limb_names
    )


def _alpha_center_of_mass(image: DecodedRgba) -> tuple[float, float]:
    total = 0
    weighted_x = 0
    weighted_y = 0
    for index, alpha in enumerate(image.rgba[3::4]):
        if not alpha:
            continue
        total += alpha
        weighted_x += (index % image.width) * alpha
        weighted_y += (index // image.width) * alpha
    return weighted_x / total, weighted_y / total


def _point_matches_top(point: tuple[int, int], top: int) -> bool:
    return abs(point[1] - top) <= 1


def _complete_side(landmarks: dict[str, tuple[int, int]], side: str) -> bool:
    names = (f"{side}_hip", f"{side}_knee", f"{side}_ankle")
    return all(name in landmarks for name in names) and all(
        first[1] < second[1]
        for first, second in zip(
            (landmarks[name] for name in names),
            (landmarks[name] for name in names[1:]),
            strict=False,
        )
    )


def _complete_foot(landmarks: dict[str, tuple[int, int]], side: str) -> bool:
    names = tuple(f"{side}_{part}" for part in ("ankle", "heel", "toe", "sole"))
    if not all(name in landmarks for name in names):
        return False
    ankle = landmarks[names[0]]
    heel = landmarks[names[1]]
    toe = landmarks[names[2]]
    sole = landmarks[names[3]]
    return ankle[1] <= heel[1] <= sole[1] and ankle[1] <= toe[1] <= sole[1]


def _landmark_y(landmarks: dict[str, tuple[int, int]], name: str) -> int | None:
    point = landmarks.get(name)
    return None if point is None else point[1]


def _failure(code: str, yaw: int | None) -> FullBodyAssetEvidenceResult:
    return FullBodyAssetEvidenceResult(False, None, (FullBodyEvidenceIssue(code, yaw),))
