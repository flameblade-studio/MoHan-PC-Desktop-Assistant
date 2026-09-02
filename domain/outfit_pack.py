from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy import re
lazy import struct
lazy import zipfile
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import NamedTemporaryFile

lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id
# Eager on purpose: these names are re-exported (``from domain.outfit_pack import
# OutfitPackError`` is used across the layers) and a lazy import of a lazily
# imported name hands the caller the unresolved proxy instead of the class.
from domain.outfit_pack_assets import (
    ASSET_PATH,
    MANIFEST,
    MAX_IMAGE_DIMENSION,
    IncompatibleBodyProfileError,
    OutfitPackError,
    _dimensions,
    _safe_member,
)

FORMAT = "mohan-outfit-pack"
VERSION = 2
BODY_PROFILE_ID = "mohan-body-v2"
BODY_PROFILE_VERSION = 2
AUTHORING_TEMPLATE = "mohan-official-poses"
AUTHORING_VERSION = 2
BASE_SILHOUETTES = ("cheek-rest", "left-neutral", "front-crossed")
GESTURE_SILHOUETTES = ("front-mock-scold", "front-mock-hit", "front-eureka", "front-exasperated")
POSE_ATLAS_SILHOUETTES = tuple(canonical_view_id(yaw) for yaw in CANONICAL_YAWS)
REQUIRED_SILHOUETTES = BASE_SILHOUETTES + GESTURE_SILHOUETTES + POSE_ATLAS_SILHOUETTES
SUPPORTED_SILHOUETTES = REQUIRED_SILHOUETTES
EXPRESSION_SILHOUETTE_ALIASES = frozendict({
    "cheek": "cheek-rest", "lean": "left-neutral", "front": "front-crossed", "protective_front": "front-crossed",
})
OFFICIAL_BODY_SPEC = frozendict({
    "adult": True, "height_cm": 168, "weight_kg": 54, "bust_cm": 86, "underbust_cm": 71, "waist_cm": 62, "hips_cm": 90,
})
BODY_REGIONS = ("neck", "shoulder-left", "shoulder-right", "arm-left", "arm-right", "torso", "leg-left", "leg-right")
VISIBILITY = frozenset({"visible", "covered"})
FABRIC_BEHAVIORS = frozenset({"structured", "draped", "stretch", "loose"})
GARMENT_SLOTS = frozenset({
    "bodice", "outerwear", "sleeve-left", "sleeve-right", "skirt", "trousers",
    "legwear-left", "legwear-right", "swimwear", "garment-occluder",
})
HAIR_SLOTS = frozenset({"back", "front", "side-left", "side-right", "bangs", "bun", "ponytail"})
REQUIRED_HAIR_SLOTS = frozenset({"back", "front"})
HEAD_ATTACHMENTS = frozenset({"crown", "temple-left", "temple-right", "ear-left", "ear-right", "back-head"})
ACCESSORY_KINDS = ("weapon", "handheld", "jewelry", "foreground-effect")
ACCESSORY_ASSET_SLOTS = frozendict({
    "weapon": frozenset({"weapon", "sheath"}), "handheld": frozenset({"handheld"}),
    "jewelry": frozenset({"jewelry"}), "foreground-effect": frozenset({"foreground-effect"}),
})
# Makeup is the one category that legitimately paints the face: three full-canvas
# RGBA layers per silhouette, composited above the bare skin and below hair,
# headwear and garments, clipped to the per-silhouette safe region
# (assets/makeup-safe-regions.json) and scaled by the user's intensity.
MAKEUP_SLOTS = frozenset({"eyes", "cheeks", "lips"})
MAKEUP_CANVASES = frozendict({"full-body": (1024, 1536), "half-body": (1254, 1254)})
BUILTIN_MAKEUP_PACK_ID = "mohan.makeup.builtin"
BUILTIN_MAKEUP_ITEM_ID = "mohan-signature"
BUILTIN_MAKEUP_VARIANTS = ("classic", "light")
OFFICIAL_PACK_ROOT = Path(__file__).resolve().parents[1] / "assets" / "makeup"
OPTIONAL_ENSEMBLE_CATEGORIES = frozenset({"makeup"})
OPTIONAL_MANIFEST_KEYS = frozenset({"makeup"})
WEAPON_PLACEMENTS = frozenset({"back", "waist-left", "waist-right", "hand-left", "hand-right"})
HANDHELD_PLACEMENTS = frozenset({"hand-left", "hand-right"})
WEAPON_ATTACHMENTS = frozenset({"back-harness", "waist-sheath", "left-grip", "right-grip"})
FACE_MASKS = frozenset({"none", "hairline-safe", "bangs-safe", "side-locks-safe"})
HAND_RULES = frozenset({"behind-hands", "front-of-hands"})
GARMENT_RULES = frozenset({"behind-collar", "front-of-collar"})
HEADWEAR_MASKS = frozenset({"crown-safe", "temple-safe", "ear-safe", "back-head-safe"})
LANGUAGES = frozenset({"zh-TW", "zh-CN", "en", "ja-JP"})
SELECTION_CATEGORIES = ("garment", "hairstyle", "headwear", "makeup", *ACCESSORY_KINDS)
THERMAL_BANDS = frozenset({"hot", "warm", "mild", "cool", "cold"})
WEATHER_TAGS = frozenset({"clear", "cloudy", "rain", "storm", "snow", "windy", "indoor"})
MOOD_TAGS = frozenset({"calm", "cheerful", "affectionate", "reserved", "upset", "focused"})
OCCASION_TAGS = frozenset({"everyday", "work", "formal", "holiday", "birthday", "christmas", "valentines"})
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_MEMBERS = 2048
MIN_ANCHOR_COORDINATE = -4096
MAX_ANCHOR_COORDINATE = 4096
MIN_Z_ORDER = -100
MAX_Z_ORDER = 100
MAX_NAME_LENGTH = 80
MAX_AUTHOR_LENGTH = 120
ANCHOR_DIMENSIONS = 2
IDENTIFIER = re.compile(r"[a-z0-9](?:[a-z0-9.-]{0,62}[a-z0-9])?\Z")
SEMVER = re.compile(r"\d+\.\d+\.\d+\Z")
APP_RANGE = re.compile(r">=\d+\.\d+\.\d+,<\d+\.\d+\.\d+\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
LICENSE = re.compile(r"[A-Za-z0-9 .()+-]{1,120}\Z")
PROTECTED_TERMS = frozenset({
    "face", "eye", "eyes", "mouth", "lip", "skin", "identity", "skull",
    "body-skin", "core-body", "body-contour", "bust-geometry", "torso-geometry",
})
# Makeup legitimately names eyes and lips; every other identity term stays banned.
MAKEUP_PATH_TERMS = PROTECTED_TERMS - frozenset({"eye", "eyes", "lip"})
MANIFEST_KEYS = frozenset({
    "format", "version", "id", "pack_version", "app_range", "display_names", "compatible_body_profile",
    "source", "authoring", "looks", "hairstyles", "headwear", "accessories", "ensembles",
})


@dataclass(frozen=True, slots=True)
class AppearanceAsset:
    slot: str
    path: str
    sha256: str
    width: int
    height: int
    anchor_x: int
    anchor_y: int
    z_order: int


@dataclass(frozen=True, slots=True)
class AppearanceVariant:
    variant_id: str
    display_names: frozendict[str, str]
    poses: frozendict[str, tuple[AppearanceAsset, ...]]
    fabric_behavior: str | None = None
    body_visibility: frozendict[str, frozendict[str, str]] | None = None
    face_masks: frozendict[str, str] | None = None
    hand_rules: frozendict[str, str] | None = None
    garment_rules: frozendict[str, str] | None = None
    placements: frozendict[str, str] | None = None
    hair_rules: frozendict[str, str] | None = None
    attachment_contracts: frozendict[str, str] | None = None
    intensity: float = 1.0


@dataclass(frozen=True, slots=True)
class AppearanceItem:
    category: str
    item_id: str
    display_names: frozendict[str, str]
    variants: tuple[AppearanceVariant, ...]
    attachment_point: str | None = None
    safe_mask: str | None = None


@dataclass(frozen=True, slots=True)
class OutfitPack:
    pack_id: str
    pack_version: str
    app_range: str
    display_names: frozendict[str, str]
    source_kind: str
    author: str
    license_name: str
    compatible_body_profile: str
    items: tuple[AppearanceItem, ...]
    ensembles: tuple[AppearanceEnsemble, ...]

    @property
    def looks(self) -> tuple[AppearanceItem, ...]:
        return tuple(item for item in self.items if item.category == "garment")


@dataclass(frozen=True, slots=True)
class InstalledSelection:
    category: str
    pack_id: str
    item_id: str
    variant_id: str
    pack_display_names: frozendict[str, str]
    item_display_names: frozendict[str, str]
    variant_display_names: frozendict[str, str]


InstalledVariant = InstalledSelection


@dataclass(frozen=True, slots=True)
class EnsembleSelection:
    category: str
    item_id: str | None
    variant_id: str | None


@dataclass(frozen=True, slots=True)
class AutonomousStyleProfile:
    thermal_bands: frozenset[str]
    weather: frozenset[str]
    moods: frozenset[str]
    occasions: frozenset[str]
    priority: int


@dataclass(frozen=True, slots=True)
class AppearanceEnsemble:
    ensemble_id: str
    display_names: frozendict[str, str]
    selections: tuple[EnsembleSelection, ...]
    autonomous_profile: AutonomousStyleProfile


@dataclass(frozen=True, slots=True)
class InstalledEnsemble:
    pack_id: str
    ensemble_id: str
    pack_display_names: frozendict[str, str]
    ensemble_display_names: frozendict[str, str]
    selections: tuple[EnsembleSelection, ...]
    autonomous_profile: AutonomousStyleProfile


@dataclass(frozen=True, slots=True)
class RemovalResult:
    pack_id: str
    removed_path: Path


@dataclass(frozen=True, slots=True)
class SelectionResolution:
    category: str
    status: str
    requested_pack_id: str
    requested_item_id: str
    requested_variant_id: str
    effective_pack_id: str
    effective_item_id: str
    effective_variant_id: str


@dataclass(frozen=True, slots=True)
class PoseAppearanceResolution:
    requested_view_id: str
    resolved_silhouette: str | None
    assets: tuple[AppearanceAsset, ...]
    exact_pose_atlas_match: bool


def official_pose_template() -> frozendict[str, object]:
    return frozendict({
        "template": AUTHORING_TEMPLATE, "version": AUTHORING_VERSION,
        "body_profile_id": BODY_PROFILE_ID, "body_profile_version": BODY_PROFILE_VERSION,
        "required_silhouettes": REQUIRED_SILHOUETTES,
        "expression_aliases": EXPRESSION_SILHOUETTE_ALIASES,
        "body_regions": BODY_REGIONS, "hair_slots": tuple(sorted(HAIR_SLOTS)),
        "head_attachments": tuple(sorted(HEAD_ATTACHMENTS)),
    })


def resolve_variant_for_view(
    variant: AppearanceVariant,
    view_id: str,
) -> PoseAppearanceResolution:
    """Resolve the exact authored view without changing the selected outfit."""

    if view_id not in REQUIRED_SILHOUETTES:
        raise OutfitPackError("Unknown appearance view.")
    try:
        assets = variant.poses[view_id]
    except KeyError:
        raise OutfitPackError("The selected outfit is missing a required view.") from None
    return PoseAppearanceResolution(
        view_id,
        view_id,
        assets,
        view_id in POSE_ATLAS_SILHOUETTES,
    )


def _names(value: object) -> frozendict[str, str]:
    if not isinstance(value, dict) or set(value) != LANGUAGES or any(not isinstance(text, str) for text in value.values()):
        raise OutfitPackError("All four localized names are required.")
    names = {language: text.strip() for language, text in value.items()}
    if any(not text or len(text) > MAX_NAME_LENGTH for text in names.values()):
        raise OutfitPackError("Invalid localized name.")
    return frozendict(names)


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise OutfitPackError(f"Invalid {label} identifier.")
    return value


def _author(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > MAX_AUTHOR_LENGTH:
        raise OutfitPackError("Invalid author declaration.")
    return value.strip()


def _asset(entry: object, allowed_slots: frozenset[str], archive: zipfile.ZipFile, names: set[str]) -> AppearanceAsset:
    required = {"slot", "path", "sha256", "width", "height", "anchor", "z_order"}
    if not isinstance(entry, dict) or set(entry) != required:
        raise OutfitPackError("Invalid asset declaration.")
    slot, path = entry["slot"], entry["path"]
    if not isinstance(slot, str) or slot not in allowed_slots or not isinstance(path, str) or not ASSET_PATH.fullmatch(path) or path not in names:
        raise OutfitPackError("Unknown slot or asset path.")
    screened, terms = (path, MAKEUP_PATH_TERMS) if slot in MAKEUP_SLOTS else (f"{slot}/{path}", PROTECTED_TERMS)
    if any(term in screened.lower() for term in terms):
        raise OutfitPackError("Core identity, skin and geometry cannot be replaced.")
    anchor = entry["anchor"]
    values = (entry["width"], entry["height"], entry["z_order"])
    if not isinstance(entry["sha256"], str) or not SHA256.fullmatch(entry["sha256"]) or not isinstance(anchor, list) or len(anchor) != ANCHOR_DIMENSIONS:
        raise OutfitPackError("Invalid hash or anchor.")
    if any(not isinstance(value, int) or isinstance(value, bool) for value in (*values, *anchor)):
        raise OutfitPackError("Invalid asset geometry.")
    width, height, z_order = values
    if not (1 <= width <= MAX_IMAGE_DIMENSION and 1 <= height <= MAX_IMAGE_DIMENSION and MIN_ANCHOR_COORDINATE <= anchor[0] <= MAX_ANCHOR_COORDINATE and MIN_ANCHOR_COORDINATE <= anchor[1] <= MAX_ANCHOR_COORDINATE and MIN_Z_ORDER <= z_order <= MAX_Z_ORDER):
        raise OutfitPackError("Asset geometry is outside the allowed range.")
    data = archive.read(path)
    if hashlib.sha256(data).hexdigest() != entry["sha256"] or _dimensions(data, Path(path).suffix) != (width, height):
        raise OutfitPackError("Asset integrity check failed.")
    return AppearanceAsset(slot, path, entry["sha256"], width, height, anchor[0], anchor[1], z_order)


def _pose_keys(poses: object) -> tuple[str, ...]:
    if not isinstance(poses, dict):
        raise OutfitPackError("Every required silhouette must be declared.")
    keys = set(poses)
    required = set(REQUIRED_SILHOUETTES)
    if keys != required:
        missing = sorted(required - keys)
        unexpected = sorted(keys - required)
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected: {', '.join(unexpected)}")
        raise OutfitPackError(
            "Every appearance variant requires the complete v2 view set ("
            + "; ".join(details)
            + ")."
        )
    return SUPPORTED_SILHOUETTES


def _pose_assets(poses: object, slots: frozenset[str], archive: zipfile.ZipFile, names: set[str]) -> frozendict[str, tuple[AppearanceAsset, ...]]:
    silhouettes = _pose_keys(poses)
    assert isinstance(poses, dict)
    parsed = {}
    for silhouette in silhouettes:
        entries = poses[silhouette]
        if not isinstance(entries, list) or not entries:
            raise OutfitPackError("Every silhouette requires assets.")
        assets = tuple(_asset(entry, slots, archive, names) for entry in entries)
        if len({asset.slot for asset in assets}) != len(assets):
            raise OutfitPackError("Duplicate slot in silhouette.")
        parsed[silhouette] = assets
    return frozendict(parsed)


def _variant_base(value: object, extra: set[str]) -> tuple[str, frozendict[str, str]]:
    if not isinstance(value, dict) or set(value) != {"id", "display_names", "poses", *extra}:
        raise OutfitPackError("Invalid appearance variant.")
    return _identifier(value["id"], "variant"), _names(value["display_names"])


def _garment_variant(value: object, archive: zipfile.ZipFile, names: set[str]) -> AppearanceVariant:
    variant_id, display = _variant_base(value, {"fabric_behavior", "body_visibility"})
    behavior, visibility = value["fabric_behavior"], value["body_visibility"]
    poses = _pose_assets(value["poses"], GARMENT_SLOTS, archive, names)
    if behavior not in FABRIC_BEHAVIORS or not isinstance(visibility, dict) or set(visibility) != set(poses):
        raise OutfitPackError("Invalid garment behavior or visibility.")
    parsed_visibility = {}
    for silhouette, regions in visibility.items():
        if not isinstance(regions, dict) or set(regions) != set(BODY_REGIONS) or any(state not in VISIBILITY for state in regions.values()):
            raise OutfitPackError("Invalid official body visibility.")
        parsed_visibility[silhouette] = frozendict(regions)
    return AppearanceVariant(variant_id, display, poses, behavior, frozendict(parsed_visibility))


def _hair_variant(value: object, archive: zipfile.ZipFile, names: set[str]) -> AppearanceVariant:
    variant_id, display = _variant_base(value, {"face_occlusion_masks", "hand_occlusion", "garment_occlusion"})
    poses = _pose_assets(value["poses"], HAIR_SLOTS, archive, names)
    slot_sets = [{asset.slot for asset in assets} for assets in poses.values()]
    if any(not slots.issuperset(REQUIRED_HAIR_SLOTS) for slots in slot_sets) or any(slots != slot_sets[0] for slots in slot_sets[1:]):
        raise OutfitPackError("Hair slots must be complete and consistent across silhouettes.")
    maps = []
    for field, allowed in (("face_occlusion_masks", FACE_MASKS), ("hand_occlusion", HAND_RULES), ("garment_occlusion", GARMENT_RULES)):
        mapping = value[field]
        if not isinstance(mapping, dict) or set(mapping) != set(poses) or any(rule not in allowed for rule in mapping.values()):
            raise OutfitPackError("Invalid hair occlusion contract.")
        maps.append(frozendict(mapping))
    return AppearanceVariant(variant_id, display, poses, face_masks=maps[0], hand_rules=maps[1], garment_rules=maps[2])


def _simple_variant(value: object, slots: frozenset[str], archive: zipfile.ZipFile, names: set[str]) -> AppearanceVariant:
    variant_id, display = _variant_base(value, set())
    return AppearanceVariant(variant_id, display, _pose_assets(value["poses"], slots, archive, names))


def _rule_map(
    value: object,
    allowed: frozenset[str],
    label: str,
    silhouettes: frozenset[str],
) -> frozendict[str, str]:
    if not isinstance(value, dict) or set(value) != set(silhouettes) or any(rule not in allowed for rule in value.values()):
        raise OutfitPackError(f"Invalid {label} contract.")
    return frozendict(value)


def _weapon_variant(value: object, archive: zipfile.ZipFile, names: set[str]) -> AppearanceVariant:
    extra = {"placement", "attachment_contract", "hand_occlusion", "garment_occlusion", "hair_occlusion"}
    variant_id, display = _variant_base(value, extra)
    poses = _pose_assets(value["poses"], ACCESSORY_ASSET_SLOTS["weapon"], archive, names)
    silhouettes = frozenset(poses)
    placements = _rule_map(value["placement"], WEAPON_PLACEMENTS, "weapon placement", silhouettes)
    attachments = _rule_map(value["attachment_contract"], WEAPON_ATTACHMENTS, "weapon attachment", silhouettes)
    compatible = {
        "back": "back-harness",
        "waist-left": "waist-sheath",
        "waist-right": "waist-sheath",
        "hand-left": "left-grip",
        "hand-right": "right-grip",
    }
    if any(attachments[silhouette] != compatible[placement] for silhouette, placement in placements.items()):
        raise OutfitPackError("Weapon placement and attachment contract disagree.")
    return AppearanceVariant(
        variant_id,
        display,
        poses,
        placements=placements,
        hand_rules=_rule_map(value["hand_occlusion"], HAND_RULES, "weapon hand occlusion", silhouettes),
        garment_rules=_rule_map(value["garment_occlusion"], GARMENT_RULES, "weapon garment occlusion", silhouettes),
        hair_rules=_rule_map(value["hair_occlusion"], frozenset({"behind-hair", "front-of-hair"}), "weapon hair occlusion", silhouettes),
        attachment_contracts=attachments,
    )


def _handheld_variant(value: object, archive: zipfile.ZipFile, names: set[str]) -> AppearanceVariant:
    variant_id, display = _variant_base(value, {"placement", "hand_occlusion"})
    poses = _pose_assets(value["poses"], ACCESSORY_ASSET_SLOTS["handheld"], archive, names)
    silhouettes = frozenset(poses)
    return AppearanceVariant(
        variant_id,
        display,
        poses,
        placements=_rule_map(value["placement"], HANDHELD_PLACEMENTS, "handheld placement", silhouettes),
        hand_rules=_rule_map(value["hand_occlusion"], HAND_RULES, "handheld hand occlusion", silhouettes),
    )


def _makeup_variant(value: object, archive: zipfile.ZipFile, names: set[str]) -> AppearanceVariant:
    """Three full-canvas registered layers per silhouette plus an optional authored intensity."""
    variant_id, display = _variant_base(value, {"intensity"} if "intensity" in value else set())
    intensity = value.get("intensity", 1.0)
    if isinstance(intensity, bool) or not isinstance(intensity, (int, float)) or not 0.0 <= intensity <= 1.0:
        raise OutfitPackError("Makeup intensity must be a number between 0 and 1.")
    poses = _pose_assets(value["poses"], MAKEUP_SLOTS, archive, names)
    for silhouette, assets in poses.items():
        canvas = MAKEUP_CANVASES["full-body" if silhouette in POSE_ATLAS_SILHOUETTES else "half-body"]
        if {asset.slot for asset in assets} != MAKEUP_SLOTS:
            raise OutfitPackError(f"Makeup silhouette {silhouette!r} requires exactly the eyes, cheeks and lips layers.")
        if any((asset.width, asset.height, asset.anchor_x, asset.anchor_y) != (*canvas, 0, 0) for asset in assets):
            raise OutfitPackError(f"Makeup layers for {silhouette!r} must cover the full {canvas[0]}x{canvas[1]} canvas at anchor 0,0.")
    return AppearanceVariant(variant_id, display, poses, intensity=float(intensity))


def _item(value: object, category: str, archive: zipfile.ZipFile, names: set[str]) -> AppearanceItem:
    extras = {"attachment_point", "safe_mask"} if category == "headwear" else set()
    if category == "accessory":
        extras = {"accessory_kind"}
    if not isinstance(value, dict) or set(value) != {"id", "display_names", "variants", *extras}:
        raise OutfitPackError("Invalid appearance item.")
    actual_category = value["accessory_kind"] if category == "accessory" else category
    if actual_category not in SELECTION_CATEGORIES:
        raise OutfitPackError("Invalid accessory kind.")
    variants = value["variants"]
    if not isinstance(variants, list) or not variants:
        raise OutfitPackError("Appearance item requires variants.")
    parser = {
        "garment": _garment_variant,
        "hairstyle": _hair_variant,
        "headwear": lambda item, arc, member_names: _simple_variant(item, frozenset({"headwear"}), arc, member_names),
        "makeup": _makeup_variant,
        "weapon": _weapon_variant,
        "handheld": _handheld_variant,
        "jewelry": lambda item, arc, member_names: _simple_variant(item, ACCESSORY_ASSET_SLOTS["jewelry"], arc, member_names),
        "foreground-effect": lambda item, arc, member_names: _simple_variant(item, ACCESSORY_ASSET_SLOTS["foreground-effect"], arc, member_names),
    }[actual_category]
    parsed = tuple(parser(variant, archive, names) for variant in variants)
    if len({variant.variant_id for variant in parsed}) != len(parsed):
        raise OutfitPackError("Duplicate variant identifier.")
    attachment = value.get("attachment_point")
    safe_mask = value.get("safe_mask")
    if category == "headwear" and (attachment not in HEAD_ATTACHMENTS or safe_mask not in HEADWEAR_MASKS):
        raise OutfitPackError("Invalid headwear attachment or safe mask.")
    return AppearanceItem(actual_category, _identifier(value["id"], "item"), _names(value["display_names"]), parsed, attachment, safe_mask)


def _available_variants(items: list[AppearanceItem]) -> set[tuple[str, str, str]]:
    return {
        *((item.category, item.item_id, variant.variant_id) for variant in item.variants)
        for item in items
    }


def _ensemble_selection(
    category: str,
    selection: object,
    available: set[tuple[str, str, str]],
) -> EnsembleSelection:
    if selection is None:
        if category not in {"headwear", "makeup", *ACCESSORY_KINDS}:
            raise OutfitPackError("Garment and hairstyle cannot be none.")
        return EnsembleSelection(category, None, None)
    if not isinstance(selection, dict) or set(selection) != {"item_id", "variant_id"}:
        raise OutfitPackError("Invalid ensemble selection.")
    identity = (
        category,
        _identifier(selection["item_id"], "ensemble item"),
        _identifier(selection["variant_id"], "ensemble variant"),
    )
    if identity not in available:
        raise OutfitPackError("Ensemble must reference an item in the same pack.")
    return EnsembleSelection(*identity)


def _ensemble(
    entry: object,
    available: set[tuple[str, str, str]],
) -> AppearanceEnsemble:
    if not isinstance(entry, dict) or set(entry) != {"id", "display_names", "selections", "autonomous_profile"}:
        raise OutfitPackError("Invalid ensemble declaration.")
    selections = entry["selections"]
    required = set(SELECTION_CATEGORIES) - OPTIONAL_ENSEMBLE_CATEGORIES
    # An ensemble that stays silent about makeup leaves the user's makeup alone;
    # an explicit ``null`` means a bare face.
    if not isinstance(selections, dict) or not required <= set(selections) <= set(SELECTION_CATEGORIES):
        raise OutfitPackError("Ensemble must declare every appearance category.")
    typed = tuple(
        _ensemble_selection(category, selections[category], available)
        for category in SELECTION_CATEGORIES
        if category in selections
    )
    profile = _autonomous_profile(entry["autonomous_profile"])
    return AppearanceEnsemble(
        _identifier(entry["id"], "ensemble"),
        _names(entry["display_names"]),
        typed,
        profile,
    )


def _autonomous_profile(value: object) -> AutonomousStyleProfile:
    keys = {"thermal_bands", "weather", "moods", "occasions", "priority"}
    if not isinstance(value, dict) or set(value) != keys:
        raise OutfitPackError("Invalid autonomous outfit profile.")

    def tags(name: str, allowed: frozenset[str]) -> frozenset[str]:
        items = value[name]
        if not isinstance(items, list) or not items or any(
            not isinstance(item, str) for item in items
        ):
            raise OutfitPackError("Invalid autonomous outfit tags.")
        result = frozenset(items)
        if len(result) != len(items) or not result.issubset(allowed):
            raise OutfitPackError("Invalid autonomous outfit tags.")
        return result

    priority = value["priority"]
    if not isinstance(priority, int) or isinstance(priority, bool) or not MIN_Z_ORDER <= priority <= MAX_Z_ORDER:
        raise OutfitPackError("Invalid autonomous outfit priority.")
    return AutonomousStyleProfile(
        tags("thermal_bands", THERMAL_BANDS),
        tags("weather", WEATHER_TAGS),
        tags("moods", MOOD_TAGS),
        tags("occasions", OCCASION_TAGS),
        priority,
    )


def _ensembles(value: object, items: list[AppearanceItem]) -> tuple[AppearanceEnsemble, ...]:
    if not isinstance(value, list):
        raise OutfitPackError("Ensembles must be a list.")
    available = _available_variants(items)
    parsed = tuple(_ensemble(entry, available) for entry in value)
    if len({ensemble.ensemble_id for ensemble in parsed}) != len(parsed):
        raise OutfitPackError("Duplicate ensemble identifier.")
    return parsed


def _archive_member_names(archive: zipfile.ZipFile) -> set[str]:
    infos = archive.infolist()
    names = {info.filename for info in infos}
    if not infos or len(infos) > MAX_MEMBERS or len(names) != len(infos) or MANIFEST not in names:
        raise OutfitPackError("Invalid archive members.")
    for info in infos:
        _safe_member(info)
    if sum(info.file_size for info in infos) > MAX_TOTAL_BYTES:
        raise OutfitPackError("Archive expands beyond the allowed size.")
    return names


def _manifest_payload(archive: zipfile.ZipFile) -> dict:
    manifest = json.loads(archive.read(MANIFEST).decode("utf-8"))
    if not isinstance(manifest, dict) or not MANIFEST_KEYS <= set(manifest) <= MANIFEST_KEYS | OPTIONAL_MANIFEST_KEYS:
        raise OutfitPackError("Unsupported appearance manifest.")
    if manifest["format"] != FORMAT or manifest["version"] != VERSION:
        raise OutfitPackError("Unsupported appearance manifest.")
    expected_profile = {"id": BODY_PROFILE_ID, "version": BODY_PROFILE_VERSION}
    if manifest["compatible_body_profile"] != expected_profile:
        raise IncompatibleBodyProfileError(f"Pack body profile {manifest['compatible_body_profile']!r} is not the current {expected_profile!r}.")
    if manifest["authoring"] != {"template": AUTHORING_TEMPLATE, "version": AUTHORING_VERSION}:
        raise OutfitPackError("Unsupported authoring template.")
    return manifest


def _source_declaration(manifest: dict) -> tuple[str, str, str]:
    source = manifest["source"]
    if not isinstance(source, dict) or set(source) != {"kind", "author", "license", "reference_included"}:
        raise OutfitPackError("Invalid source declaration.")
    if source["kind"] not in {"original", "concept", "reference-derived"}:
        raise OutfitPackError("Invalid source declaration.")
    if source["reference_included"] is not False:
        raise OutfitPackError("Invalid source declaration.")
    if not isinstance(source["license"], str) or not LICENSE.fullmatch(source["license"]):
        raise OutfitPackError("Invalid source declaration.")
    return source["kind"], _author(source["author"]), source["license"]


def _appearance_items(
    manifest: dict,
    archive: zipfile.ZipFile,
    names: set[str],
) -> list[AppearanceItem]:
    groups = (
        ("looks", "garment"), ("hairstyles", "hairstyle"), ("headwear", "headwear"),
        ("makeup", "makeup"), ("accessories", "accessory"),
    )
    items: list[AppearanceItem] = []
    for key, category in groups:
        entries = manifest.get(key, []) if key in OPTIONAL_MANIFEST_KEYS else manifest[key]
        if not isinstance(entries, list):
            raise OutfitPackError("Appearance collections must be lists.")
        parsed = [_item(entry, category, archive, names) for entry in entries]
        if len({item.item_id for item in parsed}) != len(parsed):
            raise OutfitPackError("Duplicate item identifier in category.")
        items.extend(parsed)
    if not items:
        raise OutfitPackError("An appearance pack cannot be empty.")
    return items


def _declared_asset_paths(items: list[AppearanceItem]) -> list[str]:
    return [
        *(
            asset.path
            for item in items
            for variant in item.variants
            for assets in variant.poses.values()
            for asset in assets
        )
    ]


def _validate_declared_assets(items: list[AppearanceItem], names: set[str]) -> None:
    paths = _declared_asset_paths(items)
    if len(paths) != len(set(paths)) or names != {MANIFEST, *paths}:
        raise OutfitPackError("Every asset must be declared exactly once.")


def _pack_version(manifest: dict) -> tuple[str, str]:
    pack_version = manifest["pack_version"]
    app_range = manifest["app_range"]
    if not isinstance(pack_version, str) or not SEMVER.fullmatch(pack_version):
        raise OutfitPackError("Invalid version or app range.")
    if not isinstance(app_range, str) or not APP_RANGE.fullmatch(app_range):
        raise OutfitPackError("Invalid version or app range.")
    return pack_version, app_range


def _parse_outfit_pack(
    archive: zipfile.ZipFile,
    names: set[str],
) -> OutfitPack:
    manifest = _manifest_payload(archive)
    source_kind, author, license_name = _source_declaration(manifest)
    items = _appearance_items(manifest, archive, names)
    ensembles = _ensembles(manifest["ensembles"], items)
    _validate_declared_assets(items, names)
    pack_id = _identifier(manifest["id"], "pack")
    pack_version, app_range = _pack_version(manifest)
    return OutfitPack(
        pack_id, pack_version, app_range, _names(manifest["display_names"]), source_kind, author, license_name,
        BODY_PROFILE_ID, tuple(items), ensembles,
    )


def inspect_outfit_pack(source: Path) -> OutfitPack:
    path = Path(source)
    if not path.is_file() or path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise OutfitPackError("Archive size is invalid.")
    try:
        with zipfile.ZipFile(path) as archive:
            names = _archive_member_names(archive)
            return _parse_outfit_pack(archive, names)
    except (OSError, zipfile.BadZipFile, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, struct.error, IndexError):
        raise OutfitPackError("Invalid appearance archive.") from None


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(payload, temporary, ensure_ascii=False, sort_keys=True)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _inspect_installed(path: Path) -> OutfitPack | None:
    """Parse an installed archive; ``None`` marks a pack authored for another body-profile generation."""
    try:
        return inspect_outfit_pack(path)
    except IncompatibleBodyProfileError:
        return None


def _installed_pack_paths(store: Path) -> tuple[Path, ...]:
    """User-installed packs first, then the official packs shipped with the app (never removable)."""
    paths = []
    for root in (Path(store) / "packages", OFFICIAL_PACK_ROOT):
        paths.extend(sorted(root.glob("*.mohan-outfit")) if root.is_dir() else ())
    return tuple(paths)


def installed_pack_path(store: Path, pack_id: str) -> Path:
    """Locate one installed or official pack archive by id; fails closed on an unknown id."""
    path = next((path for path in _installed_pack_paths(store) if path.stem == pack_id), None)
    if path is None:
        raise OutfitPackError("The selected appearance pack is not installed.")
    return path


def list_installed_outfits(store: Path) -> tuple[OutfitPack, ...]:
    return tuple(pack for pack in map(_inspect_installed, _installed_pack_paths(store)) if pack is not None)


def list_stale_body_profile_packs(store: Path) -> tuple[str, ...]:
    """Ids of installed packs made for another body-profile generation; they are listed, never rendered."""
    return tuple(path.stem for path in _installed_pack_paths(store) if _inspect_installed(path) is None)


def list_installed_selections(store: Path, category: str | None = None) -> tuple[InstalledSelection, ...]:
    if category is not None and category not in SELECTION_CATEGORIES:
        raise OutfitPackError("Unknown selection category.")
    return tuple(
        InstalledSelection(item.category, pack.pack_id, item.item_id, variant.variant_id, pack.display_names, item.display_names, variant.display_names)
        for pack in list_installed_outfits(store) for item in pack.items for variant in item.variants
        if category is None or item.category == category
    )


def list_installed_ensembles(store: Path) -> tuple[InstalledEnsemble, ...]:
    return tuple(
        InstalledEnsemble(pack.pack_id, ensemble.ensemble_id, pack.display_names, ensemble.display_names, ensemble.selections, ensemble.autonomous_profile)
        for pack in list_installed_outfits(store) for ensemble in pack.ensembles
    )


def list_installed_variants(store: Path) -> tuple[InstalledSelection, ...]:
    return list_installed_selections(store, "garment")


def install_outfit_pack(source: Path, store: Path) -> OutfitPack:
    pack = inspect_outfit_pack(source)
    if pack.pack_id == BUILTIN_MAKEUP_PACK_ID:
        raise OutfitPackError("The built-in makeup pack id is reserved for the official asset.")
    packages = Path(store) / "packages"
    packages.mkdir(parents=True, exist_ok=True)
    destination = packages / f"{pack.pack_id}.mohan-outfit"
    with NamedTemporaryFile("wb", dir=packages, delete=False) as temporary:
        temporary.write(Path(source).read_bytes())
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    return pack


def apply_appearance_selection(store: Path, selection: InstalledSelection) -> None:
    installed = {(item.category, item.pack_id, item.item_id, item.variant_id) for item in list_installed_selections(store)}
    identity = (selection.category, selection.pack_id, selection.item_id, selection.variant_id)
    if identity not in installed:
        raise OutfitPackError("The selected appearance variant is not installed.")
    active_path = Path(store) / "active.json"
    active = json.loads(active_path.read_text(encoding="utf-8")) if active_path.is_file() else {}
    active.pop("_ensemble", None)
    active[selection.category] = {"pack_id": selection.pack_id, "item_id": selection.item_id, "variant_id": selection.variant_id}
    _atomic_json(active_path, active)


def clear_appearance_selection(store: Path, category: str) -> None:
    if category not in {"headwear", "makeup", *ACCESSORY_KINDS}:
        raise OutfitPackError("Only optional appearance slots can be cleared.")
    active_path = Path(store) / "active.json"
    active = json.loads(active_path.read_text(encoding="utf-8")) if active_path.is_file() else {}
    if not isinstance(active, dict):
        raise OutfitPackError("Invalid saved appearance state.")
    active.pop("_ensemble", None)
    active[category] = {"pack_id": "builtin", "item_id": "none", "variant_id": "none"}
    _atomic_json(active_path, active)


def apply_ensemble(store: Path, pack_id: str, ensemble_id: str) -> None:
    ensemble = next((item for item in list_installed_ensembles(store) if (item.pack_id, item.ensemble_id) == (pack_id, ensemble_id)), None)
    if ensemble is None:
        raise OutfitPackError("The selected ensemble is not installed.")
    active_path = Path(store) / "active.json"
    active = json.loads(active_path.read_text(encoding="utf-8")) if active_path.is_file() else {}
    for selection in ensemble.selections:
        if selection.item_id is None:
            active[selection.category] = {
                "pack_id": "builtin", "item_id": "none", "variant_id": "none",
            }
        else:
            active[selection.category] = {
                "pack_id": pack_id,
                "item_id": selection.item_id,
                "variant_id": selection.variant_id,
            }
    active["_ensemble"] = {"pack_id": pack_id, "ensemble_id": ensemble_id}
    _atomic_json(active_path, active)


def apply_outfit_variant(store: Path, pack_id: str, look_id: str, colorway_id: str) -> None:
    match = next((item for item in list_installed_selections(store, "garment") if (item.pack_id, item.item_id, item.variant_id) == (pack_id, look_id, colorway_id)), None)
    if match is None:
        raise OutfitPackError("The selected outfit variant is not installed.")
    apply_appearance_selection(store, match)


def restore_builtin_outfit(store: Path) -> None:
    builtin = {category: {"pack_id": "builtin", "item_id": "builtin", "variant_id": "builtin"} for category in SELECTION_CATEGORIES}
    _atomic_json(Path(store) / "active.json", builtin)


def _builtin_makeup_resolution(store: Path, requested: tuple[str, str, str]) -> tuple[str, tuple[str, str, str]]:
    """``builtin`` makeup means the official built-in variant while its pack ships; a bare face until then."""
    variant = requested[2] if requested[2] in BUILTIN_MAKEUP_VARIANTS else BUILTIN_MAKEUP_VARIANTS[0]
    official = (BUILTIN_MAKEUP_PACK_ID, BUILTIN_MAKEUP_ITEM_ID, variant)
    installed = {(item.pack_id, item.item_id, item.variant_id) for item in list_installed_selections(store, "makeup")}
    return ("installed", official) if official in installed else ("builtin", ("builtin", "none", "none"))


def _state_references_pack(path: Path, pack_id: str) -> bool:
    if not path.is_file():
        return False
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise OutfitPackError("Invalid saved appearance state.") from None
    if not isinstance(state, dict):
        raise OutfitPackError("Invalid saved appearance state.")
    for value in state.values():
        if isinstance(value, dict) and value.get("pack_id") == pack_id:
            return True
    return False


def remove_outfit_pack(store: Path, pack_id: str) -> RemovalResult:
    validated_id = _identifier(pack_id, "pack")
    if validated_id == "builtin":
        raise OutfitPackError("The built-in appearance cannot be removed.")
    packages = Path(store) / "packages"
    target = packages / f"{validated_id}.mohan-outfit"
    if not target.is_file():
        raise OutfitPackError("The appearance pack is not installed.")
    installed = _inspect_installed(target)
    if installed is not None and installed.pack_id != validated_id:
        raise OutfitPackError("Installed archive identity does not match its filename.")
    for state_name in ("active.json", "preview.json"):
        if _state_references_pack(Path(store) / state_name, validated_id):
            raise OutfitPackError("An active or previewed appearance must be switched before removal.")
    tombstone = packages / f".{validated_id}.removing"
    if tombstone.exists():
        raise OutfitPackError("A prior removal has not completed safely.")
    os.replace(target, tombstone)
    try:
        tombstone.unlink()
    except OSError:
        os.replace(tombstone, target)
        raise OutfitPackError("Appearance pack removal failed safely.") from None
    return RemovalResult(validated_id, target)


def resolve_active_selection(store: Path, category: str) -> SelectionResolution:
    if category not in SELECTION_CATEGORIES:
        raise OutfitPackError("Unknown selection category.")
    active_path = Path(store) / "active.json"
    if not active_path.is_file():
        requested = ("builtin", "builtin", "builtin")
    else:
        try:
            active = json.loads(active_path.read_text(encoding="utf-8"))
            if not isinstance(active, dict):
                raise AttributeError
            value = active.get(category)
        except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
            raise OutfitPackError("Invalid saved appearance state.") from None
        if value is None:
            requested = ("builtin", "builtin", "builtin")
        elif not isinstance(value, dict) or set(value) != {"pack_id", "item_id", "variant_id"} or any(not isinstance(value[key], str) for key in value):
            raise OutfitPackError("Invalid saved appearance selection.")
        else:
            requested = (value["pack_id"], value["item_id"], value["variant_id"])
    if requested[0] == "builtin":
        status, effective = "builtin", requested
        if category == "makeup" and requested[1] != "none":
            status, effective = _builtin_makeup_resolution(store, requested)
    else:
        installed = {(selection.pack_id, selection.item_id, selection.variant_id) for selection in list_installed_selections(store, category)}
        if requested not in installed and requested[0] in list_stale_body_profile_packs(store):
            raise IncompatibleBodyProfileError(f"Active pack {requested[0]!r} was authored for another body-profile generation.")
        if requested not in installed and category == "makeup":
            # A removed makeup pack falls back to the built-in default; ``requested`` keeps
            # the vanished identity so the wardrobe can show the notice once.
            status, effective = _builtin_makeup_resolution(store, ("builtin", "builtin", "builtin"))
        elif requested not in installed:
            raise OutfitPackError("The selected appearance is unavailable; it was not replaced.")
        else:
            status, effective = "installed", requested
    return SelectionResolution(category, status, *requested, *effective)
