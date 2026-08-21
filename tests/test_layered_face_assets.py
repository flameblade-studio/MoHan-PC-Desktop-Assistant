from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from domain.constants import FULL_BODY_LAYER_COUNT
lazy from infrastructure.layered_face_assets import (
    LAYERED_FACE_DIMENSION,
    LAYER_NAMES,
    load_layered_face_assets,
)
lazy from infrastructure.layered_face_renderer import (
    MAX_CACHED_LAYER_PIXMAPS,
    LayeredParametricFaceRenderer,
)

LAYERED_DIR = ROOT / "assets" / "expressions" / "layered"
AUTHORITY_DIR = ROOT / "assets" / "expressions"
MAX_MEAN_CHANNEL_ERROR = 6.0
MAX_TRANSPARENT_SAMPLE_RATIO = 0.01
IDENTITY_SAMPLE_STEP = 4


def _app() -> object:
    return QApplication.instance() or QApplication([])


def test_layered_manifest_loads_all_three_poses() -> None:
    manifest = load_layered_face_assets(LAYERED_DIR)
    assert set(manifest.poses) == {FacePose.CHEEK, FacePose.LEAN, FacePose.FRONT}


def test_each_pose_has_all_twenty_five_layers() -> None:
    manifest = load_layered_face_assets(LAYERED_DIR)
    for pose in FacePose:
        layers = manifest.pose(pose).layers
        assert set(layers) == set(LAYER_NAMES)
        assert len(layers) == len(LAYER_NAMES)
        assert len(layers) == FULL_BODY_LAYER_COUNT


def test_renderer_produces_non_null_frame_for_every_pose() -> None:
    _app()
    manifest = load_layered_face_assets(LAYERED_DIR)
    renderer = LayeredParametricFaceRenderer()
    for pose in FacePose:
        frame = FaceMotionFrame(pose, "idle", Viseme.CLOSED, MouthShape(), ExpressionShape())
        out = renderer.render_pose(manifest.pose(pose), frame)
        assert not out.isNull()
        assert out.width() == LAYERED_FACE_DIMENSION
        assert out.height() == LAYERED_FACE_DIMENSION


def test_renderer_handles_open_mouth_and_blink() -> None:
    _app()
    manifest = load_layered_face_assets(LAYERED_DIR)
    renderer = LayeredParametricFaceRenderer()
    frame = FaceMotionFrame(
        FacePose.FRONT,
        "idle_front",
        Viseme.A,
        MouthShape(aperture=0.9, width=0.78, rounding=0.08, jaw=1.0),
        ExpressionShape(blink=0.8, blush=0.6, brow_lift=0.5),
    )
    out = renderer.render_pose(manifest.pose(FacePose.FRONT), frame)
    assert not out.isNull()


def _sampled_identity_error(
    rendered: QPixmap,
    authority_path: Path,
) -> tuple[float, float]:
    actual = rendered.toImage()
    expected = QPixmap(str(authority_path)).toImage()
    differences: list[int] = []
    unexpected_transparent = 0
    for y in range(0, expected.height(), IDENTITY_SAMPLE_STEP):
        for x in range(0, expected.width(), IDENTITY_SAMPLE_STEP):
            expected_pixel = expected.pixelColor(x, y)
            if expected_pixel.alpha() == 0:
                continue
            actual_pixel = actual.pixelColor(x, y)
            unexpected_transparent += actual_pixel.alpha() == 0
            differences.append(
                max(
                    abs(actual_pixel.red() - expected_pixel.red()),
                    abs(actual_pixel.green() - expected_pixel.green()),
                    abs(actual_pixel.blue() - expected_pixel.blue()),
                    abs(actual_pixel.alpha() - expected_pixel.alpha()),
                )
            )
    return (
        sum(differences) / len(differences),
        unexpected_transparent / len(differences),
    )


def test_neutral_renderer_reconstructs_authority_portraits() -> None:
    _app()
    manifest = load_layered_face_assets(LAYERED_DIR)
    renderer = LayeredParametricFaceRenderer(manifest)
    authorities = {
        FacePose.CHEEK: "idle.png",
        FacePose.LEAN: "idle_lean.png",
        FacePose.FRONT: "idle_front.png",
    }
    for pose, filename in authorities.items():
        frame = FaceMotionFrame(
            pose,
            filename.removesuffix(".png"),
            Viseme.CLOSED,
            MouthShape(),
            ExpressionShape(),
        )
        rendered = renderer.render_pose(manifest.pose(pose), frame)
        mean_error, transparent_ratio = _sampled_identity_error(
            rendered,
            AUTHORITY_DIR / filename,
        )
        assert mean_error < MAX_MEAN_CHANNEL_ERROR
        assert transparent_ratio < MAX_TRANSPARENT_SAMPLE_RATIO


def test_renderer_port_entry_scales_to_base_size() -> None:
    _app()
    renderer = LayeredParametricFaceRenderer()
    frame = FaceMotionFrame(
        FacePose.FRONT,
        "idle_front",
        Viseme.CLOSED,
        MouthShape(),
        ExpressionShape(),
    )
    base = QPixmap(465, 465)
    base.fill(Qt.transparent)
    out = renderer.render(base, frame, None)
    assert not out.isNull()
    assert out.size() == base.size()


def test_decoded_layer_cache_stays_bounded_across_pose_changes() -> None:
    _app()
    manifest = load_layered_face_assets(LAYERED_DIR)
    renderer = LayeredParametricFaceRenderer(manifest)
    for _ in range(3):
        for pose in FacePose:
            frame = FaceMotionFrame(
                pose,
                "speaking",
                Viseme.A,
                MouthShape(aperture=0.8, width=0.7, jaw=0.6),
                ExpressionShape(blink=0.4, blush=0.4),
            )
            assert not renderer.render_pose(manifest.pose(pose), frame).isNull()
            assert len(renderer._pixmap_cache) <= MAX_CACHED_LAYER_PIXMAPS
    assert len(renderer._pixmap_cache) == MAX_CACHED_LAYER_PIXMAPS


def run() -> None:
    test_layered_manifest_loads_all_three_poses()
    test_each_pose_has_all_twenty_five_layers()
    test_renderer_produces_non_null_frame_for_every_pose()
    test_renderer_handles_open_mouth_and_blink()
    test_neutral_renderer_reconstructs_authority_portraits()
    test_renderer_port_entry_scales_to_base_size()
    test_decoded_layer_cache_stays_bounded_across_pose_changes()
    print("LAYERED_FACE_ASSETS_OK")


if __name__ == "__main__":
    run()
