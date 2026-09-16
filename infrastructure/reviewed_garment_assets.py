"""Load and compose owner reviewed native garment layers.

This module is intentionally a small single-pose extension point.  It does
not change the seven-part detachable half-body contract: a reviewed garment
manifest binds one pose to one exact outfit selection, one native source
digest, one native visibility mask, and an ordered set of full-canvas RGBA
layers.  All bytes and decoded images are captured while loading so composing
never re-reads the asset root.
"""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import struct
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath
lazy from types import MappingProxyType
lazy from typing import Mapping, overload

lazy from PySide6.QtGui import QImage, QPainter, QPixmap


SCHEMA = "mohan.reviewed-native-garments.v1"
DIMENSION = 1254
SHA256_HEX_LENGTH = 64
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_HEADER_LENGTH = 26
_PNG_IHDR_START = 16
_PNG_IHDR_END = 24
_RGBA_COLOR_TYPE = 6
_GRAYSCALE_COLOR_TYPE = 0
_EIGHT_BIT_DEPTH = 8
NATIVE_APPEARANCE_CATEGORIES = frozenset({"hairstyle", "headwear"})
# The one declared frame-dynamic source a reviewed pose may name.  A pose that
# declares it states that the installed complete half-body expression set owns
# its frame dynamics, so its retained reviewed motion root is not authoritative
# and must not be loaded.  Anything else stays fail-closed.
COMPLETE_EXPRESSION_DYNAMIC_SOURCE = "complete-expressions"
DYNAMIC_SOURCES = frozenset({COMPLETE_EXPRESSION_DYNAMIC_SOURCE})


@dataclass(frozen=True, slots=True)
class ReviewedSelection:
    """The exact installed garment selection bound to one reviewed pose."""

    pack_id: str
    item_id: str
    variant_id: str

    def matches(self, pack_id: str, item_id: str, variant_id: str) -> bool:
        return (
            self.pack_id == pack_id
            and self.item_id == item_id
            and self.variant_id == variant_id
        )


@dataclass(frozen=True, slots=True)
class ReviewedPng:
    """A verified PNG's original bytes plus its decoded, in-memory image."""

    path: str
    sha256: str
    payload: bytes
    image: QImage


def _grayscale_as_alpha(image: QImage) -> QImage:
    """Copy grayscale bytes into an Alpha8 image without touching disk."""

    gray = image.convertToFormat(QImage.Format.Format_Grayscale8)
    alpha = QImage(gray.size(), QImage.Format.Format_Alpha8)
    source = bytes(gray.constBits())
    target = alpha.bits()
    for row in range(gray.height()):
        source_start = row * gray.bytesPerLine()
        target_start = row * alpha.bytesPerLine()
        width = gray.width()
        target[target_start : target_start + width] = source[
            source_start : source_start + width
        ]
    return alpha


@dataclass(frozen=True, slots=True)
class ReviewedGarmentPose:
    """One reviewed pose and its immutable in-memory composition inputs."""

    pose: str
    native_source_sha256: str
    visibility: ReviewedPng
    ordered_layers: tuple[ReviewedPng, ...]
    selection_exact: ReviewedSelection
    native_appearance_selections: Mapping[str, ReviewedSelection]
    native_source: ReviewedPng | None = None
    motion_required: bool = False
    approved_source_sha256: str | None = None
    # The declared authority for this pose's frame dynamics, or ``None`` when the
    # pose has not declared one.  ``complete-expressions`` means the installed
    # complete half-body expression set answers for this pose and its retained
    # reviewed motion root is no longer authoritative.
    dynamic_source: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "native_appearance_selections",
            MappingProxyType(dict(self.native_appearance_selections)),
        )

    @property
    def layers(self) -> tuple[ReviewedPng, ...]:
        """Expose the manifest order through the short overlay-facing name."""

        return self.ordered_layers

    @overload
    def compose(self, frame: QImage) -> QImage: ...

    @overload
    def compose(self, frame: QPixmap) -> QPixmap: ...

    def compose(self, frame: QImage | QPixmap) -> QImage | QPixmap:
        """Apply this pose over a copied native frame without mutating it.

        The visibility image is converted to an alpha image and applied with
        ``DestinationIn`` first.  This keeps the current native expression in
        its declared visible region.  The ordered full-canvas RGBA layers are
        then painted with ``SourceOver``; their order is authoritative, so the
        manifest can express garment, native lower hand, and cuff depth.
        """

        return_pixmap = isinstance(frame, QPixmap)
        if isinstance(frame, QPixmap):
            if frame.isNull():
                raise ValueError("Reviewed garment composition needs a non-null frame.")
            source = frame.toImage()
        elif isinstance(frame, QImage):
            if frame.isNull():
                raise ValueError("Reviewed garment composition needs a non-null frame.")
            source = frame
        else:
            raise TypeError("Reviewed garment composition expects QImage or QPixmap.")
        if (source.width(), source.height()) != (DIMENSION, DIMENSION):
            raise ValueError("Reviewed garment composition requires a 1254x1254 frame.")

        # ``copy`` detaches Qt's implicit storage before any painter operation;
        # the caller's source frame therefore remains byte-for-byte untouched.
        result = source.convertToFormat(QImage.Format.Format_RGBA8888).copy()
        # Qt treats a Grayscale8 source as opaque when used by a composition
        # mode.  Copy the gray bytes into Alpha8 so DestinationIn receives the
        # intended per-pixel visibility multiplier.
        visibility_alpha = _grayscale_as_alpha(self.visibility.image)

        painter = QPainter(result)
        try:
            if not painter.isActive():
                raise ValueError("Could not begin reviewed garment composition.")
            painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            painter.drawImage(0, 0, visibility_alpha)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            for layer in self.ordered_layers:
                painter.drawImage(0, 0, layer.image)
        finally:
            painter.end()

        if return_pixmap:
            return QPixmap.fromImage(result)
        return result


