"""Low-level pixmap painting operations shared by the layered face renderer."""

from __future__ import annotations

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap, QRegion, QTransform

lazy from domain.character_runtime import CHARACTER_LAYER_ROLES
lazy from infrastructure.layered_face_assets import LayeredFacePose

MAX_CACHED_MASK_BOUNDS = 64
SCALE_EPSILON = 1e-4


class LayeredFacePaintingMixin:
    """Paint opacity, masks, translations, and mouth transforms onto a face."""

    def _paint_opacity(self, target: QPixmap, path, opacity: float) -> None:
        source = self._cached_pixmap(path)
        if source.isNull() or opacity <= 0.0:
            return
        painter = QPainter(target)
        painter.setOpacity(max(0.0, min(1.0, float(opacity))))
        painter.drawPixmap(0, 0, source)
        painter.end()

    def _paint_translated(
        self,
        target: QPixmap,
        path,
        *,
        dx: float = 0.0,
        dy: float = 0.0,
    ) -> None:
        source = self._cached_pixmap(path)
        if source.isNull():
            return
        painter = QPainter(target)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(round(dx), round(dy), source)
        painter.end()

    def _paint_masked(
        self,
        target: QPixmap,
        source: QPixmap | None,
        mask: QPixmap | None,
        opacity: float,
    ) -> None:
        if source is None or mask is None or source.isNull() or mask.isNull():
            return
        mask_key = int(mask.cacheKey())
        bounds = self._mask_bounds_cache.get(mask_key)
        if bounds is None:
            bounds = QRegion(mask.mask()).boundingRect()
            self._mask_bounds_cache[mask_key] = bounds
            self._mask_bounds_cache.move_to_end(mask_key)
            while len(self._mask_bounds_cache) > MAX_CACHED_MASK_BOUNDS:
                self._mask_bounds_cache.popitem(last=False)
        else:
            self._mask_bounds_cache.move_to_end(mask_key)
        if bounds.isEmpty():
            return
        layer = QPixmap(bounds.size())
        layer.fill(Qt.transparent)
        mask_painter = QPainter(layer)
        mask_painter.drawPixmap(
            0,
            0,
            source,
            bounds.x(),
            bounds.y(),
            bounds.width(),
            bounds.height(),
        )
        mask_painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        mask_painter.drawPixmap(
            0,
            0,
            mask,
            bounds.x(),
            bounds.y(),
            bounds.width(),
            bounds.height(),
        )
        mask_painter.end()
        painter = QPainter(target)
        painter.setOpacity(max(0.0, min(1.0, float(opacity))))
        painter.drawPixmap(bounds.topLeft(), layer)
        painter.end()

    def _paint_mouth_lips(self, target: QPixmap, pose: LayeredFacePose, mouth) -> None:
        """Scale the upper/lower lips around the mouth center for articulation."""
        width_scale = 1.0 + (mouth.width - 0.5) * 0.08 - mouth.rounding * 0.02
        height_scale = 1.0 + mouth.aperture * 0.12
        if (
            abs(width_scale - 1.0) < SCALE_EPSILON
            and abs(height_scale - 1.0) < SCALE_EPSILON
        ):
            return
        for layer_name in (
            CHARACTER_LAYER_ROLES["upper_lip"],
            CHARACTER_LAYER_ROLES["lower_lip"],
        ):
            path = pose.path(layer_name)
            dy = mouth.aperture * (
                -2.0 if layer_name == CHARACTER_LAYER_ROLES["upper_lip"] else 8.0
            )
            self._paint_transformed(
                target,
                path,
                scale_x=width_scale,
                scale_y=height_scale,
                dy=dy,
            )

    def _paint_mouth_opening(self, target: QPixmap, pose: LayeredFacePose, mouth) -> None:
        """Open a visible cavity before placing the articulated lip layers."""
        aperture = max(0.0, min(1.0, float(mouth.aperture)))
        self._paint_transformed(
            target,
            pose.path(CHARACTER_LAYER_ROLES["mouth_cavity"]),
            scale_x=1.0 + mouth.rounding * 0.08,
            scale_y=1.0 + aperture * 1.4,
            dy=aperture * 3.0,
        )
        self._paint_transformed(
            target,
            pose.path(CHARACTER_LAYER_ROLES["teeth_and_tongue"]),
            scale_y=1.0 + aperture * 0.45,
            dy=aperture * 2.0,
        )

    def _paint_transformed(
        self,
        target: QPixmap,
        path,
        *,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        dx: float = 0.0,
        dy: float = 0.0,
    ) -> None:
        source = self._cached_pixmap(path)
        if source.isNull():
            return
        center_x, center_y = self._layer_center(path, source)
        transform = QTransform()
        transform.translate(center_x + dx, center_y + dy)
        transform.scale(scale_x, scale_y)
        transform.translate(-center_x, -center_y)
        painter = QPainter(target)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setTransform(transform)
        painter.drawPixmap(0, 0, source)
        painter.end()

    def _layer_center(self, path, source: QPixmap) -> tuple[float, float]:
        """Return one alpha-bounds pivot using one construction-time scan."""
        key = str(path)
        cached = self._layer_center_cache.get(key)
        if cached is not None:
            return cached
        bounds = QRegion(source.mask()).boundingRect()
        center = (float(bounds.center().x()), float(bounds.center().y()))
        self._layer_center_cache[key] = center
        return center
