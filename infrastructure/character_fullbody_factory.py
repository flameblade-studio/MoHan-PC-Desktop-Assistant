"""Assemble existing character full-body assets at a single injected boundary."""
from __future__ import annotations

lazy from collections.abc import Callable, Mapping
lazy from domain.character_source import CharacterSource
lazy from domain.character_renderer_compatibility import validated_renderer_rig
lazy from domain.constants import POSE_ATLAS_RELATIVE_ROOT, POSE_ATLAS_LAYERED_RELATIVE_ROOT
lazy from application.character_default_look import CharacterDefaultLook, complete_fullbody_path


def create_character_fullbody_renderer(
    source: CharacterSource, bindings: Mapping[str, str], overlay: object,
    default_look: CharacterDefaultLook | None, *,
    renderer_factory: Callable, manifest_loader: Callable, placement_loader: Callable,
) -> object:
    """Preserve native and structural legacy routes through explicit dependencies."""
    if not hasattr(source, "appearance"):
        return renderer_factory(
            outfit_overlay=overlay,
            display_placement=placement_loader(source.assets.resolve_path(POSE_ATLAS_RELATIVE_ROOT)),
        )
    validated_renderer_rig(source)
    layered_root = source.assets.resolve_path(
        bindings.get("fullbody_complete_layered", POSE_ATLAS_LAYERED_RELATIVE_ROOT)
    )
    authority_root = source.assets.resolve_path(POSE_ATLAS_RELATIVE_ROOT)
    return renderer_factory(
        manifest=manifest_loader(layered_root), outfit_overlay=overlay,
        authority_root=authority_root, display_placement=placement_loader(authority_root),
        native_frames_provider=default_look.fullbody_root if default_look is not None else None,
        native_frames_root=(default_look.fullbody_root() if default_look is not None
                            else complete_fullbody_path(source, bindings)),
    )
