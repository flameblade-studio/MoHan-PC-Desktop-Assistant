"""A blink composite may stamp only a source bound to that expression.

``caught`` shares the ``cheek`` pose, and therefore the ``cheek-rest`` silhouette
whose retained native motion root does answer, but no blink source was ever
authored for the ``caught`` portrait.  Sharing a pose is not source authority, so
the portrait must come back untouched.  This must not be read as "blinking is
disabled": a base whose own source is bound - a registered per-expression
endpoint, or the neutral portrait the pose-bound native endpoint was authored on
- must still receive a real blink.  HALF and CLOSED are separate sources on
separate code paths and are therefore asserted separately.
"""

from __future__ import annotations

lazy import os
lazy import sys
lazy from collections.abc import Iterator
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import numpy as np
lazy import pytest
lazy from PySide6.QtCore import QRect, QTimer
lazy from PySide6.QtGui import QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.companion_animation_contract import (
    EXPRESSION_HALF_BLINK_FRAME_SOURCES,
    EXPRESSION_NATIVE_CLOSED_BLINK_FRAME_SOURCES,
    EXPRESSION_POSES,
    outfit_silhouette,
)
lazy from presentation.companion_face_assets import CompanionFaceAssetMethods
lazy from presentation.companion_window import CompanionWindow
lazy from tests.test_native_half_blink_routing import (
    PROJECT_ROOT,
    _CompositingRenderer,
    _NativeAuthority,
    _asset,
    _pixels,
)

# ``caught`` is a complete, identity-locked portrait with no authored blink
# source; ``mock_hit_front`` is a complete portrait that does own registered
# half and closed endpoints; ``idle`` is the neutral cheek portrait whose eyes
# the retained native motion root of ``cheek-rest`` was authored for.
UNBOUND_EXPRESSION = "caught"
BOUND_EXPRESSION = "mock_hit_front"
NATIVE_NEUTRAL_EXPRESSION = "idle"
NATIVE_NEUTRAL_POSE = "cheek"

HALF_OPACITY = 0.5
CLOSED_OPACITY = 1.0

# The registered front eye mask used by the routing subject, and the margin the
# native cheek endpoint's authored eyelid/brow patch extends past the registered
# cheek eye regions (measured: the patch reaches 20px above and 7px outside).
REGISTERED_MASK_REGIONS = (QRect(180, 153, 53, 34), QRect(220, 153, 56, 34))
REGISTERED_MASK_UNION = REGISTERED_MASK_REGIONS[0].united(REGISTERED_MASK_REGIONS[1])
ROUNDED_MASK_RADIUS = 10
NATIVE_ENDPOINT_MARGIN = 24


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def window() -> Iterator[CompanionWindow]:
    app = QApplication.instance() or QApplication([])
    previous_local_appdata = os.environ.get("LOCALAPPDATA")
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        companion = CompanionWindow(startup_speech=False)
        try:
            companion.show()
            app.processEvents()
            for timer in companion.findChildren(QTimer):
                timer.stop()
            yield companion
        finally:
            # Close the window and its profile database BEFORE the temporary
            # profile root is removed: Windows refuses to unlink a file whose
            # handle is still open, and swallow-free cleanup keeps that visible.
            companion.close()
            app.processEvents()
            companion.db.close()
    if previous_local_appdata is None:
        os.environ.pop("LOCALAPPDATA", None)
    else:
        os.environ["LOCALAPPDATA"] = previous_local_appdata


def _rgba(pixmap: QPixmap) -> np.ndarray:
    image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
    height, stride = image.height(), image.bytesPerLine()
    buffer = np.frombuffer(bytes(image.constBits()), dtype=np.uint8)
    return buffer[: stride * height].reshape(height, stride // 4, 4)[
        :, : image.width()
    ]


def _changed_counts(
    before: QPixmap,
    after: QPixmap,
    region: QRect,
) -> tuple[int, int]:
    first = _rgba(before)
    second = _rgba(after)
    assert first.shape == second.shape
    changed = np.any(first != second, axis=2)
    total = int(changed.sum())
    inside = int(
        changed[
            region.top() : region.bottom() + 1,
            region.left() : region.right() + 1,
        ].sum()
    )
    return inside, total - inside


def _outfit_overlay(window: CompanionWindow) -> object:
    return window.face_renderer._outfit_overlay


def _bound_endpoint_subject() -> tuple[object, _CompositingRenderer, QPixmap]:
    """A subject whose expression owns registered HALF and CLOSED endpoints."""

    half_key = EXPRESSION_HALF_BLINK_FRAME_SOURCES[BOUND_EXPRESSION]
    closed_key = EXPRESSION_NATIVE_CLOSED_BLINK_FRAME_SOURCES[BOUND_EXPRESSION]
    subject = object.__new__(CompanionFaceAssetMethods)
    base = _asset(BOUND_EXPRESSION)
    mask = CompanionFaceAssetMethods._soft_rounded_mask(
        REGISTERED_MASK_REGIONS,
        ((0, 255),),
        ROUNDED_MASK_RADIUS,
    )
    renderer = _CompositingRenderer()
    renderer._outfit_overlay = _NativeAuthority()
    subject.state = "idle"
    subject.expression_pixmaps = {
        BOUND_EXPRESSION: base,
        half_key: _asset(half_key),
        closed_key: _asset(closed_key),
    }
    subject.physics_expression_poses = {BOUND_EXPRESSION: "front"}
    subject.active_physics_pose = "front"
    subject.blink_masks = {"front": mask}
    subject.face_renderer = renderer
    subject._expression_eye_offset = lambda _expression: (0, 2)
    subject._pose_suffix = lambda _pose: "_front"
    subject._masked_region = CompanionFaceAssetMethods._masked_region
    subject._translated_pixmap = CompanionFaceAssetMethods._translated_pixmap
    return subject, renderer, base


