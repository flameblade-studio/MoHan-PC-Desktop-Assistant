"""The four gesture expressions dress in their own silhouette layers through the runtime path.

``mock_scold``, ``mock_hit_front``, ``eureka_front`` and ``exasperated_front`` have
a body that differs from the neutral front pose, so the official pack ships
garment/hair/headwear layers cut on each gesture portrait.  The layered face
renderer must draw that portrait, dress it with the matching gesture silhouette
(never ``front-crossed``) and still paint the speech mouth patch afterwards.
"""

from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy import pytest
lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.companion_animation_contract import (
    EXPRESSION_SPEECH_FRAMES,
    GESTURE_OUTFIT_SILHOUETTES,
    GESTURE_SPEECH_EXPRESSIONS,
    GESTURE_SPEECH_MOUTH_RECTS,
    POSE_OUTFIT_SILHOUETTES,
    gesture_portrait_expression,
    outfit_silhouette,
)
lazy from domain.face_rig import ExpressionShape, FaceMotionFrame, FacePose, MouthShape, Viseme
lazy from domain.outfit_pack import BASE_SILHOUETTES, GESTURE_SILHOUETTES
lazy from domain.outfit_pack_makeup import HALF_BODY_RIGS
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer
lazy from presentation.presentation_resources import FaceRenderLayers

CANVAS = 465
# Upper chest of the bare portraits on the 465px canvas: grey tank top in every gesture,
# below the collar and above the hands of mock_hit_front.
# 2026-09-05 依 v4 原圖重抽後，垂髮披在胸口兩側，原本 170×60 的胸口窄框只剩中央白色
# 內襟露出；探測區改成整個上半身（藍袍在肩、袖與腰側都看得到），門檻維持不變。
# 量測：四個手勢姿勢在此框內 changed 1456–3846、blue 243–576。
TORSO = QRect(100, 230, 270, 120)
# A robe pixel counts as blue when its blue channel leads red by at least this much.
BLUE_MARGIN = 40
GREY_TOLERANCE = 12
GREY_MIN, GREY_MAX = 70, 200
# The inner robe is white and the outer robe blue: both replace the grey tank top.
MIN_ROBE_BLUE_PIXELS = 100
MIN_DRESSED_PIXELS = 400
DRESSED_DISTANCE = 40
# Runtime layers dressing a gesture: robe, hair front (back is transparent), hairpiece, 3 makeup slots.
MIN_DRESSED_LAYERS = 5


def _app() -> object:
    return QApplication.instance() or QApplication([])


class _RecordingOverlay:
    """The real overlay plus the list of silhouettes it was asked to dress."""

    def __init__(self, store: Path) -> None:
        self.inner = ActiveOutfitOverlay(store, ROOT)
        self.views: list[str] = []

    def apply(self, frame: QPixmap, view_id: str) -> QPixmap:
        self.views.append(view_id)
        return self.inner.apply(frame, view_id)

    def layer_count(self, view_id: str) -> int:
        return self.inner.layer_count(view_id)


def _motion(expression: str) -> FaceMotionFrame:
    return FaceMotionFrame(FacePose.FRONT, expression, Viseme.CLOSED, MouthShape(), ExpressionShape())


