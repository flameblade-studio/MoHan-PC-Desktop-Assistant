"""Composite body-pack layers while preserving the body-owned face core."""
from __future__ import annotations

lazy from collections.abc import Callable

lazy from PySide6.QtCore import Qt, QRect
lazy from PySide6.QtGui import QImage, QPainter, QPixmap, QRegion

lazy from domain.character_layer_plan import (
    CharacterLayerAsset,
    CharacterLayerMask,
    CharacterLayerPlan,
)
lazy from infrastructure.appearance_layer_stack import clear_appearance_base

LayerRecord = CharacterLayerAsset | CharacterLayerMask
ImageLoader = Callable[[LayerRecord], QPixmap]
__all__ = ["body_pack_alpha_region", "compose_body_pack_frame"]


def compose_body_pack_frame(
    base: QPixmap,
    plan: CharacterLayerPlan | None,
    load_image: ImageLoader,
    face_core: QRegion | None = None,
) -> QPixmap:
    """Draw each declared stage in order and keep face-core pixels body-owned.

    A missing plan returns a copy of the supplied frame without calling the
    loader, leaving route selection to the composition boundary.
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
        base_hide = body_pack_alpha_region(mask).subtracted(protected)
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


def body_pack_alpha_region(mask: QPixmap) -> QRegion:
    """Return every pixel whose alpha is nonzero, including alpha values 1–127."""
    if not isinstance(mask, QPixmap):
        raise TypeError("Alpha regions require a QPixmap.")
    if mask.isNull():
        raise ValueError("Alpha regions require a decoded image.")
    if not mask.hasAlphaChannel():
        raise ValueError("Alpha regions require an alpha channel.")

    image = mask.toImage().convertToFormat(QImage.Format_ARGB32)
    region = QRegion()
    for y in range(image.height()):
        x = 0
        while x < image.width():
            while x < image.width() and image.pixel(x, y) >> 24 == 0:
                x += 1
            start = x
            while x < image.width() and image.pixel(x, y) >> 24 != 0:
                x += 1
            if start < x:
                region = region.united(QRegion(QRect(start, y, x - start, 1)))
    return region
