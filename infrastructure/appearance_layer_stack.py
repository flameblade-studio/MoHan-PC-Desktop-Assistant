"""Preserve the depth boundary between rear hair and the character body."""
from __future__ import annotations
lazy from collections.abc import Callable, Iterator, Sequence
lazy from dataclasses import dataclass
lazy from typing import overload
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap, QRegion

Layer = tuple[QPixmap, int, int, QRegion, float]


class CoreMotionError(Exception):
    """Carry a motion error across asset-only fallback boundaries unchanged."""

    def __init__(self, original: Exception) -> None:
        super().__init__(str(original))
        self.original = original


@dataclass(frozen=True)
class AppearanceCallbacks:
    """Core-owned updates at the body and skin composition boundaries."""

    before_front_hair: Callable[[QPixmap], QPixmap] | None = None
    replace_body: Callable[[QPixmap], QPixmap] | None = None

    def validate_reviewed_frame(self, frame: QPixmap | None) -> None:
        if frame is not None and self.replace_body is not None:
            raise CoreMotionError(ValueError(
                "Complete body replacement requires the full-body appearance route"
            ))


def clear_appearance_base(
    frame: QPixmap, silhouette: QRegion | None, replacement: QRegion | None,
) -> QPixmap:
    """Prepare an alpha-capable native frame with declared replacement areas cleared."""
    if silhouette is None and replacement is None:
        return QPixmap(frame)
    result = QPixmap(frame.size())
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.drawPixmap(0, 0, frame)
    erase = QRegion() if replacement is None else QRegion(replacement)
    if silhouette is not None:
        erase = erase.united(QRegion(frame.rect()).subtracted(silhouette))
    painter.setCompositionMode(QPainter.CompositionMode_Clear)
    painter.setClipRegion(erase)
    painter.fillRect(result.rect(), Qt.transparent)
    painter.end()
    return result


@dataclass(frozen=True)
class AppearanceLayerStack(Sequence[Layer]):
    behind_body: tuple[Layer, ...]
    foreground: tuple[Layer, ...]
    # Makeup is sorted before appearance layers by the pack z-order contract.
    # Keep that boundary on the stack so the combined legacy renderer can use
    # SourceAtop for makeup while preserving the public five-field Layer tuple.
    makeup_prefix_count: int = 0
    # Front hair and explicitly declared garment/headwear assets cover makeup.
    front_hair_indices: frozenset[int] = frozenset()
    makeup_occluder_indices: frozenset[int] = frozenset()
    # Layers authored below repaintable core hands. Their native alpha remains
    # intact; draw order, rather than a binary region cut-out, provides depth.
    behind_hand_indices: frozenset[int] = frozenset()

    def __len__(self) -> int:
        return len(self.behind_body) + len(self.foreground)

    def __iter__(self) -> Iterator[Layer]:
        yield from self.behind_body
        yield from self.foreground

    @overload
    def __getitem__(self, index: int) -> Layer: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[Layer, ...]: ...

    def __getitem__(self, index: int | slice) -> Layer | tuple[Layer, ...]:
        return (*self.behind_body, *self.foreground)[index]


def paint_behind_body(painter: QPainter, layers: Sequence[Layer]) -> Sequence[Layer]:
    """Underpaint rear hair; return the normal foreground draw sequence."""
    if not isinstance(layers, AppearanceLayerStack):
        return layers
    painter.setCompositionMode(QPainter.CompositionMode_DestinationOver)
    for pixmap, x, y, clip, opacity in reversed(layers.behind_body):
        painter.setClipRegion(clip)
        painter.setOpacity(opacity)
        painter.drawPixmap(x, y, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    return layers.foreground


def split_hand_depth(
    layers: Sequence[Layer],
    foreground: Sequence[Layer],
    hand_region: QRegion,
) -> tuple[tuple[Layer, ...], tuple[Layer, ...]]:
    """Split hand underlays spatially while retaining the outside draw order."""
    if not isinstance(layers, AppearanceLayerStack):
        return (), tuple(foreground)
    under: list[Layer] = []
    above: list[Layer] = []
    for index, layer in enumerate(foreground):
        pixmap, x, y, clip, opacity = layer
        if index not in layers.behind_hand_indices:
            above.append(layer)
            continue
        under_clip = clip.intersected(hand_region)
        above_clip = clip.subtracted(hand_region)
        if not under_clip.isEmpty():
            under.append((pixmap, x, y, under_clip, opacity))
        if not above_clip.isEmpty():
            above.append((pixmap, x, y, above_clip, opacity))
    return tuple(under), tuple(above)


def split_hand_makeup_depth(
    layers: Sequence[Layer],
    foreground: Sequence[Layer],
    hand_region: QRegion,
) -> tuple[tuple[Layer, ...], tuple[Layer, ...], tuple[Layer, ...]]:
    """Split hand underlays plus the callback's early/deferred foreground."""
    if not isinstance(layers, AppearanceLayerStack):
        early, deferred = split_makeup_depth(layers, foreground)
        return (), early, deferred
    deferred_indices = layers.front_hair_indices | layers.makeup_occluder_indices
    under: list[Layer] = []
    early: list[Layer] = []
    deferred: list[Layer] = []
    for index, layer in enumerate(foreground):
        pixmap, x, y, clip, opacity = layer
        if index in layers.behind_hand_indices:
            under_clip = clip.intersected(hand_region)
            clip = clip.subtracted(hand_region)
            if not under_clip.isEmpty():
                under.append((pixmap, x, y, under_clip, opacity))
        if not clip.isEmpty():
            target = deferred if index in deferred_indices else early
            target.append((pixmap, x, y, clip, opacity))
    return tuple(under), tuple(early), tuple(deferred)


def split_makeup_depth(layers: Sequence[Layer], foreground: Sequence[Layer]) -> tuple[tuple[Layer, ...], tuple[Layer, ...]]:
    """Preserve order within the legacy and explicitly deferred paint stages."""
    indices = (
        layers.front_hair_indices | layers.makeup_occluder_indices
        if isinstance(layers, AppearanceLayerStack)
        else frozenset()
    )
    return (
        tuple(layer for index, layer in enumerate(foreground) if index not in indices),
        tuple(layer for index, layer in enumerate(foreground) if index in indices),
    )
