from __future__ import annotations

lazy import os
lazy import sys
lazy from dataclasses import dataclass
lazy from itertools import pairwise
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QRect, QTimer
lazy from PySide6.QtGui import QImage
lazy from PySide6.QtWidgets import QApplication

lazy from companion_animation_contract import CHEEK_SPEECH_CLOSED_EXPRESSION
lazy from companion_window import CompanionWindow


def region_signature(image: QImage, rect: QRect) -> tuple[int, ...]:
    return tuple(
        image.pixel(x, y)
        for y in range(rect.top(), rect.bottom() + 1, 2)
        for x in range(rect.left(), rect.right() + 1, 2)
    )


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
    return tuple(
        image.pixel(x, y)
        for y in range(0, image.height(), 3)
        for x in range(0, image.width(), 3)
        if not mouth.contains(x, y)
    )


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


@dataclass(frozen=True, slots=True)
class MouthReference:
    eye_rect: QRect
    mouth_rect: QRect
    corner_regions: dict[str, QRect]
    idle_base: QImage
    neutral_base: QImage


def _configure_window(window: CompanionWindow, app: QApplication) -> None:
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


def _corner_regions(mouth_rect: QRect) -> dict[str, QRect]:
    return {
        "left": QRect(
            mouth_rect.left(),
            mouth_rect.top(),
            24,
            mouth_rect.height(),
        ),
        "right": QRect(
            mouth_rect.right() - 23,
            mouth_rect.top(),
            24,
            mouth_rect.height(),
        ),
    }


def _build_mouth_reference(window: CompanionWindow) -> MouthReference:
    mouth_rect = window.mouth_clips[""]
    assert mouth_rect == QRect(168, 195, 64, 40), (
        "the chin-rest portrait must animate the complete mouth, including "
        "both corners"
    )
    assert window.speech_closed_expression == CHEEK_SPEECH_CLOSED_EXPRESSION
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
    assert region_signature(idle_base, mouth_rect) == region_signature(
        neutral_base,
        mouth_rect,
    )
    assert outside_region_changed_pixel_count(
        idle_base,
        neutral_base,
        mouth_rect,
    ) == 0
    return MouthReference(
        eye_rect=QRect(160, 135, 95, 48),
        mouth_rect=mouth_rect,
        corner_regions=_corner_regions(mouth_rect),
        idle_base=idle_base,
        neutral_base=neutral_base,
    )


def _assert_speech_expression_layers(
    window: CompanionWindow,
    reference: MouthReference,
) -> None:
    mouth_signatures: set[tuple[int, ...]] = set()
    for expression in (
        "speaking",
        "mouth_mid",
        "mouth_wide",
        "mouth_round",
        "mouth_i",
        "mouth_o",
    ):
        speech_frame = (
            window.expression_pixmaps[expression]
            .toImage()
            .convertToFormat(QImage.Format_ARGB32)
        )
        mouth_signatures.add(region_signature(speech_frame, reference.mouth_rect))
        for side, region in reference.corner_regions.items():
            assert changed_pixel_count(
                reference.neutral_base,
                speech_frame,
                region,
            ) >= 12, f"{expression} left the neutral {side} corner behind"
        assert outside_region_changed_pixel_count(
            reference.idle_base,
            speech_frame,
            reference.mouth_rect,
        ) == 0, f"{expression} changed pixels outside the cheek mouth clip"
    assert len(mouth_signatures) >= 4, (
        "complete moving corners must not flatten the A/I/U/E/O shapes"
    )


def _capture_transition_frames(window: CompanionWindow) -> list[QImage]:
    frames: list[QImage] = []
    # Hold each target through the production 50 Hz anti-flicker interval.
    vowels = ("A",) * 5 + ("O",) * 5 + ("I",) * 5 + ("CLOSED",) * 4
    # A stable 60 Hz clock avoids scheduler-dependent skipped frames on CI.
    clock = [100.0]
    with patch("time.perf_counter", side_effect=lambda: clock[0]):
        for index, vowel in enumerate(vowels):
            if index == 5:
                # A delayed callback must not redirect a live mouth to a new face.
                window.idle_pose = "front"
            window._audio_viseme_cue(0.62 if vowel != "CLOSED" else 0.0, vowel)
            if index == 0:
                assert window.eye_overlay.isHidden()
            for _ in range(3):
                clock[0] += 0.016
                window._render_audio_mouth_transition()
                frames.append(
                    window.character.pixmap()
                    .toImage()
                    .convertToFormat(QImage.Format_ARGB32)
                )
    return frames


def _assert_transition_integrity(
    window: CompanionWindow,
    frames: list[QImage],
    reference: MouthReference,
) -> None:
    assert len(
        {region_signature(frame, reference.mouth_rect) for frame in frames}
    ) >= 10
    assert len(
        {region_signature(frame, reference.eye_rect) for frame in frames}
    ) == 1, "eyes changed during mouth animation"
    clean_outside = outside_mouth_signature(
        reference.idle_base,
        reference.mouth_rect,
    )
    assert all(
        outside_mouth_signature(frame, reference.mouth_rect) == clean_outside
        for frame in frames
    ), "pixels outside the frozen mouth region changed"
    for side, region in reference.corner_regions.items():
        assert len({region_signature(frame, region) for frame in frames}) >= 4, (
            f"the {side} speech corner remained fixed during transitions"
        )
    assert window._active_speech_pose_suffix() == ""


def _assert_transition_smoothness(
    window: CompanionWindow,
    frames: list[QImage],
    mouth_rect: QRect,
) -> None:
    direct_difference = mean_region_difference(
        window.expression_pixmaps["mouth_wide"].toImage(),
        window.expression_pixmaps["mouth_o"].toImage(),
        mouth_rect,
    )
    adjacent = [
        mean_region_difference(first, second, mouth_rect)
        for first, second in pairwise(frames)
    ]
    assert direct_difference > 0.5
    assert max(adjacent) < direct_difference * 0.82, (
        f"largest adjacent transition {max(adjacent):.3f} at frame "
        f"{adjacent.index(max(adjacent)) + 1} exceeded "
        f"82% of the direct viseme difference {direct_difference:.3f}"
    )
    assert sum(value > 0.05 for value in adjacent) >= 8
    assert window.eye_overlay.isHidden()


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        try:
            _configure_window(window, app)
            reference = _build_mouth_reference(window)
            _assert_speech_expression_layers(window, reference)
            frames = _capture_transition_frames(window)
            _assert_transition_integrity(window, frames, reference)
            _assert_transition_smoothness(window, frames, reference.mouth_rect)
        finally:
            window.close()
            app.processEvents()
    print("MOUTH_VISUAL_CONTINUITY_OK")


if __name__ == "__main__":
    run()
