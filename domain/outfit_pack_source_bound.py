"""Portable, source-bound whole portraits carried by sealed outfit packs."""

from __future__ import annotations

lazy import re
lazy import zipfile

lazy from PySide6.QtGui import QImage

lazy from domain._outfit_pack_models import (
    AppearanceItem,
    SourceBoundExpression,
    SourceBoundSelection,
)
lazy from domain.character_runtime_data import (
    default_expression_catalog,
    default_rig_manifest,
)
lazy from domain.outfit_pack_assets import (
    SHA256,
    OutfitPackError,
    parse_appearance_asset,
    validate_pose_assets,
)
lazy from domain.qt_image_io import image_from_png

SCHEMA = "mohan.outfit-source-bound-expression.v1"
RECEIPT_SCHEMA = "mohan.outfit-source-bound-expression-receipt.v1"
MANIFEST_KEY = "source_bound_expressions"
EXPRESSION_ID = "exasperated_front"
SILHOUETTE = "front-exasperated"
MOUTH_VARIANTS = ("mid", "open", "round")
SELECTION_CATEGORIES = ("garment", "hairstyle")
NO_BLINK = "none"
PNG_BIT_DEPTH = 8
_IDENTIFIER = re.compile(r"[a-z0-9](?:[a-z0-9.-]{0,62}[a-z0-9])?\Z")
_RIG = default_rig_manifest()
CANVAS = (
    _RIG.half_body_asset_canvas.width,
    _RIG.half_body_asset_canvas.height,
)
MOUTH_BOUNDS = default_expression_catalog().source_bound_exasperated.mouth_bounds
MOUTH_BOUNDS_COMPONENTS = 4


def _mouth_bounds(value: object) -> tuple[int, int, int, int]:
    """Allow portrait-specific placement while retaining the local patch limit."""
    if (
        not isinstance(value, list)
        or len(value) != MOUTH_BOUNDS_COMPONENTS
        or any(type(component) is not int for component in value)
    ):
        raise OutfitPackError("Source-bound mouth bounds require four integers.")
    left, top, width, height = value
    if (
        left < 0 or top < 0
        or not 0 < width <= MOUTH_BOUNDS[2]
        or not 0 < height <= MOUTH_BOUNDS[3]
        or left + width > CANVAS[0]
        or top + height > CANVAS[1]
    ):
        raise OutfitPackError("Source-bound mouth bounds must stay local and inside the canvas.")
    return left, top, width, height


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise OutfitPackError(f"Invalid source-bound {label} identifier.")
    return value


def _selection_binding(value: object) -> frozendict[str, SourceBoundSelection]:
    if not isinstance(value, dict) or set(value) != set(SELECTION_CATEGORIES):
        raise OutfitPackError("Source-bound portraits require garment and hairstyle bindings.")
    parsed = {}
    for category in SELECTION_CATEGORIES:
        entry = value[category]
        if not isinstance(entry, dict) or set(entry) != {"item_id", "variant_id"}:
            raise OutfitPackError("Provide a supported source-bound selection binding.")
        parsed[category] = SourceBoundSelection(
            _identifier(entry["item_id"], "item"),
            _identifier(entry["variant_id"], "variant"),
        )
    return frozendict(parsed)


def _rgba_asset(
    record: object,
    slot: str,
    archive: zipfile.ZipFile,
    names: set[str],
    *,
    require_alpha: bool = True,
):
    asset = parse_appearance_asset(record, frozenset({slot}), archive, names)
    if (
        (asset.width, asset.height, asset.anchor_x, asset.anchor_y) != (*CANVAS, 0, 0)
        or not asset.path.endswith(".png")
    ):
        raise OutfitPackError("Source-bound assets require the native RGBA canvas.")
    payload = archive.read(asset.path)
    if (
        payload[:8] != b"\x89PNG\r\n\x1a\n"
        or payload[24] != PNG_BIT_DEPTH
        or payload[25] not in ({6} if require_alpha else {2, 6})
    ):
        raise OutfitPackError("Source-bound assets must use supported 8-bit PNGs.")
    image = image_from_png(payload)
    if image.isNull():
        raise OutfitPackError("Source-bound assets must decode.")
    if require_alpha:
        validate_pose_assets(
            (asset,), archive, CANVAS, require_visible=True, full_canvas=True,
        )
    return asset


def _validate_mouth_alpha(data: bytes, bounds: tuple[int, int, int, int]) -> None:
    image = image_from_png(data)
    if image.isNull():
        raise OutfitPackError("Source-bound mouth assets must decode.")
    rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
    pixels = rgba.bits()
    stride = rgba.bytesPerLine()
    left, top, width, height = bounds
    right, bottom = left + width, top + height
    visible = False
    for y in range(image.height()):
        row = pixels[y * stride:y * stride + image.width() * 4]
        if top <= y < bottom:
            outside = any(row[3:left * 4:4]) or any(
                row[right * 4 + 3:image.width() * 4:4]
            )
            visible = visible or any(row[left * 4 + 3:right * 4:4])
        else:
            outside = any(row[3:image.width() * 4:4])
        if outside:
            raise OutfitPackError("Source-bound mouth alpha escapes its declared bounds.")
    if not visible:
        raise OutfitPackError("Source-bound mouth assets must contain visible pixels.")


