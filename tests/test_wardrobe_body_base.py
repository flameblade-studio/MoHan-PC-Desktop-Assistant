"""Cover the bare body base and mandatory authored hair composition."""
from __future__ import annotations

lazy import hashlib
lazy import io
lazy import json
lazy import os
lazy from pathlib import Path
lazy import pytest
lazy from PIL import Image, ImageColor
lazy from PySide6.QtGui import QColor, QPixmap
lazy from PySide6.QtWidgets import QApplication
lazy from application import wardrobe_service as wardrobe_service_module
lazy from application.wardrobe_service import BODY_OUTFIT_ID, BUILTIN_OUTFIT_ID, WardrobeService
lazy from domain.body_pack import BodyPackMismatchError
lazy from domain.character_layer_plan import (
    BODY_FIX_LAYER_KINDS,
    CLOTHING_LAYER_KINDS,
    DEFAULT_CHARACTER_LAYER_ORDER,
    HAIR_LAYER_KINDS,
    CharacterLayerAsset,
    CharacterLayerMask,
    CharacterLayerPlan,
)
lazy from domain.face_rig import FacePose, Viseme
lazy from domain.outfit_pack import OutfitPackError
lazy from infrastructure.body_pack_renderer import BodyPackRenderer


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

LAYER_SIZE = (4, 4)
EXPECTED_COMPOSED_CACHE_ENTRIES = 2


def _asset(kind: str) -> CharacterLayerAsset:
    data = kind.encode("utf-8")
    return CharacterLayerAsset(
        kind, f"{kind}.png", hashlib.sha256(data).hexdigest(), (0, 0),
    )


def test_layer_kind_sets_separate_hair_clothing_and_body_repairs() -> None:
    assert frozenset({"hair-back", "hair-front", "ornament"}) == HAIR_LAYER_KINDS
    assert frozenset({"garment", "look-fix"}) == CLOTHING_LAYER_KINDS
    assert frozenset({"body-fix"}) == BODY_FIX_LAYER_KINDS


def test_without_clothing_keeps_only_base_and_hair_and_drops_shared_mask() -> None:
    kinds = (
        "hair-back", "body-fix", "makeup", "garment", "look-fix", "hair-front", "ornament",
    )
    layers = tuple(_asset(kind) for kind in kinds)
    base_hide = CharacterLayerMask("garment-mask.png", "f" * 64, (0, 0))
    plan = CharacterLayerPlan(DEFAULT_CHARACTER_LAYER_ORDER, layers, base_hide)

    bare = plan.without_clothing()

    assert bare.order == tuple(
        kind for kind in plan.order if kind == "base" or kind in HAIR_LAYER_KINDS
    )
    assert bare.order == ("hair-back", "base", "hair-front", "ornament")
    assert bare.layers == tuple(layer for layer in layers if layer.kind in HAIR_LAYER_KINDS)
    assert tuple(layer.kind for layer in bare.layers) == (
        "hair-back", "hair-front", "ornament",
    )
    assert bare.base_hide is None
    assert plan.layers == layers
    assert plan.base_hide is base_hide


def _png(size: tuple[int, int], color: str | tuple[int, int, int, int]) -> bytes:
    output = io.BytesIO()
    Image.new("RGBA", size, color).save(output, format="PNG")
    return output.getvalue()


def _face_core_pixel(point: tuple[int, int] = (0, 0)) -> bytes:
    output = io.BytesIO()
    image = Image.new("RGBA", LAYER_SIZE, (0, 0, 0, 0))
    image.putpixel(point, (0, 0, 0, 255))
    image.save(output, format="PNG")
    return output.getvalue()


def _sparse_layer(
    kind: str, color: str, size: tuple[int, int] = LAYER_SIZE,
    point: tuple[int, int] = (3, 3),
) -> tuple[CharacterLayerAsset, bytes]:
    output = io.BytesIO()
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    image.putpixel(point, ImageColor.getcolor(color, "RGBA"))
    image.save(output, format="PNG")
    data = output.getvalue()
    record = CharacterLayerAsset(
        kind, f"{kind}.png", hashlib.sha256(data).hexdigest(), (0, 0),
    )
    return record, data


