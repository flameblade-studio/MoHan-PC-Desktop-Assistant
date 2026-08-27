"""Audit a profile portrait as a non-destructive identity source candidate."""

from __future__ import annotations

lazy import argparse
lazy import json
lazy from collections import Counter
lazy from dataclasses import asdict, dataclass
lazy from pathlib import Path
lazy from statistics import median
lazy from typing import Any

lazy import cv2
lazy import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE = Path(
    "D:/FlamebladeStudio/CodexProjects/release-evidence/"
    "mohan-v4.4.2-visual-audit-2026-08-23/profile-source-left-candidate.png"
)
DEFAULT_AUTHORITIES = (
    ROOT / "assets" / "expressions" / "idle_front.png",
    ROOT / "assets" / "expressions" / "idle_lean.png",
    ROOT / "assets" / "expressions" / "idle.png",
)
DEFAULT_MODEL_ROOT = ROOT / "assets" / "vision-models"
SCHEMA = "mohan.profile-source-acceptance.v1"
IDENTITY_SIMILARITY_MIN = 0.65
FACE_ASPECT_DRIFT_MAX = 0.12
PROPORTION_DRIFT_MAX = 0.20
CHECKERBOARD_RATIO_MAX = 0.02
FACE_CHROMA_PIXELS_MAX = 0
CONTACT_TILE = 280
CONTACT_LABEL_HEIGHT = 38
CONTACT_COLUMNS = 5
CONTACT_ROWS = 2
IMAGE_DIMENSIONS = 3
RGBA_CHANNELS = 4
ALPHA_THRESHOLD = 16
BACKGROUND_NEUTRAL_SPREAD = 4
BACKGROUND_LIGHT_MIN = 220
CHROMA_BRIGHTNESS_MIN = 35
MIN_FOREHEAD_ROWS = 8
FOREHEAD_OUTWARD_MAX = 0.04
FOREHEAD_CURVATURE_MAX = 0.04


@dataclass(frozen=True, slots=True)
class SourceIssue:
    code: str
    subject: str
    message: str
    metrics: dict[str, float | int | str]


