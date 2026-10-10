"""Archive-member and image-format primitives shared by the outfit-pack parser and builders.

Split out of ``domain.outfit_pack`` so that module stays within its line ratchet;
``domain.outfit_pack`` re-exports the error classes, so existing
``from domain.outfit_pack import OutfitPackError`` imports keep working.
"""

from __future__ import annotations

lazy import hashlib
lazy import re
lazy import struct
lazy import zipfile
lazy from contextlib import contextmanager
lazy from contextvars import ContextVar
lazy from pathlib import Path, PurePosixPath
lazy from typing import Protocol
lazy from PySide6.QtGui import QImage
lazy from xml.etree import ElementTree

lazy from domain._outfit_pack_models import AppearanceAsset
lazy from domain.qt_image_io import image_from_png

MANIFEST = "manifest.json"
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
MAX_IMAGE_DIMENSION = 4096
MAX_AUTHOR_LENGTH = 120
MIN_PNG_HEADER_LENGTH = 24
MIN_WEBP_HEADER_LENGTH = 30
SYMLINK_FILE_TYPE = 0o120000
ASSET_PATH = re.compile(r"assets/[a-z0-9][a-z0-9_.+-]{0,127}\.(?:png|webp|svg)\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SVG_ELEMENTS = frozenset({
    "svg", "g", "defs", "linearGradient", "radialGradient", "stop", "path",
    "rect", "circle", "ellipse", "line", "polyline", "polygon",
})
GARMENT_SLOTS = frozenset({
    "bodice", "outerwear", "sleeve-left", "sleeve-right", "skirt", "trousers",
    "legwear-left", "legwear-right", "swimwear", "garment-occluder",
})
MAKEUP_OCCLUDER_SLOTS = GARMENT_SLOTS | {"headwear"}
MAKEUP_SLOTS = frozenset({"eyes", "cheeks", "lips"})
FOUNDATION_SLOT = "foundation"
MAKEUP_SLOTS_V2 = frozenset((*MAKEUP_SLOTS, FOUNDATION_SLOT))
FULL_BODY_SILHOUETTE_SCOPE = "full-body"
MIN_ANCHOR_COORDINATE = -4096
MAX_ANCHOR_COORDINATE = 4096
MIN_Z_ORDER = -100
MAX_Z_ORDER = 100
ANCHOR_DIMENSIONS = 2
PROTECTED_TERMS = frozenset({
    "face", "eye", "eyes", "mouth", "lip", "skin", "identity", "skull",
    "body-skin", "core-body", "body-contour", "bust-geometry", "torso-geometry",
})
MAKEUP_PATH_TERMS = PROTECTED_TERMS - frozenset({"eye", "eyes", "lip"})

_PNG_CONTENT_VALIDATION = ContextVar(
    "mohan_png_content_validation",
    default=True,
)


@contextmanager
def deferred_png_content_validation():
    """Defer alpha-only Qt PNG decoding for installed-pack discovery.

    Hashes, dimensions, geometry, archive contracts and visible-pixel rules
    remain checked while parsing. Runtime layer loading performs the complete
    decode and alpha checks immediately before a layer can be used.
    """
    token = _PNG_CONTENT_VALIDATION.set(False)
    try:
        yield
    finally:
        _PNG_CONTENT_VALIDATION.reset(token)


