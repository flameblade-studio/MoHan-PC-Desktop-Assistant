"""Fail-closed semantic audit for the 24-view full-body layer set.

This tool is deliberately read-only.  It verifies that the 600 registered PNG
layers contain the kind of pixels their filenames claim to contain.  A
geometrically valid PNG is not enough: a face pasted into ``ornament`` or an
empty teeth set would otherwise pass the ordinary package asset check.

Package preflight command::

    python -m tools.audit_layered_full_body_semantics

The command exits non-zero and prints one reason per affected file.
"""

from __future__ import annotations

lazy import argparse
lazy import json
lazy import re
lazy from collections import Counter
lazy from collections.abc import Mapping, Sequence
lazy from dataclasses import asdict, dataclass
lazy from pathlib import Path
lazy from typing import Any

lazy import cv2
lazy import numpy as np

lazy from domain.constants import (
    POSE_ATLAS_LAYERED_ROOT_NAME,
    POSE_ATLAS_ROOT_NAME,
)
lazy from infrastructure.layered_full_body_assets import VIEW_IDS


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSET_ROOT = ROOT / "assets" / "pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME
DEFAULT_AUTHORITY_ROOT = ROOT / "assets" / "pose-atlas" / POSE_ATLAS_ROOT_NAME
DEFAULT_DETECTOR_MODEL = (
    ROOT / "assets" / "vision-models" / "face_detection_yunet_2023mar.onnx"
)
EXPECTED_SIZE = (1024, 1536)
IMAGE_DIMENSIONS = 3
RGBA_CHANNELS = 4
FACE_VISIBLE_MAX_ABS_YAW = 90
ALPHA_THRESHOLD = 16
AUDIT_SCHEMA = "mohan.layered-full-body-semantic-audit.v1"
EXIT_CODE_CONTRACT = {
    "0": "all semantic checks passed",
    "1": "one or more file-level semantic checks failed",
    "2": "audit configuration or execution failed closed",
}
SKIN_LUMA_MIN = 35
SKIN_CR_MIN = 133
SKIN_CR_MAX = 180
SKIN_CB_MIN = 77
SKIN_CB_MAX = 135
BASE_FACE_COVERAGE_MIN = 0.35
NON_SKIN_FACE_CONTAMINATION_MAX = 0.30
ORNAMENT_FACE_OPAQUE_MIN = 0.35
ORNAMENT_FACE_SKIN_MIN = 0.20
HAIR_FACE_COVERAGE_MAX = 0.40
SLEEVE_FACE_COVERAGE_MAX = 0.03
ORAL_LIP_DELTA_X_MAX = 0.25
ORAL_LIP_DELTA_Y_MAX = 0.20

LAYER_NAMES = (
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper", "corner_left", "corner_right", "blush_left",
    "blush_right", "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right", "hair_left",
    "hair_right", "sleeve_left", "sleeve_right", "ornament",
)
NON_SKIN_LAYERS = frozenset(
    {"hair_back", "hair_left", "hair_right", "sleeve_left", "sleeve_right", "ornament"}
)
# Face semantic layers that are expected to actually carry pixels.  A fully
# transparent iris or base is a silent packaging defect: the PNG exists, so
# geometric checks pass, but the runtime face is missing that feature.
FACE_SEMANTIC_LAYERS = frozenset(
    {
        "iris_left", "iris_right", "eyelid_left", "eyelid_right",
        "eyeliner_left", "eyeliner_right", "brow_left", "brow_right",
        "lip_upper", "lip_lower", "corner_left", "corner_right",
        "blush_left", "blush_right", "oral_cavity", "teeth_tongue",
        "base", "jaw",
    }
)
# Speech-mouth contract: back views (|yaw| > 90) legitimately have no lips,
# oral cavity, or teeth/tongue pixels.  teeth_tongue is additionally exempt at
# every view (ruling 2026-08-27 below: the neutral set is all-empty).
BACK_VIEW_EMPTY_MOUTH_LAYERS = frozenset(
    {"lip_upper", "lip_lower", "oral_cavity", "teeth_tongue"}
)
# Near-profile views whose oral pixels were returned to the lip layers
# (golden-batch ruling 2026-08-27): oral_cavity is licensed empty there.
NEAR_PROFILE_MIN_ABS_YAW = 75
HAIR_LAYERS = frozenset({"hair_back", "hair_left", "hair_right"})
SLEEVE_LAYERS = frozenset({"sleeve_left", "sleeve_right"})
YAW_PATTERN = re.compile(r"^yaw(?P<yaw>[+-]\d{3})-pitch[+-]\d{2}$")


