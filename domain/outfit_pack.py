from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy import re
lazy import struct
lazy import zipfile
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath
lazy from tempfile import NamedTemporaryFile
lazy from xml.etree import ElementTree

lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id

FORMAT = "mohan-outfit-pack"
VERSION = 2
MANIFEST = "manifest.json"
BODY_PROFILE_ID = "mohan-body-v1"
BODY_PROFILE_VERSION = 1
AUTHORING_TEMPLATE = "mohan-official-poses"
AUTHORING_VERSION = 2
BASE_SILHOUETTES = ("cheek-rest", "left-neutral", "front-crossed")
GESTURE_SILHOUETTES = (
    "front-mock-scold", "front-mock-hit", "front-eureka", "front-exasperated"
)
POSE_ATLAS_SILHOUETTES = tuple(canonical_view_id(yaw) for yaw in CANONICAL_YAWS)
REQUIRED_SILHOUETTES = (
    BASE_SILHOUETTES + GESTURE_SILHOUETTES + POSE_ATLAS_SILHOUETTES
)
SUPPORTED_SILHOUETTES = REQUIRED_SILHOUETTES
EXPRESSION_SILHOUETTE_ALIASES = frozendict({
    "cheek": "cheek-rest", "lean": "left-neutral", "front": "front-crossed",
    "protective_front": "front-crossed",
})
OFFICIAL_BODY_SPEC = frozendict({
    "adult": True, "height_cm": 168, "weight_kg": 54, "bust_cm": 86,
    "underbust_cm": 71, "waist_cm": 62, "hips_cm": 90,
})
BODY_REGIONS = (
    "neck", "shoulder-left", "shoulder-right", "arm-left", "arm-right",
    "torso", "leg-left", "leg-right",
)
VISIBILITY = frozenset({"visible", "covered"})
FABRIC_BEHAVIORS = frozenset({"structured", "draped", "stretch", "loose"})
GARMENT_SLOTS = frozenset({
    "bodice", "outerwear", "sleeve-left", "sleeve-right", "skirt", "trousers",
    "legwear-left", "legwear-right", "swimwear", "garment-occluder",
})
HAIR_SLOTS = frozenset({
    "back", "front", "side-left", "side-right", "bangs", "bun", "ponytail",
})
REQUIRED_HAIR_SLOTS = frozenset({"back", "front"})
HEAD_ATTACHMENTS = frozenset({"crown", "temple-left", "temple-right", "ear-left", "ear-right", "back-head"})
ACCESSORY_KINDS = ("weapon", "handheld", "jewelry", "foreground-effect")
ACCESSORY_ASSET_SLOTS = frozendict({
    "weapon": frozenset({"weapon", "sheath"}),
    "handheld": frozenset({"handheld"}),
    "jewelry": frozenset({"jewelry"}),
    "foreground-effect": frozenset({"foreground-effect"}),
})
WEAPON_PLACEMENTS = frozenset({"back", "waist-left", "waist-right", "hand-left", "hand-right"})
HANDHELD_PLACEMENTS = frozenset({"hand-left", "hand-right"})
WEAPON_ATTACHMENTS = frozenset({"back-harness", "waist-sheath", "left-grip", "right-grip"})
FACE_MASKS = frozenset({"none", "hairline-safe", "bangs-safe", "side-locks-safe"})
HAND_RULES = frozenset({"behind-hands", "front-of-hands"})
GARMENT_RULES = frozenset({"behind-collar", "front-of-collar"})
HEADWEAR_MASKS = frozenset({"crown-safe", "temple-safe", "ear-safe", "back-head-safe"})
LANGUAGES = frozenset({"zh-TW", "zh-CN", "en", "ja-JP"})
SELECTION_CATEGORIES = ("garment", "hairstyle", "headwear", *ACCESSORY_KINDS)
THERMAL_BANDS = frozenset({"hot", "warm", "mild", "cool", "cold"})
WEATHER_TAGS = frozenset({"clear", "cloudy", "rain", "storm", "snow", "windy", "indoor"})
MOOD_TAGS = frozenset({"calm", "cheerful", "affectionate", "reserved", "upset", "focused"})
OCCASION_TAGS = frozenset({"everyday", "work", "formal", "holiday", "birthday", "christmas", "valentines"})
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_MEMBERS = 2048
MAX_COMPRESSION_RATIO = 100
MAX_IMAGE_DIMENSION = 4096
MIN_ANCHOR_COORDINATE = -4096
MAX_ANCHOR_COORDINATE = 4096
MIN_Z_ORDER = -100
MAX_Z_ORDER = 100
MAX_NAME_LENGTH = 80
MAX_AUTHOR_LENGTH = 120
MIN_PNG_HEADER_LENGTH = 24
MIN_WEBP_HEADER_LENGTH = 30
SYMLINK_FILE_TYPE = 0o120000
ANCHOR_DIMENSIONS = 2
IDENTIFIER = re.compile(r"[a-z0-9](?:[a-z0-9.-]{0,62}[a-z0-9])?\Z")
SEMVER = re.compile(r"\d+\.\d+\.\d+\Z")
APP_RANGE = re.compile(r">=\d+\.\d+\.\d+,<\d+\.\d+\.\d+\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
ASSET_PATH = re.compile(r"assets/[a-z0-9][a-z0-9_.+-]{0,127}\.(?:png|webp|svg)\Z")
LICENSE = re.compile(r"[A-Za-z0-9 .()+-]{1,120}\Z")
PROTECTED_TERMS = frozenset({
    "face", "eye", "eyes", "mouth", "lip", "skin", "identity", "skull",
    "body-skin", "core-body", "body-contour", "bust-geometry", "torso-geometry",
})
SVG_ELEMENTS = frozenset({
    "svg", "g", "defs", "linearGradient", "radialGradient", "stop", "path",
    "rect", "circle", "ellipse", "line", "polyline", "polygon",
})
MANIFEST_KEYS = frozenset({
    "format", "version", "id", "pack_version", "app_range", "display_names",
    "compatible_body_profile", "source", "authoring", "looks", "hairstyles",
    "headwear", "accessories", "ensembles",
})


class OutfitPackError(RuntimeError):
    pass


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


def _safe_member(info: zipfile.ZipInfo) -> None:
    path = PurePosixPath(info.filename)
    if info.is_dir() or path.is_absolute() or ".." in path.parts or "\\" in info.filename:
        raise OutfitPackError("Unsafe archive path.")
    if info.flag_bits & 1 or info.file_size > MAX_MEMBER_BYTES:
        raise OutfitPackError("Unsafe archive member.")
    if (info.external_attr >> 16) & 0o170000 == SYMLINK_FILE_TYPE:
        raise OutfitPackError("Symbolic links are forbidden.")
    if info.filename != MANIFEST and not ASSET_PATH.fullmatch(info.filename):
        raise OutfitPackError("Executable or unsupported member.")
    if info.file_size / max(1, info.compress_size) > MAX_COMPRESSION_RATIO:
        raise OutfitPackError("Suspicious compression ratio.")


def _png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < MIN_PNG_HEADER_LENGTH or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise OutfitPackError("Invalid PNG asset.")
    return struct.unpack(">II", data[16:24])


def _webp_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < MIN_WEBP_HEADER_LENGTH or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise OutfitPackError("Invalid WebP asset.")
    if data[12:16] != b"VP8X":
        raise OutfitPackError("Unsupported WebP header.")
    return (
        int.from_bytes(data[24:27], "little") + 1,
        int.from_bytes(data[27:30], "little") + 1,
    )


def _validate_svg_tree(root: ElementTree.Element) -> None:
    unsafe_markers = ("url(", "javascript:", "data:")
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] not in SVG_ELEMENTS:
            raise OutfitPackError("Forbidden SVG element.")
        for name, value in element.attrib.items():
            local = name.rsplit("}", 1)[-1].lower()
            unsafe_name = local.startswith("on") or local in {"href", "src"}
            if unsafe_name or any(marker in value.lower() for marker in unsafe_markers):
                raise OutfitPackError("Unsafe SVG content.")


