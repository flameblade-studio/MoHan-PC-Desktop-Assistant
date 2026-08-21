from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtWidgets import QApplication

lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from infrastructure.layered_full_body_assets import (
    FULL_BODY_DIMENSION_HEIGHT,
    FULL_BODY_DIMENSION_WIDTH,
    VIEW_IDS,
    load_layered_full_body_assets,
)
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer

FULL_BODY_DIR = ROOT / "assets" / "pose-atlas" / "v4-layered"


def _app() -> object:
    return QApplication.instance() or QApplication([])


def _frame() -> FaceMotionFrame:
    return FaceMotionFrame(
        FacePose.FRONT,
        "idle_front",
        Viseme.CLOSED,
        MouthShape(),
        ExpressionShape(),
    )


def test_manifest_loads_all_twenty_four_views() -> None:
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    assert set(manifest.views) == set(VIEW_IDS)


def test_renderer_produces_non_null_frame() -> None:
    _app()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest)
    out = renderer.render_view("yaw+000-pitch+00", _frame())
    assert not out.isNull()
    assert out.width() == FULL_BODY_DIMENSION_WIDTH
    assert out.height() == FULL_BODY_DIMENSION_HEIGHT


def test_renderer_blends_adjacent_views() -> None:
    _app()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest)
    out = renderer.render_blended("yaw+000-pitch+00", _frame(), blend=0.5)
    assert not out.isNull()


def test_renderer_wraps_view_ring() -> None:
    _app()
    manifest = load_layered_full_body_assets(FULL_BODY_DIR)
    renderer = LayeredFullBodyRenderer(manifest)
    # The last view wraps to the first.
    out = renderer.render_blended("yaw+165-pitch+00", _frame(), blend=0.5)
    assert not out.isNull()


def run() -> None:
    test_manifest_loads_all_twenty_four_views()
    test_renderer_produces_non_null_frame()
    test_renderer_blends_adjacent_views()
    test_renderer_wraps_view_ring()
    print("LAYERED_FULL_BODY_OK")


if __name__ == "__main__":
    run()
