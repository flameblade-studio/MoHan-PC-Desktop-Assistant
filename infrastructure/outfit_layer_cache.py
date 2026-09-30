"""Read and invalidate appearance layer caches with their canonical identity."""
from __future__ import annotations

lazy from collections.abc import Iterable
lazy from infrastructure.outfit_layer_cache_key import OutfitLayerCacheKey


class OutfitLayerCacheMixin:
    """ActiveOutfitOverlay owns the caches consumed by this mixin."""

    def _invalidate_view(self, view_id: str) -> None:
        """Discard both successful layers and size-dependent masks for a view."""
        getattr(self, "_reviewed_layer_counts", {}).pop(view_id, None)
        for cache in (
            self._protected_by_view, self._feature_by_view,
            self._hair_mask_by_view,
            self._core_hand_overlays_by_view, self._core_body_overlays_by_view,
            self._official_silhouettes_by_view, self._official_replacement_masks_by_view,
        ):
            cache.pop(view_id, None)
        for key in tuple(self._makeup_exclusion_by_view):
            if key[0] == view_id:
                del self._makeup_exclusion_by_view[key]
        for cache in (self._layers_by_view, self._layers_by_view_without_makeup_slots, self._phase_layers_by_view):
            for key in tuple(cache):
                if key.view_id == view_id:
                    del cache[key]

    def layer_count(
        self,
        view_id: str,
        *,
        suppress_makeup_slots: Iterable[str] = (),
        eye_state: str = "rest",
        makeup_view_id: str | None = None,
    ) -> int:
        """Successfully composed layers from either combined or split phases."""
        if eye_state not in {"rest", "half", "closed"}:
            raise ValueError("Use a recognized makeup eye state")
        suppressed = frozenset(suppress_makeup_slots)
        reviewed_count = getattr(self, "_reviewed_layer_counts", {}).get(view_id, 0)
        simple = not suppressed and eye_state == "rest" and self._active_viseme is None and makeup_view_id is None
        cache = self._layers_by_view if simple else self._layers_by_view_without_makeup_slots
        cache_key = OutfitLayerCacheKey.combined(
            view_id, suppressed, eye_state, self._active_viseme, makeup_view_id,
        )
        if cache_key in cache:
            return len(cache[cache_key]) + reviewed_count
        appearance = self._phase_layers_by_view.get(
            OutfitLayerCacheKey.for_phase(
                view_id, "appearance", suppressed, eye_state, self._active_viseme, makeup_view_id,
            ),
            self._phase_layers_by_view.get(
                OutfitLayerCacheKey.for_phase(view_id, "appearance", active_viseme=self._active_viseme), (),
            ),
        )
        makeup = self._phase_layers_by_view.get(
            OutfitLayerCacheKey.for_phase(
                view_id, "makeup", suppressed, eye_state, self._active_viseme, makeup_view_id,
            ),
            (),
        )
        return len(appearance) + len(makeup) + reviewed_count
