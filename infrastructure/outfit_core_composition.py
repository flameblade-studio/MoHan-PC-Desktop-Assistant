"""Paint appearance and core hands in their declared depth order."""
from __future__ import annotations

lazy from collections.abc import Callable, Sequence
lazy from PySide6.QtGui import QPainter, QPixmap, QRegion
lazy from infrastructure.appearance_layer_stack import AppearanceLayerStack, Layer, split_hand_depth


class _AppearanceCompositionError(Exception):
    """An asset phase requires attention; core-motion programming errors must propagate."""


def replace_restored_body(
    frame: QPixmap, overlays: Sequence[Layer],
    replace_body: Callable[[QPixmap], QPixmap] | None,
) -> tuple[QPixmap, Sequence[Layer]]:
    """Apply a complete body expression before any detachable appearance."""
    if replace_body is None:
        return frame, overlays
    painter = QPainter(frame)
    _paint_overlay_layers(painter, overlays)
    painter.end()
    return replace_body(frame), ()


def _paint_foreground_layers(
    painter: QPainter,
    layers: AppearanceLayerStack | Sequence[Layer],
    foreground: Sequence[Layer],
    *,
    makeup_prefix_count: int | None = None,
) -> None:
    """Paint the ordered foreground, preserving native alpha for makeup.

    The combined ``apply`` path keeps the historical z-order where makeup is
    below garments. ``makeup_prefix_count`` records that boundary without
    changing the layer tuple consumed by existing callers and tests.
    """
    makeup_count = makeup_prefix_count
    if makeup_count is None:
        makeup_count = layers.makeup_prefix_count if isinstance(layers, AppearanceLayerStack) else 0
    if makeup_count < 0 or makeup_count > len(foreground):
        raise _AppearanceCompositionError
    for index, (pixmap, anchor_x, anchor_y, clip, opacity) in enumerate(foreground):
        painter.setCompositionMode(
            QPainter.CompositionMode_SourceAtop
            if index < makeup_count
            else QPainter.CompositionMode_SourceOver
        )
        painter.setClipRegion(clip)
        painter.setOpacity(opacity)
        painter.drawPixmap(anchor_x, anchor_y, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)


def _hand_region(hand_overlays: Sequence[Layer]) -> QRegion:
    region = QRegion()
    for _pixmap, _x, _y, clip, _opacity in hand_overlays:
        region = region.united(clip)
    return region


def _prepare_core_hand_depth(
    painter: QPainter,
    layers: AppearanceLayerStack | Sequence[Layer],
    foreground: Sequence[Layer],
    body_overlays: Sequence[Layer],
    hand_overlays: Sequence[Layer],
) -> tuple[Layer, ...]:
    """Paint body and only the portions authored underneath alpha-aware hands."""
    _paint_overlay_layers(painter, body_overlays)
    if not hand_overlays:
        return tuple(foreground)
    behind_hands, above_hands = split_hand_depth(layers, foreground, _hand_region(hand_overlays))
    _paint_foreground_layers(painter, behind_hands, behind_hands, makeup_prefix_count=0)
    return above_hands


def _paint_overlay_layers(painter: QPainter, overlays: Sequence[Layer]) -> None:
    """Paint native RGBA overlays in their declared clips."""
    for pixmap, anchor_x, anchor_y, clip, opacity in overlays:
        painter.setClipRegion(clip)
        painter.setOpacity(opacity)
        painter.drawPixmap(anchor_x, anchor_y, pixmap)


def _paint_depth_tail(
    painter: QPainter,
    layers: AppearanceLayerStack | Sequence[Layer],
    foreground: Sequence[Layer],
    *,
    makeup_prefix_count: int | None = None,
) -> None:
    """Paint layers above hands with their established makeup prefix."""
    _paint_foreground_layers(
        painter,
        layers,
        foreground,
        makeup_prefix_count=makeup_prefix_count,
    )