@dataclass(frozen=True, slots=True)
class SourceAcceptanceReport:
    schema: str
    passed: bool
    candidate: str
    authorities: tuple[str, ...]
    candidate_dimensions: tuple[int, int]
    candidate_channels: int
    identity_similarities: dict[str, float]
    geometry: dict[str, Any]
    checkerboard_background_ratio: float
    face_green_cyan_pixels: int
    face_roi_extraction_approved: bool
    mirrored_right_source_approved: bool
    issue_count: int
    issues_by_code: dict[str, int]
    issues: tuple[SourceIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _issue(
    issues: list[SourceIssue],
    code: str,
    subject: Path | str,
    message: str,
    **metrics: float | int | str,
) -> None:
    issues.append(SourceIssue(code, str(subject), message, dict(sorted(metrics.items()))))


def _load(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if (
        image is None
        or image.ndim != IMAGE_DIMENSIONS
        or image.shape[2] not in {IMAGE_DIMENSIONS, RGBA_CHANNELS}
    ):
        raise ValueError(f"not a decodable RGB/RGBA PNG: {path}")
    return image


def _detect_all(image: np.ndarray, detector_model: Path) -> np.ndarray:
    detector = cv2.FaceDetectorYN.create(
        str(detector_model), "", (image.shape[1], image.shape[0]), 0.45, 0.3, 100
    )
    _status, faces = detector.detect(image[:, :, :3])
    if faces is None:
        raise ValueError("no face detected")
    return faces


def _primary(faces: np.ndarray) -> np.ndarray:
    return max(faces, key=lambda face: float(face[14]))


def _feature(
    image: np.ndarray, face: np.ndarray, recognizer: Any
) -> np.ndarray:
    aligned = recognizer.alignCrop(image[:, :, :3], face)
    return recognizer.feature(aligned)


def _geometry(face: np.ndarray) -> dict[str, float]:
    x, y, width, height = (float(value) for value in face[:4])
    landmarks = face[4:14].reshape(5, 2).astype(np.float64)
    eye_center_y = float(landmarks[:2, 1].mean())
    mouth_center_y = float(landmarks[3:, 1].mean())
    return {
        "face_aspect": width / height,
        "eye_span_ratio": abs(float(landmarks[0, 0] - landmarks[1, 0])) / width,
        "nose_eye_vertical_ratio": abs(float(landmarks[2, 1]) - eye_center_y) / height,
        "mouth_span_ratio": abs(float(landmarks[3, 0] - landmarks[4, 0])) / width,
        "mouth_chin_proxy_ratio": max(0.0, (y + height - mouth_center_y) / height),
    }


def _checkerboard_ratio(image: np.ndarray) -> float:
    color = image[:, :, :3].astype(np.int16)
    neutral = np.ptp(color, axis=2) <= BACKGROUND_NEUTRAL_SPREAD
    light = np.min(color, axis=2) >= BACKGROUND_LIGHT_MIN
    return float(np.mean(neutral & light))


def _face_chroma_count(image: np.ndarray, face: np.ndarray) -> int:
    x, y, width, height = (int(round(float(value))) for value in face[:4])
    x = max(0, x)
    y = max(0, y)
    roi = image[y : min(image.shape[0], y + height), x : min(image.shape[1], x + width), :3]
    blue, green, red = cv2.split(roi)
    blue_i = blue.astype(np.int16)
    green_i = green.astype(np.int16)
    red_i = red.astype(np.int16)
    green_spot = (
        (green_i > red_i + 10)
        & (green_i > blue_i + 4)
        & (green > CHROMA_BRIGHTNESS_MIN)
    )
    cyan_spot = (
        (green_i > red_i + 8)
        & (blue_i > red_i + 8)
        & (green > CHROMA_BRIGHTNESS_MIN)
    )
    return int(np.count_nonzero(green_spot | cyan_spot))


def _forehead_profile(image: np.ndarray, face: np.ndarray) -> dict[str, float]:
    x, y, width, height = (float(value) for value in face[:4])
    landmarks = face[4:14].reshape(5, 2)
    faces_right = float(landmarks[2, 0]) > x + width * 0.5
    color = image[:, :, :3].astype(np.int16)
    if image.shape[2] == RGBA_CHANNELS:
        foreground = image[:, :, 3] > ALPHA_THRESHOLD
    else:
        foreground = ~(
            (np.ptp(color, axis=2) <= BACKGROUND_NEUTRAL_SPREAD)
            & (np.min(color, axis=2) >= BACKGROUND_LIGHT_MIN)
        )
    top = max(0, int(y + height * 0.03))
    bottom = min(image.shape[0], int(y + height * 0.40))
    left = max(0, int(x - width * 0.15))
    right = min(image.shape[1], int(x + width * 1.15))
    contour: list[float] = []
    for row in range(top, bottom):
        columns = np.flatnonzero(foreground[row, left:right])
        if columns.size:
            column = int(columns.max() if faces_right else columns.min()) + left
            contour.append(float(column if faces_right else -column))
    if len(contour) < MIN_FOREHEAD_ROWS:
        return {"measured": 0.0, "outward_ratio": 1.0, "curvature_ratio": 1.0}
    values = np.asarray(contour)
    endpoint = max(2, len(values) // 8)
    chord = np.linspace(
        float(np.median(values[:endpoint])),
        float(np.median(values[-endpoint:])),
        len(values),
    )
    return {
        "measured": 1.0,
        "outward_ratio": float(np.max((values - chord) / width)),
        "curvature_ratio": float(np.max(np.abs(np.diff(values, n=2))) / width),
    }


def audit_profile_source_candidate(  # noqa: PLR0912, PLR0914, PLR0915
    candidate_path: Path,
    authorities: tuple[Path, ...],
    model_root: Path,
) -> tuple[SourceAcceptanceReport, dict[str, np.ndarray]]:
    detector_model = model_root / "face_detection_yunet_2023mar.onnx"
    recognizer_model = model_root / "face_recognition_sface_2021dec.onnx"
    if not detector_model.is_file() or not recognizer_model.is_file():
        raise FileNotFoundError("bundled YuNet/SFace models are incomplete")
    candidate = _load(candidate_path)
    authority_images = {path.name: _load(path) for path in authorities}
    issues: list[SourceIssue] = []
    channels = candidate.shape[2]
    if channels != RGBA_CHANNELS:
        _issue(
            issues, "source_has_no_alpha", candidate_path,
            "candidate is opaque RGB and cannot be directly registered as a layer",
            channels=channels,
        )
    checker_ratio = _checkerboard_ratio(candidate)
    if checker_ratio > CHECKERBOARD_RATIO_MAX:
        _issue(
            issues, "checkerboard_background_embedded", candidate_path,
            "checkerboard transparency preview is baked into RGB pixels",
            ratio=round(checker_ratio, 6), maximum=CHECKERBOARD_RATIO_MAX,
        )
    candidate_faces = _detect_all(candidate, detector_model)
    if len(candidate_faces) != 1:
        _issue(
            issues, "ambiguous_face_detection", candidate_path,
            "candidate does not produce exactly one unambiguous face detection",
            detected_faces=len(candidate_faces),
        )
    candidate_face = _primary(candidate_faces)
    authority_faces = {
        name: _primary(_detect_all(image, detector_model))
        for name, image in authority_images.items()
    }
    recognizer = cv2.FaceRecognizerSF.create(str(recognizer_model), "")
    candidate_feature = _feature(candidate, candidate_face, recognizer)
    similarities = {
        name: float(
            recognizer.match(
                candidate_feature,
                _feature(authority_images[name], face, recognizer),
                cv2.FaceRecognizerSF_FR_COSINE,
            )
        )
        for name, face in authority_faces.items()
    }
    identity_median = median(similarities.values())
    if identity_median < IDENTITY_SIMILARITY_MIN:
        _issue(
            issues, "identity_similarity_low", candidate_path,
            "candidate does not match the three half-body identity authorities",
            median_similarity=round(identity_median, 6),
            minimum=IDENTITY_SIMILARITY_MIN,
        )
    candidate_geometry = _geometry(candidate_face)
    authority_geometry = {
        name: _geometry(face) for name, face in authority_faces.items()
    }
    authority_medians = {
        metric: median(item[metric] for item in authority_geometry.values())
        for metric in candidate_geometry
    }
    geometry_drift = {
        metric: abs(candidate_geometry[metric] - authority_medians[metric])
        / max(authority_medians[metric], 1e-9)
        for metric in candidate_geometry
    }
    if geometry_drift["face_aspect"] > FACE_ASPECT_DRIFT_MAX:
        _issue(
            issues, "face_aspect_drift", candidate_path,
            "profile face aspect differs from the identity authorities",
            drift=round(geometry_drift["face_aspect"], 6),
            maximum=FACE_ASPECT_DRIFT_MAX,
        )
    for metric, drift in geometry_drift.items():
        if metric == "face_aspect" or drift <= PROPORTION_DRIFT_MAX:
            continue
        _issue(
            issues, "facial_proportion_drift", candidate_path,
            f"candidate {metric} differs excessively from authority median",
            metric=metric, drift=round(drift, 6), maximum=PROPORTION_DRIFT_MAX,
        )
    chroma_count = _face_chroma_count(candidate, candidate_face)
    if chroma_count > FACE_CHROMA_PIXELS_MAX:
        _issue(
            issues, "face_green_cyan_pixels", candidate_path,
            "candidate face ROI contains red-deficient green/cyan pixels",
            anomalous_pixels=chroma_count,
        )
    forehead = _forehead_profile(candidate, candidate_face)
    if forehead["outward_ratio"] > FOREHEAD_OUTWARD_MAX:
        _issue(
            issues, "forehead_outward_bulge", candidate_path,
            "candidate forehead contour protrudes beyond the smooth profile limit",
            outward_ratio=round(forehead["outward_ratio"], 6),
            maximum=FOREHEAD_OUTWARD_MAX,
        )
    if forehead["curvature_ratio"] > FOREHEAD_CURVATURE_MAX:
        _issue(
            issues, "forehead_curvature_discontinuity", candidate_path,
            "candidate forehead contour contains an abrupt curvature change",
            curvature_ratio=round(forehead["curvature_ratio"], 6),
            maximum=FOREHEAD_CURVATURE_MAX,
        )
    extraction_blockers = {
        "source_has_no_alpha",
        "checkerboard_background_embedded",
        "ambiguous_face_detection",
        "identity_similarity_low",
        "face_aspect_drift",
        "facial_proportion_drift",
        "face_green_cyan_pixels",
        "forehead_outward_bulge",
        "forehead_curvature_discontinuity",
    }
    extract_ok = not any(issue.code in extraction_blockers for issue in issues)
    if not extract_ok:
        _issue(
            issues, "face_roi_extraction_not_approved", candidate_path,
            "face ROI extraction is unsafe until identity/background/raster blockers pass",
        )
        _issue(
            issues, "mirrored_right_source_not_approved", candidate_path,
            "right-side mirroring would duplicate the rejected source defects",
        )
    issues.sort(key=lambda issue: (issue.subject, issue.code, issue.message))
    counts = dict(sorted(Counter(issue.code for issue in issues).items()))
    geometry: dict[str, Any] = {
        "candidate": {key: round(value, 6) for key, value in candidate_geometry.items()},
        "authority_medians": {
            key: round(value, 6) for key, value in authority_medians.items()
        },
        "relative_drift": {key: round(value, 6) for key, value in geometry_drift.items()},
        "forehead_profile": {key: round(value, 6) for key, value in forehead.items()},
    }
    report = SourceAcceptanceReport(
        schema=SCHEMA,
        passed=not issues,
        candidate=str(candidate_path),
        authorities=tuple(str(path) for path in authorities),
        candidate_dimensions=(candidate.shape[1], candidate.shape[0]),
        candidate_channels=channels,
        identity_similarities={key: round(value, 6) for key, value in similarities.items()},
        geometry=geometry,
        checkerboard_background_ratio=round(checker_ratio, 6),
        face_green_cyan_pixels=chroma_count,
        face_roi_extraction_approved=extract_ok,
        mirrored_right_source_approved=extract_ok,
        issue_count=len(issues),
        issues_by_code=counts,
        issues=tuple(issues),
    )
    previews = {candidate_path.name: candidate, **authority_images}
    return report, previews


def _tile(image: np.ndarray, label: str, *, mirror: bool = False) -> np.ndarray:
    source = cv2.flip(image, 1) if mirror else image
    color = source[:, :, :3]
    scale = min(CONTACT_TILE / color.shape[1], CONTACT_TILE / color.shape[0])
    resized = cv2.resize(
        color,
        (max(1, int(color.shape[1] * scale)), max(1, int(color.shape[0] * scale))),
        interpolation=cv2.INTER_AREA,
    )
    canvas = np.full((CONTACT_TILE + CONTACT_LABEL_HEIGHT, CONTACT_TILE, 3), 238, np.uint8)
    top = (CONTACT_TILE - resized.shape[0]) // 2
    left = (CONTACT_TILE - resized.shape[1]) // 2
    canvas[top : top + resized.shape[0], left : left + resized.shape[1]] = resized
    cv2.putText(
        canvas, label, (8, CONTACT_TILE + 27), cv2.FONT_HERSHEY_SIMPLEX,
        0.58, (30, 30, 30), 1, cv2.LINE_AA,
    )
    return canvas


def write_contact_sheet(
    previews: dict[str, np.ndarray], candidate_name: str, output: Path
) -> None:
    candidate = previews[candidate_name]
    names = [name for name in previews if name != candidate_name]
    top_tiles = [
        _tile(candidate, "candidate: opaque RGB"),
        _tile(candidate, "mirrored candidate", mirror=True),
        *[_tile(previews[name], name) for name in names],
    ][:CONTACT_COLUMNS]
    face_tiles = []
    for index, tile in enumerate(top_tiles):
        crop = tile[40:CONTACT_TILE, 40:CONTACT_TILE]
        face_tiles.append(_tile(crop, f"detail {index + 1}"))
    while len(top_tiles) < CONTACT_COLUMNS:
        top_tiles.append(np.full_like(top_tiles[0], 238))
        face_tiles.append(np.full_like(top_tiles[0], 238))
    sheet = np.vstack((np.hstack(top_tiles), np.hstack(face_tiles)))
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), sheet):
        raise OSError(f"could not write contact sheet: {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a profile identity source candidate.")
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    arguments = parser.parse_args()
    report, previews = audit_profile_source_candidate(
        arguments.candidate, DEFAULT_AUTHORITIES, arguments.model_root
    )
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = arguments.output_dir / "profile-source-left-candidate-acceptance.json"
    report_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_contact_sheet(
        previews,
        arguments.candidate.name,
        arguments.output_dir / "profile-source-left-candidate-contact-sheet.png",
    )
    print(
        f"PROFILE_SOURCE_ACCEPTANCE_{'PASS' if report.passed else 'FAIL'}: "
        f"{report.issue_count} issues; report={report_path}"
    )
    for issue in report.issues:
        print(f"[{issue.code}] {issue.message}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
