"""Validate an optional, exact-selection full-body garment visibility mask."""
from __future__ import annotations

lazy import hashlib
lazy import json
lazy import re
lazy import zipfile
lazy from collections.abc import Callable, Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from PySide6.QtGui import QImage, QPixmap, QRegion

lazy from domain.outfit_pack import (
    AppearanceVariant,
    OutfitPackError,
    SelectionResolution,
    resolve_variant_for_view,
)
lazy from domain.qt_image_io import image_from_png
lazy from infrastructure.appearance_layer_stack import clear_appearance_base
lazy from infrastructure.image_alpha_regions import visible_alpha_region
lazy from infrastructure.outfit_core_composition import replace_restored_body

SCHEMA = "mohan.source-bound-garment-visibility.v1"
MANIFEST = Path("assets/pose-atlas/v5-garment-visibility/manifest.json")
CANVAS = (1024, 1536)
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_INVERT = bytes(255 - value for value in range(256))
_PNG = b"\x89PNG\r\n\x1a\n"
_PNG_HEADER_BYTES = 26
Layer = tuple[QPixmap, int, int, QRegion, float]


@dataclass(frozen=True)
class GarmentBinding:
    removal: QRegion
    hand_overlays: tuple[Layer, ...] | None
    hand_region: QRegion | None


def _record(value: object) -> tuple[str, str]:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise OutfitPackError("Source-bound garment record needs path and SHA-256.")
    path, digest = value["path"], value["sha256"]
    if not isinstance(path, str) or not path or not isinstance(digest, str) or not _SHA.fullmatch(digest):
        raise OutfitPackError("Source-bound garment record has an invalid path or SHA-256.")
    return path, digest


def _source_bytes(root: Path, value: object, expected: str) -> bytes:
    path, digest = _record(value)
    if path != expected:
        raise OutfitPackError("Source-bound garment path disagrees with the active view.")
    target = root / path
    if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
        raise OutfitPackError("Source-bound garment path escapes the asset root.")
    try:
        payload = target.read_bytes()
    except OSError as error:
        raise OutfitPackError("Source-bound garment input is unavailable.") from error
    if hashlib.sha256(payload).hexdigest() != digest:
        raise OutfitPackError("Source-bound garment input SHA-256 drifted.")
    return payload


def _removal_region(payload: bytes) -> QRegion:
    if (len(payload) < _PNG_HEADER_BYTES or payload[:8] != _PNG
            or payload[24:26] not in {b"\x08\x00", b"\x08\x06"}):
        raise OutfitPackError("Garment visibility must be an 8-bit L or RGBA PNG.")
    image = image_from_png(payload)
    if image.isNull() or image.size().toTuple() != CANVAS:
        raise OutfitPackError("Garment visibility needs a 1024x1536 canvas.")
    channel = image.convertToFormat(
        QImage.Format_Grayscale8 if payload[25] == 0 else QImage.Format_Alpha8
    )
    plane = bytes(channel.constBits())
    if plane.count(0) + plane.count(255) != len(plane):
        raise OutfitPackError("Garment visibility must contain only 0 and 255.")
    inverted = plane.translate(_INVERT)
    removal = QImage(inverted, CANVAS[0], CANVAS[1], channel.bytesPerLine(), QImage.Format_Alpha8)
    region = visible_alpha_region(removal)
    if region.isEmpty():
        raise OutfitPackError("Garment visibility declares no native cloth to remove.")
    return region


def _native_hand_support(
    root: Path, view_id: str, value: object,
) -> tuple[tuple[Layer, ...], QRegion]:
    if not isinstance(value, dict) or set(value) != {"left", "right"}:
        raise OutfitPackError("Native hand support requires left and right records.")
    overlays: list[Layer] = []
    combined = QRegion()
    for side in ("left", "right"):
        payload = _source_bytes(
            root, value[side],
            f"assets/pose-atlas/v5-garment-visibility/{view_id}-{side}-native-hand.png",
        )
        if (len(payload) < _PNG_HEADER_BYTES or payload[:8] != _PNG
                or payload[24:26] != b"\x08\x06"):
            raise OutfitPackError("Native hand support must be an 8-bit RGBA PNG.")
        image = image_from_png(payload)
        if image.isNull() or image.size().toTuple() != CANVAS:
            raise OutfitPackError("Native hand support needs a 1024x1536 canvas.")
        region = visible_alpha_region(image)
        overlays.append((QPixmap.fromImage(image), 0, 0, region, 1.0))
        combined = combined.united(region)
    return tuple(overlays), combined


