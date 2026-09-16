"""Regression coverage for the reviewed native pose rendering hooks.

These tests deliberately use tiny in-memory pixmaps.  The native hook must
win before the legacy rig, mouth, and blink sources are considered, while a
missing native registration must leave those legacy paths usable.
"""

from __future__ import annotations

lazy import os
lazy from dataclasses import dataclass, field
lazy from types import SimpleNamespace

lazy import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QColor, QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.companion_animation_contract import CHEEK_SPEECH_CLOSED_EXPRESSION
lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from infrastructure import layered_face_renderer as renderer_module
lazy from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer


CANVAS_SIZE = (20, 20)


def _qt_app() -> QApplication:
    """Create the offscreen Qt application once for this module."""

    app = QApplication.instance()
    return app if app is not None else QApplication([])


def _solid(color: str) -> QPixmap:
    pixmap = QPixmap(*CANVAS_SIZE)
    pixmap.fill(QColor(color))
    return pixmap


def _single_pixel_mask(x: int = 5, y: int = 5) -> QPixmap:
    image = QImage(*CANVAS_SIZE, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    image.setPixelColor(x, y, QColor("white"))
    return QPixmap.fromImage(image)


def _pixel_name(pixmap: QPixmap, x: int = 5, y: int = 5) -> str:
    return pixmap.toImage().pixelColor(x, y).name()


def _motion(*, speaking: bool, pose: FacePose) -> FaceMotionFrame:
    return FaceMotionFrame(
        pose,
        "speaking" if speaking else "idle",
        Viseme.A if speaking else Viseme.CLOSED,
        MouthShape(aperture=0.9, width=0.7) if speaking else MouthShape(),
        ExpressionShape(),
    )


@dataclass
class _StubNativeOverlay:
    """Small overlay double exposing the renderer's native hook boundary."""

    native_states: dict[str, QPixmap] = field(default_factory=dict)
    native_blink: QPixmap | None = None
    native_motion_views: set[str] = field(default_factory=set)
    state_calls: list[tuple[str, bool]] = field(default_factory=list)
    blink_calls: list[tuple[str, str]] = field(default_factory=list)
    apply_calls: list[str] = field(default_factory=list)

    def has_native_motion(self, view_id: str) -> bool:
        return view_id in self.native_motion_views

    def render_native_state(self, view_id: str, *, speaking: bool = False) -> QPixmap | None:
        self.state_calls.append((view_id, speaking))
        frame = self.native_states.get(view_id)
        return QPixmap(frame) if frame is not None else None

    def render_native_blink(
        self,
        base: QPixmap,
        view_id: str,
        *,
        eye_state: str,
    ) -> QPixmap | None:
        del base
        self.blink_calls.append((view_id, eye_state))
        return QPixmap(self.native_blink) if self.native_blink is not None else None

    def native_neutral(self, view_id: str) -> QPixmap | None:
        del view_id
        return None

    def apply(self, frame: QPixmap, view_id: str) -> QPixmap:
        self.apply_calls.append(view_id)
        return frame


def test_native_speech_state_precedes_legacy_mouth_source(monkeypatch):
    """A registered native speech frame cannot be painted over by old mouth data."""

    _qt_app()
    native = _solid("blue")
    stale_mouth = _solid("red")
    overlay = _StubNativeOverlay(native_states={"cheek-rest": native})
    renderer = LayeredParametricFaceRenderer(
        outfit_overlay=overlay,
        use_detachable=False,
    )

    def legacy_path_must_not_run(*args, **kwargs):
        del args, kwargs
        pytest.fail("native state should return before the legacy portrait path")

    monkeypatch.setattr(renderer, "_detachable_portrait", legacy_path_must_not_run)
    monkeypatch.setattr(renderer, "render_pose", legacy_path_must_not_run)

    result = renderer.render(
        _solid("green"),
        _motion(speaking=True, pose=FacePose.CHEEK),
        SimpleNamespace(
            mouth_source=stale_mouth,
            mouth_mask=_single_pixel_mask(),
        ),
    )

    assert overlay.state_calls == [("cheek-rest", True)]
    assert _pixel_name(result) == QColor("blue").name()
    assert _pixel_name(result, 0, 0) == QColor("blue").name()


def test_native_closed_blink_precedes_legacy_blink_source():
    """A registered closed-eye frame must win before the old blink source."""

    _qt_app()
    native = _solid("blue")
    stale_blink = _solid("red")
    overlay = _StubNativeOverlay(native_blink=native)
    renderer = LayeredParametricFaceRenderer(
        outfit_overlay=overlay,
        use_detachable=False,
    )

    result = renderer.render_overlay(
        _solid("green"),
        stale_blink,
        eye_state="closed",
        view_id="cheek-rest",
    )

    assert overlay.blink_calls == [("cheek-rest", "closed")]
    assert _pixel_name(result) == QColor("blue").name()
    assert _pixel_name(result, 0, 0) == QColor("blue").name()


def test_discrete_speech_is_enabled_only_for_registered_native_cheek():
    """The cheek endpoint uses discrete photographs while front and lean stay legacy."""

    _qt_app()
    overlay = _StubNativeOverlay(native_motion_views={"cheek-rest"})
    renderer = LayeredParametricFaceRenderer(
        outfit_overlay=overlay,
        use_detachable=False,
    )

    assert renderer.supports_discrete_speech(CHEEK_SPEECH_CLOSED_EXPRESSION)
    assert not renderer.supports_discrete_speech("idle_front")
    assert not renderer.supports_discrete_speech("idle_lean")


def test_unregistered_native_state_keeps_legacy_mouth_path(monkeypatch):
    """A missing native pose returns None and still permits legacy speech painting."""

    _qt_app()
    legacy = _solid("green")
    stale_mouth = _solid("red")
    overlay = _StubNativeOverlay()
    renderer = LayeredParametricFaceRenderer(
        outfit_overlay=overlay,
        use_detachable=False,
    )
    monkeypatch.setattr(renderer, "render_pose", lambda *args, **kwargs: QPixmap(legacy))

    result = renderer.render(
        _solid("black"),
        _motion(speaking=True, pose=FacePose.FRONT),
        SimpleNamespace(
            mouth_source=stale_mouth,
            mouth_mask=_single_pixel_mask(),
        ),
    )

    assert overlay.state_calls == [("front-crossed", True)]
    assert _pixel_name(result) == QColor("red").name()
    assert _pixel_name(result, 0, 0) == QColor("green").name()


def test_unregistered_native_blink_keeps_legacy_source(monkeypatch):
    """A native blink hook returning None leaves the legacy blink source active."""

    _qt_app()
    stale_blink = _solid("red")
    overlay = _StubNativeOverlay()
    renderer = LayeredParametricFaceRenderer(
        outfit_overlay=overlay,
        use_detachable=False,
    )
    # The legacy blink path normally adds appearance-pack pigment after the
    # source.  This test isolates source fallback from that optional service.
    monkeypatch.setattr(renderer_module, "paint_blink_makeup", lambda *args, **kwargs: None)

    result = renderer.render_overlay(
        _solid("green"),
        stale_blink,
        eye_state="closed",
        view_id="front-crossed",
    )

    assert overlay.blink_calls == [("front-crossed", "closed")]
    assert _pixel_name(result) == QColor("red").name()
    assert _pixel_name(result, 0, 0) == QColor("red").name()
