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


class PoseAtlasAssets:
    """Load locally audited authored views without pretending they are split layers."""

    def __init__(self, root: Path, *, image_size: int) -> None:
        if image_size <= 0:
            raise ValueError("PoseAtlas image size must be positive.")
        self._root = Path(root)
        self._image_size = int(image_size)
        self._metadata = self._load_metadata()
        self._hashes = {
            str(item["view_id"]): str(item["normalized_sha256"])
            for item in self._metadata["views"]
        }
        self._cache: dict[str, FullBodyRenderSpec] = {}

    @property
    def generation(self) -> int:
        return 1

    @property
    def enabled(self) -> bool:
        return bool(self._hashes)

    @property
    def release_eligible(self) -> bool:
        return self._metadata.get("formal_promotion") in {
            "approved",
            "included_in_v4_0_0_release",
        }

    def resolve_static(
        self,
        _pose_id: str,
        view_id: str,
    ) -> FullBodyRenderSpec | None:
        try:
            canonical = normalize_view_id(view_id)
        except (TypeError, ValueError):
            return None
        cached = self._cache.get(canonical)
        if cached is not None:
            return cached
        expected = self._hashes.get(canonical)
        path = self._root / f"{canonical}.png"
        if expected is None or not path.is_file():
            return None
        source = path.read_bytes()
        if hashlib.sha256(source).hexdigest() != expected:
            return None
        rgba = self._normalized_rgba(path)
        evidence = FullBodyLayerEvidence(
            AUTHORED_FULL_BODY_SLOT,
            hashlib.sha256(rgba).hexdigest(),
            f"pose-atlas:{canonical}:{expected}",
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
        specification = FullBodyRenderSpec(
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
        self._cache[canonical] = specification
        return specification

    def resolve_speech(
        self,
        _face: str | None,
        _viseme: str,
        mouth_closed: bool,
    ) -> tuple[FullBodyRenderLayer, ...] | None:
        return () if mouth_closed else None

    def _load_metadata(self) -> dict[str, object]:
        path = self._root / "BUILD-METADATA.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema") != "mohan.pose-atlas.working-build.v1":
            raise ValueError("Unsupported PoseAtlas build metadata.")
        views = value.get("views")
        if not isinstance(views, list) or len(views) != 24:
            raise ValueError("PoseAtlas must contain the complete 24-view ring.")
        return value

    def _normalized_rgba(self, path: Path) -> bytes:
        source = QImage(str(path))
        if source.isNull():
            raise ValueError(f"PoseAtlas image cannot be decoded: {path.name}")
        source = source.convertToFormat(QImage.Format_RGBA8888)
        scaled = source.scaled(
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
