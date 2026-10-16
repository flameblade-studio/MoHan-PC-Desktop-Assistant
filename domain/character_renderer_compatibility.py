"""Compatibility gate between character rigs and compiled renderers."""

from __future__ import annotations

lazy from dataclasses import replace

lazy from domain.character_pack.character_data_models import CharacterRigManifest
lazy from domain.character_runtime_data import default_rig_manifest
lazy from domain.character_source import CharacterSource


def validated_renderer_rig(
    character_source: CharacterSource,
) -> CharacterRigManifest:
    """Reject rigs unsupported by the currently compiled compositor geometry."""

    rig = character_source.appearance.rig_manifest
    runtime_rig = default_rig_manifest()
    if replace(rig, character_id=runtime_rig.character_id) != runtime_rig:
        raise ValueError(
            "The selected character rig is incompatible with the installed renderers."
        )
    return rig


__all__ = ("validated_renderer_rig",)