def load_garment_binding(
    root: Path,
    view_id: str,
    selection: SelectionResolution,
    archive_path: Path,
    variant: AppearanceVariant,
) -> GarmentBinding | None:
    """Return an exact source-pinned garment and its optional local hands."""
    manifest_path = root / MANIFEST
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise OutfitPackError("Source-bound garment manifest is unreadable.") from error
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA or not isinstance(manifest.get("views"), dict):
        raise OutfitPackError("Source-bound garment manifest has an invalid schema.")
    entry = manifest["views"].get(view_id)
    if entry is None:
        return None
    required = {"selection_exact", "native_source", "garment_member", "visibility"}
    if (not isinstance(entry, dict) or not required.issubset(entry)
            or set(entry) - required - {"native_hand_support"}):
        raise OutfitPackError("Source-bound garment view has an invalid contract.")
    exact = entry["selection_exact"]
    if not isinstance(exact, dict) or set(exact) != {"pack_id", "item_id", "variant_id"}:
        raise OutfitPackError("Source-bound garment selection is invalid.")
    effective = {
        "pack_id": selection.effective_pack_id,
        "item_id": selection.effective_item_id,
        "variant_id": selection.effective_variant_id,
    }
    if exact != effective:
        return None
    _source_bytes(root, entry["native_source"], f"assets/pose-atlas/v5-base/{view_id}.png")
    member, digest = _record(entry["garment_member"])
    declarations = resolve_variant_for_view(variant, view_id).assets
    if not any(asset.path == member and asset.sha256 == digest for asset in declarations):
        raise OutfitPackError("Source-bound garment member differs from the selected pack.")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            payload = archive.read(member)
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        raise OutfitPackError("Source-bound garment member is unavailable.") from error
    if hashlib.sha256(payload).hexdigest() != digest:
        raise OutfitPackError("Source-bound garment member SHA-256 drifted.")
    visibility = _source_bytes(
        root, entry["visibility"], f"assets/pose-atlas/v5-garment-visibility/{view_id}.png"
    )
    removal = _removal_region(visibility)
    hands = entry.get("native_hand_support")
    if hands is None and "native_hand_support" not in entry:
        return GarmentBinding(removal, None, None)
    overlays, region = _native_hand_support(root, view_id, hands)
    return GarmentBinding(removal, overlays, region)


def load_garment_removal(
    root: Path,
    view_id: str,
    selection: SelectionResolution,
    archive_path: Path,
    variant: AppearanceVariant,
) -> QRegion | None:
    """Compatibility view of the source-bound visibility region."""
    binding = load_garment_binding(root, view_id, selection, archive_path, variant)
    return None if binding is None else binding.removal


def compose_garment_base(
    frame: QPixmap, body_overlays: Sequence[Layer],
    replace_body: Callable[[QPixmap], QPixmap] | None,
    silhouette: QRegion | None, replacement: QRegion | None, source_bound: bool,
) -> tuple[QPixmap, Sequence[Layer]]:
    result = QPixmap(frame)
    if source_bound:
        result, body_overlays = replace_restored_body(result, body_overlays, replace_body)
    result = clear_appearance_base(result, silhouette, replacement)
    if not source_bound:
        result, body_overlays = replace_restored_body(result, body_overlays, replace_body)
    return result, body_overlays


def validate_garment_removal(
    root: Path, view_id: str, canvas_size: tuple[int, int], removal: QRegion,
    protected_face: QRegion,
    visible_hands: Callable[[str], QRegion | None] | None,
) -> None:
    """Never erase native face, hair, ornament, or visible hand ownership."""
    protected = QRegion(protected_face)
    layered = root / "assets/pose-atlas/v5-base-layered"
    for layer in ("hair_back", "hair_left", "hair_right", "ornament"):
        pixmap = QPixmap(str(layered / f"{view_id}_{layer}.png"))
        if pixmap.isNull() or pixmap.size().toTuple() != canvas_size:
            raise OutfitPackError("Native hair ownership is unavailable.")
        protected = protected.united(visible_alpha_region(pixmap.toImage()))
    if visible_hands is None:
        raise OutfitPackError("Native hand ownership is unavailable.")
    hands = visible_hands(view_id)
    if not isinstance(hands, QRegion):
        raise OutfitPackError("Native hand ownership is invalid.")
    if not removal.intersected(protected.united(hands)).isEmpty():
        raise OutfitPackError("Garment visibility removes protected native identity.")
