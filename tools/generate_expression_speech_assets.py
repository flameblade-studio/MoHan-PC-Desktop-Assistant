from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QRect, QTimer
lazy from PySide6.QtGui import QImage
lazy from PySide6.QtWidgets import QApplication

lazy from app import (
    EXPRESSION_POSES,
    GESTURE_SPEECH_EXPRESSIONS,
    CompanionWindow,
)

POSE_MOUTH_RECTS = {
    "cheek": QRect(174, 198, 52, 34),
    "lean": QRect(162, 198, 54, 34),
    "front": QRect(206, 199, 54, 35),
}


def changed_bbox(first: QImage, second: QImage) -> QRect:
    if first.size() != second.size():
        raise ValueError("影像尺寸不一致")
    left = first.width()
    top = first.height()
    right = -1
    bottom = -1
    for y in range(first.height()):
        for x in range(first.width()):
            if first.pixel(x, y) == second.pixel(x, y):
                continue
            left = min(left, x)
            top = min(top, y)
            right = max(right, x)
            bottom = max(bottom, y)
    if right < left:
        return QRect()
    return QRect(left, top, right - left + 1, bottom - top + 1)


def assert_mouth_only(
    base: QImage,
    frame: QImage,
    allowed: QRect,
    expression: str,
    viseme: str,
) -> None:
    changed = changed_bbox(base, frame)
    if changed.isEmpty():
        raise AssertionError(f"{expression}/{viseme} 沒有產生嘴型差異")
    if not allowed.contains(changed):
        raise AssertionError(
            f"{expression}/{viseme} 超出嘴部安全區："
            f"{changed.getRect()} not in {allowed.getRect()}"
        )


def generate(output_dir: Path) -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        for timer in window.findChildren(QTimer):
            timer.stop()
        output_dir.mkdir(parents=True, exist_ok=True)

        for expression, pose in EXPRESSION_POSES.items():
            if expression in GESTURE_SPEECH_EXPRESSIONS:
                continue
            suffix = window._pose_suffix(pose)
            window.state = "speaking"
            window.speech_closed_expression = expression
            window.speech_pose_suffix = suffix
            window.speech_gesture_expression = None
            window.speech_mid_expression = f"mouth_mid{suffix}"
            window.speech_open_expression = f"speaking{suffix}"
            base = window.expression_pixmaps[expression]
            frames = {
                "mid": window._mouth_aperture_pixmap(
                    window.speech_mid_expression,
                    0.48,
                ),
                "open": window._mouth_aperture_pixmap(
                    window.speech_open_expression,
                    0.90,
                ),
                "round": window._mouth_aperture_pixmap(
                    f"mouth_round{suffix}",
                    0.78,
                ),
            }
            # Qt's antialiased mask can touch one pixel beyond the nominal
            # rectangle. Four pixels cover that feather without approaching
            # the nose, eyes, jaw line, hands or costume.
            allowed = POSE_MOUTH_RECTS[pose].adjusted(-4, -4, 4, 4)
            base_image = base.toImage().convertToFormat(
                QImage.Format_ARGB32
            )
            for viseme, frame in frames.items():
                frame_image = frame.toImage().convertToFormat(
                    QImage.Format_ARGB32
                )
                assert_mouth_only(
                    base_image,
                    frame_image,
                    allowed,
                    expression,
                    viseme,
                )
                path = output_dir / f"{expression}_speech_{viseme}.png"
                if not frame.save(str(path), "PNG"):
                    raise RuntimeError(f"無法儲存 {path}")
                print(path.name)

        window.close()
        window.db.close()
        app.processEvents()


if __name__ == "__main__":
    destination = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("assets/expressions")
    )
    generate(destination.resolve())
