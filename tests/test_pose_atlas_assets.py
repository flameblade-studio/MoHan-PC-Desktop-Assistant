from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtWidgets import QApplication

lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from application.full_body_render_adapter import AUTHORED_FULL_BODY_SLOT
lazy from domain.constants import (
    POSE_ATLAS_GENERATION,
    POSE_ATLAS_LAYERED_RELATIVE_ROOT,
    POSE_ATLAS_LAYERED_ROOT_NAME,
    POSE_ATLAS_RELATIVE_ROOT,
    POSE_ATLAS_ROOT_NAME,
)
lazy from presentation.pose_atlas_assets import PoseAtlasAssets

EXPECTED_GENERATION = 2
VIEW_RING_COUNT = 24
FULL_BODY_LAYER_COUNT = 25


def _neutral() -> FaceMotionFrame:
    return FaceMotionFrame(
        FacePose.FRONT,
        "idle",
        Viseme.CLOSED,
        MouthShape(),
        ExpressionShape(),
    )


def run() -> None:
    application = QApplication.instance() or QApplication([])
    repo = Path(__file__).resolve().parents[1]
    # One source of truth for the current generation: the relative roots must
    # be spelled from the root names, and both directories must be complete.
    assert POSE_ATLAS_RELATIVE_ROOT == f"assets/pose-atlas/{POSE_ATLAS_ROOT_NAME}"
    assert POSE_ATLAS_LAYERED_RELATIVE_ROOT == (
        f"assets/pose-atlas/{POSE_ATLAS_LAYERED_ROOT_NAME}"
    )
    assert POSE_ATLAS_ROOT_NAME == "v5-base"
    assert POSE_ATLAS_GENERATION == EXPECTED_GENERATION
    root = repo / POSE_ATLAS_RELATIVE_ROOT
    assert len(tuple(root.glob("yaw*-pitch+00.png"))) == VIEW_RING_COUNT
    layered = repo / POSE_ATLAS_LAYERED_RELATIVE_ROOT
    assert len(tuple(layered.glob("yaw*-pitch+00_*.png"))) == (
        VIEW_RING_COUNT * FULL_BODY_LAYER_COUNT
    )
    assets = PoseAtlasAssets(root, image_size=465)
    assert assets.enabled
    assert assets.release_eligible
    assert assets.generation == EXPECTED_GENERATION
    front = assets.resolve_static("front-crossed", "front-000", _neutral())
    back = assets.resolve_static("back-full", "back-180", _neutral())
    assert front is not None and back is not None
    assert front.view_id == "yaw+000-pitch+00"
    assert back.view_id == "yaw-180-pitch+00"
    assert front.static_layers[0].layer.name == AUTHORED_FULL_BODY_SLOT
    assert len(front.static_layers[0].layer.rgba) == 465 * 465 * 4
    assert assets.resolve_speech("neutral", "CLOSED", True) == ()
    # The parametric layered renderer deforms the mouth inside the composed
    # full-body frame, so speech contributes no separate procedural mouth layer.
    spoken = assets.resolve_speech("neutral", "A", False)
    assert spoken == ()
    # Without a motion frame the sole layered path fails closed.
    assert assets.resolve_static("front-crossed", "front-000") is None
    assert assets.resolve_static("front-crossed", "invalid-view", _neutral()) is None
    application.processEvents()
    print("POSE_ATLAS_ASSETS_OK")


if __name__ == "__main__":
    run()
