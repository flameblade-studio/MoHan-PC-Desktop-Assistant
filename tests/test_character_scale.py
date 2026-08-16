from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QApplication

lazy from companion_animation_contract import (
    CHARACTER_BASE_Y,
    CHARACTER_CANVAS_WIDTH,
    CHARACTER_IMAGE_SIZE,
)
lazy from companion_window import CompanionWindow


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        for timer in window.findChildren(QTimer):
            timer.stop()

        layers = (
            window.character,
            window.expression_overlay,
            window.sleeve_left_overlay,
            window.sleeve_right_overlay,
            window.hair_left_overlay,
            window.hair_right_overlay,
            window.physics_overlay,
            window.face_overlay,
            window.eye_overlay,
        )

        window._apply_character_scale(150, preserve_anchor=False)
        expected_size = round(CHARACTER_IMAGE_SIZE * 1.5)
        assert window.character_scale_percent == 150
        assert window.width() == max(
            CHARACTER_CANVAS_WIDTH,
            expected_size + 5,
        )
        assert window.height() == CHARACTER_BASE_Y + expected_size
        assert window.character.width() == expected_size
        assert window.character.height() == expected_size
        assert all(
            layer.geometry() == window.character.geometry()
            for layer in layers
        )
        assert (
            window.character.y() + window.character.height()
            == window.height()
        )
        assert window.bubble.x() == (window.width() - 430) // 2
        # Rendering continues from the canonical high-quality 465px sources;
        # only the display canvas changes size.
        assert window.expression_pixmaps["idle"].size().width() == 465
        assert window.expression_pixmaps["idle"].size().height() == 465
        window._attention_tick()
        window._physics_tick()
        assert window.physics_overlay.isVisible()

        window._apply_character_scale(75, preserve_anchor=False)
        expected_size = round(CHARACTER_IMAGE_SIZE * 0.75)
        assert window.width() == CHARACTER_CANVAS_WIDTH
        assert window.character.width() == expected_size
        assert window.character.height() == expected_size
        assert window.character.x() == (
            CHARACTER_CANVAS_WIDTH - expected_size
        ) // 2

        window.dashboard.character_scale_slider.setValue(135)
        app.processEvents()
        assert window.character_scale_percent == 135
        assert int(
            window.db.setting("character_scale_percent", 0)
        ) == 135
        assert window.dashboard.character_scale_label.text() == "135%"

        window.close()
        window.db.close()
        app.processEvents()
    print("CHARACTER_SCALE_OK")


if __name__ == "__main__":
    run()
