"""Composite body-pack layers while preserving the body-owned face core."""
from __future__ import annotations

lazy from collections import OrderedDict
lazy from collections.abc import Callable
lazy import re
lazy from PIL import Image as PILImage

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QBitmap, QImage, QPainter, QPixmap, QRegion

lazy from domain.character_layer_plan import (
    CharacterLayerAsset,
    CharacterLayerMask,
    CharacterLayerPlan,
)
lazy from infrastructure.appearance_layer_stack import clear_appearance_base

LayerRecord = CharacterLayerAsset | CharacterLayerMask
ImageLoader = Callable[[LayerRecord], QPixmap]
__all__ = ["body_pack_alpha_region", "compose_body_pack_frame"]

MAX_ALPHA_REGION_CACHE_BYTES = 8 * 1024 * 1024
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ALPHA_REGIONS: OrderedDict[str, tuple[QRegion, int]] = OrderedDict()
_alpha_region_cache_bytes = 0


def compose_body_pack_frame(
    base: QPixmap,
    plan: CharacterLayerPlan | None,
    load_image: ImageLoader,
    face_core: QRegion | None = None,
) -> QPixmap:
    """Draw declared stages on the GUI thread and preserve body-owned pixels.

    A missing plan returns a copy of the supplied frame without calling the
    loader, leaving route selection to the composition boundary.
    Makeup is clipped to the protected face core and painted SourceAtop after
    the base and before garments. Other character layers stay outside that
    core, so they cannot cover its body-owned makeup.
    """
    if plan is None:
        return QPixmap(base)
    if base.isNull():
        raise ValueError("Body-pack composition requires a valid base frame.")

    canvas = QRegion(base.rect())
    protected = QRegion() if face_core is None else QRegion(face_core).intersected(canvas)
    layer_clip = canvas.subtracted(protected)

    base_hide = QRegion()
    if plan.base_hide is not None:
        mask = _load_canvas_image(load_image, plan.base_hide, base, alpha_required=True)
        base_hide = body_pack_alpha_region(mask, plan.base_hide.sha256).subtracted(protected)
    cleared_base = clear_appearance_base(base, None, base_hide)

    layers_by_kind: dict[str, list[QPixmap]] = {}
    for record in plan.layers:
        image = _load_canvas_image(load_image, record, base, alpha_required=False)
        layers_by_kind.setdefault(record.kind, []).append(image)

    result = QPixmap(base.size())
    result.fill(Qt.transparent)
    painter = QPainter(result)
    try:
        for stage in plan.order:
            if stage == "base":
                painter.setClipRegion(canvas)
                painter.drawPixmap(0, 0, cleared_base)
                continue
            if stage == "makeup":
                painter.setClipRegion(protected)
                painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
                for image in layers_by_kind.get(stage, ()):
                    painter.drawPixmap(0, 0, image)
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                continue
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            for image in layers_by_kind.get(stage, ()):
                painter.setClipRegion(layer_clip)
                painter.drawPixmap(0, 0, image)
    finally:
        painter.end()
    return result


def _load_canvas_image(
    load_image: ImageLoader,
    record: LayerRecord,
    base: QPixmap,
    *,
    alpha_required: bool,
) -> QPixmap:
    image = load_image(record)
    if not isinstance(image, QPixmap):
        raise TypeError(f"Image loader must return QPixmap for {record.path!r}.")
    if image.isNull():
        raise ValueError(f"Character asset {record.path!r} could not be decoded.")
    if image.size() != base.size():
        raise ValueError(f"Character asset {record.path!r} must match the base canvas size.")
    if record.anchor != (0, 0):
        raise ValueError(f"Character asset {record.path!r} must use anchor [0, 0].")
    if alpha_required and not image.hasAlphaChannel():
        raise ValueError(f"Base hide mask {record.path!r} must contain alpha.")
    return image


def body_pack_alpha_region(mask: QPixmap, digest: str | None = None) -> QRegion:
    """Return nonzero-alpha pixels using Qt masks; call on the GUI thread.

    A supplied SHA-256 identifies immutable package bytes and shares the
    bounded alpha-region cache across decoded pixmaps. In-memory callers use
    the pixmap cache key. Alpha values 1–127 remain included.
    """
    if not isinstance(mask, QPixmap):
        raise TypeError("Alpha regions require a QPixmap.")
    if mask.isNull():
        raise ValueError("Alpha regions require a decoded image.")
    if not mask.hasAlphaChannel():
        raise ValueError("Alpha regions require an alpha channel.")

    global _alpha_region_cache_bytes
    if digest is not None and not _SHA256.fullmatch(digest):
        raise ValueError("Alpha-region cache digest must be a lowercase SHA-256.")
    cache_key = f"sha256:{digest}" if digest is not None else f"pixmap:{mask.cacheKey()}"
    cached = _ALPHA_REGIONS.get(cache_key)
    if cached is not None:
        _ALPHA_REGIONS.move_to_end(cache_key)
        return QRegion(cached[0])

    image = mask.toImage().convertToFormat(QImage.Format_RGBA8888)
    pixels = bytes(image.constBits()[:image.sizeInBytes()])
    alpha = PILImage.frombytes("RGBA", (image.width(), image.height()), pixels).getchannel("A")
    binary_alpha = alpha.point(lambda value: 255 if value else 0).tobytes()
    binary_pixels = bytearray(image.width() * image.height() * 4)
    binary_pixels[3::4] = binary_alpha
    binary_image = QImage(
        binary_pixels, image.width(), image.height(), image.width() * 4, QImage.Format_RGBA8888,
    ).copy()
    alpha_mask = binary_image.createAlphaMask()
    region = QRegion(QBitmap.fromImage(alpha_mask))
    weight = max(128, region.rectCount() * 64)
    if weight <= MAX_ALPHA_REGION_CACHE_BYTES:
        previous = _ALPHA_REGIONS.pop(cache_key, None)
        if previous is not None:
            _alpha_region_cache_bytes -= previous[1]
        _ALPHA_REGIONS[cache_key] = (QRegion(region), weight)
        _alpha_region_cache_bytes += weight
        while _alpha_region_cache_bytes > MAX_ALPHA_REGION_CACHE_BYTES:
            _, (_, removed_weight) = _ALPHA_REGIONS.popitem(last=False)
            _alpha_region_cache_bytes -= removed_weight
    return region
