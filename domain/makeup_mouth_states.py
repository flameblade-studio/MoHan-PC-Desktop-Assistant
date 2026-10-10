"""Optional viseme-driven mouth-state declarations (lips, paired with
foundation on foundation silhouettes), using the canonical pose parser.

Owner-approved 2026-09-28 (owner-final-approval-20260928.json,
code_changes_authorized: "mouth_states makeup"). Mirrors
domain.makeup_eye_states.parse_makeup_eye_states but keyed by mouth shape
(a/o/small) instead of eye state (half/closed), and requires a paired
foundation layer only on silhouettes the variant already declares as a
foundation silhouette -- the same pairing rule
_makeup_variant() already applies to eye_states' "eyes"+"foundation".
"""
from __future__ import annotations

lazy from collections.abc import Callable
lazy from typing import Protocol
lazy from domain.character_runtime import character_rig_manifest
lazy from domain.outfit_pack_assets import OutfitPackError

_RIG_MANIFEST = character_rig_manifest()
_FULL_BODY_CANVAS = (
    _RIG_MANIFEST.full_body_canvas.width,
    _RIG_MANIFEST.full_body_canvas.height,
)
_HALF_BODY_CANVAS = (
    _RIG_MANIFEST.half_body_asset_canvas.width,
    _RIG_MANIFEST.half_body_asset_canvas.height,
)

MOUTH_SHAPES = frozenset({"a", "o", "small"})
LIPS_SLOT = "lips"
# FaceMotionFrame.viseme.value -> mouth_states shape key. CLOSED is
# intentionally absent: .get(...) returns None, so the CLOSED/rest render
# path never resolves a shape and therefore never substitutes anything.
VISEME_TO_MOUTH_SHAPE = frozendict({
    "A": "a", "O": "o", "U": "o", "CONSONANT": "small", "E": "small", "I": "small",
})


class MouthAsset(Protocol):
    width: int
    height: int
    anchor_x: int
    anchor_y: int
    slot: str


def parse_mouth_states[T: MouthAsset](
    value: object,
    parse_poses: Callable[[object], frozendict[str, tuple[T, ...]]],
    foundation_silhouettes: frozenset[str],
) -> frozendict[str, frozendict[str, tuple[T, ...]]]:
    if not isinstance(value, dict) or (value and set(value) != MOUTH_SHAPES):
        raise OutfitPackError("Mouth states require exactly the a, o and small shapes.")
    parsed = {}
    silhouettes: set[str] | None = None
    for shape, entries in value.items():
        poses = parse_poses(entries)
        current_silhouettes = set(poses)
        if silhouettes is None:
            silhouettes = current_silhouettes
        elif current_silhouettes != silhouettes:
            raise OutfitPackError("Mouth states must cover the same silhouettes.")
        for silhouette, assets in poses.items():
            canvas = _FULL_BODY_CANVAS if silhouette.startswith("yaw") else _HALF_BODY_CANVAS
            if any(
                (asset.width, asset.height, asset.anchor_x, asset.anchor_y) != (*canvas, 0, 0)
                for asset in assets
            ):
                raise OutfitPackError("Mouth-state makeup must cover its canvas at anchor 0,0.")
            expected = (
                frozenset({LIPS_SLOT, "foundation"})
                if silhouette in foundation_silhouettes
                else frozenset({LIPS_SLOT})
            )
            if {asset.slot for asset in assets} != expected:
                raise OutfitPackError(
                    f"Mouth state for {silhouette!r} must carry exactly its declared mouth layers."
                )
        parsed[shape] = poses
    return frozendict(parsed)
