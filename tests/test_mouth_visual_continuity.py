from __future__ import annotations

lazy import os
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QRect, QTimer
lazy from PySide6.QtGui import QImage
lazy from PySide6.QtWidgets import QApplication

lazy from domain.companion_animation_contract import CHEEK_SPEECH_CLOSED_EXPRESSION
lazy from presentation.companion_window import CompanionWindow

VOWEL_REPEAT_COUNT = 5
MIN_CORNER_CHANGED_PIXELS = 12
MIN_MOUTH_SIGNATURES = 4
MIN_TRANSITION_SIGNATURES = 10
MIN_CORNER_SIGNATURES = 4
MIN_DIRECT_DIFFERENCE = 0.5
ADJACENT_RATIO = 0.82
MIN_ADJACENT_DIFFERENCE = 0.05
MIN_ADJACENT_CHANGED = 8
# A reviewed pose with native complete mouth photographs switches endpoints
# discretely at DISCRETE_SPEECH_SWITCH_PROGRESS: the sweep shows the rest
# endpoint, the one open endpoint shared by A/O/I, then rest again, and a
# blended frame would expose both lip contours at once.
DISCRETE_ENDPOINT_COUNT = 2
DISCRETE_ENDPOINT_RUNS = 3


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


def _discrete_speech_active(window: CompanionWindow) -> bool:
    capability = getattr(window.face_renderer, "supports_discrete_speech", None)
    base = window.speech_gesture_expression or window.speech_closed_expression
    return callable(capability) and bool(capability(base))


def _signature_runs(signatures: list[tuple[int, ...]]) -> list[tuple[int, ...]]:
    runs: list[tuple[int, ...]] = []
    for signature in signatures:
        if not runs or runs[-1] != signature:
            runs.append(signature)
    return runs


def _assert_discrete_endpoints(signatures: list[tuple[int, ...]], label: str) -> None:
    runs = _signature_runs(signatures)
    assert len(set(signatures)) == DISCRETE_ENDPOINT_COUNT, (
        f"{label} shows exactly the rest and the open reviewed endpoint"
    )
    assert len(runs) == DISCRETE_ENDPOINT_RUNS, (
        f"{label} switches endpoints once in each direction with no blended frame"
    )
    assert runs[0] == runs[-1], f"{label} returns to the rest endpoint after CLOSED"


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
            ) >= MIN_CORNER_CHANGED_PIXELS, f"{expression} left the neutral {side} corner behind"
        assert outside_region_changed_pixel_count(
            reference.idle_base,
            speech_frame,
            reference.mouth_rect,
        ) == 0, f"{expression} changed pixels outside the cheek mouth clip"
    assert len(mouth_signatures) >= MIN_MOUTH_SIGNATURES, (
        'Moving corners must preserve distinct A/I/U/E/O shapes'
    )


def _capture_transition_frames(window: CompanionWindow) -> list[QImage]:
    frames: list[QImage] = []
    # Hold each target through the production 50 Hz anti-flicker interval.
    vowels = ("A",) * VOWEL_REPEAT_COUNT + ("O",) * VOWEL_REPEAT_COUNT + ("I",) * VOWEL_REPEAT_COUNT + ("CLOSED",) * 4
    # A stable 60 Hz clock avoids scheduler-dependent skipped frames on CI.
    clock = [100.0]
    with patch("time.perf_counter", side_effect=lambda: clock[0]):
        for index, vowel in enumerate(vowels):
            if index == VOWEL_REPEAT_COUNT:
                # A delayed callback preserves the face currently owning live speech.
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
    mouth_signatures = [region_signature(frame, reference.mouth_rect) for frame in frames]
    if _discrete_speech_active(window):
        # Native complete mouth endpoints own the chin-rest pose: the whole
        # mouth, corners included, steps between the reviewed photographs.
        _assert_discrete_endpoints(mouth_signatures, "the mouth")
        for side, region in reference.corner_regions.items():
            corner_signatures = [region_signature(frame, region) for frame in frames]
            assert len(_signature_runs(corner_signatures)) == DISCRETE_ENDPOINT_RUNS, (
                f"the {side} speech corner follows the reviewed endpoints"
            )
    else:
        # The renderer recomposes all 25 half-body layers each tick. The mouth
        # region varies through transitions; eye and surrounding regions follow
        # the current complete composition contract.
        assert len(set(mouth_signatures)) >= MIN_TRANSITION_SIGNATURES
        for side, region in reference.corner_regions.items():
            assert len({region_signature(frame, region) for frame in frames}) >= MIN_CORNER_SIGNATURES, (
                f"the {side} speech corner remained fixed during transitions"
            )
    assert window._active_speech_pose_suffix() == ""


def _assert_transition_smoothness(
    window: CompanionWindow,
    frames: list[QImage],
    mouth_rect: QRect,
) -> None:
    # motion.mouth drives aperture, width, rounding, and jaw continuously.
    # The 25-layer composition must vary through transition frames, with
    # continuity assessed under the current renderer contract.
    mouth_signatures = [region_signature(frame, mouth_rect) for frame in frames]
    if _discrete_speech_active(window):
        _assert_discrete_endpoints(mouth_signatures, "the mouth")
    else:
        assert len(set(mouth_signatures)) >= MIN_TRANSITION_SIGNATURES
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
