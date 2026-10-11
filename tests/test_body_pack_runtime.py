"""Exercise dependency routing with synthetic body-owned motion endpoints."""
from __future__ import annotations

lazy import io
lazy import hashlib
lazy import os
lazy import time
lazy from types import SimpleNamespace
lazy import pytest
lazy from PIL import Image
lazy from PySide6.QtGui import QColor, QPixmap
lazy from PySide6.QtWidgets import QApplication
lazy from domain.body_pack import BodyPackMismatchError
lazy from domain.character_layer_plan import CharacterLayerAsset
lazy from domain.face_rig import FacePose, Viseme
lazy from infrastructure.body_pack_renderer import (
    MAX_LAYER_BYTES_CACHE_BYTES,
    MAX_PIXMAP_CACHE_BYTES,
    BodyPackRenderer,
)
lazy from infrastructure.character_fullbody_factory import create_character_fullbody_renderer
lazy from application.character_default_look import CharacterDefaultLook
lazy from application.service_container import _create_presentation_ports


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

LARGE_FRAME_WIDTH = 1024
LARGE_FRAME_HEIGHT = 1536
EXPECTED_RETAINED_LAYERS = 2


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


def test_rest_only_view_keeps_speaking_and_blink_requests_on_rest(qapp):
    class RestOnlyBody(_Body):
        def frame_keys(self, view: str, *, halfbody: bool = False) -> tuple[str, ...]:
            return ("rest",)

    body = RestOnlyBody()
    renderer = BodyPackRenderer(body, {}, lambda record: b"")

    frame = renderer.render(QPixmap(), _motion(Viseme.A), None)
    blink = renderer.render_complete_blink(frame, "closed")
    full = renderer.render_view("back", _motion(Viseme.A))

    assert frame.toImage().pixelColor(0, 0).name() == "#ff0000"
    assert blink.toImage().pixelColor(0, 0).name() == "#ff0000"
    assert full.toImage().pixelColor(0, 0).name() == "#ff0000"
    assert body.calls == [("front", "rest", True), ("back", "rest", False)]


def test_composed_frame_cache_reuses_view_and_state(qapp):
    body = _Body()
    renderer = BodyPackRenderer(body, {}, lambda record: b"")

    first = renderer.render_view("back", _motion(Viseme.A))
    second = renderer.render_view("back", _motion(Viseme.A))

    assert first.toImage() == second.toImage()
    assert body.calls == [("back", "a-rest", False)]


def test_1024_by_1536_repeated_frame_uses_composition_cache(qapp):
    class LargeBody(_Body):
        def __init__(self, frame: bytes) -> None:
            super().__init__()
            self.frame = frame

        def load_frame(self, view: str, key: str, *, halfbody: bool = False) -> bytes:
            self.calls.append((view, key, halfbody))
            return self.frame

    output = io.BytesIO()
    Image.new("RGBA", (LARGE_FRAME_WIDTH, LARGE_FRAME_HEIGHT), "red").save(output, format="PNG")
    body = LargeBody(output.getvalue())
    renderer = BodyPackRenderer(body, {}, lambda record: b"")

    started = time.perf_counter()
    first = renderer.render_view("back", _motion(Viseme.A))
    first_seconds = time.perf_counter() - started
    started = time.perf_counter()
    repeated = renderer.render_view("back", _motion(Viseme.A))
    repeated_seconds = time.perf_counter() - started

    assert first.size().width() == LARGE_FRAME_WIDTH
    assert first.size().height() == LARGE_FRAME_HEIGHT
    assert repeated.toImage() == first.toImage()
    assert repeated_seconds < first_seconds * 0.5
    assert body.calls == [("back", "a-rest", False)]


def test_renderer_pixmap_and_layer_byte_caches_obey_separate_budgets(qapp):
    renderer = BodyPackRenderer(_Body(), {}, lambda record: b"")
    pixmap = QPixmap(LARGE_FRAME_WIDTH, LARGE_FRAME_HEIGHT)
    pixmap.fill(QColor("green"))
    for index in range(6):
        renderer._cache_pixmap(("budget", index), pixmap)

    payloads = [bytes([index]) * 2_900_000 for index in range(3)]
    records = tuple(
        CharacterLayerAsset(
            "garment", f"layer-{index}.png", hashlib.sha256(data).hexdigest(), (0, 0),
        )
        for index, data in enumerate(payloads)
    )
    by_digest = {record.sha256: data for record, data in zip(records, payloads, strict=True)}
    renderer._load_layer = lambda record: by_digest[record.sha256]
    for record in records:
        renderer._layer_data(record)

    assert renderer._pixmap_cache_bytes <= MAX_PIXMAP_CACHE_BYTES
    assert renderer._layer_bytes_cache_bytes <= MAX_LAYER_BYTES_CACHE_BYTES
    assert renderer._pixmap_cache_bytes > 0
    assert renderer._layer_bytes_cache_bytes > 0
    assert len(renderer._layer_bytes) == EXPECTED_RETAINED_LAYERS


def test_fullbody_render_does_not_replace_halfbody_wink_context(qapp):
    body = _Body()
    renderer = BodyPackRenderer(body, {}, lambda record: b"")

    half = renderer.render(QPixmap(), _motion(), None)
    renderer.render_view("back", _motion())
    blink = renderer.render_complete_blink(half, "closed")

    assert blink.toImage().pixelColor(0, 0).name() == "#0000ff"
    assert body.calls == [
        ("front", "neutral-rest", True),
        ("back", "rest", False),
        ("front", "neutral-closed", True),
    ]


def test_last_context_applies_to_copied_and_scaled_frame(qapp):
    body = _Body()
    renderer = BodyPackRenderer(body, {}, lambda record: b"")
    rendered = renderer.render(QPixmap(), _motion(), None)
    copied = QPixmap(rendered)
    scaled = rendered.scaled(8, 8)

    copied_blink = renderer.render_complete_blink(copied, "closed")
    scaled_blink = renderer.render_complete_blink(scaled, "closed")

    assert copied_blink.size() == copied.size()
    assert scaled_blink.size() == scaled.size()
    assert body.calls == [
        ("front", "neutral-rest", True),
        ("front", "neutral-closed", True),
    ]


def test_wink_is_rejected_by_body_pack_renderer(qapp):
    renderer = BodyPackRenderer(_Body(), {}, lambda record: b"")

    assert renderer.supports_wink is False
    with pytest.raises(BodyPackMismatchError, match="unsupported_wink"):
        renderer.render_overlay(QPixmap(), QPixmap(), eye_state="wink")


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
    face_renderer = ports.face_renderer_factory()
    fullbody_renderer = ports.full_body_renderer_factory()
    assert isinstance(face_renderer, BodyPackRenderer)
    assert face_renderer is fullbody_renderer
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
