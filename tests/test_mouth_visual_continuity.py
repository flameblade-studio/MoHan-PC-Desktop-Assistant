from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QRect, QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from app import (
    CHEEK_SPEECH_CENTRAL_MOUTH_RECT,
    CHEEK_SPEECH_CLOSED_EXPRESSION,
    CompanionWindow,
)


def region_signature(image: QImage, rect: QRect) -> tuple[int, ...]:
    values: list[int] = []
    for y in range(rect.top(), rect.bottom() + 1, 2):
        for x in range(rect.left(), rect.right() + 1, 2):
            values.append(image.pixel(x, y))
    return tuple(values)


def mean_region_difference(first: QImage, second: QImage, rect: QRect) -> float:
    total = 0
    count = 0
    for y in range(rect.top(), rect.bottom() + 1):
        for x in range(rect.left(), rect.right() + 1):
            a = first.pixelColor(x, y)
            b = second.pixelColor(x, y)
            total += (
                abs(a.red() - b.red())
                + abs(a.green() - b.green())
                + abs(a.blue() - b.blue())
            )
            count += 3
    return total / max(1, count)


def outside_mouth_signature(image: QImage, mouth: QRect) -> tuple[int, ...]:
    values: list[int] = []
    for y in range(0, image.height(), 3):
        for x in range(0, image.width(), 3):
            if not mouth.contains(x, y):
                values.append(image.pixel(x, y))
    return tuple(values)


def changed_pixel_count(first: QImage, second: QImage, rect: QRect) -> int:
    return sum(
        first.pixel(x, y) != second.pixel(x, y)
        for y in range(rect.top(), rect.bottom() + 1)
        for x in range(rect.left(), rect.right() + 1)
    )


