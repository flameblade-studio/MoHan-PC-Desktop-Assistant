"""Pose-set and layer parsing for sealed appearance variants."""

from __future__ import annotations

lazy import zipfile

lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id
lazy from domain.character_runtime_data import default_rig_manifest
lazy from domain.constants import CHARACTER_EXPRESSION_ROLES
lazy from domain._outfit_pack_models import AppearanceAsset
lazy from domain.outfit_pack_assets import (
    GARMENT_SLOTS,
    OutfitPackError,
    parse_appearance_asset,
    required_pose_keys,
    validate_pose_assets,
)

_RIG_MANIFEST = default_rig_manifest()
BASE_SILHOUETTES = tuple(_RIG_MANIFEST.pose_silhouettes.values())
GESTURE_SILHOUETTES = tuple(_RIG_MANIFEST.gesture_silhouettes.values())
POSE_ATLAS_SILHOUETTES = tuple(
    canonical_view_id(yaw) for yaw in CANONICAL_YAWS
)
REQUIRED_SILHOUETTES = (
    BASE_SILHOUETTES + GESTURE_SILHOUETTES + POSE_ATLAS_SILHOUETTES
)
SUPPORTED_SILHOUETTES = REQUIRED_SILHOUETTES
GLANCE_MAKEUP_SILHOUETTES = tuple(
    f"cheek-{CHARACTER_EXPRESSION_ROLES['side_gaze']}{suffix}"
    for suffix in ("", "-half", "-closed")
)
BATCH2_MAKEUP_SILHOUETTES = tuple(
    f"cheek-{CHARACTER_EXPRESSION_ROLES[role]}{suffix}"
    for role in ("noticed", "happiness", "worry", "reminder")
    for suffix in ("", "-half", "-closed")
)
COMPLETE_EXPRESSION_MAKEUP_SILHOUETTES = (
    GLANCE_MAKEUP_SILHOUETTES + BATCH2_MAKEUP_SILHOUETTES
)
OPTIONAL_MAKEUP_SILHOUETTES = COMPLETE_EXPRESSION_MAKEUP_SILHOUETTES
OPTIONAL_EXPRESSION_APPEARANCE_SILHOUETTES = tuple(
    f"cheek-{CHARACTER_EXPRESSION_ROLES[role]}"
    for role in ("side_gaze", "noticed", "happiness", "worry", "reminder")
)
EXPRESSION_SILHOUETTE_ALIASES = frozendict({
    **_RIG_MANIFEST.pose_silhouettes,
    CHARACTER_EXPRESSION_ROLES["protection"]:
        _RIG_MANIFEST.pose_silhouettes["front"],
})
MAKEUP_CANVASES = frozendict({
    "full-body": (
        _RIG_MANIFEST.full_body_canvas.width,
        _RIG_MANIFEST.full_body_canvas.height,
    ),
    "half-body": (
        _RIG_MANIFEST.half_body_asset_canvas.width,
        _RIG_MANIFEST.half_body_asset_canvas.height,
    ),
})


def pose_keys(
    poses: object,
    silhouette_scope: object = None,
    source_bound_silhouettes: frozenset[str] = frozenset(),
) -> tuple[str, ...]:
    return required_pose_keys(
        poses,
        silhouette_scope,
        REQUIRED_SILHOUETTES,
        POSE_ATLAS_SILHOUETTES,
        SUPPORTED_SILHOUETTES,
        source_bound_silhouettes,
    )


def parse_pose_assets(
    poses: object,
    slots: frozenset[str],
    archive: zipfile.ZipFile,
    names: set[str],
    *,
    full_canvas: bool = False,
    silhouette_scope: object = None,
    source_bound_silhouettes: frozenset[str] = frozenset(),
) -> frozendict[str, tuple[AppearanceAsset, ...]]:
    silhouettes = pose_keys(
        poses,
        silhouette_scope,
        source_bound_silhouettes,
    )
    assert isinstance(poses, dict)
    parsed = {}
    for silhouette in silhouettes:
        entries = poses[silhouette]
        if not isinstance(entries, list) or not entries:
            raise OutfitPackError("Every silhouette requires assets.")
        assets = tuple(
            parse_appearance_asset(entry, slots, archive, names)
            for entry in entries
        )
        canvas = MAKEUP_CANVASES[
            "full-body"
            if silhouette in POSE_ATLAS_SILHOUETTES
            else "half-body"
        ]
        validate_pose_assets(
            assets,
            archive,
            canvas,
            require_visible=slots == GARMENT_SLOTS,
            full_canvas=full_canvas,
        )
        if len({asset.slot for asset in assets}) != len(assets):
            raise OutfitPackError("Duplicate slot in silhouette.")
        parsed[silhouette] = assets
    return frozendict(parsed)


