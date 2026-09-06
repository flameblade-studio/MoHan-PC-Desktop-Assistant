"""Load immutable, core-owned visible-hand masks at composition time."""
from __future__ import annotations

lazy from collections.abc import Callable
lazy from pathlib import Path

lazy from PySide6.QtGui import QBitmap, QImage, QRegion
lazy from domain.constants import POSE_ATLAS_LAYERED_ROOT_NAME
lazy from domain.outfit_pack import OutfitPackError, REQUIRED_SILHOUETTES
lazy from domain.outfit_pack_makeup import HALF_BODY_RIGS


def load_core_hand_regions(asset_root: Path) -> Callable[[str], QRegion] | None:
    """Snapshot optional left/right pairs; malformed or partial pairs fail closed.

    Both PNGs use the body's full canvas. Alpha describes visible hand skin;
    an empty pair is valid for naturally hidden hands. Legacy views without
    either file retain their existing behavior. No mask comes from a DLC.
    """
    regions: dict[str, QRegion] = {}
    for view_id in REQUIRED_SILHOUETTES:
        half_body = view_id in HALF_BODY_RIGS
        directory = (
            Path(asset_root) / "assets/expressions/layered"
            if half_body else
            Path(asset_root) / "assets/pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME
        )
        prefix = HALF_BODY_RIGS.get(view_id, view_id)
        paths = tuple(directory / f"{prefix}_visible_hand_{side}.png" for side in ("left", "right"))
        if not any(path.exists() for path in paths):
            continue
        dimensions = (1254, 1254) if half_body else (1024, 1536)
        region = QRegion()
        for path in paths:
            image = QImage(str(path))
            if image.isNull() or not image.hasAlphaChannel() or image.size().toTuple() != dimensions:
                raise OutfitPackError(f"Invalid core visible-hand pair: {path.name}")
            # createAlphaMask also handles an entirely opaque RGBA image;
            # QPixmap.mask() alone treats that case as an absent bitmap.
            region = region.united(QRegion(QBitmap.fromImage(image.createAlphaMask())))
        regions[view_id] = region
    if not regions:
        return None
    snapshot = frozendict(regions)

    def visible_hand_region(view_id: str) -> QRegion:
        if view_id not in REQUIRED_SILHOUETTES:
            raise OutfitPackError("Unknown core visible-hand view.")
        return QRegion(snapshot.get(view_id, QRegion()))

    return visible_hand_region
