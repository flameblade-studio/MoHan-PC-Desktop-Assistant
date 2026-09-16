"""Archive-member and image-format primitives shared by the outfit-pack parser and builders.

Split out of ``domain.outfit_pack`` so that module stays within its line ratchet;
``domain.outfit_pack`` re-exports the error classes, so existing
``from domain.outfit_pack import OutfitPackError`` imports keep working.
"""

from __future__ import annotations

lazy import re
lazy import struct
lazy import zipfile
lazy from pathlib import Path, PurePosixPath
lazy from typing import Protocol
lazy from PySide6.QtGui import QImage
lazy from xml.etree import ElementTree

MANIFEST = "manifest.json"
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
MAX_IMAGE_DIMENSION = 4096
MAX_AUTHOR_LENGTH = 120
MIN_PNG_HEADER_LENGTH = 24
MIN_WEBP_HEADER_LENGTH = 30
SYMLINK_FILE_TYPE = 0o120000
ASSET_PATH = re.compile(r"assets/[a-z0-9][a-z0-9_.+-]{0,127}\.(?:png|webp|svg)\Z")
SVG_ELEMENTS = frozenset({
    "svg", "g", "defs", "linearGradient", "radialGradient", "stop", "path",
    "rect", "circle", "ellipse", "line", "polyline", "polygon",
})


class OutfitPackError(RuntimeError):
    pass


class IncompatibleBodyProfileError(OutfitPackError):
    """The pack was authored for another body-profile generation and uses its own generation contract."""


def _safe_member(info: zipfile.ZipInfo) -> None:
    path = PurePosixPath(info.filename)
    if info.is_dir() or path.is_absolute() or ".." in path.parts or "\\" in info.filename:
        raise OutfitPackError("Provide a supported archive path.")
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

    image = QImage.fromData(data, "PNG")
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
        if Path(asset.path).suffix.lower() == ".png":
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
