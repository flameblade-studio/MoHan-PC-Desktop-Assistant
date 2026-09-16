from __future__ import annotations

lazy import os
lazy import sys
lazy from itertools import product
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
    FULL_BODY_LAYER_Z_ORDER,
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
CONTROL_LAYERS_BY_VIEW = frozendict({
    "yaw+000-pitch+00": (
        "blink_half", "blink_closed", "visible_hand_left", "visible_hand_right",
    ),
    "yaw+015-pitch+00": ("blink_half", "blink_closed"),
    "yaw+030-pitch+00": (
        "blink_half", "blink_closed", "visible_hand_left", "visible_hand_right",
    ),
    "yaw+045-pitch+00": (
        "blink_half", "blink_closed", "visible_hand_left", "visible_hand_right",
    ),
    "yaw+060-pitch+00": ("blink_half", "blink_closed"),
    "yaw+090-pitch+00": ("blink_half", "blink_closed"),
    "yaw+150-pitch+00": ("visible_hand_left", "visible_hand_right"),
    "yaw-015-pitch+00": ("blink_half", "blink_closed"),
    "yaw-030-pitch+00": ("blink_half", "blink_closed"),
    "yaw-045-pitch+00": ("blink_half", "blink_closed"),
    "yaw-060-pitch+00": ("blink_half", "blink_closed"),
    "yaw-075-pitch+00": ("blink_half", "blink_closed"),
})


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
    # Keep the complete 600-layer contract; separately enumerate every authored
    # control sidecar so acceptance requires the exact expected file set.
    expected_layers = {
        f"{path.stem}_{name}.png"
        for path, name in product(root.glob("yaw*-pitch+00.png"), FULL_BODY_LAYER_Z_ORDER)
    }
    assert len(expected_layers) == VIEW_RING_COUNT * FULL_BODY_LAYER_COUNT
    expected_controls: set[str] = set()
    for view, names in CONTROL_LAYERS_BY_VIEW.items():
        expected_controls.update(f"{view}_{name}.png" for name in names)
    actual_layers = {path.name for path in layered.glob("yaw*-pitch+00_*.png")}
    assert actual_layers == expected_layers | expected_controls
    hand_overlays = repo / "assets/pose-atlas/v5-hand-overlays"
    assert {path.name for path in hand_overlays.glob("*.png")} == {
        "yaw+000-pitch+00_left.png",
        "yaw+000-pitch+00_right.png",
        "yaw+015-pitch+00_left.png",
        "yaw+015-pitch+00_right.png",
        "yaw+030-pitch+00_left.png",
        "yaw+030-pitch+00_right.png",
        "yaw+045-pitch+00_left.png",
        "yaw+045-pitch+00_right.png",
        "yaw+060-pitch+00_left.png",
        "yaw+060-pitch+00_right.png",
        "yaw+090-pitch+00_left.png",
        "yaw+090-pitch+00_right.png",
        "yaw+105-pitch+00_left.png",
        "yaw+105-pitch+00_right.png",
        "yaw+120-pitch+00_left.png",
        "yaw+120-pitch+00_right.png",
        "yaw+165-pitch+00_left.png",
        "yaw+165-pitch+00_right.png",
        "yaw-015-pitch+00_left.png",
        "yaw-015-pitch+00_right.png",
        "yaw-030-pitch+00_left.png",
        "yaw-030-pitch+00_right.png",
        "yaw-045-pitch+00_left.png",
        "yaw-045-pitch+00_right.png",
        "yaw-060-pitch+00_left.png",
        "yaw-060-pitch+00_right.png",
        "yaw-075-pitch+00_left.png",
        "yaw-075-pitch+00_right.png",
        "yaw-105-pitch+00_left.png",
        "yaw-105-pitch+00_right.png",
        "yaw-120-pitch+00_left.png",
        "yaw-120-pitch+00_right.png",
        "yaw-135-pitch+00_left.png",
        "yaw-135-pitch+00_right.png",
        "yaw-150-pitch+00_left.png",
        "yaw-150-pitch+00_right.png",
        "yaw-165-pitch+00_left.png",
        "yaw-165-pitch+00_right.png",
        "yaw-180-pitch+00_left.png",
        "yaw-180-pitch+00_right.png",
    }
    body_overlays = repo / "assets/pose-atlas/v5-body-overlays"
    assert {path.name for path in body_overlays.glob("*.png")} == {
        "yaw+000-pitch+00.png",
        "yaw+015-pitch+00.png",
        "yaw+030-pitch+00.png",
        "yaw+045-pitch+00.png",
        "yaw+060-pitch+00.png",
        "yaw-015-pitch+00.png",
        "yaw-030-pitch+00.png",
        "yaw-045-pitch+00.png",
        "yaw-060-pitch+00.png",
        "yaw-105-pitch+00.png",
        "yaw-120-pitch+00.png",
        "yaw-135-pitch+00.png",
        "yaw-150-pitch+00.png",
        "yaw-165-pitch+00.png",
        "yaw-180-pitch+00.png",
    }
    official_silhouettes = (
        repo
        / "assets/pose-atlas/v5-appearance-silhouettes"
        / "mohan.official.blue-white-hanfu"
    )
    assert {path.name for path in official_silhouettes.glob("*.png")} == {
        "yaw+000-pitch+00.png",
        "yaw+015-pitch+00.png",
        "yaw+030-pitch+00.png",
        "yaw+045-pitch+00.png",
        "yaw+060-pitch+00.png",
        "yaw+090-pitch+00.png",
        "yaw+105-pitch+00.png",
        "yaw+120-pitch+00.png",
        "yaw-015-pitch+00.png",
        "yaw-030-pitch+00.png",
        "yaw-045-pitch+00.png",
        "yaw-060-pitch+00.png",
        "yaw-075-pitch+00.png",
        "yaw-105-pitch+00.png",
        "yaw-120-pitch+00.png",
        "yaw-135-pitch+00.png",
        "yaw-150-pitch+00.png",
        "yaw-165-pitch+00.png",
        "yaw-180-pitch+00.png",
    }
    official_replacement_masks = (
        repo
        / "assets/pose-atlas/v5-appearance-replacement-masks"
        / "mohan.official.blue-white-hanfu"
    )
    assert {path.name for path in official_replacement_masks.glob("*.png")} == {
        "yaw+000-pitch+00.png",
        "yaw+015-pitch+00.png",
        "yaw+030-pitch+00.png",
        "yaw+045-pitch+00.png",
        "yaw+060-pitch+00.png",
        "yaw+090-pitch+00.png",
        "yaw+105-pitch+00.png",
        "yaw+120-pitch+00.png",
        "yaw-015-pitch+00.png",
        "yaw-030-pitch+00.png",
        "yaw-045-pitch+00.png",
        "yaw-060-pitch+00.png",
        "yaw-075-pitch+00.png",
    }
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
    # full-body frame, with speech rendered exclusively by that composition.
    spoken = assets.resolve_speech("neutral", "A", False)
    assert spoken == ()
    # The sole layered path requires a motion frame before rendering.
    assert assets.resolve_static("front-crossed", "front-000") is None
    assert assets.resolve_static("front-crossed", "invalid-view", _neutral()) is None
    application.processEvents()
    print("POSE_ATLAS_ASSETS_OK")


if __name__ == "__main__":
    run()
