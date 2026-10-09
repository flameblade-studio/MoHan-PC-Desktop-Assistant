"""Activate the bundled product character for isolated engine tests."""

from __future__ import annotations

lazy import runpy
lazy import sys
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


def activate_bundled_character_runtime() -> None:
    """Build the same character-engine profile as the product composition root."""

    source = LegacyMohanCharacterSource(ROOT)
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


def main(arguments: list[str] | None = None) -> int:
    """Run one legacy direct test after installing its product fixture."""

    selected = sys.argv[1:] if arguments is None else arguments
    if len(selected) != 1:
        raise SystemExit("usage: python -m tests.character_runtime_support TEST_FILE")
    activate_bundled_character_runtime()
    previous_arguments = sys.argv
    try:
        sys.argv = [selected[0]]
        runpy.run_path(selected[0], run_name="__main__")
    finally:
        sys.argv = previous_arguments
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
