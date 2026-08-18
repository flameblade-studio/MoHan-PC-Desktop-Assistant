from __future__ import annotations

lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy from PySide6.QtCore import QRectF, Qt
lazy from PySide6.QtGui import QColor, QImage, QPainter

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
        self._current_view_id: str | None = None
        self._face_rects: dict[str, tuple[float, float, float, float]] = {}

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

    @property
    def view_ids(self) -> tuple[str, ...]:
        return tuple(str(item["view_id"]) for item in self._metadata["views"])

    def resolve_static(
        self,
        _pose_id: str,
        view_id: str,
    ) -> FullBodyRenderSpec | None:
        try:
            canonical = normalize_view_id(view_id)
        except (TypeError, ValueError):
            return None
        self._current_view_id = canonical
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
        viseme: str,
        mouth_closed: bool,
    ) -> tuple[FullBodyRenderLayer, ...] | None:
        # The v4 full-body photograph is a single static PNG per view.  Speech
        # must therefore overlay a procedural mouth layer at the face position
        # recorded in the per-view hands sidecar.  A closed mouth contributes
        # no layer (the authored photograph already shows a neutral mouth).
        if mouth_closed:
            return ()
        view_id = self._current_view_id
        if view_id is None:
            return None
        face_rect = self._face_rect(view_id)
        if face_rect is None:
            return None
        rgba = self._render_mouth_layer(face_rect, viseme)
        if rgba is None:
            return None
        evidence = FullBodyLayerEvidence(
            "mouth",
            hashlib.sha256(rgba).hexdigest(),
            f"pose-atlas:{view_id}:mouth:{viseme}",
        )
        layer = FullBodyRenderLayer(
            BodyPoseLayer("mouth", LAYER_DEPTHS["mouth"], rgba),
            evidence,
        )
        return (layer,)

    def _face_rect(
        self,
        view_id: str,
    ) -> tuple[float, float, float, float] | None:
        cached = self._face_rects.get(view_id)
        if cached is not None:
            return cached
        path = self._root / f"{view_id}.hands.json"
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        for region in payload.get("protected_regions", ()) or ():
            if region.get("label") != "face":
                continue
            rect = region.get("rect")
            if not isinstance(rect, list) or len(rect) != 4:
                return None
            source_width = int(payload.get("width", 1024))
            source_height = int(payload.get("height", 1536))
            if source_width <= 0 or source_height <= 0:
                return None
            normalized = self._normalize_face_rect(
                rect,
                source_width,
                source_height,
            )
            self._face_rects[view_id] = normalized
            return normalized
        return None

    def _normalize_face_rect(
        self,
        rect: list[object],
        source_width: int,
        source_height: int,
    ) -> tuple[float, float, float, float]:
        # The authored PNG is 1024x1536 and is scaled into the square canvas
        # with KeepAspectRatio (height fills the canvas, width is centered).
        scale = self._image_size / source_height
        scaled_width = source_width * scale
        offset_x = (self._image_size - scaled_width) / 2.0
        x, y, w, h = (float(value) for value in rect)
        return (
            offset_x + x * scale,
            y * scale,
            w * scale,
            h * scale,
        )

    def _render_mouth_layer(
        self,
        face_rect: tuple[float, float, float, float],
        viseme: str,
    ) -> bytes | None:
        # A procedural mouth whose aperture and width follow the viseme.  The
        # full-body photograph is a single static PNG, so speech overlays a
        # two-lip mouth at the face position recorded in the hands sidecar.
        # A closed mouth contributes no layer (the authored photograph already
        # shows a neutral mouth).
        fx, fy, fw, fh = face_rect
        aperture, width_scale = self._viseme_shape(viseme)
        if aperture <= 0.0:
            return None
        # The mouth sits in the lower third of the face region.  The authored
        # face rect is generous (it includes the chin), so anchor the mouth
        # slightly above the vertical centre of the lower half.
        mouth_cx = fx + fw * 0.5
        mouth_cy = fy + fh * 0.60
        mouth_w = max(2.0, fw * 0.30 * width_scale)
        mouth_h = max(2.0, fh * 0.14 * aperture)
        image = QImage(
            self._image_size,
            self._image_size,
            QImage.Format_RGBA8888,
        )
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        # Dark oral cavity behind the lips.
        painter.setBrush(QColor(70, 30, 38, 235))
        painter.drawEllipse(
            QRectF(
                mouth_cx - mouth_w / 2.0,
                mouth_cy - mouth_h / 2.0,
                mouth_w,
                mouth_h,
            )
        )
        # Upper and lower lips as two rounded bands that separate with the
        # aperture, giving a readable "open mouth" instead of a flat dot.
        lip_thickness = max(1.5, mouth_h * 0.28)
        lip_color = QColor(150, 78, 88, 245)
        painter.setBrush(lip_color)
        painter.drawRoundedRect(
            QRectF(
                mouth_cx - mouth_w / 2.0,
                mouth_cy - mouth_h / 2.0 - lip_thickness,
                mouth_w,
                lip_thickness,
            ),
            lip_thickness / 2.0,
            lip_thickness / 2.0,
        )
        painter.drawRoundedRect(
            QRectF(
                mouth_cx - mouth_w / 2.0,
                mouth_cy + mouth_h / 2.0,
                mouth_w,
                lip_thickness,
            ),
            lip_thickness / 2.0,
            lip_thickness / 2.0,
        )
        painter.end()
        return bytes(image.constBits())

    @staticmethod
    def _viseme_shape(viseme: str) -> tuple[float, float]:
        """Return (aperture, width_scale) for a viseme.

        Aperture controls the vertical opening; width_scale controls the
        horizontal spread.  Rounded vowels (O, U) narrow the mouth while open
        vowels (A) widen it, and spread vowels (E, I) stay wide but shallow.
        """
        normalized = str(viseme or "CLOSED").upper()
        if normalized in {"CLOSED", "CONSONANT"}:
            return 0.0, 1.0
        if normalized == "A":
            return 1.0, 1.15
        if normalized == "O":
            return 0.85, 0.72
        if normalized == "U":
            return 0.7, 0.6
        if normalized in {"E", "I"}:
            return 0.5, 1.05
        return 0.7, 1.0

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
