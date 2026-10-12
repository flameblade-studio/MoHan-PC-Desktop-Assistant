"""Assemble the shared body renderer and its character makeup adapter."""
from __future__ import annotations

lazy from collections.abc import Callable
lazy from functools import cache
lazy from pathlib import Path
lazy from PySide6.QtGui import QPixmap
lazy from domain.body_pack import BodyPackSource
lazy from domain.character_source import CharacterSource
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.body_pack_renderer import BodyPackRenderer, MakeupApplier, create_body_pack_renderer


def _body_pack_makeup_applier(
    outfit_dir: Path, asset_root: Path, official_pack_roots: tuple[Path, ...],
) -> MakeupApplier:
    """Apply the selected character makeup to the protected body frame."""
    overlay = ActiveOutfitOverlay(
        outfit_dir, asset_root, visible_hand_region=None,
        official_pack_root=official_pack_roots, native_frames=True,
    )

    def apply_body_makeup(
        frame: QPixmap, view: str, eye_state: str, viseme: str | None,
    ) -> QPixmap:
        overlay.set_active_mouth_state(viseme)
        return overlay.apply_makeup(frame, view, eye_state=eye_state)

    return apply_body_makeup


def body_pack_renderer_factory(
    character_source: CharacterSource, body_pack: BodyPackSource | None,
    outfit_dir: Path, official_pack_roots: tuple[Path, ...],
) -> Callable[[], BodyPackRenderer]:
    """Share one lazy renderer across half-body and full-body presentation ports."""
    @cache
    def renderer() -> BodyPackRenderer:
        return create_body_pack_renderer(
            body_pack, character_source.appearance.character_layer_views,
            character_source.assets.load_character_layer,
            apply_makeup=_body_pack_makeup_applier(
                outfit_dir, character_source.assets.asset_root, official_pack_roots,
            ),
        )

    return renderer
