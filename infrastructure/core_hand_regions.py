"""Load immutable, core-owned visible-hand masks at composition time."""
from __future__ import annotations

lazy from pathlib import Path
lazy from types import MappingProxyType

lazy from PySide6.QtGui import QImage, QRegion
lazy from domain.constants import POSE_ATLAS_LAYERED_ROOT_NAME
lazy from domain.outfit_pack import OutfitPackError, REQUIRED_SILHOUETTES
lazy from domain.outfit_pack_makeup import HALF_BODY_RIGS
lazy from infrastructure.image_alpha_regions import visible_alpha_region


class CoreHandSnapshot:
    """Immutable hand support and repaintable RGBA captured from one disk read."""

    __slots__ = ("_overlay_images", "_regions")

    def __init__(
        self,
        regions: dict[str, QRegion],
        overlay_images: dict[str, tuple[QImage, QImage]],
    ) -> None:
        self._regions = MappingProxyType({view: QRegion(region) for view, region in regions.items()})
        self._overlay_images = MappingProxyType({
            view: tuple(image.copy() for image in images)
            for view, images in overlay_images.items()
        })

    def __call__(self, view_id: str) -> QRegion:
        if view_id not in REQUIRED_SILHOUETTES:
            raise OutfitPackError("Use a recognized core visible-hand view.")
        return QRegion(self._regions.get(view_id, QRegion()))

    def has_repaintable_overlay(self, view_id: str) -> bool:
        if view_id not in REQUIRED_SILHOUETTES:
            raise OutfitPackError("Use a recognized core visible-hand view.")
        return view_id in self._overlay_images

    def overlay_images(self, view_id: str) -> tuple[QImage, QImage] | None:
        if view_id not in REQUIRED_SILHOUETTES:
            raise OutfitPackError("Use a recognized core visible-hand view.")
        images = self._overlay_images.get(view_id)
        return None if images is None else tuple(image.copy() for image in images)


def load_core_hand_regions(asset_root: Path) -> CoreHandSnapshot | None:
    """Snapshot optional left/right pairs; malformed or partial pairs receive a protective result.

    Both PNGs use the body's full canvas. Nonzero alpha owns visible hand skin;
    A zero-alpha pair represents naturally hidden hands. Legacy views with neither file retain their existing behavior. Half-body view-specific pairs
    precede shared rig pairs, including explicit empty pairs. Mask ownership stays with the core authority.
    """
    regions: dict[str, QRegion] = {}
    overlay_images: dict[str, tuple[QImage, QImage]] = {}
    for view_id in REQUIRED_SILHOUETTES:
        half_body = view_id in HALF_BODY_RIGS
        directory = (
            Path(asset_root) / "assets/expressions/layered"
            if half_body else
            Path(asset_root) / "assets/pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME
        )
        prefix = HALF_BODY_RIGS.get(view_id, view_id)
        paths = tuple(
            directory / f"{prefix}_visible_hand_{side}.png"
            for side in ("left", "right")
        )
        repaintable = False
        if half_body:
            preferred = tuple(
                directory / f"{view_id}_visible_hand_{side}.png"
                for side in ("left", "right")
            )
        else:
            overlay_directory = Path(asset_root) / "assets/pose-atlas/v5-hand-overlays"
            preferred = tuple(
                overlay_directory / f"{view_id}_{side}.png"
                for side in ("left", "right")
            )
        # One preferred file declares this pose's pair. A file requiring attention
        # partners must fail rather than silently select another pose's hands.
        if any(path.exists() for path in preferred):
            paths = preferred
            repaintable = not half_body
        if not any(path.exists() for path in paths):
            continue
        dimensions = (1254, 1254) if half_body else (1024, 1536)
        region = QRegion()
        decoded: list[QImage] = []
        for path in paths:
            image = QImage(str(path))
            if image.isNull() or not image.hasAlphaChannel() or image.size().toTuple() != dimensions:
                raise OutfitPackError(f"Invalid core visible-hand pair: {path.name}")
            region = region.united(visible_alpha_region(image))
            decoded.append(image.convertToFormat(QImage.Format_RGBA8888))
        regions[view_id] = region
        if repaintable:
            overlay_images[view_id] = (decoded[0], decoded[1])
    if not regions:
        return None
    return CoreHandSnapshot(regions, overlay_images)