def _svg_dimensions(data: bytes) -> tuple[int, int]:
    lowered = data.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise OutfitPackError("DTD is forbidden in SVG.")
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        raise OutfitPackError("Invalid SVG asset.") from None
    _validate_svg_tree(root)
    try:
        return int(float(root.attrib["width"])), int(float(root.attrib["height"]))
    except (KeyError, ValueError):
        raise OutfitPackError("SVG requires numeric dimensions.") from None


def _dimensions(data: bytes, suffix: str) -> tuple[int, int]:
    if suffix == ".png":
        return _png_dimensions(data)
    if suffix == ".webp":
        return _webp_dimensions(data)
    return _svg_dimensions(data)


def validated_asset_dimensions(path: str, data: bytes) -> tuple[int, int]:
    """Return dimensions using the same parser enforced during installation."""

    if not ASSET_PATH.fullmatch(path):
        raise OutfitPackError("Unsupported outfit asset path.")
    dimensions = _dimensions(data, Path(path).suffix)
    if any(not 1 <= value <= MAX_IMAGE_DIMENSION for value in dimensions):
        raise OutfitPackError("Asset dimensions exceed the supported range.")
    return dimensions


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
    if any(term in f"{slot}/{path}".lower() for term in PROTECTED_TERMS):
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
        if category not in {"headwear", *ACCESSORY_KINDS}:
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
    if not isinstance(selections, dict) or set(selections) != set(SELECTION_CATEGORIES):
        raise OutfitPackError("Ensemble must declare every appearance category.")
    typed = tuple(
        _ensemble_selection(category, selections[category], available)
        for category in SELECTION_CATEGORIES
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
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS:
        raise OutfitPackError("Unsupported appearance manifest.")
    if manifest["format"] != FORMAT or manifest["version"] != VERSION:
        raise OutfitPackError("Unsupported appearance manifest.")
    expected_profile = {"id": BODY_PROFILE_ID, "version": BODY_PROFILE_VERSION}
    expected_authoring = {"template": AUTHORING_TEMPLATE, "version": AUTHORING_VERSION}
    if manifest["compatible_body_profile"] != expected_profile or manifest["authoring"] != expected_authoring:
        raise OutfitPackError("Unsupported body profile or authoring template.")
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
        ("looks", "garment"),
        ("hairstyles", "hairstyle"),
        ("headwear", "headwear"),
        ("accessories", "accessory"),
    )
    items: list[AppearanceItem] = []
    for key, category in groups:
        entries = manifest[key]
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
        pack_id,
        pack_version,
        app_range,
        _names(manifest["display_names"]),
        source_kind,
        author,
        license_name,
        BODY_PROFILE_ID,
        tuple(items),
        ensembles,
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


