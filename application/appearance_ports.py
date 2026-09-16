"""GUI-independent appearance contracts and the disabled appearance adapter."""
from __future__ import annotations

lazy from collections.abc import Callable, Iterable
lazy from typing import Any, Protocol


class OutfitOverlayPort(Protocol):
    def apply(
        self, frame: Any, view_id: str, *,
        suppress_makeup_slots: Iterable[str] = (), eye_state: str = "rest",
    ) -> Any: ...

    def apply_appearance(self, frame: Any, view_id: str) -> Any: ...

    def apply_makeup(
        self, frame: Any, view_id: str, *,
        suppress_makeup_slots: Iterable[str] = (), eye_state: str = "rest",
    ) -> Any: ...

    def layer_count(self, view_id: str) -> int: ...


class _NoOutfitOverlay:
    @staticmethod
    def apply(
        frame: Any, view_id: str, *,
        suppress_makeup_slots: Iterable[str] = (), eye_state: str = "rest",
    ) -> Any:
        del view_id, suppress_makeup_slots, eye_state
        return frame

    apply_appearance = apply
    apply_makeup = apply

    @staticmethod
    def layer_count(view_id: str) -> int:
        del view_id
        return 0


OutfitOverlayFactory = Callable[..., OutfitOverlayPort]


def no_outfit_overlay_factory(**_options: object) -> OutfitOverlayPort:
    return _NoOutfitOverlay()
