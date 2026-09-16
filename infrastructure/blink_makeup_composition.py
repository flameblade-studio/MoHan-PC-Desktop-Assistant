"""Apply authored eye pigment within the exact registered blink patch alpha."""
from __future__ import annotations

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap
lazy from application.appearance_ports import OutfitOverlayPort
lazy from domain.outfit_pack import MAKEUP_CANVASES, MAKEUP_SLOTS


def paint_blink_makeup(
    result: QPixmap, patch: QPixmap, overlay: OutfitOverlayPort,
    view_id: str, eye_state: str,
) -> None:
    """Keep native pigment coordinates, then scale once to the display canvas."""
    pigment = QPixmap(*MAKEUP_CANVASES["half-body"])
    pigment.fill(Qt.transparent)
    # Suppress ordinary makeup. A validated authored eye-state declaration is
    # the only layer allowed to override the eyes suppression at this phase.
    pigment = overlay.apply_makeup(
        pigment, view_id, suppress_makeup_slots=MAKEUP_SLOTS, eye_state=eye_state,
    )
    if pigment.size() != result.size():
        pigment = pigment.scaled(result.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    # Qt can optimize an opaque scaled pixmap to RGB32. Mask a fresh alpha
    # canvas so transparent patch pixels do not turn opaque black instead.
    masked = QPixmap(result.size())
    masked.fill(Qt.transparent)
    painter = QPainter(masked)
    painter.drawPixmap(0, 0, pigment)
    painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    painter.drawPixmap(0, 0, patch)
    painter.end()
    painter = QPainter(result)
    painter.drawPixmap(0, 0, masked)
    painter.end()
