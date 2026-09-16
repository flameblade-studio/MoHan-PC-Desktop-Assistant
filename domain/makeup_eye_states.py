"""Optional paired eye-state declarations, using the canonical pose parser."""
from __future__ import annotations

lazy from collections.abc import Callable
lazy from typing import Protocol
lazy from domain.outfit_pack_assets import OutfitPackError


class EyeAsset(Protocol):
    width: int
    height: int
    anchor_x: int
    anchor_y: int


def parse_makeup_eye_states[T: EyeAsset](
    value: object,
    parse_poses: Callable[[object], frozendict[str, tuple[T, ...]]],
) -> frozendict[str, frozendict[str, tuple[T, ...]]]:
    if not isinstance(value, dict) or (value and set(value) != {"half", "closed"}):
        raise OutfitPackError("Makeup eye states require both half and closed.")
    parsed = {}
    silhouettes: set[str] | None = None
    for state, entries in value.items():
        poses = parse_poses(entries)
        current_silhouettes = set(poses)
        if silhouettes is None:
            silhouettes = current_silhouettes
        elif current_silhouettes != silhouettes:
            raise OutfitPackError("Makeup eye states must cover the same silhouettes.")
        for silhouette, assets in poses.items():
            canvas = (1024, 1536) if silhouette.startswith("yaw") else (1254, 1254)
            if any((asset.width, asset.height, asset.anchor_x, asset.anchor_y) != (*canvas, 0, 0) for asset in assets):
                raise OutfitPackError("Eye-state makeup must cover its canvas at anchor 0,0.")
        parsed[state] = poses
    return frozendict(parsed)


def validated_makeup_intensity(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
        raise OutfitPackError("Makeup intensity must be a number between 0 and 1.")
    return float(value)
