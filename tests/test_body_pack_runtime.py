"""Exercise dependency routing with synthetic body-owned motion endpoints."""
from __future__ import annotations

lazy import io
lazy import os
lazy from types import SimpleNamespace
lazy import pytest
lazy from PIL import Image
lazy from PySide6.QtGui import QPixmap
lazy from PySide6.QtWidgets import QApplication
lazy from domain.body_pack import BodyPackMismatchError
lazy from domain.face_rig import FacePose, Viseme
lazy from infrastructure.body_pack_renderer import BodyPackRenderer
lazy from infrastructure.character_fullbody_factory import create_character_fullbody_renderer
lazy from application.character_default_look import CharacterDefaultLook
lazy from application.service_container import _create_presentation_ports


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _png(color: str) -> bytes:
    output = io.BytesIO()
    Image.new("RGBA", (4, 4), color).save(output, format="PNG")
    return output.getvalue()


class _Body:
    manifest = SimpleNamespace(half_body=(SimpleNamespace(view_id="front"),))

    def __init__(self) -> None:
        self.calls = []

    def frame_keys(self, view: str, *, halfbody: bool = False) -> tuple[str, ...]:
        return ("rest", "half", "closed", "a-rest")

    def load_frame(self, view: str, key: str, *, halfbody: bool = False) -> bytes:
        self.calls.append((view, key, halfbody))
        colors = {"rest": "red", "half": "green", "closed": "blue", "a-rest": "yellow",
                  "neutral-rest": "red", "neutral-closed": "blue"}
        if key not in colors:
            raise BodyPackMismatchError("missing_frame", "Synthetic body endpoint is missing")
        return _png(colors[key])

    def load_face_core(self, view: str) -> None:
        return None


def _motion(viseme=Viseme.CLOSED, blink=0.0):
    return SimpleNamespace(pose=FacePose.FRONT, expression="neutral", viseme=viseme,
                           mouth=SimpleNamespace(aperture=0.2),
                           expression_shape=SimpleNamespace(blink=blink))


def test_body_motion_and_halfbody_blink_use_owned_frames(qapp):
    body = _Body()
    renderer = BodyPackRenderer(body, {}, lambda record: b"")
    full = renderer.render_view("back", _motion(Viseme.A))
    assert full.toImage().pixelColor(0, 0).name() == "#ffff00"
    half = renderer.render(QPixmap(), _motion(), None)
    blink = renderer.render_complete_blink(half, "closed")
    assert blink.toImage().pixelColor(0, 0).name() == "#0000ff"
    assert body.calls == [("back", "a-rest", False), ("front", "neutral-rest", True),
                          ("front", "neutral-closed", True)]


def test_missing_motion_endpoint_raises_without_shared_fallback(qapp):
    renderer = BodyPackRenderer(_Body(), {}, lambda record: b"")
    with pytest.raises(BodyPackMismatchError, match="missing_frame"):
        renderer.render_view("back", _motion(Viseme.A, blink=1.0))


def test_declared_body_routes_both_factories_before_legacy_assets(tmp_path):
    body = _Body()
    assets = SimpleNamespace(asset_root=tmp_path, load_character_layer=lambda record: b"")
    appearance = SimpleNamespace(resolved_body_pack=body, character_layer_views={},
                                 runtime_bindings=SimpleNamespace(asset_paths={}))
    source = SimpleNamespace(assets=assets, appearance=appearance)
    ports = _create_presentation_ports(source)
    assert isinstance(ports.face_renderer_factory(), BodyPackRenderer)
    assert isinstance(ports.full_body_renderer_factory(), BodyPackRenderer)
    assert ports.outfit_overlay_factory() is None
    with pytest.raises(BodyPackMismatchError, match="body_pack_renderer_required"):
        CharacterDefaultLook(source, tmp_path, ())


def test_unresolved_declared_dependency_rejects_before_factory_creation(tmp_path):
    source = SimpleNamespace(
        assets=SimpleNamespace(asset_root=tmp_path),
        appearance=SimpleNamespace(runtime_bindings=SimpleNamespace(asset_paths={})),
        manifest=SimpleNamespace(body_pack=SimpleNamespace(id="absent")),
    )
    with pytest.raises(BodyPackMismatchError, match="body_pack_missing"):
        _create_presentation_ports(source)


def test_undeclared_structural_source_keeps_legacy_fullbody_route(tmp_path):
    source = SimpleNamespace(assets=SimpleNamespace(resolve_path=lambda relative: tmp_path / relative))
    captured = {}

    def renderer(**kwargs):
        captured.update(kwargs)
        return "legacy"

    result = create_character_fullbody_renderer(
        source, {}, "outfit", None, renderer_factory=renderer,
        manifest_loader=lambda path: pytest.fail("Structural source must keep its existing lazy manifest"),
        placement_loader=lambda path: path,
    )
    assert result == "legacy"
    assert captured["outfit_overlay"] == "outfit"
    assert "native_frames_root" not in captured


def test_unknown_halfbody_blink_endpoint_raises_before_legacy_patch(qapp):
    renderer = BodyPackRenderer(_Body(), {}, lambda record: b"")
    with pytest.raises(BodyPackMismatchError, match="missing_frame_context"):
        renderer.render_complete_blink(QPixmap(), "closed")