def _hide_mask(
    size: tuple[int, int], point: tuple[int, int],
) -> tuple[CharacterLayerMask, bytes]:
    output = io.BytesIO()
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    image.putpixel(point, (255, 255, 255, 255))
    image.save(output, format="PNG")
    data = output.getvalue()
    return CharacterLayerMask(
        "base-hide.png", hashlib.sha256(data).hexdigest(), (0, 0),
    ), data


def _hair_plan(
    *, missing: frozenset[str] = frozenset(),
    garment: bool = False,
    body_fix: bool = False,
    makeup: bool = False,
) -> tuple[CharacterLayerPlan, dict[str, bytes]]:
    layers: list[CharacterLayerAsset] = []
    assets: dict[str, bytes] = {}
    for kind, color in (("hair-back", "blue"), ("hair-front", "yellow")):
        if kind not in missing:
            record, payload = _sparse_layer(kind, color)
            layers.append(record)
            assets[record.sha256] = payload
    if body_fix:
        record, payload = _sparse_layer("body-fix", "cyan", point=(1, 1))
        layers.append(record)
        assets[record.sha256] = payload
    if makeup:
        record, payload = _sparse_layer("makeup", "green", point=(0, 0))
        layers.append(record)
        assets[record.sha256] = payload
    if garment:
        record, payload = _sparse_layer("garment", "magenta", point=(2, 2))
        layers.append(record)
        assets[record.sha256] = payload
    return CharacterLayerPlan(DEFAULT_CHARACTER_LAYER_ORDER, tuple(layers)), assets


class _Body:
    manifest = type("Manifest", (), {
        "half_body": (type("View", (), {"view_id": "front"})(),),
    })()

    def __init__(
        self, face_core: bytes | None = None, hole: tuple[int, int] | None = None,
    ) -> None:
        self.calls: list[tuple[str, str, bool]] = []
        self.face_core = face_core
        self.frame_size = LAYER_SIZE
        self.hole = hole

    def frame_keys(self, view: str, *, halfbody: bool = False) -> tuple[str, ...]:
        return ("rest", "closed", "neutral-rest", "neutral-closed")

    def load_frame(self, view: str, key: str, *, halfbody: bool = False) -> bytes:
        self.calls.append((view, key, halfbody))
        if self.hole is None:
            return _png(self.frame_size, "red")
        # Back hair sits behind the body, so it is visible only where the body is transparent.
        output = io.BytesIO()
        image = Image.new("RGBA", self.frame_size, "red")
        image.putpixel(self.hole, (0, 0, 0, 0))
        image.save(output, format="PNG")
        return output.getvalue()

    def load_face_core(self, view: str) -> bytes:
        if self.face_core is not None:
            return self.face_core
        return _png(self.frame_size, (0, 0, 0, 0))


def _motion() -> object:
    return type("Motion", (), {
        "pose": FacePose.FRONT,
        "expression": "neutral",
        "viseme": Viseme.CLOSED,
        "mouth": type("Mouth", (), {"aperture": 0.0})(),
        "expression_shape": type("Shape", (), {"blink": 0.0})(),
    })()


def _renderer(
    body: _Body,
    views: dict[str, CharacterLayerPlan],
    assets: dict[str, bytes] | None = None,
    *,
    apply_makeup=None,
    clothing_visible=None,
) -> BodyPackRenderer:
    payloads = {} if assets is None else assets
    return BodyPackRenderer(
        body, views, lambda record: payloads[record.sha256],
        apply_makeup=apply_makeup, clothing_visible=clothing_visible,
    )