class OutfitPackError(RuntimeError):
    """A fail-closed pack error with optional privacy-safe diagnostics."""

    def __init__(
        self,
        message: str,
        *,
        reason: str | None = None,
        pack_id: str | None = None,
        asset_path: str | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.pack_id = pack_id
        self.asset_path = asset_path


class IncompatibleBodyProfileError(OutfitPackError):
    """The pack was authored for another body-profile generation and uses its own generation contract."""


def parse_appearance_asset(
    entry: object,
    allowed_slots: frozenset[str],
    archive: zipfile.ZipFile,
    names: set[str],
) -> AppearanceAsset:
    """Parse one sealed appearance declaration under the shared slot policy."""

    required = {"slot", "path", "sha256", "width", "height", "anchor", "z_order"}
    optional = {"occludes_makeup", "clears_base"}
    if not isinstance(entry, dict) or not required <= set(entry) or set(entry) - required - optional:
        raise OutfitPackError("Provide a supported asset declaration.")
    slot, path = entry["slot"], entry["path"]
    if not isinstance(slot, str) or slot not in allowed_slots or not isinstance(path, str) or not ASSET_PATH.fullmatch(path) or path not in names:
        raise OutfitPackError("Use a recognized slot or asset path.")
    occludes_makeup = entry.get("occludes_makeup", False)
    if not isinstance(occludes_makeup, bool) or ("occludes_makeup" in entry and slot not in MAKEUP_OCCLUDER_SLOTS):
        raise OutfitPackError("Makeup occlusion must be a boolean on a garment asset or headwear asset.")
    clears_base = entry.get("clears_base", False)
    if (
        not isinstance(clears_base, bool)
        or ("clears_base" in entry and slot != "garment-occluder")
        or (slot == "garment-occluder" and clears_base is not True)
    ):
        raise OutfitPackError(
            "Base clearing requires a garment-occluder asset with clears_base enabled."
        )
    screened, terms = (path, MAKEUP_PATH_TERMS) if slot in MAKEUP_SLOTS_V2 else (f"{slot}/{path}", PROTECTED_TERMS)
    if any(term in screened.lower() for term in terms):
        raise OutfitPackError("Core identity, skin and geometry remain protected.")
    anchor = entry["anchor"]
    values = (entry["width"], entry["height"], entry["z_order"])
    if not isinstance(entry["sha256"], str) or not SHA256.fullmatch(entry["sha256"]) or not isinstance(anchor, list) or len(anchor) != ANCHOR_DIMENSIONS:
        raise OutfitPackError("Provide a supported hash or anchor.")
    if any(not isinstance(value, int) or isinstance(value, bool) for value in (*values, *anchor)):
        raise OutfitPackError("Provide a supported asset geometry.")
    width, height, z_order = values
    if not (1 <= width <= MAX_IMAGE_DIMENSION and 1 <= height <= MAX_IMAGE_DIMENSION and MIN_ANCHOR_COORDINATE <= anchor[0] <= MAX_ANCHOR_COORDINATE and MIN_ANCHOR_COORDINATE <= anchor[1] <= MAX_ANCHOR_COORDINATE and MIN_Z_ORDER <= z_order <= MAX_Z_ORDER):
        raise OutfitPackError("Asset geometry is outside the allowed range.")
    data = archive.read(path)
    if hashlib.sha256(data).hexdigest() != entry["sha256"] or _dimensions(data, Path(path).suffix) != (width, height):
        raise OutfitPackError(
            "Asset integrity check requires attention; retry the operation.",
            reason="manifest_asset_hash_mismatch",
            asset_path=path,
        )
    return AppearanceAsset(
        slot, path, entry["sha256"], width, height, anchor[0], anchor[1],
        z_order, occludes_makeup, clears_base,
    )


def required_pose_keys(
    poses: object,
    silhouette_scope: object,
    required_silhouettes: tuple[str, ...],
    pose_atlas_silhouettes: tuple[str, ...],
    supported_silhouettes: tuple[str, ...],
    source_bound_silhouettes: frozenset[str] = frozenset(),
) -> tuple[str, ...]:
    """Validate either the complete runtime set or an explicit full-body set."""

    if not isinstance(poses, dict):
        raise OutfitPackError("Every required silhouette must be declared.")
    keys = set(poses)
    if silhouette_scope is None:
        required = set(required_silhouettes) - set(source_bound_silhouettes)
    elif silhouette_scope == FULL_BODY_SILHOUETTE_SCOPE:
        if source_bound_silhouettes:
            raise OutfitPackError(
                "Full-body appearance variants cannot omit source-bound views."
            )
        required = set(pose_atlas_silhouettes)
    else:
        raise OutfitPackError("Provide a supported silhouette scope.")
    if keys != required:
        missing = sorted(required - keys)
        unexpected = sorted(keys - required)
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected: {', '.join(unexpected)}")
        contract = (
            "the complete v2 view set"
            if silhouette_scope is None
            else "its complete declared view set"
        )
        raise OutfitPackError(
            f"Every appearance variant requires {contract} ("
            + "; ".join(details)
            + ")."
        )
    return tuple(
        silhouette for silhouette in supported_silhouettes if silhouette in required
    )


def _safe_member(info: zipfile.ZipInfo) -> None:
    path = PurePosixPath(info.filename)
    if info.is_dir() or path.is_absolute() or ".." in path.parts or "\\" in info.filename:
        raise OutfitPackError(
            "Provide a supported archive path.",
            reason="asset_path_traversal",
            asset_path=info.filename,
        )
    if info.flag_bits & 1 or info.file_size > MAX_MEMBER_BYTES:
        raise OutfitPackError("Provide a supported archive member.")
    if (info.external_attr >> 16) & 0o170000 == SYMLINK_FILE_TYPE:
        raise OutfitPackError("Symbolic links require a supported archive entry.")
    if info.filename != MANIFEST and not ASSET_PATH.fullmatch(info.filename):
        raise OutfitPackError("Provide a supported archive member path.")
    if info.file_size / max(1, info.compress_size) > MAX_COMPRESSION_RATIO:
        raise OutfitPackError("Suspicious compression ratio.")


def _png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < MIN_PNG_HEADER_LENGTH or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise OutfitPackError("Provide a supported PNG asset.")
    return struct.unpack(">II", data[16:24])


class PoseAsset(Protocol):
    """Read-only geometry required from a frozen appearance asset declaration."""

    @property
    def path(self) -> str: ...

    @property
    def width(self) -> int: ...

    @property
    def height(self) -> int: ...

    @property
    def anchor_x(self) -> int: ...

    @property
    def anchor_y(self) -> int: ...


def validate_author(value: object) -> str:
    """Validate the pack's author declaration while preserving its public limit."""
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > MAX_AUTHOR_LENGTH:
        raise OutfitPackError("Provide a supported author declaration.")
    return value.strip()


def validate_png_appearance(data: bytes, *, require_visible: bool) -> None:
    """Validate alpha semantics shared by the sealed pack and runtime paths."""

    image = image_from_png(data)
    if image.isNull():
        raise OutfitPackError("Provide a supported PNG appearance asset.")
    if image.hasAlphaChannel() is False:
        raise OutfitPackError("PNG appearance assets must have an alpha channel.")
    if require_visible:
        rgba = image.convertToFormat(QImage.Format_RGBA8888)
        if not any(bytes(rgba.bits())[3::4]):
            raise OutfitPackError("Garment appearance assets must contain visible pixels.")


def validate_pose_assets(
    assets: tuple[PoseAsset, ...],
    archive: zipfile.ZipFile,
    canvas: tuple[int, int],
    *,
    require_visible: bool,
    full_canvas: bool = False,
) -> None:
    """Apply runtime geometry and PNG checks to one authored view."""

    for asset in assets:
        if full_canvas and (asset.width, asset.height, asset.anchor_x, asset.anchor_y) != (*canvas, 0, 0):
            raise OutfitPackError(f"Makeup layers must cover the full {canvas[0]}x{canvas[1]} canvas at anchor 0,0.")
        if (
            asset.anchor_x < 0
            or asset.anchor_y < 0
            or asset.anchor_x + asset.width > canvas[0]
            or asset.anchor_y + asset.height > canvas[1]
        ):
            raise OutfitPackError("Asset geometry escapes the runtime canvas.")
        # Visible-pixel rules are not repeated at runtime, so only alpha-only
        # checks may be deferred to the runtime layer decode.
        if Path(asset.path).suffix.lower() == ".png" and (
            require_visible or _PNG_CONTENT_VALIDATION.get()
        ):
            validate_png_appearance(archive.read(asset.path), require_visible=require_visible)


def _webp_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < MIN_WEBP_HEADER_LENGTH or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise OutfitPackError("Provide a supported WebP asset.")
    if data[12:16] != b"VP8X":
        raise OutfitPackError("Provide a supported WebP header.")
    return (
        int.from_bytes(data[24:27], "little") + 1,
        int.from_bytes(data[27:30], "little") + 1,
    )


def _validate_svg_tree(root: ElementTree.Element) -> None:
    unsafe_markers = ("url(", "javascript:", "data:")
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] not in SVG_ELEMENTS:
            raise OutfitPackError("Provide a supported SVG element.")
        for name, value in element.attrib.items():
            local = name.rsplit("}", 1)[-1].lower()
            unsafe_name = local.startswith("on") or local in {"href", "src"}
            if unsafe_name or any(marker in value.lower() for marker in unsafe_markers):
                raise OutfitPackError("Provide a supported SVG content.")


def _svg_dimensions(data: bytes) -> tuple[int, int]:
    lowered = data.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise OutfitPackError("SVG DTD declarations require supported document content.")
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        raise OutfitPackError("Provide a supported SVG asset.") from None
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
        raise OutfitPackError("Provide a supported outfit asset path.")
    dimensions = _dimensions(data, Path(path).suffix)
    if any(not 1 <= value <= MAX_IMAGE_DIMENSION for value in dimensions):
        raise OutfitPackError("Asset dimensions exceed the supported range.")
    return dimensions
