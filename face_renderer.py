from __future__ import annotations

lazy from dataclasses import dataclass
lazy from typing import Protocol

lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QPainter, QPixmap, QTransform

lazy from face_rig import FaceMotionFrame, MouthShape, Viseme


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
        if motion.viseme is not Viseme.CLOSED or actual_aperture > 0.01:
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
        if motion.viseme is Viseme.CLOSED and actual_aperture <= 0.01:
            return QPixmap(base)
        result = QPixmap(base)
        ParametricFaceRenderer._paint_masked(
            result,
            layers.mouth_source,
            layers.mouth_mask,
            max(0.0, min(1.0, actual_aperture / 0.18)),
        )
        return result
