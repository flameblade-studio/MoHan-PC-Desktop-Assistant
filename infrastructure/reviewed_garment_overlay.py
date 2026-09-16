"""Integrate reviewed native clothing into the existing selection and depth pipeline."""
from __future__ import annotations

lazy from collections.abc import Callable, Sequence
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap
lazy from domain.outfit_pack import SELECTION_CATEGORIES, resolve_active_selection
lazy from infrastructure.appearance_layer_stack import (
    AppearanceLayerStack, Layer, paint_behind_body, split_makeup_depth,
)
lazy from infrastructure.reviewed_garment_assets import DIMENSION, load_reviewed_garment_assets
lazy from infrastructure.reviewed_pose_overlay import ReviewedPoseOverlayMixin


def _paint_foreground(
    painter: QPainter, layers: Sequence[Layer], *, makeup_count: int = 0,
) -> None:
    for index, (pixmap, x, y, clip, opacity) in enumerate(layers):
        painter.setCompositionMode(
            QPainter.CompositionMode_SourceAtop if index < makeup_count
            else QPainter.CompositionMode_SourceOver
        )
        painter.setClipRegion(clip)
        painter.setOpacity(opacity)
        painter.drawPixmap(x, y, pixmap)


def _finish_appearance(
    result: QPixmap, layers: AppearanceLayerStack,
    before_front_hair: Callable[[QPixmap], QPixmap] | None,
) -> QPixmap:
    painter = QPainter(result)
    try:
        foreground = paint_behind_body(painter, layers)
        if before_front_hair is None:
            _paint_foreground(painter, foreground, makeup_count=layers.makeup_prefix_count)
            return result
        early, deferred = split_makeup_depth(layers, foreground)
        _paint_foreground(painter, early, makeup_count=layers.makeup_prefix_count)
    finally:
        painter.end()
    result = before_front_hair(result)
    painter = QPainter(result)
    try:
        _paint_foreground(painter, deferred)
    finally:
        painter.end()
    return result


class ReviewedGarmentOverlayMixin(ReviewedPoseOverlayMixin):
    """Keep the approved native pose and its separately selected clothing.

    Native identity is bound to the pose. The reviewed garment is used only
    for its exact selection; other selections use ordinary appearance layers.
    ActiveOutfitOverlay owns selection validation and cache invalidation.
    """

    def native_neutral(self, view_id: str) -> QPixmap | None:
        """Return the pinned neutral authority before registered facial motion.

        The rig's older reconstructed face must not replace a reviewed native
        face merely because both use the same pose id. Motion is painted later
        by the face renderer, while composition still uses detachable clothing.
        """
        self._refresh_state()
        if not getattr(self, "_reviewed_assets_loaded", False):
            self._reviewed_assets = load_reviewed_garment_assets(
                self._asset_root / "assets" / "expressions" / "reviewed-garments"
            )
            self._reviewed_assets_loaded = True
        if self._reviewed_assets is None or view_id not in self._reviewed_assets.poses:
            return None
        pose = self._reviewed_assets.poses[view_id]
        if pose.native_source is None:
            return None
        # The native face belongs to the pose, independent of garment choice.
        return QPixmap.fromImage(pose.native_source.image)

    def _reviewed_frame(
        self, frame: QPixmap, view_id: str, suppressed: frozenset[str], eye_state: str,
        *, phase: str = "combined",
        before_front_hair: Callable[[QPixmap], QPixmap] | None = None,
    ) -> QPixmap | None:
        if phase == "makeup":
            return None
        appearance_only = phase == "appearance"
        if not getattr(self, "_reviewed_assets_loaded", False):
            self._reviewed_assets = load_reviewed_garment_assets(
                self._asset_root / "assets" / "expressions" / "reviewed-garments"
            )
            self._reviewed_assets_loaded = True
        counts = getattr(self, "_reviewed_layer_counts", {})
        self._reviewed_layer_counts = counts
        counts[view_id] = 0
        if self._reviewed_assets is None or view_id not in self._reviewed_assets.poses:
            return None
        selected = resolve_active_selection(self._store, "garment")
        pose = self._reviewed_assets.match(
            view_id, selected.effective_pack_id, selected.effective_item_id,
            selected.effective_variant_id,
        )
        registered_pose = self._reviewed_assets.poses[view_id]
        if pose is None and not registered_pose.motion_required:
            return None
        # Native hair remains registered when the garment is removed. Otherwise
        # the old pack hair would be painted over the newly selected body.
        excluded = set()
        if pose is not None:
            self._selected_variant("garment", selected)
            excluded.add("garment")
        for category, native_selection in registered_pose.native_appearance_selections.items():
            selection = resolve_active_selection(self._store, category)
            if native_selection.matches(
                selection.effective_pack_id, selection.effective_item_id,
                selection.effective_variant_id,
            ):
                self._selected_variant(category, selection)
                excluded.add(category)
        if appearance_only:
            excluded.add("makeup")
        layers = self._active_layers(
            view_id, frame.size().toTuple(), suppress_makeup_slots=suppressed,
            eye_state=eye_state, categories=frozenset(SELECTION_CATEGORIES) - excluded,
        )
        native = frame if frame.size().toTuple() == (DIMENSION, DIMENSION) else frame.scaled(
            DIMENSION, DIMENSION, Qt.IgnoreAspectRatio, Qt.SmoothTransformation,
        )
        result = pose.compose(native) if pose is not None else QPixmap(native)
        if result.size() != frame.size():
            result = result.scaled(frame.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        result = _finish_appearance(result, layers, before_front_hair)
        counts[view_id] = len(pose.ordered_layers) if pose is not None else 0
        if appearance_only:
            self._phase_layers_by_view[(view_id, "appearance", suppressed, eye_state)] = layers
        elif not suppressed and eye_state == "rest":
            self._layers_by_view[view_id] = layers
        else:
            self._layers_by_view_without_makeup_slots[(view_id, suppressed, eye_state)] = layers
        return result
