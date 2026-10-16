"""Compose static body layers against the registered face authority."""

from __future__ import annotations

lazy from PySide6.QtGui import QPainter, QPixmap, QRegion
lazy from domain.character_runtime import CHARACTER_LAYER_ROLES, character_rig_manifest
lazy from infrastructure.layered_full_body_assets import LayeredFullBodyView

_RIG_MANIFEST = character_rig_manifest()
_BACK_HAIR_LAYER = CHARACTER_LAYER_ROLES["rear_hair"]
_FRONT_HAIR_LAYERS = (
    CHARACTER_LAYER_ROLES["left_side_hair"],
    CHARACTER_LAYER_ROLES["right_side_hair"],
)
_SLEEVE_LAYERS = (
    CHARACTER_LAYER_ROLES["left_sleeve"],
    CHARACTER_LAYER_ROLES["right_sleeve"],
)
MAX_CACHED_STATIC_COMPOSITES = 4
SEAM_HEAL_RADIUS = 7
REGISTERED_COMPOSITE_LAYERS = _RIG_MANIFEST.registered_composite_layers
FACE_AUTHORITY_REGION_LAYERS = _RIG_MANIFEST.face_authority_layers


class LayeredFullBodyAuthorityMixin:
    """Compose motion-independent layers and restore the bound face authority."""

    def _static_base_composite(
        self,
        view: LayeredFullBodyView,
        pose_id: str,
        left_hand: str,
        right_hand: str,
        bounded_energy: float,
    ) -> QPixmap:
        """Compose and cache every motion-independent layer of one view.

        Everything from the body up to and including the authority-face
        restoration is identical for every animation frame of a given view,
        pose and hand state: the neutral face cutouts painted here are fully
        covered again by ``_restore_authority_face``.  Rebuilding this stack
        on the 50 Hz viseme path dominated the frame budget, so it is cached
        and only the dynamic eye/mouth layers are painted per frame.
        """

        key = (
            view.view_id,
            pose_id,
            left_hand,
            right_hand,
            round(bounded_energy, 3),
        )
        cached = self._static_composite_cache.get(key)
        if cached is not None:
            self._static_composite_cache.move_to_end(key)
            return cached
        body = self._cached_pixmap(view.path("body"))
        if body.isNull():
            return QPixmap()
        if self._strict_authority:
            self._view_authority(view, body)
        result = QPixmap(body)
        self._paint_opacity(result, view.path(_BACK_HAIR_LAYER), 1.0)
        self._paint_opacity(result, view.path("base"), 1.0)
        self._paint_neutral_face_layers(result, view)

        # Front hair, sleeves, ornament.
        self._paint_opacity(result, view.path(_FRONT_HAIR_LAYERS[0]), 1.0)
        self._paint_opacity(result, view.path(_FRONT_HAIR_LAYERS[1]), 1.0)
        left_lift = self._sleeve_lift(left_hand, pose_id, bounded_energy)
        right_lift = self._sleeve_lift(right_hand, pose_id, bounded_energy)
        self._paint_translated(result, view.path(_SLEEVE_LAYERS[0]), dy=left_lift)
        self._paint_translated(result, view.path(_SLEEVE_LAYERS[1]), dy=right_lift)
        self._paint_opacity(result, view.path("ornament"), 1.0)
        self._heal_registered_seams(result, view)
        self._restore_authority_face(result, view)
        self._static_composite_cache[key] = result
        self._static_composite_cache.move_to_end(key)
        while len(self._static_composite_cache) > MAX_CACHED_STATIC_COMPOSITES:
            self._static_composite_cache.popitem(last=False)
        return result

    def _paint_neutral_face_layers(
        self,
        result: QPixmap,
        view: LayeredFullBodyView,
    ) -> None:
        """Paint the registered neutral facial cutouts (with parameter motion applied later).

        The authored facial layers are neutral registered cutouts, not
        effect-only overlays: painting them fills the transparent holes in
        ``base``.  Every pixel painted here sits inside the authority-face
        region and is replaced by ``_restore_authority_face``, so parameter
        motion (corner smile, gaze) is intentionally not applied — dynamic
        eye and mouth motion is re-applied after restoration instead.
        """

        for layer_name in _RIG_MANIFEST.face_authority_layers[1:]:
            self._paint_opacity(result, view.path(layer_name), 1.0)

    def _heal_registered_seams(
        self,
        target: QPixmap,
        view: LayeredFullBodyView,
    ) -> None:
        """Colour-register only authored cut-out boundaries to the view authority."""
        region = self._seam_region_cache.get(view.view_id)
        if region is None:
            region = QRegion()
            offsets = tuple(
                (dx, dy)
                for dx in range(-SEAM_HEAL_RADIUS, SEAM_HEAL_RADIUS + 1)
                for dy in range(-SEAM_HEAL_RADIUS, SEAM_HEAL_RADIUS + 1)
                if abs(dx) + abs(dy) <= SEAM_HEAL_RADIUS
            )
            for layer_name in REGISTERED_COMPOSITE_LAYERS:
                path = view.path(layer_name)
                if path is None:
                    continue
                source = self._cached_pixmap(path)
                if source.isNull():
                    continue
                source_region = self._mask_region(source)
                if source_region.isEmpty():
                    continue
                outer = QRegion(source_region)
                inner = QRegion(source_region)
                for dx, dy in offsets:
                    outer = outer.united(source_region.translated(dx, dy))
                    inner = inner.intersected(source_region.translated(dx, dy))
                region = region.united(outer.subtracted(inner))
            self._seam_region_cache[view.view_id] = region
        if region.isEmpty():
            return
        authority = self._view_authority(view, target)
        if authority.isNull():
            return
        painter = QPainter(target)
        painter.setClipRegion(region)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.drawPixmap(0, 0, authority)
        painter.end()

    def _restore_authority_face(
        self,
        target: QPixmap,
        view: LayeredFullBodyView,
    ) -> None:
        """Remove broad skin-cutout artefacts while preserving body layers."""
        region = self._face_region_cache.get(view.view_id)
        if region is None:
            region = QRegion()
            for layer_name in FACE_AUTHORITY_REGION_LAYERS:
                path = view.path(layer_name)
                if path is None:
                    continue
                source = self._cached_pixmap(path)
                if not source.isNull():
                    region = region.united(self._mask_region(source))
            self._face_region_cache[view.view_id] = region
        if region.isEmpty():
            return
        authority = self._view_authority(view, target)
        if authority.isNull():
            return
        painter = QPainter(target)
        painter.setClipRegion(region)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.drawPixmap(0, 0, authority)
        painter.end()

    def _view_authority(self, view: LayeredFullBodyView, target: QPixmap) -> QPixmap:
        """Bind seam/face restoration to this renderer's immutable source set."""
        path = self._authority_root / f"{view.view_id}.png"
        authority = self._cached_pixmap(path, required=self._strict_authority)
        if self._strict_authority:
            if authority.isNull():
                raise ValueError(f"Missing or invalid view authority: {path}")
            if authority.size() != target.size():
                raise ValueError(f"View authority canvas mismatch: {path}")
        return authority
