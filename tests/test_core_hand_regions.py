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
    with pytest.raises(OutfitPackError, match="recognized core visible-hand view"):
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


def test_every_visible_alpha_level_preserves_hand_ownership(tmp_path):
    app = QApplication.instance() or QApplication([])
    paths = _pair(tmp_path)
    image = QImage(str(paths[0]))
    for alpha in range(256):
        image.setPixelColor(100 + alpha, 600, QColor(140, 100, 80, alpha))
    assert image.save(str(paths[0]))
    source_bytes = paths[0].read_bytes()

    provider = load_core_hand_regions(tmp_path)
    assert provider is not None
    region = provider(VIEW)
    for alpha in range(256):
        assert region.contains(QPoint(100 + alpha, 600)) == bool(alpha), alpha
    assert not region.contains(QPoint(99, 600))
    assert not region.contains(QPoint(356, 600))
    assert paths[0].read_bytes() == source_bytes
    app.processEvents()


def test_core_overlay_pair_is_the_full_body_authority(tmp_path):
    app = QApplication.instance() or QApplication([])
    _pair(tmp_path)
    paths = _overlay_pair(tmp_path)
    provider = load_core_hand_regions(tmp_path)
    assert provider is not None
    assert provider(VIEW).contains(QPoint(300, 800))
    assert provider(OVERLAY_VIEW).contains(QPoint(400, 900))
    assert provider(OVERLAY_VIEW).contains(QPoint(401, 900))
    assert not provider(OVERLAY_VIEW).contains(QPoint(300, 800))
    assert provider.has_repaintable_overlay(OVERLAY_VIEW)
    assert not provider.has_repaintable_overlay(VIEW)
    first_images = provider.overlay_images(OVERLAY_VIEW)
    assert first_images is not None
    first_images[0].setPixelColor(400, 900, QColor("red"))
    paths[0].write_bytes(b"changed after snapshot")
    second_images = provider.overlay_images(OVERLAY_VIEW)
    assert second_images is not None
    assert second_images[0].pixelColor(400, 900) == QColor("white")
    assert provider.overlay_images(VIEW) is None
    app.processEvents()



def _half_body_pair(root: Path, prefix: str, point: QPoint | None) -> tuple[Path, Path]:
    directory = root / "assets/expressions/layered"
    directory.mkdir(parents=True, exist_ok=True)
    paths = tuple(directory / f"{prefix}_visible_hand_{side}.png" for side in ("left", "right"))
    for path in paths:
        image = QImage(1254, 1254, QImage.Format_RGBA8888)
        image.fill(QColor(0, 0, 0, 0))
        if point is not None:
            image.setPixelColor(point, QColor("white"))
        assert image.save(str(path))
    return paths


def test_half_body_pose_hands_override_shared_front_rig(tmp_path):
    app = QApplication.instance() or QApplication([])
    _half_body_pair(tmp_path, "front", QPoint(500, 1100))
    _half_body_pair(tmp_path, "front-exasperated", QPoint(450, 600))
    provider = load_core_hand_regions(tmp_path)
    assert provider is not None
    raised = provider("front-exasperated")
    assert raised.contains(QPoint(450, 600))
    assert not raised.contains(QPoint(500, 1100))
    crossed = provider("front-crossed")
    assert crossed.contains(QPoint(500, 1100))
    assert not crossed.contains(QPoint(450, 600))
    app.processEvents()


@pytest.mark.parametrize("failure", ["missing", "corrupt"])
def test_broken_pose_hand_pair_cannot_fall_back_to_other_pose(tmp_path, failure):
    app = QApplication.instance() or QApplication([])
    _half_body_pair(tmp_path, "front", QPoint(500, 1100))
    paths = _half_body_pair(tmp_path, "front-eureka", QPoint(550, 700))
    if failure == "missing":
        paths[1].unlink()
    else:
        paths[1].write_bytes(b"broken pose-specific hand")
    with pytest.raises(OutfitPackError, match="Invalid core"):
        load_core_hand_regions(tmp_path)
    app.processEvents()


def test_explicit_hidden_pose_hands_do_not_reuse_visible_legacy_hands(tmp_path):
    app = QApplication.instance() or QApplication([])
    _half_body_pair(tmp_path, "front", QPoint(500, 1100))
    _half_body_pair(tmp_path, "front-mock-hit", None)
    provider = load_core_hand_regions(tmp_path)
    assert provider is not None
    assert provider("front-mock-hit").isEmpty()
    assert not provider("front-crossed").isEmpty()
    app.processEvents()


def main() -> None:
    result = pytest.main([__file__, "-q"])
    if result:
        raise SystemExit(result)
    print("CORE_HAND_REGIONS_OK")


if __name__ == "__main__":
    main()
