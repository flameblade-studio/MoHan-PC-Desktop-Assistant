"""Deterministic raster geometry for authority-bound semantic mouth layers."""

from __future__ import annotations

lazy import math

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap, QTransform

lazy from domain.face_rig import viseme_u_inward_scale


def inward_lerped_u_layer(
    source: QPixmap,
    mouth_center_x: float | None,
    u_inward: float,
) -> QPixmap:
    """Move one semantic U lip/corner layer inward on x only.

    ``mouth_center_x`` must come from a trusted canonical authority manifest.
    It is deliberately never inferred from this layer's alpha bounds: doing so
    gives each lip/corner a different pivot and makes the mouth collapse or
    drift.  Missing or non-finite authority data therefore fails closed by
    returning an unchanged copy.

    The transform implements ``x' = center + scale * (x - center)`` while y
    remains unchanged.  Callers are responsible for restricting this helper to
    ``lip_upper``, ``lip_lower``, ``corner_left`` and ``corner_right``.
    """

    scale = viseme_u_inward_scale(u_inward)
    if (
        source.isNull()
        or mouth_center_x is None
        or not math.isfinite(float(mouth_center_x))
        or scale >= 1.0
    ):
        return QPixmap(source)
    center_x = float(mouth_center_x)
    transform = QTransform()
    transform.translate(center_x, 0.0)
    transform.scale(scale, 1.0)
    transform.translate(-center_x, 0.0)
    # Nearest-neighbour rasterization moves each semantic RGBA sample only on
    # x. It does not interpolate new alpha values or blur the vertical lip
    # thickness; the canonical source is re-read on every call.
    result = QPixmap(source.size())
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.setTransform(transform)
    painter.drawPixmap(0, 0, source)
    painter.end()
    return result
