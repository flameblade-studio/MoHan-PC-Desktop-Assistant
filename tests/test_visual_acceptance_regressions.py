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

lazy from domain.companion_animation_contract import EXPRESSION_HALF_BLINK_FRAME_SOURCES
lazy from presentation.companion_window import CompanionWindow

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


def _assert_blink_uses_discrete_authority_frames(
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
    half_key = EXPRESSION_HALF_BLINK_FRAME_SOURCES.get(expression, "blink_half_front")
    half_source = window.expression_pixmaps.get(half_key)
    half_authority = half_source is not None and not half_source.isNull()
    assert closed_change > 0
    if half_authority:
        # A registered HALF authority draws its own eyelids: distinct from the
        # rest frame and from the CLOSED authority.
        assert partial_change > 0
        assert any(
            region_signature(partial, region)
            != region_signature(base_image, region)
            for region in eye_regions
        ), "a registered half authority must draw its eyelids"
    else:
        assert partial_change == 0
        assert all(
            region_signature(partial, region)
            == region_signature(base_image, region)
            for region in eye_regions
        ), 'an absent half authority must preserve the rest frame'
    assert any(
        region_signature(partial, region)
        != region_signature(closed, region)
        for region in eye_regions
    ), "closed authority must remain distinct from HALF"

    # The runtime consumes a distinct registered HALF authority when present;
    # inject the already registered closed pixmap under the HALF key only to
    # prove routing while leaving each authored appearance to visual review.
    window.expression_pixmaps[half_key] = window.expression_pixmaps["blink_front"]
    try:
        authored_half = window._blink_composite(base, expression, 0.5).toImage()
        assert all(
            region_signature(authored_half, region)
            == region_signature(closed, region)
            for region in eye_regions
        )
    finally:
        if half_source is None:
            window.expression_pixmaps.pop(half_key, None)
        else:
            window.expression_pixmaps[half_key] = half_source


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
    # Complete-expression happy owns its whole closed frame; the speech alias
    # preserves that exact endpoint instead of synthesizing a legacy mouth.
    assert speech_closed == happy


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
            _assert_blink_uses_discrete_authority_frames(window)
            _assert_chin_rest_smile_uses_neutral_speech_mouth(window)
            _assert_left_facing_mouth_replaces_right_corner(window)
        finally:
            window.close()
            app.processEvents()
    print("VISUAL_ACCEPTANCE_REGRESSIONS_OK")


if __name__ == "__main__":
    run()
