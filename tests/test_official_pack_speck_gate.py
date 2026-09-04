"""Every official silhouette is checked after the real runtime overlay composes it."""

from __future__ import annotations

lazy import os
lazy import json
lazy import zipfile
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import numpy as np
lazy import pytest
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.outfit_pack import POSE_ATLAS_SILHOUETTES, REQUIRED_SILHOUETTES
lazy from domain.outfit_pack import OFFICIAL_PACK_ROOT
lazy from infrastructure.active_outfit_overlay import (
    MAX_CACHED_LAYER_BYTES,
    MAX_CACHED_VIEWS,
    ActiveOutfitOverlay,
)
lazy from tools.audit_official_pack_quality import (
    SPECK_HEAD_ROI,
    fine_chain_metrics,
    isolated_speck_metrics,
)
lazy from tools.art_pipeline.speck_cleanup import (
    FULL_BODY_SPECK_ROI,
    speck_roi_for_shape,
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
HALF_BASE_RIGS = {
    "cheek-rest": "cheek",
    "left-neutral": "lean",
    "front-crossed": "front",
    "front-mock-scold": "front",
    "front-mock-hit": "front",
    "front-eureka": "front",
    "front-exasperated": "front",
}
# 2026-09-04 實測值：移除 31 個 alpha=1 假像素與 5 個孤立殘留後的基線。
EXPECTED_FRONT_CROSSED_BACK_PIXELS = 13_506
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


def _expand_declared_layer(
    image: np.ndarray, declaration: dict[str, object], silhouette: str
) -> np.ndarray:
    base = QImage(str(_base_path(silhouette)))
    assert not base.isNull(), silhouette
    canvas_shape = (base.height(), base.width())
    x, y = (int(value) for value in declaration.get("anchor", [0, 0]))
    height, width = image.shape[:2]
    assert (
        0 <= x
        and 0 <= y
        and x + width <= canvas_shape[1]
        and y + height <= canvas_shape[0]
    )
    if (height, width) == canvas_shape and (x, y) == (0, 0):
        return image
    expanded = np.zeros((*canvas_shape, 4), dtype=image.dtype)
    expanded[y : y + height, x : x + width] = image
    return expanded


def _headwear_alpha(silhouette: str) -> np.ndarray:
    with zipfile.ZipFile(OUTFIT_PACK) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        declaration = manifest["headwear"][0]["variants"][0]["poses"][silhouette][0]
        image = QImage.fromData(archive.read(declaration["path"]), "PNG")
    assert not image.isNull(), silhouette
    return _expand_declared_layer(_rgba(image), declaration, silhouette)[:, :, 3]


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
    return _expand_declared_layer(_rgba(image), declaration, silhouette)


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


def test_official_speck_roi_keeps_half_and_full_body_regions() -> None:
    assert speck_roi_for_shape((1254, 1254)) == SPECK_HEAD_ROI
    assert speck_roi_for_shape((1536, 1024)) == FULL_BODY_SPECK_ROI


@pytest.mark.parametrize("slot", ("front", "back", "headwear"))
@pytest.mark.parametrize("silhouette", REQUIRED_SILHOUETTES)
def test_every_official_layer_has_zero_owner_isolated_small_points(
    silhouette: str, slot: str
) -> None:
    image = _layer_image(silhouette, slot)
    measured = isolated_speck_metrics(
        image, roi=speck_roi_for_shape(image.shape[:2])
    )

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
    rendered_rgba = _rgba(rendered.toImage())
    measured = isolated_speck_metrics(
        rendered_rgba, roi=speck_roi_for_shape(rendered_rgba.shape[:2])
    )
    native_rgba = _rgba(QImage(str(_native_base_path(silhouette))))
    native = isolated_speck_metrics(
        native_rgba, roi=speck_roi_for_shape(native_rgba.shape[:2])
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
    rendered_rgba = _rgba(rendered.toImage())
    measured = isolated_speck_metrics(
        rendered_rgba,
        roi=speck_roi_for_shape(rendered_rgba.shape[:2]),
        source_alpha=_headwear_alpha(silhouette),
    )

    assert measured["isolated_count"] == 0, f"{silhouette}: {measured}"


@pytest.mark.parametrize("silhouette", REQUIRED_SILHOUETTES)
def test_every_official_composite_has_zero_isolated_small_points(
    tmp_path: Path, silhouette: str
) -> None:
    _app()
    rendered = ActiveOutfitOverlay(tmp_path / "store", ROOT).apply(
        QPixmap(str(_base_path(silhouette))), silhouette
    )
    rgba = _rgba(rendered.toImage())
    measured = isolated_speck_metrics(
        rgba, roi=speck_roi_for_shape(rgba.shape[:2])
    )

    assert measured["isolated_count"] == 0, f"{silhouette}: {measured}"


def test_cropped_back_layer_composes_pixel_identically_to_full_canvas_layer() -> None:
    silhouette = "front-crossed"
    with zipfile.ZipFile(OUTFIT_PACK) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        declaration = next(
            item
            for item in manifest["hairstyles"][0]["variants"][0]["poses"][silhouette]
            if item["slot"] == "back"
        )
        encoded = archive.read(declaration["path"])
    cropped = QImage.fromData(encoded, "PNG").convertToFormat(QImage.Format_RGBA8888)
    # An opaque sentinel canvas makes the comparison about layer placement and
    # alpha blending, not Qt's rounding of already-transparent edge pixels
    # outside the cropped asset's bbox.
    base = QImage(str(_base_path(silhouette))).convertToFormat(QImage.Format_RGBA8888)
    base.fill(QColor(127, 127, 127, 255))
    x, y = (int(value) for value in declaration["anchor"])
    full = QImage(base.size(), QImage.Format_RGBA8888)
    full.fill(QColor(0, 0, 0, 0))
    painter = QPainter(full)
    painter.drawImage(x, y, cropped)
    painter.end()

    composited_full = QImage(base)
    painter = QPainter(composited_full)
    painter.drawImage(0, 0, full)
    painter.end()
    composited_cropped = QImage(base)
    painter = QPainter(composited_cropped)
    painter.drawImage(x, y, cropped)
    painter.end()

    assert np.array_equal(_rgba(composited_full), _rgba(composited_cropped))


def test_runtime_layer_cache_stays_within_measured_memory_budget(
    tmp_path: Path,
) -> None:
    _app()
    overlay = ActiveOutfitOverlay(tmp_path / "store", ROOT)
    for silhouette in REQUIRED_SILHOUETTES:
        frame = QPixmap(str(_base_path(silhouette)))
        assert not frame.isNull(), silhouette
        overlay.apply(frame, silhouette)

    assert len(overlay._layers_by_view) <= MAX_CACHED_VIEWS
    assert overlay.cached_layer_memory_bytes() <= MAX_CACHED_LAYER_BYTES