def test_clothing_toggle_recomposes_cached_frame_and_restores_base_under_shared_mask() -> None:
    app = QApplication.instance() or QApplication([])
    body = _Body(_face_core_pixel())
    mask, mask_bytes = _hide_mask(LAYER_SIZE, (2, 2))
    plan, assets = _hair_plan(garment=True, body_fix=True, makeup=True)
    plan = CharacterLayerPlan(plan.order, plan.layers, mask)
    assets[mask.sha256] = mask_bytes
    visible = {"value": True}
    makeup_calls: list[str] = []

    def fail_if_bare(base, view, _eye, _viseme):
        if not visible["value"]:
            raise AssertionError("Bare body composition must skip the makeup callback.")
        makeup_calls.append(view)
        return base

    renderer = _renderer(
        body, {"front": plan}, assets,
        apply_makeup=fail_if_bare,
        clothing_visible=lambda: visible["value"],
    )

    dressed = renderer.render_view("front", _motion()).toImage()
    assert makeup_calls == ["front"]
    visible["value"] = False
    bare = renderer.render_view("front", _motion()).toImage()
    assert makeup_calls == ["front"]
    visible["value"] = True
    dressed_again = renderer.render_view("front", _motion()).toImage()

    assert dressed.pixelColor(0, 0) == QColor("green")
    assert dressed.pixelColor(1, 1) == QColor("cyan")
    assert dressed.pixelColor(2, 2) == QColor("magenta")
    assert bare.pixelColor(0, 0) == QColor("red")
    assert bare.pixelColor(1, 1) == QColor("red")
    assert bare.pixelColor(2, 2) == QColor("red")
    assert dressed_again == dressed
    assert dressed.pixelColor(3, 3) == bare.pixelColor(3, 3)
    composed = [key for key in renderer._pixmaps if key[0] == "composed"]
    assert {key[4] for key in composed} == {False, True}
    assert len(composed) == EXPECTED_COMPOSED_CACHE_ENTRIES
    assert body.calls == [("front", "rest", False)]
    assert app is not None


@pytest.mark.parametrize("endpoint", ["full", "half", "blink"])
def test_full_half_and_blink_reject_a_missing_plan(endpoint) -> None:
    app = QApplication.instance() or QApplication([])
    body = _Body()
    renderer = _renderer(body, {})

    with pytest.raises(BodyPackMismatchError, match="character_hair_required"):
        if endpoint == "full":
            renderer.render_view("front", _motion())
        elif endpoint == "half":
            renderer.render(QPixmap(), _motion(), None)
        else:
            renderer._remember("front", "neutral", "neutral")
            renderer.render_complete_blink(QPixmap(4, 4), "closed")

    assert body.calls == []
    assert app is not None


@pytest.mark.parametrize("endpoint", ["full", "half", "blink"])
@pytest.mark.parametrize(("hair_kind", "color"), [("hair-back", "blue"), ("hair-front", "yellow")])
def test_each_default_hair_layer_can_support_a_view(endpoint, hair_kind, color) -> None:
    app = QApplication.instance() or QApplication([])
    body = _Body(hole=(3, 3))
    other = "hair-front" if hair_kind == "hair-back" else "hair-back"
    plan, assets = _hair_plan(missing=frozenset({other}))
    renderer = _renderer(body, {"front": plan}, assets)

    if endpoint == "full":
        result = renderer.render_view("front", _motion())
    elif endpoint == "half":
        result = renderer.render(QPixmap(), _motion(), None)
    else:
        renderer._remember("front", "neutral", "neutral")
        result = renderer.render_complete_blink(QPixmap(4, 4), "closed")

    assert result.toImage().pixelColor(3, 3) == QColor(color)
    assert app is not None


@pytest.mark.parametrize("endpoint", ["full", "half", "blink"])
def test_ornament_only_plan_does_not_count_as_default_hair(endpoint) -> None:
    app = QApplication.instance() or QApplication([])
    body = _Body()
    ornament, payload = _sparse_layer("ornament", "yellow")
    plan = CharacterLayerPlan(DEFAULT_CHARACTER_LAYER_ORDER, (ornament,))
    renderer = _renderer(body, {"front": plan}, {ornament.sha256: payload})

    with pytest.raises(BodyPackMismatchError, match="character_hair_required"):
        if endpoint == "full":
            renderer.render_view("front", _motion())
        elif endpoint == "half":
            renderer.render(QPixmap(), _motion(), None)
        else:
            renderer._remember("front", "neutral", "neutral")
            renderer.render_complete_blink(QPixmap(4, 4), "closed")

    assert body.calls == []
    assert app is not None