@dataclass(frozen=True, slots=True)
class ReviewedGarmentAssets:
    """The validated reviewed-native-garment manifest held entirely in memory."""

    root: Path
    poses: Mapping[str, ReviewedGarmentPose]

    def __post_init__(self) -> None:
        object.__setattr__(self, "poses", MappingProxyType(dict(self.poses)))

    def match(
        self,
        view_id: str,
        pack_id: str,
        item_id: str,
        variant_id: str,
    ) -> ReviewedGarmentPose | None:
        """Return a pose only for the manifest's exact outfit selection."""

        pose = self.poses.get(view_id)
        if pose is None or not pose.selection_exact.matches(pack_id, item_id, variant_id):
            return None
        return pose


def _valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == SHA256_HEX_LENGTH
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _selection(value: object, *, context: str) -> ReviewedSelection:
    if not isinstance(value, dict):
        raise ValueError(f"Invalid reviewed garment selection: {context}")
    fields = ("pack_id", "item_id", "variant_id")
    if any(not isinstance(value.get(field), str) or not value[field] for field in fields):
        raise ValueError(f"Invalid reviewed garment selection: {context}")
    return ReviewedSelection(*(value[field] for field in fields))


def _safe_relative_path(root: Path, relative: object, *, context: str) -> tuple[str, Path]:
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"Invalid reviewed garment path: {context}")
    if relative.startswith(("/", "\\")) or "\\" in relative:
        raise ValueError(f"Reviewed garment path must be portable and relative: {context}")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"Reviewed garment path escapes its root: {context}")
    candidate = (root / Path(*pure.parts)).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"Reviewed garment path escapes its root: {context}")
    return relative, candidate


def _png_header(payload: bytes, *, context: str) -> tuple[int, int, int, int]:
    if len(payload) < _PNG_HEADER_LENGTH or payload[:8] != PNG_SIGNATURE:
        raise ValueError(f"Reviewed garment asset is not a PNG: {context}")
    width, height = struct.unpack(">II", payload[_PNG_IHDR_START:_PNG_IHDR_END])
    return width, height, payload[24], payload[25]


def _read_png(
    root: Path,
    record: object,
    *,
    context: str,
    grayscale: bool,
) -> ReviewedPng:
    if not isinstance(record, dict):
        raise ValueError(f"Invalid reviewed garment PNG record: {context}")
    relative, path = _safe_relative_path(root, record.get("path"), context=context)
    expected_sha = record.get("sha256")
    if not _valid_sha256(expected_sha):
        raise ValueError(f"Invalid reviewed garment SHA-256: {context}")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"Missing reviewed garment asset: {relative}") from exc
    actual_sha = hashlib.sha256(payload).hexdigest()
    if actual_sha != expected_sha:
        raise ValueError(f"Reviewed garment SHA-256 mismatch: {relative}")
    width, height, depth, color_type = _png_header(payload, context=relative)
    expected_color_type = _GRAYSCALE_COLOR_TYPE if grayscale else _RGBA_COLOR_TYPE
    if depth != _EIGHT_BIT_DEPTH or color_type != expected_color_type:
        expected = "8-bit grayscale" if grayscale else "8-bit RGBA"
        raise ValueError(f"Reviewed garment asset must be {expected}: {relative}")
    image = QImage.fromData(payload, "PNG")
    if image.isNull() or (width, height) != (DIMENSION, DIMENSION):
        raise ValueError(f"Invalid reviewed garment dimensions: {relative}")
    if (image.width(), image.height()) != (DIMENSION, DIMENSION):
        raise ValueError(f"Invalid reviewed garment dimensions: {relative}")
    decoded = image.convertToFormat(
        QImage.Format.Format_Grayscale8
        if grayscale
        else QImage.Format.Format_RGBA8888
    )
    return ReviewedPng(relative, expected_sha, payload, decoded)


