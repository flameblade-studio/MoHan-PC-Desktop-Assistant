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

lazy from companion_animation_contract import (
    CHEEK_SPEECH_CLOSED_EXPRESSION,
    EXPRESSION_SPEECH_MOUTH_RECTS,
)
lazy from companion_window import CompanionWindow

MIN_CHANGED_PIXELS = 24


def changed_pixel_count(first: QImage, second: QImage, rect: QRect) -> int:
    return sum(
        first.pixel(x, y) != second.pixel(x, y)
        for y in range(rect.top(), rect.bottom() + 1)
        for x in range(rect.left(), rect.right() + 1)
    )


def region_signature(image: QImage, rect: QRect) -> tuple[int, ...]:
    return tuple(
        image.pixel(x, y)
        for y in range(rect.top(), rect.bottom() + 1)
        for x in range(rect.left(), rect.right() + 1)
    )


def mean_region_difference(first: QImage, second: QImage, rect: QRect) -> float:
    total = 0
    samples = 0
    for y in range(rect.top(), rect.bottom() + 1):
        for x in range(rect.left(), rect.right() + 1):
            first_color = first.pixelColor(x, y)
            second_color = second.pixelColor(x, y)
            total += (
                abs(first_color.red() - second_color.red())
                + abs(first_color.green() - second_color.green())
                + abs(first_color.blue() - second_color.blue())
            )
            samples += 3
    return total / max(1, samples)


def _assert_blush_survives_front_blink(window: CompanionWindow) -> None:
    expression = "shy_cute_front"
    base = window.expression_pixmaps[expression]
    window.state = "speaking"
    blinked = window._blink_composite(base, expression).toImage()
    open_image = base.toImage()
    cheek_regions = (
        QRect(177, 176, 25, 13),
        QRect(257, 176, 25, 13),
    )
    assert all(
        region_signature(open_image, region)
        == region_signature(blinked, region)
        for region in cheek_regions
    ), "front blink replaced the expression's blush with neutral skin"


def _assert_blink_uses_progressive_layer_opacity(
    window: CompanionWindow,
) -> None:
    expression = "idle_front"
    base = window.expression_pixmaps[expression]
    partial = window._blink_composite(base, expression, 0.45).toImage()
    closed = window._blink_composite(base, expression, 1.0).toImage()
    base_image = base.toImage()
    eye_regions = window._blink_regions()["front"]
    partial_change = sum(
        changed_pixel_count(base_image, partial, region)
        for region in eye_regions
    )
    closed_change = sum(
        changed_pixel_count(base_image, closed, region)
        for region in eye_regions
    )
    assert 0 < partial_change <= closed_change
    assert any(
        region_signature(partial, region)
        != region_signature(closed, region)
        for region in eye_regions
    ), "partial and fully closed eyelids must not be identical"


def _assert_chin_rest_smile_uses_neutral_speech_mouth(
    window: CompanionWindow,
) -> None:
    window._configure_speech_frames("happy")
    assert window.speech_closed_expression != "happy", (
        "chin-rest smile must switch to a neutral mouth while speaking"
    )
    happy = window.expression_pixmaps["happy"].toImage()
    speech_closed = window.expression_pixmaps[
        window.speech_closed_expression
    ].toImage()
    mouth_rect = EXPRESSION_SPEECH_MOUTH_RECTS["happy"]
    eye_rect = QRect(158, 145, 105, 45)
    assert changed_pixel_count(happy, speech_closed, mouth_rect) > 0
    assert region_signature(happy, eye_rect) == region_signature(
        speech_closed,
        eye_rect,
    ), "neutral speech mouth must retain the smiling eyes"
    neutral = window.expression_pixmaps[
        CHEEK_SPEECH_CLOSED_EXPRESSION
    ].toImage()
    corner_regions = (
        QRect(174, 202, 18, 20),
        QRect(208, 202, 18, 20),
    )
    assert all(
        mean_region_difference(speech_closed, neutral, region)
        < mean_region_difference(happy, neutral, region) * 0.72
        for region in corner_regions
    ), "speech corners did not move sufficiently toward the neutral mouth"


def _assert_left_facing_mouth_replaces_right_corner(
    window: CompanionWindow,
) -> None:
    closed = window.expression_pixmaps["idle_lean"].toImage()
    right_corner = QRect(201, 202, 15, 22)
    for expression in (
        "speaking_lean",
        "mouth_mid_lean",
        "mouth_wide_lean",
        "mouth_round_lean",
        "mouth_i_lean",
        "mouth_o_lean",
    ):
        frame = window.expression_pixmaps[expression].toImage()
        assert changed_pixel_count(closed, frame, right_corner) >= MIN_CHANGED_PIXELS, (
            f"{expression} left the closed-mouth right edge behind"
        )


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        try:
            for timer in window.findChildren(QTimer):
                timer.stop()
            _assert_blush_survives_front_blink(window)
            _assert_blink_uses_progressive_layer_opacity(window)
            _assert_chin_rest_smile_uses_neutral_speech_mouth(window)
            _assert_left_facing_mouth_replaces_right_corner(window)
        finally:
            window.close()
            app.processEvents()
    print("VISUAL_ACCEPTANCE_REGRESSIONS_OK")


if __name__ == "__main__":
    run()
