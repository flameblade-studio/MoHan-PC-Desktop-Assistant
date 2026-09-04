from __future__ import annotations

lazy from dataclasses import dataclass
lazy from typing import Protocol

lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QTransform

lazy from domain.face_rig import (
    FaceMotionFrame,
    MouthShape,
    Viseme,
)

MOUTH_APERTURE_THRESHOLD = 0.01
SPEECH_MASK_FULL_ALPHA = 255
SPEECH_MASK_OPAQUE_ALPHA = 250
SPEECH_MASK_DARK_EDGE_MAX_RGB = 185
SPEECH_MASK_MIN_SKIN_RED = 150
SPEECH_MASK_MIN_SKIN_GREEN = 85
SPEECH_MASK_MIN_SKIN_BLUE = 65
SPEECH_MASK_MIN_RED_GREEN_DELTA = 20
SPEECH_MASK_MIN_GREEN_BLUE_DELTA = 5
SPEECH_MASK_MIN_SOURCE_LIFT = 16
SPEECH_MASK_CORNER_EDGE_WIDTH = 14


def recover_speech_mask_edge_source(
    mask: QPixmap | None,
    closed_reference: QPixmap | None,
    source: QPixmap | None,
    mouth_clip: QRect | None,
) -> QPixmap | None:
    """Recover source-backed mouth edges against the rendered closed frame."""

    if (
        mask is None
        or closed_reference is None
        or source is None
        or mouth_clip is None
        or mask.isNull()
        or closed_reference.isNull()
        or source.isNull()
    ):
        return mask
    mask_image = mask.toImage().convertToFormat(QImage.Format_ARGB32)
    closed_image = closed_reference.toImage().convertToFormat(QImage.Format_ARGB32)
    source_image = source.toImage().convertToFormat(QImage.Format_ARGB32)
    for y in range(mouth_clip.top(), mouth_clip.bottom() + 1):
        for x in range(mouth_clip.left(), mouth_clip.right() + 1):
            if (
                mouth_clip.left() + SPEECH_MASK_CORNER_EDGE_WIDTH <= x
                <= mouth_clip.right() - SPEECH_MASK_CORNER_EDGE_WIDTH
            ):
                continue
            mask_color = mask_image.pixelColor(x, y)
            if not 0 < mask_color.alpha() < SPEECH_MASK_FULL_ALPHA:
                continue
            closed_color = closed_image.pixelColor(x, y)
            if closed_color.alpha() < SPEECH_MASK_OPAQUE_ALPHA:
                continue
            closed_max = max(
                closed_color.red(),
                closed_color.green(),
                closed_color.blue(),
            )
            if closed_max > SPEECH_MASK_DARK_EDGE_MAX_RGB:
                continue
            source_color = source_image.pixelColor(x, y)
            source_max = max(
                source_color.red(),
                source_color.green(),
                source_color.blue(),
            )
            if not (
                source_color.alpha() >= SPEECH_MASK_OPAQUE_ALPHA
                and source_max >= closed_max + SPEECH_MASK_MIN_SOURCE_LIFT
                and source_color.red() >= SPEECH_MASK_MIN_SKIN_RED
                and source_color.green() >= SPEECH_MASK_MIN_SKIN_GREEN
                and source_color.blue() >= SPEECH_MASK_MIN_SKIN_BLUE
                and source_color.red() - source_color.green()
                >= SPEECH_MASK_MIN_RED_GREEN_DELTA
                and source_color.green() - source_color.blue()
                >= SPEECH_MASK_MIN_GREEN_BLUE_DELTA
            ):
                continue
            mask_image.setPixelColor(x, y, QColor(255, 255, 255, 255))
    return QPixmap.fromImage(mask_image)


@dataclass(frozen=True, slots=True)
class FaceRenderLayers:
    """Registered layers for one pose and expression on one canvas."""

    mouth_source: QPixmap
    mouth_mask: QPixmap
    mouth_rect: QRect
    blink_source: QPixmap | None = None
    blink_mask: QPixmap | None = None
    blush_source: QPixmap | None = None
    blush_mask: QPixmap | None = None


class FaceRendererPort(Protocol):
    def render(
        self,
        base: QPixmap,
        motion: FaceMotionFrame,
        layers: FaceRenderLayers,
        *,
        aperture: float | None = None,
    ) -> QPixmap: ...


