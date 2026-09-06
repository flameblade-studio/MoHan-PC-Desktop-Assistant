"""Authored eyelids preserve neutral rendering and reject incomplete assets."""
from __future__ import annotations

lazy import os
lazy import sys
lazy from dataclasses import replace
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy import pytest
lazy from PySide6.QtGui import QColor, QImage
lazy from PySide6.QtWidgets import QApplication
lazy from domain.constants import POSE_ATLAS_LAYERED_ROOT_NAME
lazy from domain.face_rig import EyeState, ExpressionShape, FaceMotionFrame, FacePose, MouthShape, Viseme
lazy from infrastructure import layered_full_body_assets as assets
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer

VIEW = "yaw+000-pitch+00"
CANVAS = (assets.FULL_BODY_DIMENSION_WIDTH, assets.FULL_BODY_DIMENSION_HEIGHT)
EYE_POINT = (500, 220)


def _png(path: Path, size: tuple[int, int] = CANVAS, color: str = "transparent") -> None:
    image = QImage(*size, QImage.Format_ARGB32)
    image.fill(QColor("transparent"))
    if size == CANVAS:
        image.setPixelColor(*EYE_POINT, QColor(color))
    assert image.save(str(path))


def _minimal_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(assets, "VIEW_IDS", (VIEW,))
    for layer in assets.REQUIRED_LAYERS:
        _png(tmp_path / f"{VIEW}_{layer}.png")


def test_optional_blink_pair_is_complete_and_same_canvas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _minimal_root(tmp_path, monkeypatch)
    assert not assets.load_layered_full_body_assets(tmp_path).view(VIEW).blink_frames
    half = tmp_path / f"{VIEW}_blink_half.png"
    closed = tmp_path / f"{VIEW}_blink_closed.png"
    _png(half)
    with pytest.raises(FileNotFoundError, match="incomplete full-body blink pair"):
        assets.load_layered_full_body_assets(tmp_path)
    _png(closed, (1, 1))
    with pytest.raises(ValueError, match="blink dimensions"):
        assets.load_layered_full_body_assets(tmp_path)
    closed.write_bytes(b"invalid PNG")
    with pytest.raises(ValueError, match="invalid full-body PNG"):
        assets.load_layered_full_body_assets(tmp_path)
    _png(closed)
    assert assets.load_layered_full_body_assets(tmp_path).view(VIEW).blink_frames == {
        EyeState.HALF: half, EyeState.CLOSED: closed,
    }


def test_authored_states_replace_legacy_motion_and_restore_neutral(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    manifest = assets.load_layered_full_body_assets(ROOT / "assets/pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME)
    paths = {}
    colors = {EyeState.HALF: QColor("red"), EyeState.CLOSED: QColor("blue")}
    for state, color in colors.items():
        path = tmp_path / f"{state.value}.png"
        _png(path, color=color.name())
        paths[state] = path
    view = replace(manifest.view(VIEW), blink_frames=frozendict(paths))
    renderer = LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))
    motion = FaceMotionFrame(FacePose.FRONT, "idle_front", Viseme.CLOSED, MouthShape(), ExpressionShape(), breath=0.5)
    neutral = renderer.render_view(VIEW, motion).toImage()
    assert neutral == LayeredFullBodyRenderer(manifest).render_view(VIEW, motion).toImage()
    for blink, state in ((0.5, EyeState.HALF), (1., EyeState.CLOSED)):
        result = renderer.render_view(VIEW, replace(motion, expression_shape=ExpressionShape(blink=blink))).toImage()
        assert result.pixelColor(*EYE_POINT) == colors[state]
        result.setPixelColor(*EYE_POINT, neutral.pixelColor(*EYE_POINT))
        assert result == neutral
    assert renderer.render_view(VIEW, motion).toImage() == neutral

    class Overlay:
        def __init__(self) -> None:
            self.suppressed = []
            self.states = []

        def apply(self, frame, view_id, *, suppress_makeup_slots=(), eye_state="rest"):
            self.suppressed.append(frozenset(suppress_makeup_slots))
            self.states.append(eye_state)
            return frame

    overlay = Overlay()
    dressed = LayeredFullBodyRenderer(renderer._manifest, outfit_overlay=overlay)
    for blink in (0., .5, 1., 0.):
        dressed.render_view(VIEW, replace(motion, expression_shape=ExpressionShape(blink=blink)))
    assert overlay.states == ["rest", "half", "closed", "rest"]
    assert overlay.suppressed == [frozenset(), frozenset({'eyes'}), frozenset({'eyes'}), frozenset()]


def main() -> None:
    result = pytest.main([__file__, "-q"])
    if result:
        raise SystemExit(result)
    print("FULL_BODY_AUTHORED_BLINK_OK")


if __name__ == "__main__":
    main()
