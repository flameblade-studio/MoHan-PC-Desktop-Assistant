"""Installed outfit and makeup eye-state round-trip through the public runtime path."""

from __future__ import annotations

lazy import copy
lazy import hashlib
lazy import json
lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy import pytest
lazy from PySide6.QtCore import QBuffer, QByteArray, QIODevice
lazy from PySide6.QtGui import QColor, QImage, QPixmap

lazy from application.outfit_pack_builder import build_outfit_pack
lazy from domain import outfit_pack, outfit_pack_makeup
lazy from domain.outfit_pack import (
    apply_appearance_selection,
    install_outfit_pack,
    inspect_outfit_pack,
    list_installed_selections,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from test_active_outfit_overlay_makeup import _app, _authority
lazy from test_makeup_blink_states import _state_pack
lazy from test_outfit_pack import _manifest, _png

VIEW = "front-crossed"
CANVAS = (1254, 1254)
GARMENT_SIZE = (96, 96)
GARMENT_ANCHOR = (20, 500)
GARMENT_POINT = (40, 520)
GARMENT_REGION = (*GARMENT_ANCHOR, *GARMENT_SIZE)
EYE_POINT = (610, 250)
REST_COLOR = QColor(30, 180, 80, 255)
HALF_COLOR = QColor("red")
CLOSED_COLOR = QColor("blue")
GARMENT_COLOR = QColor(20, 80, 180, 255)


def _encode_png(image: QImage) -> bytes:
    payload = QByteArray()
    buffer = QBuffer(payload)
    assert buffer.open(QIODevice.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(payload)


def _layer_png(
    size: tuple[int, int],
    blocks: tuple[tuple[int, int, int, int, QColor], ...] = (),
) -> bytes:
    image = QImage(size[0], size[1], QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))
    for x, y, width, height, color in blocks:
        for row in range(y, y + height):
            for column in range(x, x + width):
                image.setPixelColor(column, row, color)
    return _encode_png(image)


def _garment_png() -> bytes:
    image = QImage(GARMENT_SIZE[0], GARMENT_SIZE[1], QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))
    for row in range(8, 88):
        for column in range(8, 88):
            image.setPixelColor(column, row, GARMENT_COLOR)
    return _encode_png(image)


def _replace_asset(entry: dict, path: str, data: bytes, size: tuple[int, int], anchor: tuple[int, int]) -> None:
    entry.update(
        path=path,
        sha256=hashlib.sha256(data).hexdigest(),
        width=size[0],
        height=size[1],
        anchor=list(anchor),
    )


def _strip_sealed_fields(value: object) -> None:
    if isinstance(value, dict):
        if "path" in value and "slot" in value:
            for field in ("sha256", "width", "height"):
                value.pop(field, None)
        for child in value.values():
            _strip_sealed_fields(child)
    elif isinstance(value, list):
        for child in value:
            _strip_sealed_fields(child)


def _referenced_paths(value: object) -> set[str]:
    paths: set[str] = set()
    if isinstance(value, dict):
        path = value.get("path")
        if isinstance(path, str) and "slot" in value:
            paths.add(path)
        for child in value.values():
            paths.update(_referenced_paths(child))
    elif isinstance(value, list):
        for child in value:
            paths.update(_referenced_paths(child))
    return paths


def _roundtrip_authoring() -> tuple[dict, dict[str, bytes]]:
    manifest, assets = _manifest(_png())
    state_manifest, state_assets = _state_pack()
    manifest = copy.deepcopy(manifest)
    manifest["id"] = "installed-roundtrip"
    for key in ("hairstyles", "headwear", "accessories", "ensembles"):
        manifest[key] = []
    manifest["makeup"] = copy.deepcopy(state_manifest["makeup"])
    assets = {**assets, **state_assets}

    garment = next(
        asset
        for asset in manifest["looks"][0]["variants"][0]["poses"][VIEW]
        if asset["slot"] == "outerwear"
    )
    old_garment_path = garment["path"]
    garment_data = _garment_png()
    garment_path = "assets/roundtrip-garment-front-crossed.png"
    assets.pop(old_garment_path)
    assets[garment_path] = garment_data
    _replace_asset(garment, garment_path, garment_data, GARMENT_SIZE, GARMENT_ANCHOR)

    makeup_variant = manifest["makeup"][0]["variants"][0]
    eyes = next(asset for asset in makeup_variant["poses"][VIEW] if asset["slot"] == "eyes")
    old_rest_path = eyes["path"]
    rest_data = _layer_png(
        CANVAS,
        ((600, 250, 11, 1, REST_COLOR),),
    )
    rest_path = "assets/roundtrip-rest-front-crossed-eyes.png"
    assets.pop(old_rest_path)
    assets[rest_path] = rest_data
    _replace_asset(eyes, rest_path, rest_data, CANVAS, (0, 0))

    paths = _referenced_paths(manifest)
    assets = {path: data for path, data in assets.items() if path in paths}
    _strip_sealed_fields(manifest)
    return manifest, assets