def list_installed_outfits(store: Path) -> tuple[OutfitPack, ...]:
    packages = Path(store) / "packages"
    return () if not packages.is_dir() else tuple(inspect_outfit_pack(path) for path in sorted(packages.glob("*.mohan-outfit")))


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
        InstalledEnsemble(
            pack.pack_id,
            ensemble.ensemble_id,
            pack.display_names,
            ensemble.display_names,
            ensemble.selections,
            ensemble.autonomous_profile,
        )
        for pack in list_installed_outfits(store)
        for ensemble in pack.ensembles
    )


def list_installed_variants(store: Path) -> tuple[InstalledSelection, ...]:
    return list_installed_selections(store, "garment")


def install_outfit_pack(source: Path, store: Path) -> OutfitPack:
    pack = inspect_outfit_pack(source)
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
    if category not in {"headwear", *ACCESSORY_KINDS}:
        raise OutfitPackError("Only optional appearance slots can be cleared.")
    active_path = Path(store) / "active.json"
    active = json.loads(active_path.read_text(encoding="utf-8")) if active_path.is_file() else {}
    if not isinstance(active, dict):
        raise OutfitPackError("Invalid saved appearance state.")
    active.pop("_ensemble", None)
    active[category] = {"pack_id": "builtin", "item_id": "none", "variant_id": "none"}
    _atomic_json(active_path, active)


def apply_ensemble(store: Path, pack_id: str, ensemble_id: str) -> None:
    ensemble = next(
        (
            item
            for item in list_installed_ensembles(store)
            if (item.pack_id, item.ensemble_id) == (pack_id, ensemble_id)
        ),
        None,
    )
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
    installed = inspect_outfit_pack(target)
    if installed.pack_id != validated_id:
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
            value = active.get(category, {})
        except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
            raise OutfitPackError("Invalid saved appearance state.") from None
        if not isinstance(value, dict) or set(value) != {"pack_id", "item_id", "variant_id"} or any(not isinstance(value[key], str) for key in value):
            raise OutfitPackError("Invalid saved appearance selection.")
        requested = (value["pack_id"], value["item_id"], value["variant_id"])
    if requested[0] == "builtin":
        status, effective = "builtin", requested
    else:
        installed = {
            (selection.pack_id, selection.item_id, selection.variant_id)
            for selection in list_installed_selections(store, category)
        }
        if requested not in installed:
            raise OutfitPackError(
                "The selected appearance is unavailable; it was not replaced."
            )
        status, effective = "installed", requested
    return SelectionResolution(category, status, *requested, *effective)
