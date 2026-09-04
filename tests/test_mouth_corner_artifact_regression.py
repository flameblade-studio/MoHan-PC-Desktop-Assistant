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

lazy from presentation.companion_window import CompanionWindow

OPEN_FRAMES = {
    "C": ("mouth_mid", 0.12, ("viseme_mid", "speaking")),
    "A": ("mouth_wide", 0.92, ("speaking",)),
    "I": ("mouth_i", 0.42, ("viseme_i",)),
    "U": ("mouth_round", 0.46, ("viseme_round",)),
    "E": ("mouth_i", 0.50, ("viseme_i",)),
    "O": ("mouth_o", 0.78, ("viseme_o",)),
}
FULL_ALPHA = 255
OPAQUE_ALPHA_THRESHOLD = 250
DARK_EDGE_MAX_RGB = 185
DARK_EYE_MAX_RGB = 100
MIN_SKIN_RED = 150
MIN_SKIN_GREEN = 85
MIN_SKIN_BLUE = 65
MIN_RED_GREEN_DELTA = 20
MIN_GREEN_BLUE_DELTA = 5
MIN_SOURCE_LIFT = 16
MAX_RENDERED_SOURCE_GAP = 8
POSES = (
    ("cheek", "", "idle_speech_neutral"),
    ("lean", "_lean", "idle_lean"),
    ("front", "_front", "idle_front"),
)

# These are deliberately small semantic probes around the source-backed face
# edge, rather than the full mouth clip.  The latter includes hair/hand
# silhouettes that are expected to remain dark while the mouth moves.
MOUTH_CORNER_PROBES = {
    "cheek": (QRect(166, 202, 26, 31), QRect(192, 202, 19, 27)),
    "lean": (QRect(157, 193, 22, 30), QRect(193, 202, 18, 27)),
    "front": (QRect(205, 201, 14, 12), QRect(237, 201, 14, 12)),
}


def _image(pixmap) -> QImage:
    return pixmap.toImage().convertToFormat(QImage.Format_ARGB32)


def _max_rgb(image: QImage, x: int, y: int) -> int:
    color = image.pixelColor(x, y)
    return max(color.red(), color.green(), color.blue())


def _skin_like(image: QImage, x: int, y: int) -> bool:
    color = image.pixelColor(x, y)
    return (
        color.alpha() >= OPAQUE_ALPHA_THRESHOLD
        and color.red() >= MIN_SKIN_RED
        and color.green() >= MIN_SKIN_GREEN
        and color.blue() >= MIN_SKIN_BLUE
        and color.red() - color.green() >= MIN_RED_GREEN_DELTA
        and color.green() - color.blue() >= MIN_GREEN_BLUE_DELTA
    )


def _source_backed_residuals(
    closed: QImage,
    source: QImage,
    rendered: QImage,
    mask: QImage,
    probes: tuple[QRect, QRect],
) -> list[tuple[int, int]]:
    """Find a dark closed-edge pixel left under a light open source pixel."""

    residuals: list[tuple[int, int]] = []
    for probe in probes:
        for y in range(probe.top(), probe.bottom() + 1):
            for x in range(probe.left(), probe.right() + 1):
                closed_color = closed.pixelColor(x, y)
                source_color = source.pixelColor(x, y)
                mask_alpha = mask.pixelColor(x, y).alpha()
                source_max = _max_rgb(source, x, y)
                if (
                    closed_color.alpha() >= OPAQUE_ALPHA_THRESHOLD
                    and source_color.alpha() >= OPAQUE_ALPHA_THRESHOLD
                    and 0 < mask_alpha < FULL_ALPHA
                    and _max_rgb(closed, x, y) <= DARK_EDGE_MAX_RGB
                    and source_max >= _max_rgb(closed, x, y) + MIN_SOURCE_LIFT
                    and _skin_like(source, x, y)
                    and _max_rgb(rendered, x, y)
                    <= source_max - MAX_RENDERED_SOURCE_GAP
                ):
                    residuals.append((x, y))
    return residuals


def _new_dark_eye_pixels(
    closed: QImage,
    rendered: QImage,
    regions: tuple[QRect, QRect],
) -> list[tuple[int, int]]:
    changed: list[tuple[int, int]] = []
    for region in regions:
        for y in range(region.top(), region.bottom() + 1):
            for x in range(region.left(), region.right() + 1):
                if (
                    rendered.pixelColor(x, y).alpha() >= OPAQUE_ALPHA_THRESHOLD
                    and _max_rgb(rendered, x, y) <= DARK_EYE_MAX_RGB
                    and _max_rgb(closed, x, y) > DARK_EYE_MAX_RGB
                ):
                    changed.append((x, y))
    return changed


def _configure_speech(window: CompanionWindow, pose: str, suffix: str, closed: str) -> None:
    window.state = "speaking"
    window.idle_pose = pose
    window.speech_pose_suffix = suffix
    window.speech_closed_expression = closed
    window.speech_mid_expression = f"mouth_mid{suffix}"
    window.speech_open_expression = f"speaking{suffix}"
    window.speech_gesture_expression = None
    window.audio_driven_mouth = True
    window.speech_blinking = False
    window._set_expression(closed, fade=False)


def _source_expression(window: CompanionWindow, roots: tuple[str, ...], suffix: str):
    for root in roots:
        name = f"{root}{suffix}"
        source = window.expression_pixmaps.get(name)
        if source is not None and not source.isNull():
            return source
    raise AssertionError(f"missing source expression for {roots!r}{suffix}")


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        failures: list[str] = []
        try:
            window.show()
            app.processEvents()
            for timer in window.findChildren(QTimer):
                timer.stop()
            for pose, suffix, closed_name in POSES:
                _configure_speech(window, pose, suffix, closed_name)
                closed = _image(window._mouth_aperture_pixmap(closed_name, 0.0))
                eye_regions = window.dedicated_blink_regions[pose]
                for label, (expression_root, aperture, source_roots) in OPEN_FRAMES.items():
                    expression = f"{expression_root}{suffix}"
                    source = _image(_source_expression(window, source_roots, suffix))
                    rendered = _image(window._mouth_aperture_pixmap(expression, aperture))
                    mask = _image(window.viseme_mouth_masks[suffix])
                    mouth_residuals = _source_backed_residuals(
                        closed,
                        source,
                        rendered,
                        mask,
                        MOUTH_CORNER_PROBES[pose],
                    )
                    eye_residuals = _new_dark_eye_pixels(
                        closed,
                        rendered,
                        eye_regions,
                    )
                    if mouth_residuals:
                        failures.append(
                            f"{pose}/{label}: mouth={len(mouth_residuals)} "
                            f"bbox={QRect(*mouth_residuals[0], 1, 1).united(QRect(*mouth_residuals[-1], 1, 1)).getRect()}"
                        )
                    if eye_residuals:
                        failures.append(f"{pose}/{label}: eye={len(eye_residuals)}")
        finally:
            window.close()
            app.processEvents()
    assert not failures, "; ".join(failures)
    print("MOUTH_CORNER_ARTIFACT_REGRESSION_OK")


if __name__ == "__main__":
    run()