def test_invalid_hair_image_fails_closed_without_a_body_only_frame() -> None:
    app = QApplication.instance() or QApplication([])
    body = _Body()
    plan, assets = _hair_plan()
    broken = b"declared hair image cannot be decoded"
    bad_record = CharacterLayerAsset(
        "hair-back", "broken-hair.png", hashlib.sha256(broken).hexdigest(), (0, 0),
    )
    plan = CharacterLayerPlan(plan.order, (bad_record, plan.layers[1]))
    assets[bad_record.sha256] = broken
    renderer = _renderer(body, {"front": plan}, assets)

    with pytest.raises(BodyPackMismatchError, match="invalid_image"):
        renderer.render_view("front", _motion())

    assert not any(key[0] == "composed" for key in renderer._pixmaps)
    assert app is not None


def _empty_service(monkeypatch, tmp_path: Path, *, has_body: bool) -> WardrobeService:
    service = WardrobeService(tmp_path / "store")
    monkeypatch.setattr(service, "_has_body_pack", lambda: has_body)
    monkeypatch.setattr(wardrobe_service_module, "list_installed_ensembles", lambda *a, **k: ())
    monkeypatch.setattr(wardrobe_service_module, "official_outfit_ensemble", lambda _items: None)
    monkeypatch.setattr(wardrobe_service_module, "list_installed_selections", lambda *a, **k: ())
    monkeypatch.setattr(wardrobe_service_module, "list_stale_body_profile_packs", lambda *a, **k: ())
    monkeypatch.setattr(wardrobe_service_module, "_builtin_outfit_fallback_name", lambda _language: "Built in")
    return service


def _write_active(store: Path, state: dict[str, object]) -> None:
    active = store / "active.json"
    active.parent.mkdir(parents=True, exist_ok=True)
    active.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def test_body_outfit_is_listed_only_when_body_pack_is_available(monkeypatch, tmp_path: Path) -> None:
    with_body = _empty_service(monkeypatch, tmp_path / "with-body", has_body=True)
    without_body = _empty_service(monkeypatch, tmp_path / "without-body", has_body=False)

    assert BODY_OUTFIT_ID == "body"
    assert BODY_OUTFIT_ID in {outfit.outfit_id for outfit in with_body.outfits()}
    assert tuple(outfit.outfit_id for outfit in without_body.outfits()) == (BUILTIN_OUTFIT_ID,)


def test_applying_body_outfit_clears_only_garment_selection(monkeypatch, tmp_path: Path) -> None:
    service = _empty_service(monkeypatch, tmp_path, has_body=True)
    original = {
        "garment": {"pack_id": "robe-pack", "item_id": "robe", "variant_id": "blue"},
        "makeup": {"pack_id": "builtin", "item_id": "mohan-signature", "variant_id": "classic"},
        "hairstyle": {"pack_id": "silk-pack", "item_id": "long-hair", "variant_id": "ink"},
        "headwear": {"pack_id": "silver-pack", "item_id": "hairpin", "variant_id": "moon"},
    }
    _write_active(service.install_root, original)

    selected = service.apply(BODY_OUTFIT_ID)

    current = json.loads((service.install_root / "active.json").read_text(encoding="utf-8"))
    assert selected.outfit_id == BODY_OUTFIT_ID
    assert current["garment"] == {"pack_id": "builtin", "item_id": "none", "variant_id": "none"}
    assert current["makeup"] == original["makeup"]
    assert current["hairstyle"] == original["hairstyle"]
    assert current["headwear"] == original["headwear"]


def test_body_outfit_cannot_be_applied_when_body_pack_is_missing(monkeypatch, tmp_path: Path) -> None:
    service = _empty_service(monkeypatch, tmp_path, has_body=False)
    original = {"garment": {"pack_id": "robe-pack", "item_id": "robe", "variant_id": "blue"}}
    _write_active(service.install_root, original)
    before = (service.install_root / "active.json").read_bytes()

    with pytest.raises(OutfitPackError, match="not installed"):
        service.apply(BODY_OUTFIT_ID)

    assert (service.install_root / "active.json").read_bytes() == before