def _receipt(
    value: object,
    approved_source_sha256: str,
    assets: tuple,
) -> tuple[frozendict[str, str], str]:
    keys = {
        "schema",
        "owner_approved",
        "approved_source_sha256",
        "installed_files_sha256",
        "mouth_source_sha256",
        "blink",
    }
    if (
        not isinstance(value, dict)
        or set(value) != keys
        or value["schema"] != RECEIPT_SCHEMA
        or value["owner_approved"] is not True
        or value["approved_source_sha256"] != approved_source_sha256
        or value["blink"] != NO_BLINK
    ):
        raise OutfitPackError("Source-bound expression receipt is invalid.")
    installed = value["installed_files_sha256"]
    expected = {asset.path: asset.sha256 for asset in assets}
    if installed != expected:
        raise OutfitPackError("Source-bound receipt must cover every installed asset.")
    mouth_sources = value["mouth_source_sha256"]
    if (
        not isinstance(mouth_sources, dict)
        or set(mouth_sources) != set(MOUTH_VARIANTS)
        or any(not isinstance(digest, str) or not SHA256.fullmatch(digest) for digest in mouth_sources.values())
    ):
        raise OutfitPackError("Source-bound receipt requires the V5 mouth sources.")
    return frozendict(mouth_sources), NO_BLINK


def _expression(
    value: object,
    archive: zipfile.ZipFile,
    names: set[str],
) -> SourceBoundExpression:
    keys = {
        "schema",
        "expression",
        "silhouette",
        "approved_source_sha256",
        "mouth_bounds",
        "selection_binding",
        "parts",
        "mouths",
        "receipt",
    }
    if (
        not isinstance(value, dict)
        or set(value) != keys
        or value["schema"] != SCHEMA
        or value["expression"] != EXPRESSION_ID
        or value["silhouette"] != SILHOUETTE
    ):
        raise OutfitPackError("Provide a supported source-bound expression manifest.")
    mouth_bounds = _mouth_bounds(value["mouth_bounds"])
    digest = value["approved_source_sha256"]
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise OutfitPackError("Source-bound expressions require an approved source digest.")
    parts = value["parts"]
    mouths = value["mouths"]
    if not isinstance(parts, dict) or set(parts) != {"portrait"}:
        raise OutfitPackError("Source-bound expressions require one whole portrait.")
    if not isinstance(mouths, dict) or set(mouths) != set(MOUTH_VARIANTS):
        raise OutfitPackError("Source-bound expressions require mid/open/round mouths.")
    portrait = _rgba_asset(
        parts["portrait"],
        "portrait",
        archive,
        names,
        require_alpha=False,
    )
    if portrait.sha256 != digest:
        raise OutfitPackError("Source-bound portrait does not match its approved source.")
    parsed_mouths = frozendict({
        variant: _rgba_asset(mouths[variant], variant, archive, names)
        for variant in MOUTH_VARIANTS
    })
    for asset in parsed_mouths.values():
        _validate_mouth_alpha(archive.read(asset.path), mouth_bounds)
    mouth_sources, blink = _receipt(
        value["receipt"], digest, (portrait, *parsed_mouths.values()),
    )
    return SourceBoundExpression(
        EXPRESSION_ID,
        SILHOUETTE,
        digest,
        mouth_bounds,
        _selection_binding(value["selection_binding"]),
        portrait,
        parsed_mouths,
        mouth_sources,
        blink,
    )


def parse_source_bound_expressions(
    value: object,
    archive: zipfile.ZipFile,
    names: set[str],
) -> frozendict[str, SourceBoundExpression]:
    if value is None:
        return frozendict()
    if not isinstance(value, list) or not value:
        raise OutfitPackError("Source-bound expressions must be a non-empty list.")
    parsed = tuple(_expression(entry, archive, names) for entry in value)
    if len({entry.expression_id for entry in parsed}) != len(parsed):
        raise OutfitPackError("Duplicate source-bound expression.")
    return frozendict((entry.expression_id, entry) for entry in parsed)


def source_bound_asset_paths(
    expressions: frozendict[str, SourceBoundExpression],
) -> tuple[str, ...]:
    return tuple(
        path
        for expression in expressions.values()
        for path in (
            expression.portrait.path,
            *(expression.mouths[key].path for key in MOUTH_VARIANTS),
        )
    )


def validate_source_bound_bindings(
    expressions: frozendict[str, SourceBoundExpression],
    items: list[AppearanceItem],
) -> None:
    available = {}
    for item in items:
        for variant in item.variants:
            available[item.category, item.item_id, variant.variant_id] = variant
    declared: set[tuple[str, str, str, str]] = set()
    for expression in expressions.values():
        for category, selection in expression.selections.items():
            identity = (category, selection.item_id, selection.variant_id)
            variant = available.get(identity)
            if variant is None or expression.silhouette not in variant.source_bound_silhouettes:
                raise OutfitPackError("Source-bound expression selection is not declared by its variant.")
            declared.add((*identity, expression.silhouette))
    omitted: set[tuple[str, str, str, str]] = set()
    for item in items:
        for variant in item.variants:
            for silhouette in variant.source_bound_silhouettes:
                omitted.add(
                    (item.category, item.item_id, variant.variant_id, silhouette)
                )
    if omitted != declared:
        raise OutfitPackError("Every omitted appearance view requires one source-bound expression.")