def parse_partial_pose_assets(
    poses: object,
    slots: frozenset[str],
    archive: zipfile.ZipFile,
    names: set[str],
    *,
    full_canvas: bool = False,
) -> frozendict[str, tuple[AppearanceAsset, ...]]:
    """Parse a declaration that legitimately covers only some views."""

    if not isinstance(poses, dict):
        raise OutfitPackError(
            "Every declared mouth-state silhouette must use a supported view."
        )
    supported = REQUIRED_SILHOUETTES + OPTIONAL_MAKEUP_SILHOUETTES
    if not set(poses).issubset(supported):
        raise OutfitPackError("Mouth state declares an unsupported silhouette.")
    return _parse_optional_entries(
        poses, slots, archive, names, full_canvas=full_canvas,
    )


def _parse_optional_entries(
    poses: dict[str, object],
    slots: frozenset[str],
    archive: zipfile.ZipFile,
    names: set[str],
    *,
    full_canvas: bool,
    require_visible: bool = False,
) -> frozendict[str, tuple[AppearanceAsset, ...]]:
    parsed = {}
    for silhouette, entries in poses.items():
        if not isinstance(entries, list) or not entries:
            raise OutfitPackError("Every silhouette requires assets.")
        assets = tuple(
            parse_appearance_asset(entry, slots, archive, names)
            for entry in entries
        )
        canvas = MAKEUP_CANVASES[
            "full-body"
            if silhouette in POSE_ATLAS_SILHOUETTES
            else "half-body"
        ]
        validate_pose_assets(
            assets,
            archive,
            canvas,
            require_visible=require_visible,
            full_canvas=full_canvas,
        )
        if len({asset.slot for asset in assets}) != len(assets):
            raise OutfitPackError("Duplicate slot in silhouette.")
        parsed[silhouette] = assets
    return frozendict(parsed)


def parse_makeup_pose_assets(
    poses: object,
    slots: frozenset[str],
    archive: zipfile.ZipFile,
    names: set[str],
    *,
    full_canvas: bool = False,
) -> frozendict[str, tuple[AppearanceAsset, ...]]:
    """Parse the required views plus optional complete-expression makeup."""

    if not isinstance(poses, dict):
        raise OutfitPackError("Every required silhouette must be declared.")
    optional = set(poses).intersection(OPTIONAL_MAKEUP_SILHOUETTES)
    required = {key: value for key, value in poses.items() if key not in optional}
    parsed = dict(
        parse_pose_assets(
            required, slots, archive, names, full_canvas=full_canvas,
        )
    )
    parsed.update(_parse_optional_entries(
        {key: poses[key] for key in optional},
        slots,
        archive,
        names,
        full_canvas=full_canvas,
    ))
    return frozendict(parsed)


def parse_appearance_pose_assets(
    poses: object,
    slots: frozenset[str],
    archive: zipfile.ZipFile,
    names: set[str],
    *,
    silhouette_scope: object = None,
    source_bound_silhouettes: frozenset[str] = frozenset(),
) -> frozendict[str, tuple[AppearanceAsset, ...]]:
    """Parse required views plus optional exact complete-expression views."""

    if silhouette_scope is not None:
        return parse_pose_assets(
            poses,
            slots,
            archive,
            names,
            silhouette_scope=silhouette_scope,
            source_bound_silhouettes=source_bound_silhouettes,
        )
    if not isinstance(poses, dict):
        raise OutfitPackError("Every required silhouette must be declared.")
    optional = set(poses).intersection(
        OPTIONAL_EXPRESSION_APPEARANCE_SILHOUETTES
    )
    required = {key: value for key, value in poses.items() if key not in optional}
    parsed = dict(parse_pose_assets(
        required,
        slots,
        archive,
        names,
        source_bound_silhouettes=source_bound_silhouettes,
    ))
    parsed.update(_parse_optional_entries(
        {key: poses[key] for key in optional},
        slots,
        archive,
        names,
        full_canvas=False,
        require_visible=slots == GARMENT_SLOTS,
    ))
    return frozendict(parsed)