def _load_pose(root: Path, pose_name: str, record: object) -> ReviewedGarmentPose:
    if not isinstance(pose_name, str) or not pose_name or "/" in pose_name or "\\" in pose_name:
        raise ValueError("Invalid reviewed garment pose id.")
    if not isinstance(record, dict):
        raise ValueError(f"Invalid reviewed garment pose: {pose_name}")
    native_sha = record.get("native_source_sha256")
    if not _valid_sha256(native_sha):
        raise ValueError(f"Invalid native source SHA-256: {pose_name}")
    name = record.get("native_source_file")
    if (
        not isinstance(name, str)
        or len(PurePosixPath(name).parts) != 1
        or not name.endswith(".png")
        or ":" in name
    ):
        raise ValueError(f"Native source must name one PNG in the expression directory: {pose_name}")
    native_source = _read_png(
        root.parent, {"path": name, "sha256": native_sha},
        context=f"{pose_name}/native_source", grayscale=False,
    )
    visibility = _read_png(
        root,
        record.get("visibility"),
        context=f"{pose_name}/visibility",
        grayscale=True,
    )
    raw_layers = record.get("ordered_layers")
    if not isinstance(raw_layers, list) or not raw_layers:
        raise ValueError(f"Reviewed garment pose has no ordered layers: {pose_name}")
    layers: list[ReviewedPng] = []
    seen_paths: set[str] = set()
    for index, layer_record in enumerate(raw_layers):
        layer = _read_png(
            root,
            layer_record,
            context=f"{pose_name}/ordered_layers[{index}]",
            grayscale=False,
        )
        if layer.path in seen_paths:
            raise ValueError(f"Duplicate reviewed garment layer path: {layer.path}")
        seen_paths.add(layer.path)
        layers.append(layer)
    selection = _selection(record.get("selection_exact"), context=pose_name)
    raw_native_selections = record.get("native_appearance_selections", {})
    if not isinstance(raw_native_selections, dict):
        raise ValueError(f"Invalid native appearance selections: {pose_name}")
    if not set(raw_native_selections) <= NATIVE_APPEARANCE_CATEGORIES:
        raise ValueError(
            f"Native appearance selections may only declare hairstyle/headwear: {pose_name}"
        )
    native_selections = {
        category: _selection(value, context=f"{pose_name}/{category}")
        for category, value in raw_native_selections.items()
        if isinstance(category, str) and category
    }
    if len(native_selections) != len(raw_native_selections):
        raise ValueError(f"Invalid native appearance selection category: {pose_name}")
    motion_required = record.get("motion_required", False)
    if not isinstance(motion_required, bool):
        raise ValueError(f"Invalid reviewed motion requirement: {pose_name}")
    approved_source_sha = record.get("approved_source_sha256")
    if approved_source_sha is not None and not _valid_sha256(approved_source_sha):
        raise ValueError(f"Invalid approved source SHA-256: {pose_name}")
    dynamic_source = record.get("dynamic_source")
    if dynamic_source is not None and dynamic_source not in DYNAMIC_SOURCES:
        raise ValueError(f"Unsupported reviewed pose dynamic source: {pose_name}")
    return ReviewedGarmentPose(
        pose=pose_name,
        native_source_sha256=native_sha,
        visibility=visibility,
        ordered_layers=tuple(layers),
        selection_exact=selection,
        native_appearance_selections=native_selections,
        native_source=native_source,
        motion_required=motion_required,
        approved_source_sha256=approved_source_sha,
        dynamic_source=dynamic_source,
    )


def load_reviewed_garment_assets(root: Path) -> ReviewedGarmentAssets | None:
    """Load a reviewed garment root; only a missing root means uninstalled.

    Every other problem is a ``ValueError`` so an incomplete or drifting
    installation cannot silently fall back into a production composition.
    """

    requested_root = Path(root)
    if not requested_root.exists():
        return None
    if not requested_root.is_dir():
        raise ValueError("Reviewed garment asset root must be a directory.")
    resolved_root = requested_root.resolve()
    manifest_path = resolved_root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("Reviewed garment asset root lacks manifest.json.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid reviewed garment manifest JSON.") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise ValueError("Invalid reviewed garment manifest schema.")
    raw_poses = manifest.get("poses")
    if not isinstance(raw_poses, dict) or not raw_poses:
        raise ValueError("Reviewed garment manifest must declare poses.")
    poses = {
        pose_name: _load_pose(resolved_root, pose_name, record)
        for pose_name, record in raw_poses.items()
    }
    return ReviewedGarmentAssets(resolved_root, poses)