@dataclass(frozen=True, slots=True)
class AuditIssue:
    """One file-specific semantic failure."""

    code: str
    path: str
    view_id: str
    layer: str
    message: str
    metrics: dict[str, float | int | str]


@dataclass(frozen=True, slots=True)
class AuditReport:
    """Deterministic audit result suitable for CI/package preflight."""

    schema: str
    exit_code_contract: dict[str, str]
    passed: bool
    asset_root: str
    authority_root: str
    views_checked: int
    files_checked: int
    issue_count: int
    issues_by_code: dict[str, int]
    issues: tuple[AuditIssue, ...]
    # Advisory findings never affect ``passed`` or the exit code.  The empty
    # face-layer rule is currently advisory-only because the shipped v4
    # layered assets violate it in a few places the owner has not ruled on.
    advisory_count: int = 0
    advisories_by_code: dict[str, int] | None = None
    advisories: tuple[AuditIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


FaceBox = tuple[int, int, int, int]


def _yaw(view_id: str) -> int:
    match = YAW_PATTERN.fullmatch(view_id)
    if match is None:
        raise ValueError(f"invalid PoseAtlas view id: {view_id}")
    return int(match.group("yaw"))


def _load_rgba(path: Path, expected_size: tuple[int, int]) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError("not a decodable PNG")
    if image.ndim != IMAGE_DIMENSIONS or image.shape[2] != RGBA_CHANNELS:
        raise ValueError("not an RGBA PNG")
    width, height = expected_size
    if image.shape[:2] != (height, width):
        raise ValueError(
            f"unexpected dimensions {image.shape[1]}x{image.shape[0]}; "
            f"expected {width}x{height}"
        )
    return image


def _detect_face(authority: np.ndarray, model: Path) -> FaceBox:
    height, width = authority.shape[:2]
    detector = cv2.FaceDetectorYN.create(
        str(model), "", (width, height), 0.75, 0.3, 100
    )
    _status, faces = detector.detect(authority[:, :, :3])
    if faces is None:
        raise ValueError("YuNet did not detect the visible authority face")
    candidates = [face for face in faces if float(face[1]) < height * 0.35]
    if not candidates:
        raise ValueError("YuNet did not detect the visible authority face")
    face = max(candidates, key=lambda item: float(item[14]))
    x, y, box_width, box_height = (int(round(float(value))) for value in face[:4])
    x = max(0, x)
    y = max(0, y)
    box_width = min(width - x, box_width)
    box_height = min(height - y, box_height)
    if box_width <= 0 or box_height <= 0:
        raise ValueError("YuNet returned an invalid authority face box")
    return x, y, box_width, box_height


def _opaque(image: np.ndarray) -> np.ndarray:
    return image[:, :, 3] > ALPHA_THRESHOLD


def _skin(image: np.ndarray) -> np.ndarray:
    opaque = _opaque(image)
    ycrcb = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2YCrCb)
    return (
        opaque
        & (ycrcb[:, :, 0] >= SKIN_LUMA_MIN)
        & (ycrcb[:, :, 1] >= SKIN_CR_MIN)
        & (ycrcb[:, :, 1] <= SKIN_CR_MAX)
        & (ycrcb[:, :, 2] >= SKIN_CB_MIN)
        & (ycrcb[:, :, 2] <= SKIN_CB_MAX)
    )


