"""Canonical cache identity for every active-outfit layer path."""

from __future__ import annotations

lazy from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OutfitLayerCacheKey:
    """Keep combined, split-phase, and layer-count lookups in one schema."""

    view_id: str
    phase: str = "combined"
    suppressed_makeup_slots: frozenset[str] = frozenset()
    eye_state: str = "rest"
    active_viseme: str | None = None
    makeup_view_id: str | None = None

    @classmethod
    def combined(
        cls,
        view_id: str,
        suppressed_makeup_slots: frozenset[str] = frozenset(),
        eye_state: str = "rest",
        active_viseme: str | None = None,
        makeup_view_id: str | None = None,
    ) -> OutfitLayerCacheKey:
        return cls(
            view_id,
            suppressed_makeup_slots=suppressed_makeup_slots,
            eye_state=eye_state,
            active_viseme=active_viseme,
            makeup_view_id=makeup_view_id,
        )

    @classmethod
    def for_phase(
        cls,
        view_id: str,
        phase: str,
        suppressed_makeup_slots: frozenset[str] = frozenset(),
        eye_state: str = "rest",
        active_viseme: str | None = None,
        makeup_view_id: str | None = None,
    ) -> OutfitLayerCacheKey:
        return cls(
            view_id,
            phase=phase,
            suppressed_makeup_slots=suppressed_makeup_slots,
            eye_state=eye_state,
            active_viseme=active_viseme,
            makeup_view_id=makeup_view_id,
        )
