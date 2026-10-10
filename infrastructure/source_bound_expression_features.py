"""Detect the minimal animated feature region in source-bound portraits."""

from __future__ import annotations

lazy from pathlib import Path

lazy import numpy as np
lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QImage, QRegion

lazy from domain.character_runtime import (
    CHARACTER_ASSET_PATHS,
    CHARACTER_EXPRESSION_ROLES,
    character_rig_manifest,
)
lazy from domain.qt_image_pixels import rgba8888_image
lazy from infrastructure.image_alpha_regions import visible_alpha_region

RGB_DELTA_MIN = 4
FEATURE_LUMA_MAX = 100
SOURCE_EYE_GUARD = QRect(500, 395, 210, 60)
SOURCE_MOUTH_GUARD = QRect(545, 535, 115, 55)
TILTED_EYE_GUARD = QRect(480, 470, 210, 50)
TILTED_MOUTH_GUARD = QRect(560, 600, 100, 50)
_EXASPERATED_SILHOUETTE = character_rig_manifest().gesture_silhouettes[
    CHARACTER_EXPRESSION_ROLES["exasperation"]
]


def gesture_expression_feature_region(
    asset_root: Path,
    view_id: str,
    cache: dict[str, QRegion],
) -> QRegion | None:
    cached = cache.get(view_id)
    if cached is not None:
        return cached
    frame_root = (
        asset_root
        / CHARACTER_ASSET_PATHS["halfbody_root"]
        / "complete-expressions"
        / "frames"
    )
    baseline = rgba8888_image(
        QImage(str(frame_root / f"{view_id}-neutral-rest.rgba.png"))
    )
    if baseline.isNull():
        return None
    baseline_rows = np.frombuffer(
        baseline.constBits(), dtype=np.uint8,
    ).reshape(baseline.height(), baseline.bytesPerLine())
    baseline_pixels = baseline_rows[:, :baseline.width() * 4].reshape(
        baseline.height(), baseline.width(), 4,
    ).astype(np.int16)
    changed = np.zeros((baseline.height(), baseline.width()), dtype=np.uint8)
    for path in sorted(frame_root.glob(f"{view_id}-*.rgba.png")):
        image = rgba8888_image(QImage(str(path)))
        if image.isNull() or image.size() != baseline.size():
            continue
        rows = np.frombuffer(image.constBits(), dtype=np.uint8).reshape(
            image.height(), image.bytesPerLine(),
        )
        pixels = rows[:, :image.width() * 4].reshape(
            image.height(), image.width(), 4,
        ).astype(np.int16)
        changed[
            np.max(np.abs(pixels - baseline_pixels), axis=2) > RGB_DELTA_MIN
        ] = 255
    luma = baseline_pixels[:, :, :3].mean(axis=2)
    feature = np.where(
        (changed > 0) & (luma < FEATURE_LUMA_MAX), 255, 0,
    ).astype(np.uint8)
    mask = QImage(
        feature.data,
        baseline.width(),
        baseline.height(),
        baseline.width(),
        QImage.Format_Alpha8,
    ).copy()
    guard = QRegion(SOURCE_EYE_GUARD).united(QRegion(SOURCE_MOUTH_GUARD))
    if view_id == _EXASPERATED_SILHOUETTE:
        guard = QRegion(TILTED_EYE_GUARD).united(QRegion(TILTED_MOUTH_GUARD))
    region = visible_alpha_region(mask).intersected(guard)
    if region.isEmpty():
        return None
    cache[view_id] = region
    return region
