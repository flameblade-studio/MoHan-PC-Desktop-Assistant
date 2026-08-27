from __future__ import annotations

lazy from pathlib import Path

lazy import cv2
lazy import numpy as np

lazy from tools.audit_layered_full_body_semantics import (
    DEFAULT_DETECTOR_MODEL,
    LAYER_NAMES,
    audit_layered_full_body_semantics,
    main,
)


SIZE = (128, 192)
VIEW = "yaw+000-pitch+00"
FACE_BOX = (40, 20, 48, 70)
EXPECTED_LAYER_COUNT = 25
EXPECTED_IDENTICAL_LIP_ISSUES = 2


def _blank() -> np.ndarray:
    return np.zeros((SIZE[1], SIZE[0], 4), dtype=np.uint8)


def _paint(image: np.ndarray, box: tuple[int, int, int, int], color: tuple[int, ...]) -> None:
    x, y, width, height = box
    image[y : y + height, x : x + width] = color


def _write(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(path), image)


def _clean_set(root: Path, views: tuple[str, ...] = (VIEW,)) -> dict[str, tuple[int, ...]]:
    boxes: dict[str, tuple[int, ...]] = {}
    for view in views:
        boxes[view] = FACE_BOX
        layers = {layer: _blank() for layer in LAYER_NAMES}
        _paint(layers["body"], (28, 100, 72, 82), (80, 60, 40, 255))
        _paint(layers["base"], FACE_BOX, (150, 180, 220, 255))
        _paint(layers["hair_back"], (34, 10, 60, 12), (20, 20, 20, 255))
        _paint(layers["hair_left"], (34, 20, 5, 55), (20, 20, 20, 255))
        _paint(layers["hair_right"], (89, 20, 5, 55), (20, 20, 20, 255))
        _paint(layers["sleeve_left"], (18, 105, 9, 55), (120, 60, 25, 255))
        _paint(layers["sleeve_right"], (101, 105, 9, 55), (120, 60, 25, 255))
        _paint(layers["ornament"], (60, 7, 8, 6), (230, 230, 230, 255))
        _paint(layers["oral_cavity"], (59, 67, 10, 4), (20, 20, 50, 255))
        _paint(layers["lip_upper"], (57, 65, 14, 2), (100, 100, 190, 255))
        _paint(layers["lip_lower"], (58, 71, 12, 2), (110, 110, 200, 255))
        _paint(layers["teeth_tongue"], (62, 68, 4, 1), (230, 230, 230, 255))
        for layer, image in layers.items():
            _write(root / f"{view}_{layer}.png", image)
    return boxes


def _audit(root: Path, views: tuple[str, ...] = (VIEW,)):
    return audit_layered_full_body_semantics(
        root,
        root / "authority",
        root / "unused.onnx",
        view_ids=views,
        expected_size=SIZE,
        face_boxes={view: FACE_BOX for view in views},
    )


def test_clean_semantic_set_passes(tmp_path: Path) -> None:
    _clean_set(tmp_path)
    report = _audit(tmp_path)
    assert report.passed
    assert report.issue_count == 0
    assert report.files_checked == EXPECTED_LAYER_COUNT


def test_reports_face_pollution_and_crossing_per_file(tmp_path: Path) -> None:
    _clean_set(tmp_path)
    face = (42, 22, 44, 62)
    for layer in ("ornament", "hair_left", "sleeve_left"):
        image = cv2.imread(str(tmp_path / f"{VIEW}_{layer}.png"), cv2.IMREAD_UNCHANGED)
        _paint(image, face, (150, 180, 220, 255))
        _write(tmp_path / f"{VIEW}_{layer}.png", image)
    report = _audit(tmp_path)
    assert not report.passed
    codes = {(issue.layer, issue.code) for issue in report.issues}
    assert ("ornament", "ornament_contains_face") in codes
    assert ("ornament", "non_skin_layer_face_contamination") in codes
    assert ("hair_left", "hair_crosses_face_core") in codes
    assert ("sleeve_left", "sleeve_crosses_face") in codes


