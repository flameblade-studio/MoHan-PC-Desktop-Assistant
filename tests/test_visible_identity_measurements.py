"""Source-binding, visibility, and placement tests for the visible tools."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import shutil
lazy import tempfile
lazy from collections.abc import Iterator
lazy from pathlib import Path

lazy import numpy as np
lazy import pytest
lazy from PIL import Image

lazy from domain import visible_identity_audit as audit
lazy from tools import identity_geometry as geometry
lazy from tools import measure_pose_atlas_visible_identity as measure
lazy from tools import visible_scale_placement as placement

CANVAS = (64, 96)
WIDE_CANVAS = (128, 96)
VIEW = "yaw+000-pitch+00"
FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "scratchpad/mohan-v5-visible-geometry-scale-166/worker/.pytest-fixtures"
)
ALPHA_FULL = 255
ALPHA_FAINT = 100
ALPHA_THRESHOLD_VALUE = 128
INSIDE = (34.0, 72.0)
SPREAD_STEP = 3.0
EXPECTED_FULL_HEIGHT = 70
EXPECTED_OPAQUE_HEIGHT = 60
EXPECTED_TAIL_PIXELS = 16
SQUARE_SIDE = 16
PLACEMENT_TOLERANCE_PX = 1.0


@pytest.fixture()
def workdir() -> Iterator[Path]:
    """A repo-local scratch directory, independent of the system temp policy."""

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(dir=FIXTURE_ROOT))
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_rgba(
    path: Path, *, alpha: int = ALPHA_FULL, size: tuple[int, int] = CANVAS
) -> None:
    image = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    image[..., :3] = 120
    image[8 : size[1] - 8, 8 : size[0] - 8, 3] = alpha
    Image.fromarray(image).save(path)


def write_mask(path: Path, mask: np.ndarray) -> None:
    image = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
    image[..., 3] = np.where(mask, 200, 0).astype(np.uint8)
    Image.fromarray(image).save(path)


def vertex_layout(canvas: tuple[int, int]) -> dict[int, tuple[float, float]]:
    """Spread the measured vertices across the middle of the canvas."""

    centre_x, centre_y = canvas[0] / 2.0, canvas[1] / 2.0
    layout = {}
    for position, index in enumerate(geometry._used_vertices()):
        layout[index] = (
            min(max(centre_x + (position % 6 - 2.5) * SPREAD_STEP, 2.0), canvas[0] - 3.0),
            min(max(centre_y + (position // 6 - 1.5) * SPREAD_STEP, 2.0), canvas[1] - 3.0),
        )
    return layout


def points(
    canvas: tuple[int, int] = CANVAS,
    *,
    offset: tuple[float, float] = (0.0, 0.0),
    scale: float = 1.0,
    z_overrides: dict[int, float] | None = None,
) -> list[dict[str, float]]:
    layout = vertex_layout(canvas)
    centre = (canvas[0] / 2.0, canvas[1] / 2.0)
    rows = []
    for index in range(geometry.EXPLICIT_MESH_POINT_COUNT):
        x, y = layout.get(index, centre)
        x = (x * scale + offset[0]) / canvas[0]
        y = (y * scale + offset[1]) / canvas[1]
        z = 0.0 if z_overrides is None else z_overrides.get(index, 0.0)
        rows.append({"x": x, "y": y, "z": z})
    return rows


def artifact_document(
    landmarks: list[dict[str, float]], png_sha: str, canvas: tuple[int, int]
) -> dict:
    return {
        "confidence": 0.9,
        "landmarks": landmarks,
        "size": list(canvas),
        "source": {"path": f"assets/pose-atlas/v5-base/{VIEW}.png", "sha256": png_sha},
    }


def fixture_atlas(
    root: Path,
    *,
    canvas: tuple[int, int] = CANVAS,
    z_overrides: dict[int, float] | None = None,
    offset: tuple[float, float] = (0.0, 0.0),
) -> tuple[Path, Path, dict]:
    atlas = root / "v5-base"
    layers = root / "v5-base-layered"
    atlas.mkdir(parents=True)
    layers.mkdir(parents=True)
    write_rgba(atlas / f"{VIEW}.png", size=canvas)
    png_sha = sha256(atlas / f"{VIEW}.png")
    artifact = atlas / f"{VIEW}.native-landmarks.json"
    artifact.write_text(
        json.dumps(artifact_document(
            points(canvas, z_overrides=z_overrides, offset=offset), png_sha, canvas
        )),
        encoding="utf-8",
    )
    sidecar = {
        "view_id": VIEW,
        "yaw_degrees": 0,
        "width": canvas[0],
        "height": canvas[1],
        "measurement": {"source_sha256": png_sha, "target_subject_height": 80},
        "native_face_landmarks": {
            "landmark_count": geometry.EXPLICIT_MESH_POINT_COUNT,
            "source": {
                "path": f"assets/pose-atlas/v5-base/{VIEW}.png",
                "sha256": png_sha,
            },
            "artifact": {
                "path": f"assets/pose-atlas/v5-base/{artifact.name}",
                "sha256": sha256(artifact),
            },
        },
    }
    sidecar_path = atlas / f"{VIEW}.landmarks.json"
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
    record = {
        "view_id": VIEW,
        "normalized_sha256": png_sha,
        "body_sidecar_sha256": sha256(sidecar_path),
        "native_face": {
            "landmark_count": geometry.EXPLICIT_MESH_POINT_COUNT,
            "source_sha256": png_sha,
        },
    }
    empty = np.zeros((canvas[1], canvas[0]), bool)
    for part in (*measure.OCCLUDER_LAYERS, *measure.SKIN_LAYERS, *measure.FEATURE_LAYERS):
        write_mask(layers / f"{VIEW}_{part}.png", empty)
    # Authored bare skin under the whole subject so skin support is real.
    skin = np.zeros((canvas[1], canvas[0]), bool)
    skin[8 : canvas[1] - 8, 8 : canvas[0] - 8] = True
    for part in measure.SKIN_LAYERS:
        write_mask(layers / f"{VIEW}_{part}.png", skin)
    return atlas, layers, record


def evidence_for(
    directory: Path,
    *,
    canvas: tuple[int, int] = CANVAS,
    z_overrides: dict[int, float] | None = None,
    offset: tuple[float, float] = (0.0, 0.0),
) -> tuple[geometry.ViewGeometryEvidence, Path, Path, dict]:
    atlas, layers, record = fixture_atlas(
        directory, canvas=canvas, z_overrides=z_overrides, offset=offset
    )
    evidence, binding = measure.collect_view(atlas, layers, 0, record)
    return evidence, atlas, layers, binding


def test_pixel_keeps_float_coordinates_and_distance_is_scale_invariant(
    workdir: Path,
) -> None:
    small, _atlas, _layers, _binding = evidence_for(workdir)
    doubled, _a, _l, _b = evidence_for(workdir / "double", canvas=(128, 192))
    small_layout = vertex_layout(CANVAS)
    doubled_layout = vertex_layout((128, 192))

    for index in (10, 152, 234, 454):
        assert isinstance(small.pixel(index)[0], float)
        assert doubled.pixel(index)[0] == doubled_layout[index][0]
    ratio_small = small.pixel_distance(234, 454) / small.pixel_distance(10, 152)
    ratio_large = doubled.pixel_distance(234, 454) / doubled.pixel_distance(10, 152)
    assert ratio_small == pytest.approx(ratio_large)
    assert small.pixel(234) == pytest.approx(small_layout[234])


def test_non_square_canvas_keeps_pixel_mapping_honest(workdir: Path) -> None:
    evidence, _atlas, _layers, _binding = evidence_for(workdir, canvas=WIDE_CANVAS)
    layout = vertex_layout(WIDE_CANVAS)

    assert evidence.canvas == WIDE_CANVAS
    assert evidence.pixel(10) == pytest.approx(layout[10])
    assert evidence.pixel_distance(10, 152) > 0


def test_out_of_canvas_sample_point_fails_closed(workdir: Path) -> None:
    evidence, _atlas, _layers, _binding = evidence_for(workdir, offset=(200.0, 200.0))

    record = geometry.classify_vertex(evidence, 10)

    assert record.state == geometry.VISIBILITY_UNVERIFIED
    report = geometry.measure_view_fields(evidence)
    assert report["fields"]["face_length_width"]["status"] == geometry.UNSUPPORTED_SOURCE
    assert report["fields"]["face_length_width"]["reason"].startswith(
        "visibility_unverified"
    )


def test_empty_window_raises_instead_of_returning_nan() -> None:
    mask = np.zeros((4, 4), bool)

    with pytest.raises(geometry.GeometryError, match="sample_point_out_of_canvas"):
        geometry._window(mask, 9, 9, 2)
    with pytest.raises(geometry.GeometryError, match="empty_sample_window"):
        geometry._window(np.zeros((0, 0), bool), 0, 0, 2)


def test_authored_hair_layer_supports_occlusion_but_empty_layer_does_not(
    workdir: Path,
) -> None:
    evidence, atlas, layers, _binding = evidence_for(workdir)
    hair = np.zeros(evidence.canvas[::-1], bool)
    hair[8 : evidence.canvas[1] - 8, 8 : evidence.canvas[0] - 8] = True
    write_mask(layers / f"{VIEW}_hair_back.png", hair)
    covered, _a, _l, _b = evidence_for(workdir / "covered")
    covered = geometry.ViewGeometryEvidence(
        view_id=covered.view_id,
        yaw_degrees=covered.yaw_degrees,
        canvas=covered.canvas,
        png_sha256=covered.png_sha256,
        artifact_sha256=covered.artifact_sha256,
        points=covered.points,
        figure_alpha=covered.figure_alpha,
        skin_alpha=covered.skin_alpha,
        occluder_alpha=hair,
        occluder_layer_alpha={"hair_back": hair},
        feature_alpha=covered.feature_alpha,
        chin_row=covered.chin_row,
    )

    occluded = geometry.classify_vertex(covered, 10)
    assert occluded.state == geometry.OCCLUDED_BY_AUTHORED_LAYER
    assert occluded.occluder_layers == ("hair_back",)
    report = geometry.measure_view_fields(covered)
    assert report["fields"]["face_length_width"]["status"] == geometry.OCCLUDED
    assert report["fields"]["face_length_width"]["reason"].startswith(
        "occluded_by_authored_layer"
    )
    # An empty feature layer is not evidence of visibility.
    eye = geometry.classify_vertex(evidence, 133)
    assert eye.state == geometry.VISIBILITY_UNVERIFIED
    empty_report = geometry.measure_view_fields(evidence)
    assert empty_report["fields"]["eye_spacing_width"]["status"] == (
        geometry.UNSUPPORTED_SOURCE
    )
    assert "133" in empty_report["fields"]["eye_spacing_width"]["reason"]
    assert atlas.is_dir()


def test_relative_depth_is_a_labelled_diagnostic_not_a_verdict(workdir: Path) -> None:
    plain, _atlas, _layers, _binding = evidence_for(workdir)
    deep, _a, _l, _b = evidence_for(
        workdir / "deep", z_overrides={234: 0.9, 454: -0.9}
    )

    plain_report = geometry.measure_view_fields(plain)
    deep_report = geometry.measure_view_fields(deep)

    assert geometry.classify_vertex(plain, 234).state == (
        geometry.classify_vertex(deep, 234).state
    )
    assert max(deep_report["relative_depth_diagnostic"].values()) > 1.0
    assert plain_report["relative_depth_diagnostic"] != (
        deep_report["relative_depth_diagnostic"]
    )
    assert "never used as an occlusion" in deep_report["relative_depth_note"]


def test_measurements_are_labelled_model_derived(workdir: Path) -> None:
    evidence, _atlas, _layers, binding = evidence_for(workdir)

    report = geometry.measure_view_fields(evidence)

    assert binding["problems"] == []
    measured = [
        record for record in report["fields"].values()
        if record["status"] == geometry.MEASURED
    ]
    assert measured
    assert all(
        record["measurement_basis"] == geometry.MODEL_DERIVED_BASIS
        for record in measured
    )
    assert report["measurement_basis"] == geometry.MODEL_DERIVED_BASIS


def test_contract_record_conversion_keeps_not_applicable_without_a_digest(
    workdir: Path,
) -> None:
    evidence, _atlas, _layers, _binding = evidence_for(workdir)
    report = geometry.measure_view_fields(
        evidence, applicable_fields=audit.BAND_FIELDS[audit.FaceVisibility.PROFILE]
    )

    record = measure._to_contract_record(
        "eye_spacing_width", report["fields"]["eye_spacing_width"]
    )

    assert record.status is audit.FieldStatus.NOT_APPLICABLE
    assert record.source_sha256 is None


def test_collect_view_reports_declaration_drift_instead_of_passing(workdir: Path) -> None:
    atlas, layers, record = fixture_atlas(workdir)
    artifact = atlas / f"{VIEW}.native-landmarks.json"
    artifact.write_bytes(artifact.read_bytes() + b"\n")

    _evidence, binding = measure.collect_view(atlas, layers, 0, record)

    assert "artifact_declaration_sha_mismatch" in binding["problems"]


def test_collect_view_rejects_wrong_shape_missing_keys_and_bad_types(
    workdir: Path,
) -> None:
    atlas, layers, record = fixture_atlas(workdir)
    artifact = atlas / f"{VIEW}.native-landmarks.json"
    document = json.loads(artifact.read_text(encoding="utf-8"))
    document["landmarks"].pop()
    artifact.write_text(json.dumps(document), encoding="utf-8")
    record["body_sidecar_sha256"] = sha256(atlas / f"{VIEW}.landmarks.json")
    with pytest.raises(measure.SourceContractError, match="478 points"):
        measure.collect_view(atlas, layers, 0, record)

    atlas2, layers2, record2 = fixture_atlas(workdir / "second")
    artifact2 = atlas2 / f"{VIEW}.native-landmarks.json"
    document2 = json.loads(artifact2.read_text(encoding="utf-8"))
    del document2["landmarks"][3]["y"]
    artifact2.write_text(json.dumps(document2), encoding="utf-8")
    with pytest.raises(measure.SourceContractError, match="lacks x/y/z"):
        measure.validate_points(document2, VIEW)

    document2["landmarks"][3]["y"] = True
    with pytest.raises(measure.SourceContractError, match="not a finite number"):
        measure.validate_points(document2, VIEW)
    assert record2["view_id"] == VIEW and layers2.is_dir()


def test_collect_view_rejects_a_missing_layer_source(workdir: Path) -> None:
    atlas, layers, record = fixture_atlas(workdir)
    (layers / f"{VIEW}_hair_back.png").unlink()

    with pytest.raises(measure.SourceContractError, match="missing occluder layer"):
        measure.collect_view(atlas, layers, 0, record)


def test_image_height_measurement_records_every_threshold(workdir: Path) -> None:
    png = workdir / "view.png"
    image = np.zeros((96, 64, 4), dtype=np.uint8)
    image[10:20, 10:50, 3] = ALPHA_FAINT
    image[20:80, 10:50, 3] = ALPHA_FULL
    Image.fromarray(image).save(png)

    measured = measure.image_height_measurement(png, (64, 96))

    assert measured["nonzero"]["bbox_height_px"] == EXPECTED_FULL_HEIGHT
    assert measured["semi"]["bbox_height_px"] == EXPECTED_OPAQUE_HEIGHT
    assert measured["opaque"]["bbox_height_px"] == EXPECTED_OPAQUE_HEIGHT


def test_visibility_threshold_includes_128() -> None:
    alpha = np.zeros((32, 32), dtype=np.uint8)
    alpha[8:24, 8:24] = ALPHA_THRESHOLD_VALUE - 1

    with pytest.raises(placement.PlacementError, match="empty_alpha_above_threshold"):
        placement.visible_bounds(alpha)
    alpha[8:24, 8:24] = ALPHA_THRESHOLD_VALUE
    assert placement.visible_bounds(alpha).height == SQUARE_SIDE


@pytest.mark.parametrize("alpha", [1, 128, 255])
def test_placement_rejects_a_disconnected_island_lost_outside_canvas(alpha: int) -> None:
    rgba = np.zeros((32, 32, 4), dtype=np.uint8)
    rgba[10:20, 10:20, 3] = 255
    rgba[2, 2, 3] = alpha
    affine = placement.UniformPlacement(
        view_id="v", mode=placement.HEIGHT_NORMALISED, scale=1.0,
        offset_x=-4.0, offset_y=0.0,
        visible_bounds=placement.VisibleBounds(10, 19, 10, 19), canvas=(32, 32),
    )
    with pytest.raises(placement.PlacementError, match="would_crop_nonzero_alpha"):
        placement.place_image(rgba, affine)


def test_visible_bounds_rejects_empty_alpha_and_edge_touch() -> None:
    with pytest.raises(placement.PlacementError, match="empty_alpha_above_threshold"):
        placement.visible_bounds(np.zeros((32, 32), dtype=np.uint8))
    touching = np.zeros((32, 32), dtype=np.uint8)
    touching[0:10, 4:12] = ALPHA_FULL
    with pytest.raises(placement.PlacementError, match="touches_canvas_edge"):
        placement.visible_bounds(touching)


def test_height_normalised_placement_is_uniform_and_lands_on_standard() -> None:
    reference = np.zeros((64, 64), dtype=np.uint8)
    reference[10:40, 20:44] = ALPHA_FULL
    standard = placement.display_standard(reference, view_id="ref", sha256="0" * 64)
    smaller = placement.VisibleBounds(top=12, bottom=36, left=22, right=42)

    placed = placement.compute_placement(
        smaller, standard, view_id="v", mode=placement.HEIGHT_NORMALISED
    )

    assert placed.to_dict()["uniform_scale_x_equals_y"] is True
    assert placed.placed_height == pytest.approx(standard.reference_height)
    assert placed.sole_row == pytest.approx(standard.baseline_row)
    assert standard.alpha_threshold == ALPHA_THRESHOLD_VALUE


def test_refined_placement_and_transform_check_are_within_budget() -> None:
    alpha = np.zeros((64, 64), dtype=np.uint8)
    alpha[10:40, 20:44] = ALPHA_FULL
    rgba = np.dstack([np.zeros((64, 64, 3), np.uint8), alpha])
    standard = placement.display_standard(alpha, view_id="ref", sha256="0" * 64)
    placed = placement.refine_placement(
        rgba,
        placement.compute_placement(
            placement.visible_bounds(alpha), standard, view_id="v",
            mode=placement.HEIGHT_NORMALISED,
        ),
        standard,
        tolerance_px=PLACEMENT_TOLERANCE_PX,
    )
    result = placement.place_image(rgba, placed)
    check = placement.transform_is_exact(placed, alpha, result[..., 3])
    crop = placement.crop_report(placed, {"state": rgba}, {"state": result})

    assert check["exact"] is True
    assert crop["visible_cropped"] is False
    assert abs(placement.placed_bounds_delta(placed, result[..., 3])["sole_delta_px"]) <= (
        PLACEMENT_TOLERANCE_PX
    )
    colours = result[result[..., 3] > 0][:, :3]
    assert (colours == 0).all()


def test_crop_report_flags_a_visible_pixel_at_the_edge() -> None:
    alpha = np.zeros((32, 32), dtype=np.uint8)
    alpha[0:12, 4:12] = ALPHA_FULL
    rgba = np.dstack([np.zeros((32, 32, 3), np.uint8), alpha])
    placed = placement.UniformPlacement(
        view_id="v", mode=placement.HEIGHT_NORMALISED, scale=1.0,
        offset_x=0.0, offset_y=0.0,
        visible_bounds=placement.VisibleBounds(0, 11, 4, 11), canvas=(32, 32),
    )

    crop = placement.crop_report(placed, {"state": rgba}, {"state": rgba})

    assert crop["visible_cropped"] is True


def test_transform_checks_actual_pixel_centres_and_both_vertical_edges() -> None:
    alpha = np.zeros((64, 64), dtype=np.uint8)
    alpha[10:40, 20:44] = ALPHA_FULL
    rgba = np.dstack([np.zeros((64, 64, 3), np.uint8), alpha])
    affine = placement.UniformPlacement(
        view_id="v", mode=placement.HEIGHT_NORMALISED, scale=0.9,
        offset_x=1.49, offset_y=2.49,
        visible_bounds=placement.visible_bounds(alpha), canvas=(64, 64),
    )
    result = placement.place_image(rgba, affine)
    check = placement.transform_is_exact(affine, alpha, result[..., 3])
    assert check["exact"] is True
    result[5:9, 20:44, 3] = ALPHA_FULL
    assert placement.transform_is_exact(affine, alpha, result[..., 3])["exact"] is False


def test_subthreshold_tail_is_reported_not_silently_dropped() -> None:
    alpha = np.zeros((32, 32), dtype=np.uint8)
    alpha[8:20, 8:20] = ALPHA_FULL
    alpha[0:4, 0:4] = ALPHA_FAINT

    report = placement.subthreshold_report(alpha)

    assert report["tail_pixels"] == EXPECTED_TAIL_PIXELS
    assert report["tail_touches_edge"] is True
    assert report["tail_bbox"] == {"top": 0, "bottom": 3, "left": 0, "right": 3}