def _portrait(expression: str) -> QPixmap:
    pixmap = QPixmap(str(ROOT / "assets" / "expressions" / f"{expression}.png"))
    assert not pixmap.isNull(), expression
    return pixmap.scaled(CANVAS, CANVAS, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _is_grey(color: QColor) -> bool:
    red, green, blue, _alpha = color.getRgb()
    return (
        abs(red - green) <= GREY_TOLERANCE
        and abs(green - blue) <= GREY_TOLERANCE
        and GREY_MIN < red < GREY_MAX
    )


def _robe_over_grey_pixels(bare: QImage, dressed: QImage, area: QRect) -> tuple[int, int]:
    """(pixels no longer grey, robe-blue pixels) where the bare portrait shows the grey tank top."""
    changed = blue = 0
    for y in range(area.top(), area.bottom() + 1):
        for x in range(area.left(), area.right() + 1):
            before, after = bare.pixelColor(x, y), dressed.pixelColor(x, y)
            if not _is_grey(before):
                continue
            distance = sum(abs(a - b) for a, b in zip(after.getRgb()[:3], before.getRgb()[:3], strict=True))
            changed += distance >= DRESSED_DISTANCE
            blue += after.blue() - after.red() >= BLUE_MARGIN
    return changed, blue


def _assert_dressed(bare: QPixmap, dressed: QPixmap, label: str) -> None:
    changed, blue = _robe_over_grey_pixels(bare.toImage(), dressed.toImage(), TORSO)
    assert changed >= MIN_DRESSED_PIXELS and blue >= MIN_ROBE_BLUE_PIXELS, (label, changed, blue)


def _changed_pixels(before: QImage, after: QImage, allowed: QRect) -> tuple[int, int]:
    inside = outside = 0
    for y in range(before.height()):
        for x in range(before.width()):
            if before.pixel(x, y) == after.pixel(x, y):
                continue
            if allowed.contains(x, y):
                inside += 1
            else:
                outside += 1
    return inside, outside


def _rect_mask(rect: QRect) -> QPixmap:
    mask = QPixmap(CANVAS, CANVAS)
    mask.fill(Qt.transparent)
    painter = QPainter(mask)
    painter.fillRect(rect, Qt.white)
    painter.end()
    return mask


def test_gesture_silhouette_mapping_is_defined_once_in_domain() -> None:
    assert set(GESTURE_OUTFIT_SILHOUETTES) == GESTURE_SPEECH_EXPRESSIONS
    assert set(GESTURE_OUTFIT_SILHOUETTES.values()) == set(GESTURE_SILHOUETTES)
    assert set(POSE_OUTFIT_SILHOUETTES.values()) == set(BASE_SILHOUETTES)
    assert all(silhouette in HALF_BODY_RIGS for silhouette in GESTURE_OUTFIT_SILHOUETTES.values())
    assert outfit_silhouette("idle_front", "front") == "front-crossed"
    assert outfit_silhouette("happy", "cheek") == "cheek-rest"
    assert outfit_silhouette("protective_front", "front") == "front-crossed"
    assert outfit_silhouette("mock_scold", "front") == "front-mock-scold"
    assert outfit_silhouette("mock_scold_speech_open", "front") == "front-mock-scold"
    assert outfit_silhouette("eureka_front_speech_blink", "front") == "front-eureka"
    assert gesture_portrait_expression("happy_speech_open") is None
    assert gesture_portrait_expression("mock_hit_front_speech_i") == "mock_hit_front"


@pytest.mark.parametrize("expression", sorted(GESTURE_SPEECH_EXPRESSIONS))
def test_gesture_expression_composites_its_own_portrait_and_silhouette(tmp_path: Path, expression: str) -> None:
    _app()
    overlay = _RecordingOverlay(tmp_path / "store")
    renderer = LayeredParametricFaceRenderer(outfit_overlay=overlay)
    bare = _portrait(expression)
    rendered = renderer.render(bare, _motion(expression), None)
    assert not rendered.isNull() and rendered.size() == bare.size()
    silhouette = GESTURE_OUTFIT_SILHOUETTES[expression]
    assert overlay.views == [silhouette]
    assert overlay.layer_count(silhouette) >= MIN_DRESSED_LAYERS
    assert overlay.layer_count("front-crossed") == 0
    # A robe over the chest where the bare gesture portrait is grey.
    _assert_dressed(bare, rendered, expression)
    # The frame is the gesture portrait, not the neutral front body dressed in
    # front-crossed: the two composites must differ.
    neutral = renderer.render(_portrait("idle_front"), _motion("idle_front"), None)
    assert overlay.views == [silhouette, "front-crossed"]
    assert neutral.toImage() != rendered.toImage()


def test_mock_scold_speech_open_keeps_the_robe_and_opens_the_mouth(tmp_path: Path) -> None:
    """The overlay is applied before the mouth patch, exactly as the companion's speech path does."""
    _app()
    expression = "mock_scold"
    overlay = _RecordingOverlay(tmp_path / "store")
    renderer = LayeredParametricFaceRenderer(outfit_overlay=overlay)
    closed = _portrait(expression)
    open_frame = EXPRESSION_SPEECH_FRAMES[expression]["open"]
    mouth_rect = GESTURE_SPEECH_MOUTH_RECTS[expression]
    layers = FaceRenderLayers(
        mouth_source=_portrait(open_frame),
        mouth_mask=_rect_mask(mouth_rect),
        mouth_rect=mouth_rect,
    )
    speech_motion = _motion(open_frame)
    shut = renderer.render(closed, speech_motion, layers, aperture=0.0)
    opened = renderer.render(closed, speech_motion, layers, aperture=1.0)
    assert overlay.views == ["front-mock-scold", "front-mock-scold"]
    inside, outside = _changed_pixels(shut.toImage(), opened.toImage(), mouth_rect)
    assert inside > 0
    assert outside == 0
    for label, frame in (("shut", shut), ("opened", opened)):
        _assert_dressed(closed, frame, label)
