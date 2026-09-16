"""Fail-closed loading and alpha-aware composition for reviewed garments."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy from pathlib import Path

lazy import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QColor, QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure.reviewed_garment_assets import (
    DIMENSION,
    SCHEMA,
    load_reviewed_garment_assets,
)


POSE = "cheek-rest"
EXPECTED_LAYER_COUNT = 3
SELECTION = {
    "pack_id": "mohan.official.blue-white-hanfu",
    "item_id": "hanfu-robe",
    "variant_id": "blue-white",
}


def test_declared_native_authority_is_pinned_and_cached(tmp_path: Path) -> None:
    root = tmp_path / "reviewed-garments"
    native_path = tmp_path / "idle.png"
    payload = _rgba(QColor("gold"), (40, 30))
    native_path.write_bytes(payload)
    manifest = _write(root, native_sha=hashlib.sha256(payload).hexdigest())
    manifest["poses"][POSE]["native_source_file"] = "idle.png"
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assets = load_reviewed_garment_assets(root)
    assert assets is not None
    native = assets.poses[POSE].native_source
    assert native is not None
    assert native.image.pixelColor(40, 30) == QColor("gold")
    native_path.write_bytes(_rgba(QColor("red"), (40, 30)))
    assert native.image.pixelColor(40, 30) == QColor("gold")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_reviewed_garment_assets(root)


@pytest.mark.parametrize("name", ["../outside.png", "nested/idle.png", "C:/outside.png"])
def test_native_authority_cannot_escape_expression_directory(tmp_path: Path, name: str) -> None:
    root = tmp_path / "reviewed-garments"
    manifest = _write(root)
    manifest["poses"][POSE]["native_source_file"] = name
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="one PNG"):
        load_reviewed_garment_assets(root)


def _png(image: QImage) -> bytes:
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice

    output = QByteArray()
    buffer = QBuffer(output)
    assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(output)


def _rgba(color: QColor, point: tuple[int, int] | None = None) -> bytes:
    image = QImage(DIMENSION, DIMENSION, QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    if point is not None:
        image.setPixelColor(*point, color)
    return _png(image)


def _visibility() -> bytes:
    image = QImage(DIMENSION, DIMENSION, QImage.Format.Format_Grayscale8)
    image.fill(255)
    image.setPixel(0, 0, 0)
    return _png(image)


def _write(root: Path, *, native_sha: str | None = None) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    native_path = root.parent / "idle.png"
    if not native_path.exists():
        native_path.write_bytes(_rgba(QColor("tan"), (40, 30)))
    if native_sha is None:
        native_sha = hashlib.sha256(native_path.read_bytes()).hexdigest()
    files = {
        "cheek-rest/visibility.png": _visibility(),
        "cheek-rest/garment.rgba.png": _rgba(QColor("red"), (10, 10)),
        "cheek-rest/lower-hand.rgba.png": _rgba(QColor("green"), (10, 10)),
        "cheek-rest/cuff.rgba.png": _rgba(QColor("blue"), (10, 10)),
    }
    for relative, payload in files.items():
        target = root / Path(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    digest = lambda relative: hashlib.sha256(files[relative]).hexdigest()
    manifest = {
        "schema": SCHEMA,
        "poses": {
            POSE: {
                "native_source_file": "idle.png",
                "native_source_sha256": native_sha,
                "visibility": {
                    "path": "cheek-rest/visibility.png",
                    "sha256": digest("cheek-rest/visibility.png"),
                },
                "ordered_layers": [
                    {
                        "role": "garment",
                        "path": "cheek-rest/garment.rgba.png",
                        "sha256": digest("cheek-rest/garment.rgba.png"),
                    },
                    {
                        "role": "native-lower-hand",
                        "path": "cheek-rest/lower-hand.rgba.png",
                        "sha256": digest("cheek-rest/lower-hand.rgba.png"),
                    },
                    {
                        "role": "cuff",
                        "path": "cheek-rest/cuff.rgba.png",
                        "sha256": digest("cheek-rest/cuff.rgba.png"),
                    },
                ],
                "selection_exact": SELECTION,
                "native_appearance_selections": {
                    "hairstyle": {
                        "pack_id": "mohan.official.blue-white-hanfu",
                        "item_id": "loose-hair",
                        "variant_id": "ink-black",
                    },
                    "headwear": {
                        "pack_id": "mohan.official.blue-white-hanfu",
                        "item_id": "silver-hairpiece",
                        "variant_id": "silver",
                    },
                },
            }
        },
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def test_missing_root_is_uninstalled_but_existing_invalid_root_fails_closed(tmp_path: Path) -> None:
    assert load_reviewed_garment_assets(tmp_path / "missing") is None
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(ValueError, match="manifest"):
        load_reviewed_garment_assets(existing)


def test_loader_validates_exact_selection_and_preserves_typed_native_selections(
    tmp_path: Path,
) -> None:
    root = tmp_path / "reviewed-garments"
    _write(root)
    assets = load_reviewed_garment_assets(root)
    assert assets is not None
    pose = assets.match(POSE, **SELECTION)
    assert pose is not None
    assert len(pose.layers) == EXPECTED_LAYER_COUNT
    assert pose.layers[0].path == "cheek-rest/garment.rgba.png"
    assert pose.selection_exact.pack_id == SELECTION["pack_id"]
    assert pose.native_appearance_selections["hairstyle"].item_id == "loose-hair"
    assert assets.match(POSE, SELECTION["pack_id"], SELECTION["item_id"], "other") is None
    assert assets.match("front-crossed", **SELECTION) is None


def test_compose_uses_destination_in_order_and_keeps_source_frame_unchanged(
    tmp_path: Path,
) -> None:
    _ = QApplication.instance() or QApplication([])
    root = tmp_path / "reviewed-garments"
    _write(root)
    assets = load_reviewed_garment_assets(root)
    assert assets is not None
    pose = assets.match(POSE, **SELECTION)
    assert pose is not None

    frame = QImage(DIMENSION, DIMENSION, QImage.Format.Format_RGBA8888)
    frame.fill(QColor("yellow"))
    frame_before = frame.copy()
    result = pose.compose(frame)
    assert isinstance(result, QImage)
    assert result.format() == QImage.Format.Format_RGBA8888
    assert result.pixelColor(0, 0).alpha() == 0
    assert result.pixelColor(10, 10) == QColor("blue")
    assert result.pixelColor(20, 20) == QColor("yellow")
    assert frame == frame_before

    pixmap_result = pose.compose(QPixmap.fromImage(frame))
    assert isinstance(pixmap_result, QPixmap)
    assert pixmap_result.toImage().pixelColor(10, 10) == QColor("blue")


def test_compose_reads_decoded_inputs_only_at_load(tmp_path: Path) -> None:
    root = tmp_path / "reviewed-garments"
    _write(root)
    assets = load_reviewed_garment_assets(root)
    assert assets is not None
    pose = assets.match(POSE, **SELECTION)
    assert pose is not None
    # Drift on disk after load cannot alter the in-memory composition.
    (root / "cheek-rest/cuff.rgba.png").write_bytes(_rgba(QColor("magenta"), (10, 10)))
    frame = QImage(DIMENSION, DIMENSION, QImage.Format.Format_RGBA8888)
    frame.fill(QColor("yellow"))
    assert pose.compose(frame).pixelColor(10, 10) == QColor("blue")


@pytest.mark.parametrize(
    "mutation",
    (
        "layer_sha",
        "visibility_sha",
        "traversal",
        "rgb_layer",
        "bad_native_sha",
        "missing_native_file",
        "unsupported_native_selection",
    ),
)
def test_invalid_manifest_or_asset_fails_closed(tmp_path: Path, mutation: str) -> None:
    root = tmp_path / "reviewed-garments"
    manifest = _write(root)
    pose = manifest["poses"][POSE]
    if mutation == "layer_sha":
        pose["ordered_layers"][0]["sha256"] = "0" * 64
    elif mutation == "visibility_sha":
        pose["visibility"]["sha256"] = "0" * 64
    elif mutation == "traversal":
        pose["ordered_layers"][0]["path"] = "../outside.png"
    elif mutation == "rgb_layer":
        rgb = QImage(DIMENSION, DIMENSION, QImage.Format.Format_RGB888)
        rgb.fill(QColor("red"))
        payload = _png(rgb)
        path = root / "cheek-rest/garment.rgba.png"
        path.write_bytes(payload)
        pose["ordered_layers"][0]["sha256"] = hashlib.sha256(payload).hexdigest()
    elif mutation == "bad_native_sha":
        pose["native_source_sha256"] = "G" * 64
    elif mutation == "missing_native_file":
        pose.pop("native_source_file")
    elif mutation == "unsupported_native_selection":
        pose["native_appearance_selections"]["garment"] = dict(SELECTION)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        load_reviewed_garment_assets(root)
