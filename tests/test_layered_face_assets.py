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
lazy from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer

LAYERED_DIR = ROOT / "assets" / "expressions" / "layered"


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


def run() -> None:
    test_layered_manifest_loads_all_three_poses()
    test_each_pose_has_all_twenty_five_layers()
    test_renderer_produces_non_null_frame_for_every_pose()
    test_renderer_handles_open_mouth_and_blink()
    test_renderer_port_entry_scales_to_base_size()
    print("LAYERED_FACE_ASSETS_OK")


if __name__ == "__main__":
    run()
