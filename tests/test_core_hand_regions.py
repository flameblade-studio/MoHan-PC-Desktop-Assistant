"""Production core hand loading preserves legacy views and rejects broken pairs."""
from __future__ import annotations
lazy import sys
lazy from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import pytest
lazy from PySide6.QtCore import QPoint
lazy from PySide6.QtGui import QColor, QImage
lazy from PySide6.QtWidgets import QApplication
lazy from domain.constants import POSE_ATLAS_LAYERED_ROOT_NAME
lazy from domain.outfit_pack import OutfitPackError
lazy from infrastructure.core_hand_regions import load_core_hand_regions

VIEW = "yaw+030-pitch+00"
OVERLAY_VIEW = "yaw+165-pitch+00"


def _pair(root: Path, *, opaque: bool = False) -> tuple[Path, Path]:
    directory = root / "assets/pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME
    directory.mkdir(parents=True)
    paths = tuple(directory / f"{VIEW}_visible_hand_{side}.png" for side in ("left", "right"))
    for index, path in enumerate(paths):
        image = QImage(1024, 1536, QImage.Format_RGBA8888)
        image.fill(QColor(255, 255, 255, 255 if opaque else 0))
        image.setPixelColor(300 + index, 800, QColor(255, 255, 255, 255))
        assert image.save(str(path))
    return paths


def _overlay_pair(root: Path) -> tuple[Path, Path]:
    directory = root / "assets/pose-atlas/v5-hand-overlays"
    directory.mkdir(parents=True)
    paths = tuple(directory / f"{OVERLAY_VIEW}_{side}.png" for side in ("left", "right"))
    for index, path in enumerate(paths):
        image = QImage(1024, 1536, QImage.Format_RGBA8888)
        image.fill(QColor(0, 0, 0, 0))
        image.setPixelColor(400 + index, 900, QColor("white"))
        assert image.save(str(path))
    return paths


def test_core_pair_snapshot_and_legacy(tmp_path):
    app = QApplication.instance() or QApplication([])
    assert load_core_hand_regions(tmp_path) is None
    paths = _pair(tmp_path)
    provider = load_core_hand_regions(tmp_path)
    assert provider is not None
    assert provider(VIEW).contains(QPoint(300, 800))
    assert provider(VIEW).contains(QPoint(301, 800))
    assert not provider(VIEW).contains(QPoint(302, 800))
    assert provider("yaw+000-pitch+00").isEmpty()
    paths[0].write_bytes(b"changed after snapshot")
    assert provider(VIEW).contains(QPoint(300, 800))
    with pytest.raises(OutfitPackError, match="Unknown"):
        provider("../unknown")
    app.processEvents()


@pytest.mark.parametrize("failure", ["missing", "invalid", "dimensions", "no-alpha"])
def test_invalid_pair_rejected(tmp_path, failure):
    app = QApplication.instance() or QApplication([])
    paths = _pair(tmp_path)
    if failure == "missing":
        paths[1].unlink()
    elif failure == "invalid":
        paths[1].write_bytes(b"not a PNG")
    else:
        image = QImage(1, 1, QImage.Format_RGBA8888) if failure == "dimensions" else QImage(1024, 1536, QImage.Format_RGB888)
        image.fill(QColor("white"))
        assert image.save(str(paths[1]))
    with pytest.raises(OutfitPackError, match="Invalid core"):
        load_core_hand_regions(tmp_path)
    app.processEvents()


def test_opaque_alpha_mask_is_not_silently_empty(tmp_path):
    app = QApplication.instance() or QApplication([])
    _pair(tmp_path, opaque=True)
    provider = load_core_hand_regions(tmp_path)
    assert provider is not None
    assert provider(VIEW).contains(QPoint(1023, 1535))
    app.processEvents()


def test_core_overlay_pair_is_the_full_body_authority(tmp_path):
    app = QApplication.instance() or QApplication([])
    _pair(tmp_path)
    _overlay_pair(tmp_path)
    provider = load_core_hand_regions(tmp_path)
    assert provider is not None
    assert provider(VIEW).contains(QPoint(300, 800))
    assert provider(OVERLAY_VIEW).contains(QPoint(400, 900))
    assert provider(OVERLAY_VIEW).contains(QPoint(401, 900))
    assert not provider(OVERLAY_VIEW).contains(QPoint(300, 800))
    app.processEvents()


def main() -> None:
    result = pytest.main([__file__, "-q"])
    if result:
        raise SystemExit(result)
    print("CORE_HAND_REGIONS_OK")


if __name__ == "__main__":
    main()
