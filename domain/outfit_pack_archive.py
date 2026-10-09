"""Validate the ZIP envelope and top-level manifest contract for outfit packs."""

from __future__ import annotations

lazy import json
lazy import re
lazy import zipfile
lazy from collections.abc import Callable

lazy from domain._outfit_pack_models import AppearanceItem
lazy from domain.character_runtime import character_rig_manifest
lazy from domain.outfit_pack_assets import (
    MANIFEST,
    IncompatibleBodyProfileError,
    OutfitPackError,
    _safe_member,
    validate_author,
)

FORMAT = "mohan-outfit-pack"
VERSION = 2
_RIG_MANIFEST = character_rig_manifest()
BODY_PROFILE_ID = _RIG_MANIFEST.body_profile_id
BODY_PROFILE_VERSION = _RIG_MANIFEST.body_profile_version
AUTHORING_TEMPLATE = "mohan-official-poses"
AUTHORING_VERSION = 2
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_MEMBERS = 2048
OPTIONAL_MANIFEST_KEYS = frozenset({"makeup"})
MANIFEST_KEYS = frozenset({
    "format", "version", "id", "pack_version", "app_range", "display_names",
    "compatible_body_profile", "source", "authoring", "looks", "hairstyles",
    "headwear", "accessories", "ensembles",
})
LICENSE = re.compile(r"[A-Za-z0-9 .()+-]{1,120}\Z")
SUPPORTED_SOURCE_LICENSES = frozenset({
    "All Rights Reserved",
    "All Rights Reserved - see ASSETS-LICENSE.md",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "CC BY 4.0",
    "CC-BY-4.0",
    "CC-BY-NC-ND-4.0",
    "CC0-1.0",
    "MIT",
})
SEMVER = re.compile(r"\d+\.\d+\.\d+\Z")
APP_RANGE = re.compile(r">=\d+\.\d+\.\d+,<\d+\.\d+\.\d+\Z")


def archive_member_names(archive: zipfile.ZipFile) -> set[str]:
    """Return unique safe member names after enforcing archive size limits."""
    infos = archive.infolist()
    names = {info.filename for info in infos}
    if not infos or len(infos) > MAX_MEMBERS or len(names) != len(infos) or MANIFEST not in names:
        raise OutfitPackError("Provide a supported archive members.")
    for info in infos:
        _safe_member(info)
    if sum(info.file_size for info in infos) > MAX_TOTAL_BYTES:
        raise OutfitPackError("Archive expands beyond the allowed size.")
    return names


def manifest_payload(archive: zipfile.ZipFile) -> dict:
    """Load and validate the top-level manifest and body-profile identity."""
    manifest = json.loads(archive.read(MANIFEST).decode("utf-8"))
    if (
        not isinstance(manifest, dict)
        or not MANIFEST_KEYS <= set(manifest) <= MANIFEST_KEYS | OPTIONAL_MANIFEST_KEYS
    ):
        raise OutfitPackError("Provide a supported appearance manifest.")
    if manifest["format"] != FORMAT or manifest["version"] != VERSION:
        raise OutfitPackError("Provide a supported appearance manifest.")
    expected_profile = {"id": BODY_PROFILE_ID, "version": BODY_PROFILE_VERSION}
    if manifest["compatible_body_profile"] != expected_profile:
        raise IncompatibleBodyProfileError(
            f"Pack body profile {manifest['compatible_body_profile']!r} "
            f"is not the current {expected_profile!r}."
        )
    if manifest["authoring"] != {"template": AUTHORING_TEMPLATE, "version": AUTHORING_VERSION}:
        raise OutfitPackError("Provide a supported authoring template.")
    return manifest


def source_declaration(manifest: dict) -> tuple[str, str, str]:
    """Validate and return the manifest's provenance declaration."""
    source = manifest["source"]
    if (
        not isinstance(source, dict)
        or set(source) != {"kind", "author", "license", "reference_included"}
    ):
        raise OutfitPackError("Provide a supported source declaration.")
    if source["kind"] not in {"original", "concept", "reference-derived"}:
        raise OutfitPackError("Provide a supported source declaration.")
    if source["reference_included"] is not False:
        raise OutfitPackError("Provide a supported source declaration.")
    if (
        not isinstance(source["license"], str)
        or not LICENSE.fullmatch(source["license"])
        or source["license"] not in SUPPORTED_SOURCE_LICENSES
    ):
        raise OutfitPackError("Provide a supported source declaration.")
    return source["kind"], validate_author(source["author"]), source["license"]


def appearance_items(
    manifest: dict,
    archive: zipfile.ZipFile,
    names: set[str],
    item_parser: Callable[[object, str, zipfile.ZipFile, set[str]], AppearanceItem],
) -> list[AppearanceItem]:
    """Parse each manifest appearance collection with the supplied item parser."""
    groups = (
        ("looks", "garment"), ("hairstyles", "hairstyle"), ("headwear", "headwear"),
        ("makeup", "makeup"), ("accessories", "accessory"),
    )
    items: list[AppearanceItem] = []
    for key, category in groups:
        entries = manifest.get(key, []) if key in OPTIONAL_MANIFEST_KEYS else manifest[key]
        if not isinstance(entries, list):
            raise OutfitPackError("Appearance collections must be lists.")
        parsed = [item_parser(entry, category, archive, names) for entry in entries]
        if len({item.item_id for item in parsed}) != len(parsed):
            raise OutfitPackError("Duplicate item identifier in category.")
        items.extend(parsed)
    if not items:
        raise OutfitPackError("An appearance pack requires content.")
    return items


def declared_asset_paths(items: list[AppearanceItem]) -> list[str]:
    """Return every asset path declared by variants and their motion states."""
    return [*(
        asset.path
        for item in items
        for variant in item.variants
        for poses in (variant.poses, *variant.eye_states.values(), *variant.mouth_states.values())
        for assets in poses.values()
        for asset in assets
    )]


def validate_declared_assets(items: list[AppearanceItem], names: set[str]) -> None:
    """Require every archive asset to have exactly one manifest declaration."""
    paths = declared_asset_paths(items)
    if len(paths) != len(set(paths)) or names != {MANIFEST, *paths}:
        raise OutfitPackError("Every asset must be declared exactly once.")


def pack_version(manifest: dict) -> tuple[str, str]:
    """Return validated package and compatible-application version strings."""
    version = manifest["pack_version"]
    app_range = manifest["app_range"]
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise OutfitPackError("Provide a supported version or app range.")
    if not isinstance(app_range, str) or not APP_RANGE.fullmatch(app_range):
        raise OutfitPackError("Provide a supported version or app range.")
    return version, app_range
