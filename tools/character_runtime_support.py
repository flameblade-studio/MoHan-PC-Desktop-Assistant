"""Explicit product-character activation for standalone repository tools."""

from __future__ import annotations

lazy from pathlib import Path

lazy from domain.character_source import (
    CharacterEngineProfile,
    activate_character_engine_profile,
    activate_character_source,
)
lazy from domain.constants import (
    POSE_ATLAS_GENERATION,
    POSE_ATLAS_LAYERED_RELATIVE_ROOT,
    POSE_ATLAS_RELATIVE_ROOT,
)
lazy from infrastructure.bundled_character_source import LegacyMohanCharacterSource

ROOT = Path(__file__).resolve().parents[1]


def activate_bundled_mohan_character_runtime(
    repo_root: Path = ROOT,
) -> None:
    """Activate the bundled MoHan source for a standalone product entry point."""

    source = LegacyMohanCharacterSource(repo_root)
    activate_character_source(source)
    activate_character_engine_profile(
        CharacterEngineProfile(
            assets=source.assets,
            runtime_bindings=source.appearance.runtime_bindings,
            rig_manifest=source.appearance.rig_manifest,
            pose_atlas_generation=POSE_ATLAS_GENERATION,
            pose_atlas_relative_root=POSE_ATLAS_RELATIVE_ROOT,
            pose_atlas_layered_relative_root=POSE_ATLAS_LAYERED_RELATIVE_ROOT,
        )
    )


__all__ = ("activate_bundled_mohan_character_runtime",)
