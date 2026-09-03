"""Active appearance art, not bare placeholders, drives runtime physics.

The generation-2 bare body intentionally has no clothing, loose hair or
hairpiece.  The default appearance pack supplies those visuals, so this test
requires every enabled physical source and its rotated result to contain the
active pack's pixels.
"""

from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtGui import QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from presentation.companion_window import CompanionWindow

RUNTIME_LAYER_SIZE = 465
HAIR_CENTER_X = RUNTIME_LAYER_SIZE // 2
GESTURE_HAIR_SILHOUETTES = (
    ("mock_scold", "front-mock-scold"),
    ("mock_hit_front", "front-mock-hit"),
    ("eureka_front", "front-eureka"),
    ("exasperated_front", "front-exasperated"),
)
POSE_IDLE_FRAMES = (
    ("cheek", "idle"),
    ("lean", "idle_lean"),
    ("front", "idle_front"),
)
PHYSICAL_PARTS = ("ornament", "hair_left", "hair_right", "sleeve_left", "sleeve_right")
ALPHA_OFFSET = 3
RGBA_STRIDE = 4
POSE_CHANGE_KICK = 0.4


def stop_automatic_timers(window: CompanionWindow) -> None:
    for timer in window.findChildren(QTimer):
        timer.stop()


def is_fully_transparent(pixmap: QPixmap) -> bool:
    image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
    return not any(bytes(image.bits())[ALPHA_OFFSET::RGBA_STRIDE])


def physics_sources_for(window: CompanionWindow, pose: str) -> dict[str, QPixmap]:
    return {
        "ornament": window.physics_sources[pose],
        "hair_left": window.hair_sources[pose]["left"],
        "hair_right": window.hair_sources[pose]["right"],
        "sleeve_left": window.sleeve_sources[pose]["left"],
        "sleeve_right": window.sleeve_sources[pose]["right"],
    }


def assert_active_appearance_sources_loaded(window: CompanionWindow) -> None:
    for pose, _idle in POSE_IDLE_FRAMES:
        for part, pixmap in physics_sources_for(window, pose).items():
            assert not pixmap.isNull(), (pose, part)
            assert max(pixmap.width(), pixmap.height()) == RUNTIME_LAYER_SIZE, (
                pose,
                part,
            )
            assert not is_fully_transparent(pixmap), (pose, part)


def assert_rotation_preserves_active_appearance(window: CompanionWindow) -> None:
    overlays = (
        window.physics_overlay,
        window.hair_left_overlay,
        window.hair_right_overlay,
        window.sleeve_left_overlay,
        window.sleeve_right_overlay,
    )
    for pose, idle in POSE_IDLE_FRAMES:
        window.idle_pose = pose
        window.state = "idle"
        window._set_expression(idle, fade=False)
        assert window.active_physics_pose == pose
        # Kick every spring so the tick actually rotates and repaints.
        window.ornament_velocity += POSE_CHANGE_KICK
        window.hair_left_velocity += POSE_CHANGE_KICK
        window.hair_right_velocity -= POSE_CHANGE_KICK
        window.sleeve_left_velocity += POSE_CHANGE_KICK
        window.sleeve_right_velocity -= POSE_CHANGE_KICK
        window._physics_tick()
        for overlay in overlays:
            rendered = overlay.pixmap()
            assert not rendered.isNull(), (pose, overlay)
            assert not is_fully_transparent(rendered), (pose, overlay)
        local_layers = window.expression_physics_sources[idle]
        assert set(local_layers) == set(PHYSICAL_PARTS), pose
        assert all(not is_fully_transparent(layer) for layer in local_layers.values()), pose


def alpha_columns(pixmap: QPixmap) -> set[int]:
    image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
    columns: set[int] = set()
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha():
                columns.add(x)
    return columns


def assert_hair_sides_and_gesture_silhouettes(window: CompanionWindow) -> None:
    for pose in ("cheek", "lean", "front"):
        left = window.hair_sources[pose]["left"]
        right = window.hair_sources[pose]["right"]
        assert left.toImage() != right.toImage(), pose
        assert max(alpha_columns(left)) < HAIR_CENTER_X
        assert min(alpha_columns(right)) >= HAIR_CENTER_X
    front = window.physics_sources_by_silhouette["front-crossed"]
    for expression, silhouette in GESTURE_HAIR_SILHOUETTES:
        source_set = window.physics_sources_by_silhouette[silhouette]
        local = window.expression_physics_sources[expression]
        assert source_set["hair_left"].toImage() != source_set["hair_right"].toImage()
        for part in PHYSICAL_PARTS:
            assert source_set[part].toImage() != front[part].toImage(), (expression, part)
        assert local["hair_left"].toImage() == source_set["hair_left"].toImage()
        assert local["hair_right"].toImage() == source_set["hair_right"].toImage()
        assert local["hair_left"].toImage() != front["hair_left"].toImage()
        assert local["hair_right"].toImage() != front["hair_right"].toImage()

        window.state = "speaking"
        window.current_expression = expression
        window.speech_gesture_expression = expression
        window.active_physics_pose = "front"
        window.hair_left_angle = -0.34
        window.hair_right_angle = 0.32
        window.ornament_angle = 0.4
        window.sleeve_left_angle = -0.16
        window.sleeve_right_angle = 0.15
        window._render_hair_layers(force=True)
        window._render_sleeve_layers(force=True)
        window._render_physics_layer(force=True)
        for side, overlay in (
            ("left", window.hair_left_overlay),
            ("right", window.hair_right_overlay),
        ):
            columns = alpha_columns(overlay.pixmap())
            assert columns
            if side == "left":
                assert max(columns) < HAIR_CENTER_X
            else:
                assert min(columns) >= HAIR_CENTER_X
        assert not is_fully_transparent(window.physics_overlay.pixmap())
        assert not is_fully_transparent(window.sleeve_left_overlay.pixmap())
        assert not is_fully_transparent(window.sleeve_right_overlay.pixmap())


def run() -> None:
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        stop_automatic_timers(window)
        assert_active_appearance_sources_loaded(window)
        assert_hair_sides_and_gesture_silhouettes(window)
        assert_rotation_preserves_active_appearance(window)
        window.close()
        app.processEvents()
    print("V120_ACTIVE_APPEARANCE_PHYSICS_OK")


if __name__ == "__main__":
    run()