def test_reports_identical_lips_and_detached_oral_cavity(tmp_path: Path) -> None:
    _clean_set(tmp_path)
    upper = tmp_path / f"{VIEW}_lip_upper.png"
    lower = tmp_path / f"{VIEW}_lip_lower.png"
    lower.write_bytes(upper.read_bytes())
    oral = _blank()
    _paint(oral, (82, 35, 8, 4), (20, 20, 50, 255))
    _write(tmp_path / f"{VIEW}_oral_cavity.png", oral)
    report = _audit(tmp_path)
    assert (
        report.issues_by_code["lip_layers_byte_identical"]
        == EXPECTED_IDENTICAL_LIP_ISSUES
    )
    assert report.issues_by_code["oral_cavity_lip_misaligned"] == 1


def test_all_empty_teeth_layers_are_the_valid_neutral_state(tmp_path: Path) -> None:
    _clean_set(tmp_path)
    _write(tmp_path / f"{VIEW}_teeth_tongue.png", _blank())
    report = _audit(tmp_path)
    assert "teeth_tongue_all_views_empty" not in report.issues_by_code


def test_empty_face_layers_surface_as_nonblocking_advisories(tmp_path: Path) -> None:
    # _clean_set deliberately leaves the eye/brow/blush/corner/jaw layers
    # blank, so a visible view must report them as advisories without ever
    # blocking packaging: the shipped v4 assets still violate the strict
    # rule and the owner has not ruled on them yet.
    _clean_set(tmp_path)
    report = _audit(tmp_path)
    assert report.passed
    assert report.issue_count == 0
    advisory_pairs = {(a.view_id, a.layer) for a in report.advisories}
    assert (VIEW, "iris_left") in advisory_pairs
    assert (VIEW, "jaw") in advisory_pairs
    # teeth_tongue is a valid all-empty neutral set at every view.
    assert (VIEW, "teeth_tongue") not in advisory_pairs
    assert report.advisory_count == len(report.advisories)
    assert all(
        advisory.code == "face_semantic_layer_fully_transparent"
        for advisory in report.advisories
    )


def test_back_view_mouth_layers_are_exempt_from_empty_advisories(tmp_path: Path) -> None:
    back = "yaw+105-pitch+00"
    _clean_set(tmp_path, views=(back,))
    for layer in ("lip_upper", "lip_lower", "oral_cavity", "teeth_tongue"):
        _write(tmp_path / f"{back}_{layer}.png", _blank())
    report = audit_layered_full_body_semantics(
        tmp_path,
        tmp_path / "authority",
        tmp_path / "unused.onnx",
        view_ids=(back,),
        expected_size=SIZE,
        face_boxes={},
    )
    assert report.passed
    advisory_layers = {a.layer for a in report.advisories}
    # Speech-mouth contract: back views legitimately ship empty mouth layers.
    assert advisory_layers.isdisjoint(
        {"lip_upper", "lip_lower", "oral_cavity", "teeth_tongue"}
    )
    # Other empty face layers on a back view are still surfaced for ruling.
    assert "iris_left" in advisory_layers

def test_reports_insufficient_base_face_coverage(tmp_path: Path) -> None:
    _clean_set(tmp_path)
    base = _blank()
    _paint(base, (40, 20, 5, 5), (150, 180, 220, 255))
    _write(tmp_path / f"{VIEW}_base.png", base)
    report = _audit(tmp_path)
    assert report.issues_by_code["base_face_coverage_low"] == 1


def test_cli_is_a_fail_closed_single_preflight_command(tmp_path: Path, capsys) -> None:
    _clean_set(tmp_path)
    _write(tmp_path / f"{VIEW}_teeth_tongue.png", _blank())
    # Use a back view so the CLI does not require a synthetic detector model.
    back = "yaw-180-pitch+00"
    for layer in LAYER_NAMES:
        source = tmp_path / f"{VIEW}_{layer}.png"
        (tmp_path / f"{back}_{layer}.png").write_bytes(source.read_bytes())
    exit_code = main(
        (
            "--asset-root", str(tmp_path),
            "--authority-root", str(tmp_path / "authority"),
            "--detector-model", str(DEFAULT_DETECTOR_MODEL),
        )
    )
    # Default CLI audits all 24 views, so missing files and empty teeth fail closed.
    assert exit_code == 1
    output = capsys.readouterr().out
    assert "LAYERED_FULL_BODY_SEMANTICS_FAIL" in output
    assert "[missing_layer]" in output
