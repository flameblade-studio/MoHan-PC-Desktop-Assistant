from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import QRect, QSize, Qt, QTimer
lazy from PySide6.QtGui import QColor, QFont, QImage, QPainter
lazy from PySide6.QtTest import QTest
lazy from PySide6.QtWidgets import QApplication

lazy from companion_window import CompanionWindow

POSES = (
    ("cheek", "", QRect(145, 140, 145, 125)),
    ("lean", "_lean", QRect(137, 140, 145, 125)),
    ("front", "_front", QRect(174, 140, 145, 125)),
)
VISEME_CUES = (
    ("CLOSED", 0.0),
    ("A", 0.62),
    ("A", 0.62),
    ("I", 0.55),
    ("I", 0.55),
    ("O", 0.68),
    ("O", 0.68),
    ("CLOSED", 0.0),
    ("CLOSED", 0.0),
    ("CLOSED", 0.0),
)
CELL_WIDTH = 232
CELL_HEIGHT = 200
TITLE_HEIGHT = 25
GRID_MARGIN = 8
GRID_COLUMNS = 5


def hide_physics_overlays(window: CompanionWindow) -> None:
    for overlay in (
        window.sleeve_left_overlay,
        window.sleeve_right_overlay,
        window.hair_left_overlay,
        window.hair_right_overlay,
        window.physics_overlay,
    ):
        overlay.hide()


def prepare_audit_window(window: CompanionWindow, isolate_face: bool) -> None:
    window.show()
    window.bubble.hide()
    for timer in window.findChildren(QTimer):
        timer.stop()
    if isolate_face:
        hide_physics_overlays(window)


def configure_pose(window: CompanionWindow, pose: str, suffix: str) -> None:
    window.state = "speaking"
    window.idle_pose = pose
    window.speech_pose_suffix = suffix
    window.speech_closed_expression = f"idle{suffix}"
    window.speech_mid_expression = f"mouth_mid{suffix}"
    window.speech_open_expression = f"speaking{suffix}"
    window.speech_gesture_expression = None
    window._start_mouth_animation(audio_driven=True)


def capture_face_frame(window: CompanionWindow, crop: QRect) -> QImage:
    frame_rect = crop.translated(window.character.x(), window.character.y())
    captured = window.grab()
    ratio = captured.devicePixelRatio()
    physical_rect = QRect(
        round(frame_rect.x() * ratio),
        round(frame_rect.y() * ratio),
        round(frame_rect.width() * ratio),
        round(frame_rect.height() * ratio),
    )
    return (
        captured
        .toImage()
        .copy(physical_rect)
        .scaled(
            QSize(CELL_WIDTH, CELL_HEIGHT),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
    )


def render_viseme_frame(
    app: QApplication,
    window: CompanionWindow,
    crop: QRect,
    isolate_face: bool,
    cue: tuple[str, float],
) -> QImage:
    vowel, level = cue
    window._audio_viseme_cue(level, vowel)
    QTest.qWait(24)
    if window.mouth_visual_timer.isActive():
        window._render_audio_mouth_transition()
    window._render_attention_layers(force=True)
    window._attention_tick()
    if isolate_face:
        hide_physics_overlays(window)
    app.processEvents()
    return capture_face_frame(window, crop)


def capture_pose_frames(
    app: QApplication,
    window: CompanionWindow,
    crop: QRect,
    isolate_face: bool,
) -> list[QImage]:
    return [
        render_viseme_frame(
            app,
            window,
            crop,
            isolate_face,
            cue,
        )
        for cue in VISEME_CUES
    ]


def capture_pose_rows(
    app: QApplication,
    window: CompanionWindow,
    isolate_face: bool,
) -> list[tuple[str, list[QImage]]]:
    rows = []
    for pose, suffix, crop in POSES:
        configure_pose(window, pose, suffix)
        frames = capture_pose_frames(app, window, crop, isolate_face)
        window._stop_mouth_animation()
        rows.append((pose, frames))
    return rows


def draw_pose_rows(
    painter: QPainter,
    rows: list[tuple[str, list[QImage]]],
) -> None:
    for pose_index, (pose, frames) in enumerate(rows):
        for index, frame in enumerate(frames):
            local_row, column = divmod(index, GRID_COLUMNS)
            row = pose_index * 2 + local_row
            x = GRID_MARGIN + column * (CELL_WIDTH + GRID_MARGIN)
            y = GRID_MARGIN + row * (CELL_HEIGHT + TITLE_HEIGHT + GRID_MARGIN)
            painter.setPen(QColor("#ffffff"))
            painter.drawText(
                QRect(x, y, CELL_WIDTH, TITLE_HEIGHT),
                Qt.AlignCenter,
                f"{pose} {index * 24:03d} ms",
            )
            painter.drawImage(x, y + TITLE_HEIGHT, frame)


def compose_audit_canvas(rows: list[tuple[str, list[QImage]]]) -> QImage:
    canvas = QImage(
        GRID_COLUMNS * CELL_WIDTH + (GRID_COLUMNS + 1) * GRID_MARGIN,
        len(rows) * 2 * (CELL_HEIGHT + TITLE_HEIGHT + GRID_MARGIN) + GRID_MARGIN,
        QImage.Format_ARGB32,
    )
    canvas.fill(QColor("#0d2130"))
    painter = QPainter(canvas)
    painter.setFont(QFont("Arial", 10))
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    draw_pose_rows(painter, rows)
    painter.end()
    return canvas


def save_audit_canvas(canvas: QImage, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if not canvas.save(str(output)):
        raise RuntimeError(f"Could not save {output}")


def render(output: Path) -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        isolate_face = os.getenv("AUDIT_ALL_PHYSICS", "0") != "1"
        prepare_audit_window(window, isolate_face)
        rows = capture_pose_rows(app, window, isolate_face)
        save_audit_canvas(compose_audit_canvas(rows), output)
        window.close()
        app.processEvents()


if __name__ == "__main__":
    target = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else ROOT / "tmp" / "mouth-layer-audit.png"
    )
    render(target)
    print(target)
