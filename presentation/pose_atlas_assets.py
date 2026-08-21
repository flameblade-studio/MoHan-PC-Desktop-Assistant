from __future__ import annotations

lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QImage, QPainter

lazy from application.body_pose_renderer import LAYER_DEPTHS, BodyPoseLayer
lazy from application.full_body_render_adapter import (
    AUTHORED_FULL_BODY_SLOT,
    FULL_BODY_RIG_ID,
    FullBodyLayerEvidence,
    FullBodyRenderLayer,
    FullBodyRenderSpec,
    NormalizedCrop,
)
lazy from domain.character_body_profile import MOHAN_BODY_PROFILE
lazy from domain.character_full_body_rig import FULL_BODY_RIG_SCHEMA_VERSION
lazy from domain.character_pose import normalize_view_id
lazy from domain.face_rig import FaceMotionFrame
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer

VIEW_RING_COUNT = 24


class PoseAtlasAssets:
    """Load locally audited authored views without pretending they are split layers."""

    def __init__(self, root: Path, *, image_size: int) -> None:
        if image_size <= 0:
            raise ValueError("PoseAtlas image size must be positive.")
        self._root = Path(root)
        self._image_size = int(image_size)
        self._metadata = self._load_metadata()
        # The parametric 24-view × 25-layer renderer is the sole full-body
        # rendering path.  The legacy static photograph + procedural mouth have
        # been removed entirely.
        self._layered_renderer = LayeredFullBodyRenderer()

    @property
    def generation(self) -> int:
        return 1

    @property
    def enabled(self) -> bool:
        return bool(self._metadata.get("views"))

    @property
    def release_eligible(self) -> bool:
        return self._metadata.get("formal_promotion") in {
            "approved",
            "included_in_v4_0_0_release",
        }

    @property
    def view_ids(self) -> tuple[str, ...]:
        return tuple(str(item["view_id"]) for item in self._metadata["views"])

    def resolve_static(
        self,
        pose_id: str,
        view_id: str,
        motion: FaceMotionFrame | None = None,
        *,
        left_hand: str = "relaxed",
        right_hand: str = "relaxed",
        body_energy: float = 0.0,
        gesture_beat: bool = False,
    ) -> FullBodyRenderSpec | None:
        try:
            canonical = normalize_view_id(view_id)
        except (TypeError, ValueError):
            return None
        # The parametric layered renderer is the sole full-body path.  Without a
        # motion frame there is nothing to compose, so fail closed.
        if motion is None:
            return None
        return self._resolve_layered(
            canonical,
            motion,
            pose_id=pose_id,
            left_hand=left_hand,
            right_hand=right_hand,
            body_energy=body_energy,
            gesture_beat=gesture_beat,
        )

    def _resolve_layered(
        self,
        canonical: str,
        motion: FaceMotionFrame,
        *,
        pose_id: str,
        left_hand: str,
        right_hand: str,
        body_energy: float,
        gesture_beat: bool,
    ) -> FullBodyRenderSpec | None:
        """Compose the parametric full body for one view and motion frame."""
        composed = self._layered_renderer.render_view(
            canonical,
            motion,
            pose_id=pose_id,
            left_hand=left_hand,
            right_hand=right_hand,
            body_energy=body_energy,
            gesture_beat=gesture_beat,
        )
        if composed.isNull():
            return None
        rgba = self._pixmap_rgba(composed)
        if rgba is None:
            return None
        return self._specification(
            canonical,
            rgba,
            f"layered:{canonical}:{motion.viseme}",
        )

    def _specification(
        self,
        canonical: str,
        rgba: bytes,
        evidence_tag: str,
    ) -> FullBodyRenderSpec:
        evidence = FullBodyLayerEvidence(
            AUTHORED_FULL_BODY_SLOT,
            hashlib.sha256(rgba).hexdigest(),
            f"pose-atlas:{canonical}:{evidence_tag}",
        )
        layer = FullBodyRenderLayer(
            BodyPoseLayer(
                AUTHORED_FULL_BODY_SLOT,
                LAYER_DEPTHS[AUTHORED_FULL_BODY_SLOT],
                rgba,
            ),
            evidence,
        )
        measurements = MOHAN_BODY_PROFILE.measurements
        return FullBodyRenderSpec(
            canonical,
            self._image_size,
            self._image_size,
            MOHAN_BODY_PROFILE.profile_id,
            (MOHAN_BODY_PROFILE.version, MOHAN_BODY_PROFILE.version + 1),
            FULL_BODY_RIG_ID,
            (FULL_BODY_RIG_SCHEMA_VERSION, FULL_BODY_RIG_SCHEMA_VERSION + 1),
            (
                float(measurements.height_cm),
                float(measurements.weight_kg),
                float(measurements.bust_cm),
                float(measurements.waist_cm),
                float(measurements.hips_cm),
            ),
            NormalizedCrop(0.0, 0.0, 1.0, 1.0),
            (layer,),
            f"{self._root / 'BUILD-METADATA.json'}#{canonical}",
        )

    def _pixmap_rgba(self, pixmap) -> bytes | None:
        """Convert a composed QPixmap to the square RGBA canvas bytes."""
        image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
        if image.isNull():
            return None
        scaled = image.scaled(
            self._image_size,
            self._image_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        canvas = QImage(
            self._image_size,
            self._image_size,
            QImage.Format_RGBA8888,
        )
        canvas.fill(Qt.transparent)
        painter = QPainter(canvas)
        painter.drawImage(
            (self._image_size - scaled.width()) // 2,
            (self._image_size - scaled.height()) // 2,
            scaled,
        )
        painter.end()
        return bytes(canvas.constBits())

    def resolve_speech(
        self,
        _face: str | None,
        _viseme: str,
        _mouth_closed: bool,
        _motion: FaceMotionFrame | None = None,
    ) -> tuple[FullBodyRenderLayer, ...] | None:
        # The parametric layered renderer already deforms the mouth, lips, jaw
        # and oral cavity inside the composed full-body frame produced by
        # ``resolve_static``.  There is no separate procedural mouth patch to
        # overlay, so speech contributes no additional layer.
        return ()

    def _load_metadata(self) -> dict[str, object]:
        path = self._root / "BUILD-METADATA.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema") != "mohan.pose-atlas.working-build.v1":
            raise ValueError("Unsupported PoseAtlas build metadata.")
        views = value.get("views")
        if not isinstance(views, list) or len(views) != VIEW_RING_COUNT:
            raise ValueError("PoseAtlas must contain the complete 24-view ring.")
        return value