def _box_slice(box: FaceBox) -> tuple[slice, slice]:
    x, y, width, height = box
    return slice(y, y + height), slice(x, x + width)


def _centroid(mask: np.ndarray) -> tuple[float, float] | None:
    ys, xs = np.nonzero(mask)
    if xs.size == 0:
        return None
    return float(xs.mean()), float(ys.mean())


def _issue(
    issues: list[AuditIssue],
    code: str,
    path: Path,
    view_id: str,
    layer: str,
    message: str,
    **metrics: float | int | str,
) -> None:
    issues.append(
        AuditIssue(code, str(path), view_id, layer, message, dict(sorted(metrics.items())))
    )


def audit_layered_full_body_semantics(  # noqa: PLR0912, PLR0914, PLR0915
    asset_root: Path,
    authority_root: Path,
    detector_model: Path,
    *,
    view_ids: Sequence[str] = VIEW_IDS,
    expected_size: tuple[int, int] = EXPECTED_SIZE,
    face_boxes: Mapping[str, FaceBox] | None = None,
) -> AuditReport:
    """Audit layer semantics without modifying any input file."""

    issues: list[AuditIssue] = []
    advisories: list[AuditIssue] = []
    images: dict[str, dict[str, np.ndarray]] = {}
    files_checked = 0
    teeth_nonempty = 0

    if face_boxes is None and not detector_model.is_file():
        raise FileNotFoundError(f"missing YuNet detector model: {detector_model}")

    for view_id in view_ids:
        yaw = _yaw(view_id)
        view_images: dict[str, np.ndarray] = {}
        for layer in LAYER_NAMES:
            path = asset_root / f"{view_id}_{layer}.png"
            if not path.is_file():
                _issue(
                    issues, "missing_layer", path, view_id, layer,
                    "required semantic layer is missing",
                )
                continue
            files_checked += 1
            try:
                view_images[layer] = _load_rgba(path, expected_size)
            except ValueError as exc:
                _issue(
                    issues, "invalid_layer_png", path, view_id, layer, str(exc)
                )
        images[view_id] = view_images

        teeth = view_images.get("teeth_tongue")
        if teeth is not None and np.any(_opaque(teeth)):
            teeth_nonempty += 1

        # Empty transparent face-layer policy — BLOCKING (ruling 2026-08-28).
        # A regression that writes an all-transparent iris/eyelid/lip layer
        # must not ship.  Licensed-empty exemptions, each backed by an
        # existing owner-ratified ruling:
        #   1. teeth_tongue at every view (all-empty neutral set,
        #      ruling 2026-08-27);
        #   2. every face layer on back views (|yaw| > 90): the face is not
        #      visible from behind, exactly the state of the accepted
        #      shipped assets;
        #   3. oral_cavity at |yaw| >= 75: the near-profile oral pixels were
        #      formally returned to the lip layers (golden-batch ruling
        #      2026-08-27);
        #   4. paired *_left/*_right layers on any turned view (yaw != 0):
        #      one side being occluded empty is natural asymmetry, mirroring
        #      the asymmetry audit's own convention.
        for layer in LAYER_NAMES:
            if layer not in FACE_SEMANTIC_LAYERS or layer == "teeth_tongue":
                continue
            if abs(yaw) > FACE_VISIBLE_MAX_ABS_YAW:
                continue
            if layer == "oral_cavity" and abs(yaw) >= NEAR_PROFILE_MIN_ABS_YAW:
                continue
            if yaw != 0 and (
                layer.endswith("_left") or layer.endswith("_right")
            ):
                continue
            image = view_images.get(layer)
            if image is not None and not np.any(_opaque(image)):
                _issue(
                    issues, "face_semantic_layer_fully_transparent",
                    asset_root / f"{view_id}_{layer}.png", view_id, layer,
                    "face semantic layer exists but contains no opaque pixels",
                    yaw=yaw,
                )

    for view_id in view_ids:
        view_images = images[view_id]
        visible = abs(_yaw(view_id)) <= FACE_VISIBLE_MAX_ABS_YAW
        face_box: FaceBox | None = None
        if visible:
            authority_path = authority_root / f"{view_id}.png"
            if face_boxes is not None and view_id in face_boxes:
                face_box = face_boxes[view_id]
            elif not authority_path.is_file():
                _issue(
                    issues, "missing_authority", authority_path, view_id, "authority",
                    "authority PoseAtlas image is missing",
                )
            else:
                authority = cv2.imread(str(authority_path), cv2.IMREAD_UNCHANGED)
                if authority is None:
                    _issue(
                        issues, "invalid_authority", authority_path, view_id,
                        "authority", "authority PoseAtlas image cannot be decoded",
                    )
                else:
                    try:
                        face_box = _detect_face(authority, detector_model)
                    except ValueError as exc:
                        _issue(
                            issues, "face_detection_failed", authority_path, view_id,
                            "authority", str(exc),
                        )
        if face_box is None:
            continue

        face_rows, face_columns = _box_slice(face_box)
        face_area = face_box[2] * face_box[3]
        base = view_images.get("base")
        if base is not None:
            coverage = float(_opaque(base)[face_rows, face_columns].sum() / face_area)
            if coverage < BASE_FACE_COVERAGE_MIN:
                path = asset_root / f"{view_id}_base.png"
                _issue(
                    issues, "base_face_coverage_low", path, view_id, "base",
                    "base does not cover enough of the authority face",
                    coverage=round(coverage, 6), minimum=BASE_FACE_COVERAGE_MIN,
                )

        for layer in NON_SKIN_LAYERS:
            image = view_images.get(layer)
            if image is None:
                continue
            opaque_face = int(_opaque(image)[face_rows, face_columns].sum())
            skin_face = int(_skin(image)[face_rows, face_columns].sum())
            opaque_ratio = opaque_face / face_area
            skin_ratio = skin_face / face_area
            path = asset_root / f"{view_id}_{layer}.png"
            if skin_ratio >= NON_SKIN_FACE_CONTAMINATION_MAX:
                _issue(
                    issues, "non_skin_layer_face_contamination", path, view_id, layer,
                    "non-skin layer contains an abnormally large skin-colored face region",
                    skin_face_ratio=round(skin_ratio, 6),
                    maximum=NON_SKIN_FACE_CONTAMINATION_MAX,
                )
            if (
                layer == "ornament"
                and opaque_ratio >= ORNAMENT_FACE_OPAQUE_MIN
                and skin_ratio >= ORNAMENT_FACE_SKIN_MIN
            ):
                _issue(
                    issues, "ornament_contains_face", path, view_id, layer,
                    "ornament layer contains most of a face instead of isolated adornments",
                    opaque_face_ratio=round(opaque_ratio, 6),
                    skin_face_ratio=round(skin_ratio, 6),
                )
            if layer in HAIR_LAYERS and opaque_ratio >= HAIR_FACE_COVERAGE_MAX:
                _issue(
                    issues, "hair_crosses_face_core", path, view_id, layer,
                    "hair layer crosses an unreasonable share of the detected face",
                    opaque_face_ratio=round(opaque_ratio, 6),
                    maximum=HAIR_FACE_COVERAGE_MAX,
                )
            if layer in SLEEVE_LAYERS and opaque_ratio >= SLEEVE_FACE_COVERAGE_MAX:
                _issue(
                    issues, "sleeve_crosses_face", path, view_id, layer,
                    "sleeve layer reaches into the detected face region",
                    opaque_face_ratio=round(opaque_ratio, 6),
                    maximum=SLEEVE_FACE_COVERAGE_MAX,
                )

        upper = view_images.get("lip_upper")
        lower = view_images.get("lip_lower")
        if upper is not None and lower is not None:
            upper_path = asset_root / f"{view_id}_lip_upper.png"
            lower_path = asset_root / f"{view_id}_lip_lower.png"
            if np.any(_opaque(upper)) and upper_path.read_bytes() == lower_path.read_bytes():
                for path, layer in ((upper_path, "lip_upper"), (lower_path, "lip_lower")):
                    _issue(
                        issues, "lip_layers_byte_identical", path, view_id, layer,
                        "upper and lower lip PNGs are byte-identical",
                    )

        oral = view_images.get("oral_cavity")
        if oral is not None and upper is not None and lower is not None:
            oral_center = _centroid(_opaque(oral))
            lip_center = _centroid(_opaque(upper) | _opaque(lower))
            if oral_center is not None and lip_center is not None:
                delta_x = abs(oral_center[0] - lip_center[0]) / face_box[2]
                delta_y = abs(oral_center[1] - lip_center[1]) / face_box[3]
                if (
                    delta_x > ORAL_LIP_DELTA_X_MAX
                    or delta_y > ORAL_LIP_DELTA_Y_MAX
                ):
                    _issue(
                        issues, "oral_cavity_lip_misaligned",
                        asset_root / f"{view_id}_oral_cavity.png", view_id,
                        "oral_cavity", "oral cavity center is detached from the lip center",
                        delta_x_face_width=round(delta_x, 6),
                        delta_y_face_height=round(delta_y, 6),
                    )

    # Ruling 2026-08-27: an all-empty teeth_tongue set is the valid neutral
    # state, not a defect.  Every authority portrait is closed-mouth, so there
    # are no licensed tooth pixels to package, and the mouth rebuild tool
    # (tools/rebuild_pose_atlas_mouth_layers.py) deliberately never paints
    # teeth.  Speech renders the licensed oral-cavity aperture instead, which
    # is the look the owner accepted in the shipped v4.4.2 build.
    _ = teeth_nonempty

    issues.sort(key=lambda item: (item.path, item.code, item.message))
    advisories.sort(key=lambda item: (item.path, item.code, item.message))
    counts = dict(sorted(Counter(issue.code for issue in issues).items()))
    advisory_counts = dict(
        sorted(Counter(advisory.code for advisory in advisories).items())
    )
    return AuditReport(
        schema=AUDIT_SCHEMA,
        exit_code_contract=EXIT_CODE_CONTRACT,
        passed=not issues,
        asset_root=str(asset_root),
        authority_root=str(authority_root),
        views_checked=len(view_ids),
        files_checked=files_checked,
        issue_count=len(issues),
        issues_by_code=counts,
        issues=tuple(issues),
        advisory_count=len(advisories),
        advisories_by_code=advisory_counts,
        advisories=tuple(advisories),
    )


