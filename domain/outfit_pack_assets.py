"""Archive-member and image-format primitives shared by the outfit-pack parser and builders.

Split out of ``domain.outfit_pack`` so that module stays under its line ratchet;
``domain.outfit_pack`` re-exports the error classes, so existing
``from domain.outfit_pack import OutfitPackError`` imports keep working.
"""

from __future__ import annotations

lazy import re
lazy import struct
lazy import zipfile
lazy from pathlib import Path, PurePosixPath
lazy from xml.etree import ElementTree

MANIFEST = "manifest.json"
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
MAX_IMAGE_DIMENSION = 4096
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
    """The pack was authored for another body-profile generation and is never grandfathered."""


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