def _assert_registered_endpoint_is_real_bytes(stem: str) -> QPixmap:
    image = QImage(str(PROJECT_ROOT / "assets" / "expressions" / f"{stem}.png"))
    assert not image.isNull()
    assert image.hasAlphaChannel()
    return _asset(stem)


def test_caught_has_no_matching_source_while_its_pose_endpoint_does(window) -> None:
    """The binding evidence: no per-expression source; the pose endpoint exists."""

    pose = EXPRESSION_POSES[UNBOUND_EXPRESSION]
    view_id = outfit_silhouette(UNBOUND_EXPRESSION, pose)
    assert EXPRESSION_HALF_BLINK_FRAME_SOURCES.get(UNBOUND_EXPRESSION) is None
    assert EXPRESSION_NATIVE_CLOSED_BLINK_FRAME_SOURCES.get(UNBOUND_EXPRESSION) is None
    assert window.expression_pixmaps.get(f"{UNBOUND_EXPRESSION}_half") is None
    assert (
        window.expression_pixmaps.get(f"{UNBOUND_EXPRESSION}_closed") is None
    )
    # Sharing the silhouette is exactly what made the portrait blink before:
    # the retained reviewed motion root answers for this pose.
    assert _outfit_overlay(window).has_native_motion(view_id) is True


def test_unbound_portrait_is_untouched_by_a_half_blink(window) -> None:
    window.state = UNBOUND_EXPRESSION
    base = window.expression_pixmaps[UNBOUND_EXPRESSION]
    blinked = window._blink_composite(base, UNBOUND_EXPRESSION, HALF_OPACITY)
    assert _pixels(blinked) == _pixels(base)


def test_unbound_portrait_is_untouched_by_a_closed_blink(window) -> None:
    window.state = UNBOUND_EXPRESSION
    base = window.expression_pixmaps[UNBOUND_EXPRESSION]
    blinked = window._blink_composite(base, UNBOUND_EXPRESSION, CLOSED_OPACITY)
    assert _pixels(blinked) == _pixels(base)


def test_registered_half_endpoint_still_stamps_a_real_blink(qapp) -> None:
    subject, renderer, base = _bound_endpoint_subject()
    half_key = EXPRESSION_HALF_BLINK_FRAME_SOURCES[BOUND_EXPRESSION]
    assert half_key == "mock_hit_front_half"
    source = _assert_registered_endpoint_is_real_bytes(half_key)

    result = subject._blink_composite(base, BOUND_EXPRESSION, HALF_OPACITY)

    expected = CompanionFaceAssetMethods._masked_region(
        source,
        subject.blink_masks["front"],
    )
    assert len(renderer.calls) == 1
    assert _pixels(renderer.calls[0]["patch"]) == _pixels(expected)
    inside, outside = _changed_counts(base, result, REGISTERED_MASK_UNION)
    assert inside > 0
    assert outside == 0


def test_registered_closed_endpoint_still_stamps_a_real_blink(qapp) -> None:
    subject, renderer, base = _bound_endpoint_subject()
    closed_key = EXPRESSION_NATIVE_CLOSED_BLINK_FRAME_SOURCES[BOUND_EXPRESSION]
    assert closed_key == "mock_hit_front_closed"
    source = _assert_registered_endpoint_is_real_bytes(closed_key)

    result = subject._blink_composite(base, BOUND_EXPRESSION, CLOSED_OPACITY)

    expected = CompanionFaceAssetMethods._masked_region(
        source,
        subject.blink_masks["front"],
    )
    assert len(renderer.calls) == 1
    assert _pixels(renderer.calls[0]["patch"]) == _pixels(expected)
    inside, outside = _changed_counts(base, result, REGISTERED_MASK_UNION)
    assert inside > 0
    assert outside == 0


def test_pose_bound_native_endpoint_still_blinks_its_own_neutral_portrait(
    window,
) -> None:
    """The fix must not disable the native endpoint where it really is the source."""

    assert NATIVE_NEUTRAL_EXPRESSION not in EXPRESSION_POSES
    assert (
        EXPRESSION_NATIVE_CLOSED_BLINK_FRAME_SOURCES.get(NATIVE_NEUTRAL_EXPRESSION)
        is None
    )
    view_id = outfit_silhouette(NATIVE_NEUTRAL_EXPRESSION, NATIVE_NEUTRAL_POSE)
    assert _outfit_overlay(window).has_native_motion(view_id) is True
    window.state = "idle"
    base = window.expression_pixmaps[NATIVE_NEUTRAL_EXPRESSION]

    blinked = window._blink_composite(base, NATIVE_NEUTRAL_EXPRESSION, CLOSED_OPACITY)

    band = window._blink_regions()[NATIVE_NEUTRAL_POSE][0]
    for region in window._blink_regions()[NATIVE_NEUTRAL_POSE][1:]:
        band = band.united(region)
    band = band.adjusted(
        -NATIVE_ENDPOINT_MARGIN,
        -NATIVE_ENDPOINT_MARGIN,
        NATIVE_ENDPOINT_MARGIN,
        NATIVE_ENDPOINT_MARGIN,
    )
    inside, outside = _changed_counts(base, blinked, band)
    assert inside > 0
    assert outside == 0