class ParametricFaceRenderer:
    """Compose registered raster layers from continuous face parameters."""

    def render(
        self,
        base: QPixmap,
        motion: FaceMotionFrame,
        layers: FaceRenderLayers,
        *,
        aperture: float | None = None,
    ) -> QPixmap:
        if base.isNull():
            return QPixmap(base)
        result = QPixmap(base)
        expression = motion.expression_shape
        if expression.blush > 0.0:
            self._paint_masked(
                result,
                layers.blush_source,
                layers.blush_mask,
                expression.blush,
            )
        actual_aperture = (
            motion.mouth.aperture if aperture is None else float(aperture)
        )
        if motion.viseme is not Viseme.CLOSED or actual_aperture > MOUTH_APERTURE_THRESHOLD:
            self._paint_mouth(
                result,
                layers,
                motion.mouth,
                actual_aperture,
            )
        if expression.blink > 0.0:
            self._paint_masked(
                result,
                layers.blink_source,
                layers.blink_mask,
                expression.blink,
            )
        return result

    def render_overlay(
        self,
        base: QPixmap,
        source: QPixmap,
        *,
        mask: QPixmap | None = None,
        opacity: float = 1.0,
    ) -> QPixmap:
        """Compose one registered expression layer without owning its policy."""

        result = QPixmap(base)
        if mask is None:
            if not source.isNull():
                painter = QPainter(result)
                painter.setOpacity(max(0.0, min(1.0, float(opacity))))
                painter.drawPixmap(0, 0, source)
                painter.end()
            return result
        self._paint_masked(result, source, mask, opacity)
        return result

    @staticmethod
    def _paint_masked(
        target: QPixmap,
        source: QPixmap | None,
        mask: QPixmap | None,
        opacity: float,
    ) -> None:
        if source is None or mask is None or source.isNull() or mask.isNull():
            return
        layer = QPixmap(source.size())
        layer.fill(Qt.transparent)
        mask_painter = QPainter(layer)
        mask_painter.drawPixmap(0, 0, source)
        mask_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        mask_painter.drawPixmap(0, 0, mask)
        mask_painter.end()
        painter = QPainter(target)
        painter.setOpacity(max(0.0, min(1.0, float(opacity))))
        painter.drawPixmap(0, 0, layer)
        painter.end()

    def _paint_mouth(
        self,
        target: QPixmap,
        layers: FaceRenderLayers,
        shape: MouthShape,
        aperture: float,
    ) -> None:
        if layers.mouth_source.isNull() or layers.mouth_mask.isNull():
            return
        patch = QPixmap(layers.mouth_source.size())
        patch.fill(Qt.transparent)
        mask_painter = QPainter(patch)
        mask_painter.drawPixmap(0, 0, layers.mouth_source)
        mask_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        mask_painter.drawPixmap(0, 0, layers.mouth_mask)
        mask_painter.end()

        rect = layers.mouth_rect
        center_x = rect.center().x()
        center_y = rect.center().y()
        # The ranges are intentionally conservative: the photographed source
        # remains identity-locked while width, rounding, jaw, and aperture
        # provide sub-frame motion instead of replacing facial geometry.
        width_scale = (
            1.0
            + (shape.width - 0.5) * 0.08
            - shape.rounding * 0.02
        )
        height_scale = 1.0 + shape.aperture * 0.04
        jaw_shift = max(0.0, min(1.0, shape.jaw)) * 0.8
        transform = QTransform()
        transform.translate(center_x, center_y + jaw_shift)
        transform.scale(width_scale, height_scale)
        transform.translate(-center_x, -center_y)

        transformed = QPixmap(patch.size())
        transformed.fill(Qt.transparent)
        painter = QPainter(transformed)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setTransform(transform)
        painter.drawPixmap(0, 0, patch)
        painter.end()

        # Clip again after transformation so sub-pixel motion cannot leak a
        # photographed rectangular edge onto the face.
        mask_painter = QPainter(transformed)
        mask_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        mask_painter.drawPixmap(0, 0, layers.mouth_mask)
        mask_painter.end()
        painter = QPainter(target)
        painter.setOpacity(max(0.0, min(1.0, aperture / 0.18)))
        painter.drawPixmap(0, 0, transformed)
        painter.end()


class LegacyFaceRenderer:
    """Rollback renderer preserving the established masked-mouth behavior."""

    def render(
        self,
        base: QPixmap,
        motion: FaceMotionFrame,
        layers: FaceRenderLayers,
        *,
        aperture: float | None = None,
    ) -> QPixmap:
        actual_aperture = (
            motion.mouth.aperture if aperture is None else float(aperture)
        )
        if motion.viseme is Viseme.CLOSED and actual_aperture <= MOUTH_APERTURE_THRESHOLD:
            return QPixmap(base)
        result = QPixmap(base)
        ParametricFaceRenderer._paint_masked(
            result,
            layers.mouth_source,
            layers.mouth_mask,
            max(0.0, min(1.0, actual_aperture / 0.18)),
        )
        return result