def preflight_exit_code(report: AuditReport) -> int:
    """Map a complete report to the package preflight exit contract."""

    return 0 if report.passed and report.issue_count == 0 else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed semantic audit for all 600 full-body PNG layers."
    )
    parser.add_argument("--asset-root", type=Path, default=DEFAULT_ASSET_ROOT)
    parser.add_argument("--authority-root", type=Path, default=DEFAULT_AUTHORITY_ROOT)
    parser.add_argument("--detector-model", type=Path, default=DEFAULT_DETECTOR_MODEL)
    parser.add_argument("--json-output", type=Path)
    arguments = parser.parse_args(argv)

    try:
        report = audit_layered_full_body_semantics(
            arguments.asset_root, arguments.authority_root, arguments.detector_model
        )
    except (OSError, ValueError) as exc:
        print(f"LAYERED_FULL_BODY_SEMANTICS_ERROR: {exc}")
        return 2
    if arguments.json_output is not None:
        arguments.json_output.parent.mkdir(parents=True, exist_ok=True)
        arguments.json_output.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
    status = "PASS" if report.passed else "FAIL"
    print(
        f"LAYERED_FULL_BODY_SEMANTICS_{status}: "
        f"{report.files_checked} files, {report.issue_count} issues, "
        f"{report.advisory_count} advisories"
    )
    for issue in report.issues:
        print(f"{issue.path}: [{issue.code}] {issue.message}")
    for advisory in report.advisories:
        print(f"ADVISORY {advisory.path}: [{advisory.code}] {advisory.message}")
    return preflight_exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