def outside_region_changed_pixel_count(
    first: QImage,
    second: QImage,
    rect: QRect,
) -> int:
    return sum(
        first.pixel(x, y) != second.pixel(x, y)
        for y in range(first.height())
        for x in range(first.width())
        if not rect.contains(x, y)
    )


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        try:
            window.show()
            app.processEvents()
            for timer in window.findChildren(QTimer):
                timer.stop()
            window.idle_pose = "cheek"
            window.state = "speaking"
            window.speech_pose_suffix = ""
            window.speech_closed_expression = window._closed_speech_expression()
            window.speech_mid_expression = "mouth_mid"
            window.speech_open_expression = "speaking"
            window.audio_driven_mouth = True
            window.speech_blinking = False
            window._set_expression("idle", fade=False)
            window.eye_overlay.show()
            assert not window.eye_overlay.isHidden()

            frames: list[QImage] = []
            eye_rect = QRect(160, 135, 95, 48)
            mouth_rect = window.mouth_clips[""]
            expected_cheek_mouth_rect = QRect(168, 195, 64, 40)
            assert mouth_rect == expected_cheek_mouth_rect, (
                "the chin-rest portrait must provide a stable neutral frame "
                "for both speech corners"
            )
            assert window.speech_closed_expression == (
                CHEEK_SPEECH_CLOSED_EXPRESSION
            )
            fixed_corner_strips = {
                "left": QRect(
                    mouth_rect.left(),
                    mouth_rect.top(),
                    CHEEK_SPEECH_CENTRAL_MOUTH_RECT.left()
                    - mouth_rect.left(),
                    mouth_rect.height(),
                ),
                "right": QRect(
                    CHEEK_SPEECH_CENTRAL_MOUTH_RECT.right() + 1,
                    mouth_rect.top(),
                    mouth_rect.right()
                    - CHEEK_SPEECH_CENTRAL_MOUTH_RECT.right(),
                    mouth_rect.height(),
                ),
            }
            idle_base = (
                window.expression_pixmaps["idle"]
                .toImage()
                .convertToFormat(QImage.Format_ARGB32)
            )
            neutral_base = (
                window.expression_pixmaps[CHEEK_SPEECH_CLOSED_EXPRESSION]
                .toImage()
                .convertToFormat(QImage.Format_ARGB32)
            )
            assert changed_pixel_count(
                idle_base,
                neutral_base,
                mouth_rect,
            ) > mouth_rect.width() * mouth_rect.height() // 12
            assert outside_region_changed_pixel_count(
                idle_base,
                neutral_base,
                mouth_rect,
            ) == 0

            speech_expressions = (
                "speaking",
                "mouth_mid",
                "mouth_wide",
                "mouth_round",
                "mouth_i",
                "mouth_o",
            )
            central_signatures: set[tuple[int, ...]] = set()
            for expression in speech_expressions:
                speech_frame = (
                    window.expression_pixmaps[expression]
                    .toImage()
                    .convertToFormat(QImage.Format_ARGB32)
                )
                central_signatures.add(
                    region_signature(
                        speech_frame,
                        CHEEK_SPEECH_CENTRAL_MOUTH_RECT,
                    )
                )
                for side, strip in fixed_corner_strips.items():
                    assert region_signature(speech_frame, strip) == (
                        region_signature(neutral_base, strip)
                    ), f"{expression} changed the fixed {side} speech corner"
                assert outside_region_changed_pixel_count(
                    idle_base,
                    speech_frame,
                    mouth_rect,
                ) == 0, (
                    f"{expression} changed pixels outside the cheek mouth clip"
                )
            assert len(central_signatures) >= 4, (
                "fixed corners must not flatten the central A/I/U/E/O shapes"
            )
            # Keep each target long enough to satisfy the production 50 Hz
            # anti-flicker holds while still sampling every visual transition.
            vowels = ("A",) * 5 + ("O",) * 5 + ("I",) * 5 + ("CLOSED",) * 4
            # Drive the transition clock at a stable 60 Hz. Sleeping for 16 ms
            # lets a busy Windows runner skip intermediate frames and turns a
            # visual-continuity assertion into a scheduler lottery.
            clock = [100.0]
            with patch("app.time.perf_counter", side_effect=lambda: clock[0]):
                for index, vowel in enumerate(vowels):
                    if index == 5:
                        # A delayed idle-pose callback must not redirect a live
                        # mouth onto another face while speech is still playing.
                        window.idle_pose = "front"
                    window._audio_viseme_cue(
                        0.62 if vowel != "CLOSED" else 0.0,
                        vowel,
                    )
                    if index == 0:
                        assert window.eye_overlay.isHidden()
                    for _ in range(3):
                        clock[0] += 0.016
                        window._render_audio_mouth_transition()
                        frames.append(
                            window.character.pixmap().toImage().convertToFormat(
                                QImage.Format_ARGB32
                            )
                        )

            assert len({region_signature(frame, mouth_rect) for frame in frames}) >= 10
            eye_signatures = {
                region_signature(frame, eye_rect)
                for frame in frames
            }
            assert len(eye_signatures) == 1, "eyes changed during mouth animation"
            clean_outside = outside_mouth_signature(idle_base, mouth_rect)
            assert all(
                outside_mouth_signature(frame, mouth_rect) == clean_outside
                for frame in frames
            ), "pixels outside the frozen mouth region changed"
            for frame in frames:
                for side, strip in fixed_corner_strips.items():
                    assert region_signature(frame, strip) == region_signature(
                        neutral_base,
                        strip,
                    ), f"transition changed the fixed {side} speech corner"
            assert window._active_speech_pose_suffix() == ""

            direct_difference = mean_region_difference(
                window.expression_pixmaps["mouth_wide"].toImage(),
                window.expression_pixmaps["mouth_o"].toImage(),
                mouth_rect,
            )
            adjacent = [
                mean_region_difference(first, second, mouth_rect)
                for first, second in zip(frames, frames[1:])
            ]
            assert direct_difference > 0.5
            assert max(adjacent) < direct_difference * 0.82
            assert sum(value > 0.05 for value in adjacent) >= 8
            assert window.eye_overlay.isHidden()
        finally:
            window.close()
            app.processEvents()
    print("MOUTH_VISUAL_CONTINUITY_OK")


if __name__ == "__main__":
    run()