def _write_authoring(root: Path, manifest: dict, assets: dict[str, bytes]) -> Path:
    source = root / "authoring" / "manifest.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    for name, data in assets.items():
        target = source.parent / Path(*name.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return source


def _frame() -> QPixmap:
    frame = QPixmap(*CANVAS)
    frame.fill(QColor(240, 240, 240, 255))
    return frame


def test_installed_outfit_blink_roundtrip_preserves_garment_and_coordinates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Install one pack and preserve its garment while eye states swap and reopen."""
    _app()
    _authority(tmp_path)
    monkeypatch.setattr(outfit_pack, "OFFICIAL_PACK_ROOT", tmp_path / "official")
    monkeypatch.setattr(outfit_pack_makeup, "SAFE_REGION_PATH", tmp_path / "assets" / "makeup-safe-regions.json")

    manifest, assets = _roundtrip_authoring()
    source = _write_authoring(tmp_path, manifest, assets)
    archive = build_outfit_pack(source, source.parent, tmp_path / "roundtrip.mohan-outfit")
    store = tmp_path / "store"
    installed = install_outfit_pack(archive, store)
    assert installed.pack_id == "installed-roundtrip"
    installed_archive = store / "packages" / f"{installed.pack_id}.mohan-outfit"
    archive_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert hashlib.sha256(installed_archive.read_bytes()).hexdigest() == archive_digest

    garment_selection = next(item for item in list_installed_selections(store, "garment"))
    makeup_selection = next(item for item in list_installed_selections(store, "makeup"))
    assert garment_selection.pack_id == makeup_selection.pack_id == installed.pack_id
    apply_appearance_selection(store, garment_selection)
    apply_appearance_selection(store, makeup_selection)

    parsed = inspect_outfit_pack(archive)
    garment_item = next(item for item in parsed.items if item.category == "garment")
    makeup_item = next(item for item in parsed.items if item.category == "makeup")
    garment_asset = next(
        asset for asset in garment_item.variants[0].poses[VIEW] if asset.slot == "outerwear"
    )
    makeup_variant = makeup_item.variants[0]
    assert (garment_asset.width, garment_asset.height) == GARMENT_SIZE
    assert (garment_asset.anchor_x, garment_asset.anchor_y) == GARMENT_ANCHOR
    for state in ("half", "closed"):
        state_asset = makeup_variant.eye_states[state][VIEW][0]
        assert state_asset.slot == "eyes"
        assert (state_asset.width, state_asset.height, state_asset.anchor_x, state_asset.anchor_y) == (*CANVAS, 0, 0)

    overlay = ActiveOutfitOverlay(store, tmp_path)
    rendered = {
        "rest": overlay.apply(_frame(), VIEW).toImage(),
        "half": overlay.apply(_frame(), VIEW, suppress_makeup_slots={"eyes"}, eye_state="half").toImage(),
        "closed": overlay.apply(_frame(), VIEW, suppress_makeup_slots={"eyes"}, eye_state="closed").toImage(),
        "reopened": overlay.apply(_frame(), VIEW).toImage(),
    }
    garment_region = rendered["rest"].copy(*GARMENT_REGION)
    for state in ("half", "closed", "reopened"):
        assert rendered[state].size().toTuple() == CANVAS
        assert rendered[state].copy(*GARMENT_REGION) == garment_region
    assert rendered["rest"].pixelColor(*GARMENT_POINT) == GARMENT_COLOR
    assert rendered["half"].pixelColor(*EYE_POINT) == HALF_COLOR
    assert rendered["closed"].pixelColor(*EYE_POINT) == CLOSED_COLOR
    assert rendered["reopened"].pixelColor(*EYE_POINT) == REST_COLOR
    assert rendered["reopened"].pixelColor(*EYE_POINT) == rendered["rest"].pixelColor(*EYE_POINT)
    assert rendered["reopened"] == rendered["rest"]
    assert hashlib.sha256(installed_archive.read_bytes()).hexdigest() == archive_digest


def main() -> int:
    result = pytest.main([__file__, "-q", *sys.argv[1:]])
    if result == 0:
        print("INSTALLED_OUTFIT_BLINK_ROUNDTRIP_OK")
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
