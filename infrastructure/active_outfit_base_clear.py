"""Resolve source-bound and legacy base-clear regions for outfit composition."""

from __future__ import annotations

lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QRegion

lazy from domain.outfit_pack import (
    POSE_ATLAS_SILHOUETTES,
    OutfitPackError,
)
lazy from domain.outfit_pack_official import (
    OFFICIAL_OUTFIT_CATEGORIES,
    OFFICIAL_OUTFIT_PACK_ID,
)
lazy from infrastructure.active_outfit_overlay_layers import FULL_BODY_CANVAS
lazy from infrastructure.source_bound_garment_visibility import (
    MANIFEST,
    GarmentBinding,
    load_garment_binding,
    validate_garment_removal,
)

V5_NECK_GUARD_SIDE_PX = 25
V5_NECK_GUARD_HEIGHT_PX = 110


class ActiveOutfitBaseClearMixin:
    """Choose the exact body region removed before appearance layers are painted."""

    def _base_clear_regions(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
        garment_is_active: bool,
        include_core: bool,
    ) -> tuple[QRegion | None, QRegion | None, GarmentBinding | None]:
        """Prefer an exact source-bound removal; retain the legacy route otherwise."""
        if garment_is_active and (self._asset_root / MANIFEST).exists():
            selected = self._resolve_base_clear_selection("garment")
            archive_path, _item, variant = self._selected_variant("garment", selected)
            binding = load_garment_binding(
                self._asset_root, view_id, selected, archive_path, variant,
            )
            if binding is not None:
                visible_hands = self._visible_hand_region
                if binding.hand_region is not None:
                    hand_region = binding.hand_region
                    visible_hands = lambda _view: hand_region
                validate_garment_removal(
                    self._asset_root, view_id, canvas_size, binding.removal,
                    self._protected_face_region(view_id, canvas_size),
                    visible_hands,
                )
                return None, binding.removal, binding
        silhouette = (
            self._selected_silhouette_region(view_id, canvas_size, garment_is_active)
            if include_core else None
        )
        replacement = (
            self._official_replacement_region(view_id, canvas_size)
            if include_core and self._official_outfit_is_active() else None
        )
        if (
            include_core
            and view_id in POSE_ATLAS_SILHOUETTES
            and canvas_size == FULL_BODY_CANVAS
        ):
            head = self._protected_face_region(view_id, canvas_size).boundingRect()
            if not head.isEmpty():
                native_head = QRegion(QRect(0, 0, canvas_size[0], head.bottom() + 1))
                native_head = native_head.united(QRegion(QRect(
                    head.left() - V5_NECK_GUARD_SIDE_PX,
                    head.bottom() + 1,
                    head.width() + 2 * V5_NECK_GUARD_SIDE_PX,
                    V5_NECK_GUARD_HEIGHT_PX,
                )))
                if silhouette is not None:
                    silhouette = silhouette.united(native_head)
                if replacement is not None:
                    replacement = replacement.subtracted(native_head)
        return silhouette, replacement, None

    def _selected_silhouette_region(
        self,
        view_id: str,
        canvas_size: tuple[int, int],
        garment_is_active: bool,
    ) -> QRegion | None:
        """Keep garment occlusion when independently changing hair or headwear."""
        if self._official_outfit_is_active():
            return self._official_silhouette_region(view_id, canvas_size)
        if not garment_is_active:
            return None
        garment = self._resolve_base_clear_selection("garment")
        if garment.effective_pack_id != OFFICIAL_OUTFIT_PACK_ID:
            return None
        silhouette = self._official_silhouette_region(view_id, canvas_size)
        if silhouette is None:
            return None
        head = self._protected_face_region(view_id, canvas_size).boundingRect()
        if head.isEmpty():
            raise OutfitPackError("Protected head boundary is unavailable.")
        head_band = QRegion(QRect(0, 0, canvas_size[0], head.bottom() + 1))
        return silhouette.united(head_band)

    def _official_outfit_is_active(self) -> bool:
        """Keep the official base boundary when its headwear is explicitly removed."""
        if self._official_outfit_active_cache is not None:
            return self._official_outfit_active_cache
        result = True
        for category in OFFICIAL_OUTFIT_CATEGORIES:
            selected = self._resolve_base_clear_selection(category)
            if getattr(selected, "effective_pack_id", None) == OFFICIAL_OUTFIT_PACK_ID:
                continue
            requested = tuple(
                getattr(selected, f"requested_{field}", None)
                for field in ("pack_id", "item_id", "variant_id")
            )
            effective = tuple(
                getattr(selected, f"effective_{field}", None)
                for field in ("pack_id", "item_id", "variant_id")
            )
            if (
                category == "headwear"
                and getattr(selected, "status", None) == "builtin"
                and requested == effective == ("builtin", "none", "none")
            ):
                continue
            result = False
            break
        self._official_outfit_active_cache = result
        return result

    def _garment_is_active(self) -> bool:
        """Resolve the active garment once per appearance-state token."""
        if self._garment_active_cache is None:
            self._garment_active_cache = (
                self._resolve_base_clear_selection("garment").status != "builtin"
            )
        return self._garment_active_cache
