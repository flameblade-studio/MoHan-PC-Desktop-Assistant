"""Native speaking frames keep authored tooth pixels stable during articulation."""
from __future__ import annotations

lazy import os
lazy from dataclasses import replace
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import pytest
lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication
lazy from domain.constants import FULL_BODY_LAYER_Z_ORDER
lazy from domain.face_rig import ExpressionShape, FaceMotionFrame, FacePose, MouthShape, Viseme
lazy from infrastructure import layered_full_body_assets as assets
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer

VIEW = "yaw+000-pitch+00"
CANVAS = (64, 80)
TOOTH_RECT = QRect(28, 40, 9, 3)


def _png(path: Path, *, tooth: str | None = None, size: tuple[int, int] = CANVAS,
         opaque: bool = False) -> None:
    image = QImage(*size, QImage.Format_RGBA8888)
    image.fill(QColor("#bb987d") if opaque else QColor("transparent"))
    if tooth:
        painter = QPainter(image)
        painter.fillRect(TOOTH_RECT, QColor(tooth))
        painter.end()
    assert image.save(str(path))


def _renderer(tmp_path: Path) -> tuple[LayeredFullBodyRenderer, assets.LayeredFullBodyView]:
    QApplication.instance() or QApplication([])
    body = tmp_path / "body.png"
    frame_a, frame_o = tmp_path / "a.png", tmp_path / "o.png"
    _png(body, opaque=True)
    _png(frame_a, tooth="#eee8df")
    _png(frame_o, tooth="#c0a292")
    view = assets.LayeredFullBodyView(
        VIEW, frozendict({"body": body}), mouth_center_x=32.0,
        speech_frames=frozendict({Viseme.A: frame_a, Viseme.U: frame_a, Viseme.O: frame_o}),
    )
    manifest = assets.LayeredFullBodyManifest(frozendict({VIEW: view}))
    return LayeredFullBodyRenderer(manifest), view


def _motion(viseme: Viseme, aperture: float, *, u_inward: float = 0.) -> FaceMotionFrame:
    return FaceMotionFrame(
        FacePose.FRONT, "native_speech", viseme,
        MouthShape(aperture=aperture, u_inward=u_inward), ExpressionShape(), breath=0.5,
    )


def test_authored_teeth_keep_shape_color_and_registration_at_large_aperture(tmp_path: Path) -> None:
    renderer, view = _renderer(tmp_path)
    first = renderer.render_view(VIEW, _motion(Viseme.A, 0.4)).toImage()
    widest = renderer.render_view(VIEW, _motion(Viseme.A, 1.0)).toImage()
    rounded = renderer.render_view(VIEW, _motion(Viseme.U, 1.0, u_inward=1.0)).toImage()
    assert first == widest == rounded
    assert widest.pixelColor(32, 41).name() == "#eee8df"
    # Enamel has exactly the authored height; its upper/lower neighbouring skin is untouched.
    body = QImage(str(view.path("body")))
    assert widest.pixelColor(32, 39) == body.pixelColor(32, 39)
    assert widest.pixelColor(32, 43) == body.pixelColor(32, 43)
    for y in range(CANVAS[1]):
        for x in range(CANVAS[0]):
            if not TOOTH_RECT.contains(x, y):
                assert widest.pixelColor(x, y) == body.pixelColor(x, y)


def test_speech_selects_native_viseme_and_restores_closed_frame(tmp_path: Path) -> None:
    renderer, _ = _renderer(tmp_path)
    rest = renderer.render_view(VIEW, _motion(Viseme.CLOSED, 0.)).toImage()
    assert renderer.render_view(VIEW, _motion(Viseme.O, 0.4)).toImage().pixelColor(32, 41).name() == "#c0a292"
    assert renderer.render_view(VIEW, _motion(Viseme.CLOSED, 0.)).toImage() == rest
    assert renderer.render_view(VIEW, _motion(Viseme.A, 0.)).toImage() == rest
    with pytest.raises(ValueError, match="Missing native speech frame"):
        renderer.render_view(VIEW, _motion(Viseme.I, 0.5))


def test_speech_bytes_are_frozen_before_rendering_and_cache_eviction(tmp_path: Path) -> None:
    renderer, view = _renderer(tmp_path)
    _png(view.speech_frames[Viseme.A], tooth="red")
    frame = renderer.render_view(VIEW, _motion(Viseme.A, 0.5)).toImage()
    assert frame.pixelColor(32, 41).name() == "#eee8df"
    renderer._pixmap_cache.clear()
    assert renderer.render_view(VIEW, _motion(Viseme.A, 0.5)).toImage() == frame


