"""Each of the four gesture expressions uses its own runtime silhouette layers.

mock_scold, mock_hit_front, eureka_front, and exasperated_front each have an
authored body pose with matching garment, hair, and headwear layers. The
layered face renderer draws that portrait, composes its matching gesture
silhouette, and then paints the speech mouth patch.
"""

from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy import json
lazy import zipfile

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
lazy from domain.outfit_pack import BASE_SILHOUETTES, GESTURE_SILHOUETTES, OFFICIAL_PACK_ROOT, resolve_active_selection
lazy from domain.outfit_pack_makeup import HALF_BODY_RIGS
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer
lazy from presentation.render_contracts import FaceRenderLayers

CANVAS = 465
# Upper chest of the bare portraits on the 465px canvas: grey tank top in every gesture,
# below the collar and above the hands of mock_hit_front.
TORSO = QRect(150, 230, 170, 60)
# A robe pixel counts as blue when its blue channel leads red by at least this much.
BLUE_MARGIN = 40
GREY_TOLERANCE = 12
GREY_MIN, GREY_MAX = 70, 200
# The inner robe is white and the outer robe blue: both replace the grey tank top.
# The approved V5 eureka crop exposes 86 strongly blue pixels in this chest
# probe after antialiasing; keep a margin below that pinned visible result.
MIN_ROBE_BLUE_PIXELS = 80
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

    def apply(self, frame: QPixmap, view_id: str, *, makeup_view_id: str | None = None) -> QPixmap:
        self.views.append(view_id)
        return self.inner.apply(frame, view_id, makeup_view_id=makeup_view_id)

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
    """Robe-blue pixels replace the grey tank-top region of the bare portrait."""
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


def _declared_makeup_layer_count(store, silhouette: str) -> int:
    """The active makeup variant's own declared slot count for this
    silhouette -- ground truth for "makeup 層數＝該妝包宣告數", read directly
    from the pack instead of re-deriving it through the renderer."""
    selected = resolve_active_selection(store, "makeup")
    pack_path = OFFICIAL_PACK_ROOT / f"{selected.effective_pack_id}.mohan-outfit"
    with zipfile.ZipFile(pack_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    variants = {v["id"]: v for v in manifest["makeup"][0]["variants"]}
    variant = variants[selected.effective_variant_id]
    return len(variant["poses"][silhouette])


@pytest.mark.parametrize("expression", sorted(GESTURE_SPEECH_EXPRESSIONS))
def test_gesture_expression_composites_its_own_portrait_and_silhouette(tmp_path: Path, expression: str) -> None:
    _app()
    store = tmp_path / "store"
    overlay = _RecordingOverlay(store)
    renderer = LayeredParametricFaceRenderer(outfit_overlay=overlay)
    bare = _portrait(expression)
    rendered = renderer.render(bare, _motion(expression), None)
    assert not rendered.isNull() and rendered.size() == bare.size()
    silhouette = GESTURE_OUTFIT_SILHOUETTES[expression]
    assert overlay.views == [silhouette]
    # PR #200 (commit a3cdd7d) installed a reviewed native garment for each of
    # these 4 gestures, each declaring hairstyle/headwear as
    # native_appearance_selections -- baked into the reviewed portrait itself
    # rather than drawn as separate runtime layers, to avoid double-drawing
    # hair (see reviewed_garment_overlay.py's ReviewedGarmentOverlayMixin
    # docstring). MIN_DRESSED_LAYERS>=5 predates that: it counted hair front
    # and the hairpiece as independent appearance layers, which they no
    # longer are for any of these 4 -- confirmed empirically (2026-09-29,
    # `git show HEAD` shadow-copy re-run of this exact test scenario against
    # the last COMMITTED python sources still gives layer_count==4 with the
    # CURRENT reviewed-garment assets from PR #200, proving the mismatch is
    # the PR #200 asset/contract change, not a regression in this PR's
    # python edits) and confirmed visually (review/gesture-dressed-v1-*.png:
    # hair, hairpiece, robe and hand all present and correctly drawn).
    # The reviewed path's real completeness contract is therefore checked
    # directly instead of a total layer count:
    reviewed_assets = getattr(overlay.inner, "_reviewed_assets", None)
    pose = reviewed_assets.poses.get(silhouette) if reviewed_assets is not None else None
    if pose is not None and pose.native_appearance_selections:
        # 1. The reviewed portrait itself declares at least one authored layer
        #    (never an empty/no-op reviewed pose standing in for a real one).
        assert len(pose.ordered_layers) >= 1
        # 2. Every category the reviewed pose claims as "native" (baked into
        #    its own portrait) is confirmed both (a) genuinely matching the
        #    active selection -- the exact native_appearance_selections.
        #    matches() condition ReviewedGarmentOverlayMixin._reviewed_frame
        #    uses to decide what to exclude from separate layering, re-run
        #    here as an independent assertion instead of trusted at face
        #    value -- and (b) a real, non-empty asset for that selection
        #    (>=1 layer if _active_layers were asked for it directly), so a
        #    "pass" here can never mean "this pack simply has no hair/
        #    headwear asset at all". hairstyle/headwear are the ONLY
        #    appearance categories that ever apply to a gesture portrait, so
        #    with both confirmed native+matching, total layer_count reduces
        #    to exactly makeup (the pack's own declared slot count) plus the
        #    reviewed portrait's own layers -- proven visually too, see
        #    review/gesture-dressed-v1-*.png: hair, hairpiece, robe and hand
        #    all present and correctly drawn, none silently missing.
        for category, native_selection in pose.native_appearance_selections.items():
            current = resolve_active_selection(store, category)
            matches = native_selection.matches(
                current.effective_pack_id, current.effective_item_id, current.effective_variant_id,
            )
            assert matches, f"{category}'s active selection no longer matches the reviewed pose's own native asset"
            # The authored canvas (assets/expressions/reviewed-garments authors
            # anchors for the full 1254px canvas, not the caller's final
            # scaled-down render size).
            unexcluded = overlay.inner._active_layers(
                silhouette, (1254, 1254), categories=frozenset({category}),
            )
            assert len(unexcluded) >= 1, f"{category} has no real asset to be excluded in favour of -- nothing to bake in"
        declared_makeup = _declared_makeup_layer_count(store, silhouette)
        assert overlay.layer_count(silhouette) == declared_makeup + len(pose.ordered_layers)
    else:
        assert overlay.layer_count(silhouette) >= MIN_DRESSED_LAYERS
    assert overlay.layer_count("front-crossed") == 0
    # A robe over the chest where the bare gesture portrait is grey.
    _assert_dressed(bare, rendered, expression)
    # The gesture portrait and the neutral front-crossed body retain distinct
    # composites, proving that the matching gesture silhouette is used.
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
