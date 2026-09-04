"""Every official silhouette is checked after the real runtime overlay composes it."""

from __future__ import annotations

lazy import os
lazy import json
lazy import zipfile
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import numpy as np
lazy import pytest
lazy from PySide6.QtGui import QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.outfit_pack import POSE_ATLAS_SILHOUETTES, REQUIRED_SILHOUETTES
lazy from domain.outfit_pack import OFFICIAL_PACK_ROOT
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from tools.audit_official_pack_quality import (
    SPECK_FULL_BODY_ROI,
    SPECK_HEAD_ROI,
    isolated_speck_metrics,
)

ROOT = Path(__file__).resolve().parents[1]
OUTFIT_PACK = OFFICIAL_PACK_ROOT / "mohan.official.blue-white-hanfu.mohan-outfit"
HALF_BASES = {
    "cheek-rest": "idle.png",
    "left-neutral": "idle_lean.png",
    "front-crossed": "idle_front.png",
    "front-mock-scold": "mock_scold.png",
    "front-mock-hit": "mock_hit_front.png",
    "front-eureka": "eureka_front.png",
    "front-exasperated": "exasperated_front.png",
}


def _app() -> object:
    return QApplication.instance() or QApplication([])


def _rgba(image: QImage) -> np.ndarray:
    image = image.convertToFormat(QImage.Format_RGBA8888)
    width, height = image.width(), image.height()
    rows = np.frombuffer(bytes(image.constBits()), np.uint8).reshape(
        height, image.bytesPerLine()
    )
    return rows[:, : width * 4].reshape(height, width, 4).copy()


def _base_path(silhouette: str) -> Path:
    if silhouette in POSE_ATLAS_SILHOUETTES:
        return ROOT / "assets/pose-atlas/v5-base" / f"{silhouette}.png"
    return ROOT / "assets/expressions" / HALF_BASES[silhouette]


def _headwear_alpha(silhouette: str) -> np.ndarray:
    with zipfile.ZipFile(OUTFIT_PACK) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        declaration = manifest["headwear"][0]["variants"][0]["poses"][silhouette][0]
        image = QImage.fromData(archive.read(declaration["path"]), "PNG")
    assert not image.isNull(), silhouette
    return _rgba(image)[:, :, 3]


@pytest.mark.parametrize("silhouette", REQUIRED_SILHOUETTES)
def test_every_official_silhouette_has_zero_isolated_head_specks(
    tmp_path: Path, silhouette: str
) -> None:
    _app()
    source = _base_path(silhouette)
    frame = QPixmap(str(source))
    assert not frame.isNull(), source

    rendered = ActiveOutfitOverlay(tmp_path / "store", ROOT).apply(frame, silhouette)
    roi = SPECK_FULL_BODY_ROI if silhouette in POSE_ATLAS_SILHOUETTES else SPECK_HEAD_ROI
    measured = isolated_speck_metrics(
        _rgba(rendered.toImage()),
        roi=roi,
        source_alpha=_headwear_alpha(silhouette),
    )

    assert measured["isolated_count"] == 0, f"{silhouette}: {measured}"
