"""Importer checks for runtime appearance alpha, visibility and canvas bounds."""

lazy import hashlib
lazy import json
lazy import sys
lazy import zipfile
lazy from pathlib import Path

lazy import pytest
lazy from PySide6.QtCore import QBuffer, QByteArray, QIODevice
lazy from PySide6.QtGui import QColor, QImage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.outfit_pack_builder import build_outfit_pack
lazy from domain.outfit_pack import OutfitPackError, inspect_outfit_pack
lazy from test_outfit_pack import _manifest, _pack, _png

RGBA = QImage.Format_RGBA8888
RGB = QImage.Format_RGB888


def _encoded(width: int, height: int, image_format: QImage.Format, color: QColor) -> bytes:
    image = QImage(width, height, image_format)
    image.fill(color)
    payload = QByteArray()
    buffer = QBuffer(payload)
    assert buffer.open(QIODevice.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(payload)


def _target(manifest: dict, group: str, view_id: str) -> dict:
    return manifest[group][0]["variants"][0]["poses"][view_id][0]


def _corrupt_idat(data: bytes) -> bytes:
    corrupted = bytearray(data)
    offset = 8
    while offset + 12 <= len(corrupted):
        size = int.from_bytes(corrupted[offset : offset + 4], "big")
        kind = bytes(corrupted[offset + 4 : offset + 8])
        if kind == b"IDAT" and size:
            corrupted[offset + 8] ^= 0xFF
            return bytes(corrupted)
        offset += 12 + size
    raise AssertionError("test PNG fixture must contain IDAT data")


def _archive(
    root: Path,
    name: str,
    data: bytes,
    *,
    group: str = "looks",
    view_id: str = "yaw+000-pitch+00",
    anchor: tuple[int, int] = (0, 0),
    declared_size: tuple[int, int] | None = None,
) -> Path:
    manifest, assets = _manifest(_png())
    target = _target(manifest, group, view_id)
    old_path = target["path"]
    new_path = f"assets/{name}.png"
    image = QImage.fromData(data, "PNG")
    target.update({
        "path": new_path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "width": image.width() if declared_size is None else declared_size[0],
        "height": image.height() if declared_size is None else declared_size[1],
        "anchor": list(anchor),
    })
    assets.pop(old_path)
    assets[new_path] = data
    return _pack(root / f"{name}.mohan-outfit", manifest, assets)


def _authoring_copy(root: Path, archive: Path) -> tuple[Path, Path]:
    with zipfile.ZipFile(archive) as source:
        manifest = json.loads(source.read("manifest.json"))
        assets = {
            name: source.read(name)
            for name in source.namelist()
            if name != "manifest.json"
        }
    for item in manifest["looks"] + manifest["hairstyles"] + manifest["headwear"]:
        for variant in item["variants"]:
            for entries in variant["poses"].values():
                for entry in entries:
                    entry.pop("sha256", None)
                    entry.pop("width", None)
                    entry.pop("height", None)
    root.mkdir(parents=True, exist_ok=True)
    authoring = root / "authoring.json"
    authoring.write_text(json.dumps(manifest), encoding="utf-8")
    asset_root = root / "authoring-assets"
    for name, data in assets.items():
        path = asset_root / Path(*name.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return authoring, asset_root


def test_importer_rejects_rgb_outerwear_without_alpha(tmp_path: Path) -> None:
    data = _encoded(4, 5, RGB, QColor(30, 70, 150))
    archive = _archive(tmp_path, "rgb-outerwear", data)
    with pytest.raises(OutfitPackError, match="alpha channel"):
        inspect_outfit_pack(archive)


def test_importer_rejects_corrupt_optional_hair_png(tmp_path: Path) -> None:
    corrupted = _corrupt_idat(_png())
    archive = _archive(
        tmp_path,
        "corrupt-hair",
        corrupted,
        group="hairstyles",
        declared_size=(512, 768),
    )
    with pytest.raises(OutfitPackError, match="supported PNG"):
        inspect_outfit_pack(archive)


def test_importer_rejects_empty_outerwear_but_keeps_empty_hair_back(tmp_path: Path) -> None:
    empty = _encoded(4, 5, RGBA, QColor(0, 0, 0, 0))
    garment = _archive(tmp_path, "empty-outerwear", empty)
    with pytest.raises(OutfitPackError, match="visible pixels"):
        inspect_outfit_pack(garment)

    hair = _archive(tmp_path, "empty-hair-back", empty, group="hairstyles")
    assert inspect_outfit_pack(hair).items


def test_importer_rejects_layer_that_escapes_pose_canvas(tmp_path: Path) -> None:
    data = _encoded(1025, 1, RGBA, QColor(30, 70, 150, 255))
    archive = _archive(tmp_path, "oversized-full-body", data)
    with pytest.raises(OutfitPackError, match="runtime canvas"):
        inspect_outfit_pack(archive)


def test_importer_keeps_cropped_tile_and_positive_anchor(tmp_path: Path) -> None:
    data = _encoded(4, 5, RGBA, QColor(30, 70, 150, 255))
    archive = _archive(tmp_path, "cropped-tile", data, anchor=(100, 200))
    pack = inspect_outfit_pack(archive)
    declaration = pack.items[0].variants[0].poses["yaw+000-pitch+00"][0]
    assert declaration.path == "assets/cropped-tile.png"
    assert (declaration.width, declaration.height, declaration.anchor_x, declaration.anchor_y) == (4, 5, 100, 200)


def test_builder_uses_importer_contract_before_publishing(tmp_path: Path) -> None:
    data = _encoded(4, 5, RGB, QColor(30, 70, 150))
    archive = _archive(tmp_path, "builder-rgb-outerwear", data)
    authoring, asset_root = _authoring_copy(tmp_path / "builder", archive)
    output = tmp_path / "builder-output.mohan-outfit"
    with pytest.raises(OutfitPackError, match="alpha channel"):
        build_outfit_pack(authoring, asset_root, output)
    assert not output.exists()
