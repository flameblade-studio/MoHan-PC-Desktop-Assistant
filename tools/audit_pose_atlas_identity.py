"""Fail-closed visual identity audit for the 24 static PoseAtlas yaw PNGs."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import math
lazy import re
lazy from collections import Counter
lazy from collections.abc import Mapping, Sequence
lazy from dataclasses import asdict, dataclass
lazy from pathlib import Path
lazy from typing import Any

lazy import cv2
lazy import numpy as np

lazy from infrastructure.layered_full_body_assets import VIEW_IDS


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ATLAS_ROOT = ROOT / "assets" / "pose-atlas" / "v4"
DEFAULT_DETECTOR_MODEL = (
    ROOT / "assets" / "vision-models" / "face_detection_yunet_2023mar.onnx"
)
DEFAULT_BASELINE = DEFAULT_ATLAS_ROOT / "identity-audit-baseline.json"
EXPECTED_SIZE = (1024, 1536)
IMAGE_DIMENSIONS = 3
RGBA_CHANNELS = 4
MIN_FOREHEAD_CONTOUR_ROWS = 8
AUDIT_SCHEMA = "mohan.pose-atlas-static-identity-audit.v2"
BASELINE_SCHEMA = "mohan.pose-atlas-identity-baseline.v1"
SHA256_HEX_LENGTH = 64
EXIT_CODE_CONTRACT = {
    "0": "all static identity checks passed",
    "1": "one or more visual identity checks failed",
    "2": "audit configuration or execution failed closed",
}
VISIBLE_MAX_ABS_YAW = 90
PROFILE_YAWS = frozenset({-90, -75, -60, 60, 75, 90})
ALPHA_THRESHOLD = 16
FACE_ALPHA_COVERAGE_MIN = 0.75
MIRROR_ASPECT_DRIFT_MAX = 0.12
ADJACENT_FACE_CENTER_DELTA_MAX = 0.08
ADJACENT_NOSE_POSITION_DELTA_MAX = 0.35
FOREHEAD_OUTWARD_MAX = 0.025
FOREHEAD_SLOPE_STEP_MAX = 0.05
FOREHEAD_CURVATURE_STEP_MAX = 0.04
CHROMA_RED_DEFICIT_MIN = 8
CHROMA_MIN_BRIGHTNESS = 35
YAW_PATTERN = re.compile(r"^yaw(?P<yaw>[+-]\d{3})-pitch[+-]\d{2}$")


@dataclass(frozen=True, slots=True)
class FaceEvidence:
    box: tuple[float, float, float, float]
    landmarks: tuple[tuple[float, float], ...]
    confidence: float


@dataclass(frozen=True, slots=True)
class IdentityIssue:
    code: str
    path: str
    view_id: str
    message: str
    metrics: dict[str, float | int | str]


@dataclass(frozen=True, slots=True)
class IdentityReport:
    schema: str
    exit_code_contract: dict[str, str]
    passed: bool
    atlas_root: str
    views_checked: int
    files_checked: int
    issue_count: int
    issues_by_code: dict[str, int]
    issues: tuple[IdentityIssue, ...]
    waived_issue_count: int = 0
    waived_issues_by_code: dict[str, int] | None = None
    waived_issues: tuple[IdentityIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_identity_baseline(path: Path) -> dict[str, tuple[str, frozenset[str]]]:
    """Load the owner-accepted identity baseline, failing closed on any defect.

    The baseline waives *pre-existing* findings on files the owner formally
    accepted, pinned by SHA-256.  Any byte change to a view invalidates its
    entry, so every rule applies in full to new or regenerated images.
    """

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != BASELINE_SCHEMA:
        raise ValueError(f"unexpected identity baseline schema in {path}")
    views = payload.get("views")
    if not isinstance(views, dict) or not views:
        raise ValueError(f"identity baseline has no views: {path}")
    baseline: dict[str, tuple[str, frozenset[str]]] = {}
    for view_id, entry in views.items():
        sha256 = entry.get("sha256")
        codes = entry.get("waived_issue_codes")
        if not isinstance(sha256, str) or len(sha256) != SHA256_HEX_LENGTH:
            raise ValueError(f"identity baseline {view_id} has no valid sha256")
        if not isinstance(codes, list) or not all(isinstance(c, str) for c in codes):
            raise ValueError(f"identity baseline {view_id} has no valid issue codes")
        baseline[view_id] = (sha256.lower(), frozenset(codes))
    return baseline


def _yaw(view_id: str) -> int:
    match = YAW_PATTERN.fullmatch(view_id)
    if match is None:
        raise ValueError(f"invalid PoseAtlas view id: {view_id}")
    return int(match.group("yaw"))


def _load_rgba(path: Path, expected_size: tuple[int, int]) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError("not a decodable PNG")
    width, height = expected_size
    if image.ndim != IMAGE_DIMENSIONS or image.shape[2] != RGBA_CHANNELS:
        raise ValueError("not an RGBA PNG")
    if image.shape[:2] != (height, width):
        raise ValueError(
            f"unexpected dimensions {image.shape[1]}x{image.shape[0]}; "
            f"expected {width}x{height}"
        )
    return image


def _detect(image: np.ndarray, model: Path) -> FaceEvidence:
    height, width = image.shape[:2]
    detector = cv2.FaceDetectorYN.create(
        str(model), "", (width, height), 0.75, 0.3, 100
    )
    _status, faces = detector.detect(image[:, :, :3])
    candidates = [] if faces is None else [face for face in faces if face[1] < height * 0.35]
    if not candidates:
        raise ValueError("YuNet did not detect the visible face")
    face = max(candidates, key=lambda item: float(item[14]))
    landmarks = tuple(
        (float(point[0]), float(point[1]))
        for point in face[4:14].reshape(5, 2)
    )
    return FaceEvidence(
        tuple(float(value) for value in face[:4]), landmarks, float(face[14])
    )


def _issue(
    issues: list[IdentityIssue],
    code: str,
    path: Path,
    view_id: str,
    message: str,
    **metrics: float | int | str,
) -> None:
    issues.append(
        IdentityIssue(code, str(path), view_id, message, dict(sorted(metrics.items())))
    )


def _forehead_metrics(
    image: np.ndarray, evidence: FaceEvidence
) -> tuple[float, float, float]:
    x, y, width, height = evidence.box
    nose_x = evidence.landmarks[2][0]
    faces_right = nose_x > x + width * 0.5
    mask = image[:, :, 3] > ALPHA_THRESHOLD
    top = max(0, int(math.floor(y + height * 0.03)))
    bottom = min(image.shape[0], int(math.ceil(y + height * 0.40)))
    left = max(0, int(math.floor(x - width * 0.15)))
    right = min(image.shape[1], int(math.ceil(x + width * 1.15)))
    contour: list[float] = []
    for row in range(top, bottom):
        columns = np.flatnonzero(mask[row, left:right])
        if columns.size == 0:
            continue
        column = int(columns.max() if faces_right else columns.min()) + left
        contour.append(float(column if faces_right else -column))
    if len(contour) < MIN_FOREHEAD_CONTOUR_ROWS:
        raise ValueError("insufficient alpha silhouette for forehead audit")
    values = np.asarray(contour)
    endpoint = max(2, len(values) // 8)
    chord = np.linspace(
        float(np.median(values[:endpoint])),
        float(np.median(values[-endpoint:])),
        len(values),
    )
    outward = float(np.max((values - chord) / width))
    slope = float(np.max(np.abs(np.diff(values))) / width)
    curvature = float(np.max(np.abs(np.diff(values, n=2))) / width)
    return outward, slope, curvature


def _mouth_chroma_count(image: np.ndarray, evidence: FaceEvidence) -> int:
    mouths = evidence.landmarks[3:5]
    center_x = sum(point[0] for point in mouths) / 2
    center_y = sum(point[1] for point in mouths) / 2
    mouth_width = max(8.0, abs(mouths[0][0] - mouths[1][0]))
    left = max(0, int(center_x - mouth_width))
    right = min(image.shape[1], int(center_x + mouth_width))
    top = max(0, int(center_y - mouth_width * 0.6))
    bottom = min(image.shape[0], int(center_y + mouth_width * 0.7))
    blue, green, red = cv2.split(image[top:bottom, left:right, :3])
    blue_i = blue.astype(np.int16)
    green_i = green.astype(np.int16)
    red_i = red.astype(np.int16)
    green_spot = (
        (green_i > red_i + CHROMA_RED_DEFICIT_MIN)
        & (green_i > blue_i + 4)
        & (green > CHROMA_MIN_BRIGHTNESS)
    )
    cyan_spot = (
        (green_i > red_i + CHROMA_RED_DEFICIT_MIN)
        & (blue_i > red_i + CHROMA_RED_DEFICIT_MIN)
        & (green > CHROMA_MIN_BRIGHTNESS)
    )
    return int(np.count_nonzero(green_spot | cyan_spot))


def audit_pose_atlas_identity(  # noqa: PLR0912, PLR0914, PLR0915
    atlas_root: Path,
    detector_model: Path,
    *,
    view_ids: Sequence[str] = VIEW_IDS,
    expected_size: tuple[int, int] = EXPECTED_SIZE,
    face_evidence: Mapping[str, FaceEvidence] | None = None,
    baseline: Mapping[str, tuple[str, frozenset[str]]] | None = None,
) -> IdentityReport:
    """Audit static PoseAtlas identity and silhouette continuity read-only."""

    if face_evidence is None and not detector_model.is_file():
        raise FileNotFoundError(f"missing YuNet detector model: {detector_model}")
    digests: dict[str, str] = {}
    issues: list[IdentityIssue] = []
    images: dict[str, np.ndarray] = {}
    faces: dict[str, FaceEvidence] = {}
    files_checked = 0
    for view_id in view_ids:
        yaw = _yaw(view_id)
        path = atlas_root / f"{view_id}.png"
        if not path.is_file():
            _issue(issues, "missing_view", path, view_id, "static PoseAtlas view is missing")
            continue
        files_checked += 1
        if baseline is not None and view_id in baseline:
            digests[view_id] = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            image = _load_rgba(path, expected_size)
        except ValueError as exc:
            _issue(issues, "invalid_view_png", path, view_id, str(exc))
            continue
        images[view_id] = image
        if abs(yaw) > VISIBLE_MAX_ABS_YAW:
            continue
        try:
            evidence = (
                face_evidence[view_id]
                if face_evidence is not None
                else _detect(image, detector_model)
            )
        except (KeyError, ValueError) as exc:
            _issue(issues, "visible_face_not_detected", path, view_id, str(exc))
            continue
        faces[view_id] = evidence
        x, y, width, height = evidence.box
        left = max(0, int(x))
        top = max(0, int(y))
        right = min(image.shape[1], int(math.ceil(x + width)))
        bottom = min(image.shape[0], int(math.ceil(y + height)))
        if right <= left or bottom <= top:
            _issue(issues, "face_roi_invalid", path, view_id, "face ROI is outside canvas")
            continue
        coverage = float(
            np.mean(image[top:bottom, left:right, 3] > ALPHA_THRESHOLD)
        )
        if coverage < FACE_ALPHA_COVERAGE_MIN:
            _issue(
                issues, "face_roi_visibility_low", path, view_id,
                "detected face ROI is not sufficiently registered to visible pixels",
                alpha_coverage=round(coverage, 6), minimum=FACE_ALPHA_COVERAGE_MIN,
            )
        chroma_count = _mouth_chroma_count(image, evidence)
        if chroma_count:
            _issue(
                issues, "mouth_green_cyan_pixels", path, view_id,
                "mouth/face ROI contains red-deficient green or cyan pixels",
                anomalous_pixels=chroma_count,
            )
        if yaw in PROFILE_YAWS:
            try:
                outward, slope, curvature = _forehead_metrics(image, evidence)
            except ValueError as exc:
                _issue(issues, "forehead_silhouette_unmeasurable", path, view_id, str(exc))
                continue
            if outward >= FOREHEAD_OUTWARD_MAX:
                _issue(
                    issues, "forehead_outward_bulge", path, view_id,
                    "profile forehead protrudes beyond the permitted smooth chord",
                    outward_ratio=round(outward, 6), maximum=FOREHEAD_OUTWARD_MAX,
                )
            if slope > FOREHEAD_SLOPE_STEP_MAX:
                _issue(
                    issues, "forehead_slope_discontinuity", path, view_id,
                    "profile forehead contains an abrupt one-row slope step",
                    slope_step_ratio=round(slope, 6), maximum=FOREHEAD_SLOPE_STEP_MAX,
                )
            if curvature > FOREHEAD_CURVATURE_STEP_MAX:
                _issue(
                    issues, "forehead_curvature_discontinuity", path, view_id,
                    "profile forehead contains an abrupt curvature step",
                    curvature_step_ratio=round(curvature, 6),
                    maximum=FOREHEAD_CURVATURE_STEP_MAX,
                )

    for yaw in (60, 75, 90):
        left_id = f"yaw{-yaw:+04d}-pitch+00"
        right_id = f"yaw{yaw:+04d}-pitch+00"
        if left_id not in faces or right_id not in faces:
            continue
        left_aspect = faces[left_id].box[2] / faces[left_id].box[3]
        right_aspect = faces[right_id].box[2] / faces[right_id].box[3]
        drift = abs(left_aspect - right_aspect) / max(left_aspect, right_aspect)
        if drift > MIRROR_ASPECT_DRIFT_MAX:
            for view_id in (left_id, right_id):
                _issue(
                    issues, "mirror_face_aspect_drift", atlas_root / f"{view_id}.png",
                    view_id, "left/right mirrored face aspect differs excessively",
                    aspect_drift=round(drift, 6), maximum=MIRROR_ASPECT_DRIFT_MAX,
                )

    ordered = sorted(
        (( _yaw(view_id), view_id, face) for view_id, face in faces.items()),
        key=lambda item: item[0],
    )
    canvas_width = expected_size[0]
    for (_left_yaw, left_id, left), (_right_yaw, right_id, right) in zip(
        ordered, ordered[1:], strict=False
    ):
        left_center = (left.box[0] + left.box[2] / 2) / canvas_width
        right_center = (right.box[0] + right.box[2] / 2) / canvas_width
        center_delta = abs(left_center - right_center)
        left_nose = (left.landmarks[2][0] - left.box[0]) / left.box[2]
        right_nose = (right.landmarks[2][0] - right.box[0]) / right.box[2]
        nose_delta = abs(left_nose - right_nose)
        if center_delta > ADJACENT_FACE_CENTER_DELTA_MAX or nose_delta > ADJACENT_NOSE_POSITION_DELTA_MAX:
            # The jump belongs to the pair, so record one issue per view.
            # A baseline waiver then only holds while BOTH owner-accepted
            # files keep their exact pinned bytes: regenerating either side
            # of the pair re-exposes the registration rule in full.
            for view_id in (left_id, right_id):
                _issue(
                    issues, "adjacent_face_registration_jump",
                    atlas_root / f"{view_id}.png", view_id,
                    f"face registration jumps between {left_id} and {right_id}",
                    center_delta=round(center_delta, 6),
                    nose_position_delta=round(nose_delta, 6),
                )

    blocking: list[IdentityIssue] = []
    waived: list[IdentityIssue] = []
    for issue in issues:
        entry = None if baseline is None else baseline.get(issue.view_id)
        if (
            entry is not None
            and digests.get(issue.view_id) == entry[0]
            and issue.code in entry[1]
        ):
            waived.append(issue)
        else:
            blocking.append(issue)
    blocking.sort(key=lambda item: (item.path, item.code, item.message))
    waived.sort(key=lambda item: (item.path, item.code, item.message))
    counts = dict(sorted(Counter(issue.code for issue in blocking).items()))
    waived_counts = dict(sorted(Counter(issue.code for issue in waived).items()))
    return IdentityReport(
        schema=AUDIT_SCHEMA,
        exit_code_contract=EXIT_CODE_CONTRACT,
        passed=not blocking,
        atlas_root=str(atlas_root),
        views_checked=len(view_ids),
        files_checked=files_checked,
        issue_count=len(blocking),
        issues_by_code=counts,
        issues=tuple(blocking),
        waived_issue_count=len(waived),
        waived_issues_by_code=waived_counts,
        waived_issues=tuple(waived),
    )


def preflight_exit_code(report: IdentityReport) -> int:
    return 0 if report.passed and report.issue_count == 0 else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed visual identity audit for static PoseAtlas v4."
    )
    parser.add_argument("--atlas-root", type=Path, default=DEFAULT_ATLAS_ROOT)
    parser.add_argument("--detector-model", type=Path, default=DEFAULT_DETECTOR_MODEL)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--json-output", type=Path)
    arguments = parser.parse_args(argv)
    try:
        baseline = (
            load_identity_baseline(arguments.baseline)
            if arguments.baseline.is_file()
            else None
        )
        report = audit_pose_atlas_identity(
            arguments.atlas_root, arguments.detector_model, baseline=baseline
        )
    except (OSError, ValueError) as exc:
        print(f"POSE_ATLAS_STATIC_IDENTITY_ERROR: {exc}")
        return 2
    if arguments.json_output is not None:
        arguments.json_output.parent.mkdir(parents=True, exist_ok=True)
        arguments.json_output.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
    status = "PASS" if report.passed else "FAIL"
    print(
        f"POSE_ATLAS_STATIC_IDENTITY_{status}: "
        f"{report.files_checked} files, {report.issue_count} issues, "
        f"{report.waived_issue_count} waived by owner-accepted baseline"
    )
    for issue in report.issues:
        print(f"{issue.path}: [{issue.code}] {issue.message}")
    return preflight_exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