@pytest.mark.parametrize("size,opaque", [((1, 1), False), (CANVAS, True)])
def test_speech_rejects_non_native_or_opaque_frame(tmp_path: Path, size: tuple[int, int], opaque: bool) -> None:
    _, view = _renderer(tmp_path)
    invalid = tmp_path / "invalid.png"
    _png(invalid, size=size, opaque=opaque)
    view = replace(view, speech_frames=frozendict({Viseme.A: invalid}))
    with pytest.raises(ValueError, match="same-canvas transparent RGBA"):
        LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))


def test_optional_speech_files_require_complete_viseme_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(assets, "VIEW_IDS", (VIEW,))
    size = (assets.FULL_BODY_DIMENSION_WIDTH, assets.FULL_BODY_DIMENSION_HEIGHT)
    for layer in FULL_BODY_LAYER_Z_ORDER:
        _png(tmp_path / f"{VIEW}_{layer}.png", size=size)
    assert not assets.load_layered_full_body_assets(tmp_path).view(VIEW).speech_frames
    _png(tmp_path / f"{VIEW}_speech_A.png", size=size, tooth="white")
    with pytest.raises(FileNotFoundError, match="incomplete full-body speech set"):
        assets.load_layered_full_body_assets(tmp_path)
    for viseme in Viseme:
        if viseme is not Viseme.CLOSED:
            _png(tmp_path / f"{VIEW}_speech_{viseme.value}.png", size=size, tooth="white")
    view = assets.load_layered_full_body_assets(tmp_path).view(VIEW)
    assert set(view.speech_frames) == set(Viseme) - {Viseme.CLOSED}


@pytest.mark.parametrize("aperture", [0.08, 0.4, 1.0])
def test_lipstick_cannot_paint_authored_teeth_but_still_paints_lips(tmp_path: Path, aperture: float) -> None:
    renderer, view = _renderer(tmp_path)
    before_makeup = renderer.render_view(VIEW, _motion(Viseme.A, aperture)).toImage()
    mask = tmp_path / "oral.png"
    _png(mask, tooth="white")
    masks = frozendict({viseme: mask for viseme in view.speech_frames})
    view = replace(view, speech_oral_masks=masks)

    class LipstickOverlay:
        def apply_animated(self, frame, view_id, paint_motion, *, paint_after_makeup=None, **options):
            del view_id, options
            frame = QPixmap(frame)
            paint_motion(frame)
            painter = QPainter(frame)
            painter.fillRect(QRect(25, 38, 15, 7), QColor("red"))
            painter.end()
            if paint_after_makeup is not None:
                paint_after_makeup(frame)
            return frame

    renderer = LayeredFullBodyRenderer(
        assets.LayeredFullBodyManifest(frozendict({VIEW: view})),
        outfit_overlay=LipstickOverlay(),
    )
    result = renderer.render_view(VIEW, _motion(Viseme.A, aperture)).toImage()
    assert result.pixelColor(32, 41) == before_makeup.pixelColor(32, 41)
    assert result.pixelColor(32, 39) == QColor("red")
    assert result.pixelColor(32, 43) == QColor("red")
    # Freeze the mask alongside the mouth, so later file edits cannot uncover teeth.
    _png(mask)
    renderer._pixmap_cache.clear()
    assert renderer.render_view(VIEW, _motion(Viseme.A, aperture)).toImage() == result


def test_oral_mask_visemes_must_match_speech_frames(tmp_path: Path) -> None:
    _, view = _renderer(tmp_path)
    mask = tmp_path / "oral.png"
    _png(mask, tooth="white")
    view = replace(view, speech_oral_masks=frozendict({Viseme.A: mask}))
    with pytest.raises(ValueError, match="oral masks must match"):
        LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))


@pytest.mark.parametrize("oral_mask", [False, True])
def test_transparent_speech_or_oral_mask_fails_before_rendering(tmp_path: Path, oral_mask: bool) -> None:
    _, view = _renderer(tmp_path)
    empty = tmp_path / "empty.png"
    _png(empty)
    frames = frozendict({viseme: empty for viseme in view.speech_frames})
    view = replace(view, **{"speech_oral_masks" if oral_mask else "speech_frames": frames})
    with pytest.raises(ValueError, match="nonempty"):
        LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))

