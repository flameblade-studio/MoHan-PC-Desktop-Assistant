"""Every official silhouette is checked after the real runtime overlay composes it."""

from __future__ import annotations

lazy import os
lazy import json
lazy import sys
lazy import zipfile
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy import numpy as np
lazy import pytest
lazy from PySide6.QtGui import QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.outfit_pack import POSE_ATLAS_SILHOUETTES, REQUIRED_SILHOUETTES
lazy from domain.outfit_pack import OFFICIAL_PACK_ROOT
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from tools.audit_official_pack_quality import (
    SPECK_HEAD_ROI,
    fine_chain_metrics,
    isolated_speck_metrics,
)

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
HALF_BASE_RIGS = {
    "cheek-rest": "cheek",
    "left-neutral": "lean",
    "front-crossed": "front",
    "front-mock-scold": "front",
    "front-mock-hit": "front",
    "front-eureka": "front",
    "front-exasperated": "front",
}
EXPECTED_FRONT_CROSSED_BACK_PIXELS = 13_542
EXPECTED_FINE_CHAIN_LINKS = 15
EXPECTED_FINE_CHAIN_MAX_GAP = 9


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


def _layer_image(silhouette: str, slot: str) -> np.ndarray:
    category = "headwear" if slot == "headwear" else "hairstyles"
    with zipfile.ZipFile(OUTFIT_PACK) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        declarations = manifest[category][0]["variants"][0]["poses"][silhouette]
        declaration = (
            declarations[0]
            if category == "headwear"
            else next(item for item in declarations if item["slot"] == slot)
        )
        image = QImage.fromData(archive.read(declaration["path"]), "PNG")
    assert not image.isNull(), silhouette
    return _rgba(image)


def _native_base_path(silhouette: str) -> Path:
    if silhouette in POSE_ATLAS_SILHOUETTES:
        return ROOT / "assets/pose-atlas/v5-base" / f"{silhouette}.png"
    rig = HALF_BASE_RIGS[silhouette]
    return ROOT / "assets/expressions/layered" / f"{rig}_base.png"


def test_front_crossed_fine_chain_contract() -> None:
    measured = fine_chain_metrics(_layer_image("front-crossed", "headwear"))

    assert measured["link_count"] >= EXPECTED_FINE_CHAIN_LINKS, measured
    assert set(measured["endpoint_areas"]) >= {386, 89}, measured
    assert measured["maximum_link_distance_px"] <= EXPECTED_FINE_CHAIN_MAX_GAP, measured


def test_front_crossed_back_pixel_budget_does_not_regress() -> None:
    alpha = _layer_image("front-crossed", "back")[:, :, 3]

    assert int((alpha > 0).sum()) >= EXPECTED_FRONT_CROSSED_BACK_PIXELS


@pytest.mark.parametrize("slot", ("front", "back", "headwear"))
@pytest.mark.parametrize("silhouette", REQUIRED_SILHOUETTES)
def test_every_official_layer_has_zero_owner_isolated_small_points(
    silhouette: str, slot: str
) -> None:
    image = _layer_image(silhouette, slot)
    measured = isolated_speck_metrics(image, roi=SPECK_HEAD_ROI)

    assert measured["isolated_count"] == 0, f"{silhouette}/{slot}: {measured}"


@pytest.mark.parametrize("silhouette", REQUIRED_SILHOUETTES)
def test_every_official_composite_stays_within_native_base_speck_budget(
    tmp_path: Path, silhouette: str
) -> None:
    _app()
    source = _base_path(silhouette)
    frame = QPixmap(str(source))
    assert not frame.isNull(), source

    rendered = ActiveOutfitOverlay(tmp_path / "store", ROOT).apply(frame, silhouette)
    measured = isolated_speck_metrics(
        _rgba(rendered.toImage()), roi=SPECK_HEAD_ROI
    )
    native = isolated_speck_metrics(
        _rgba(QImage(str(_native_base_path(silhouette)))), roi=SPECK_HEAD_ROI
    )

    assert measured["isolated_count"] <= native["direct_definition_count"], (
        f"{silhouette}: composite={measured}, native={native}"
    )


@pytest.mark.parametrize("silhouette", REQUIRED_SILHOUETTES)
def test_every_official_silhouette_has_zero_isolated_head_specks(
    tmp_path: Path, silhouette: str
) -> None:
    _app()
    source = _base_path(silhouette)
    frame = QPixmap(str(source))
    assert not frame.isNull(), source

    rendered = ActiveOutfitOverlay(tmp_path / "store", ROOT).apply(frame, silhouette)
    measured = isolated_speck_metrics(
        _rgba(rendered.toImage()),
        roi=SPECK_HEAD_ROI,
        source_alpha=_headwear_alpha(silhouette),
    )

    assert measured["isolated_count"] == 0, f"{silhouette}: {measured}"
