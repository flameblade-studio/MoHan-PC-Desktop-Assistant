"""Render the approved exasperated native parts and registered mouth endpoints."""
from __future__ import annotations

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap
lazy from domain.face_rig import FaceMotionFrame
lazy from infrastructure.exasperated_candidate_assets import (
    DIMENSION as EXASPERATED_DIMENSION, load_exasperated_candidate_assets,
)

MOUTH_APERTURE_THRESHOLD = 0.01


class ExasperatedFaceRenderingMixin:
    """Keep source-bound expression composition separate from the general rig."""

    def _render_exasperated_candidate(
        self,
        base: QPixmap,
        motion: FaceMotionFrame,
        layers: object,
        aperture: float | None,
    ) -> QPixmap:
        """Compose native parts and their own mouth before optional matching appearance."""
        if self._exasperated_candidate_assets is None:
            assert self._exasperated_candidate_dir is not None
            self._exasperated_candidate_assets = load_exasperated_candidate_assets(
                self._exasperated_candidate_dir
            )
        assets = self._exasperated_candidate_assets
        if self._exasperated_candidate_rest is None:
            self._exasperated_candidate_rest = assets.compose()
        frame = QPixmap(self._exasperated_candidate_rest)
        actual_aperture = motion.mouth.aperture if aperture is None else float(aperture)
        mouth_expression = getattr(layers, "mouth_expression", None)
        if mouth_expression is None:
            mouth_expression = {
                "A": "exasperated_front_speech_open",
                "I": "exasperated_front_speech_i",
                "U": "exasperated_front_speech_u",
                "E": "exasperated_front_speech_mid",
                "O": "exasperated_front_speech_round",
                "CONSONANT": "exasperated_front_speech_mid",
            }.get(str(motion.viseme))
        if actual_aperture <= MOUTH_APERTURE_THRESHOLD:
            mouth_expression = None
        if mouth_expression is not None:
            patch = self._exasperated_candidate_patches.get(mouth_expression)
            if patch is None:
                patch = assets.patch(mouth_expression)
                if patch is not None:
                    self._exasperated_candidate_patches[mouth_expression] = patch
            if patch is not None:
                painter = QPainter(frame)
                try:
                    # The speech timer blends complete endpoint frames. A second
                    # opacity blend here exposes both the REST and open lips.
                    painter.drawPixmap(0, 0, patch)
                finally:
                    painter.end()
        if self._candidate_appearance_overlay is not None:
            frame = self._candidate_appearance_overlay.apply(
                frame, "front-exasperated", mouth_expression=mouth_expression
            )
            if frame.isNull() or (frame.width(), frame.height()) != (
                EXASPERATED_DIMENSION, EXASPERATED_DIMENSION
            ):
                raise ValueError("Exasperated appearance must preserve the native 1254 canvas.")
        if base.isNull() or frame.size() == base.size():
            return frame
        return frame.scaled(base.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

