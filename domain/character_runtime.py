"""Character-neutral access to composition-root-injected runtime values."""

from __future__ import annotations

lazy from collections.abc import Iterator, Mapping, Sequence
lazy from pathlib import PurePosixPath

lazy from domain.character_pack.character_data_models import (
    CharacterRigManifest,
    FaceCalibrationSpec,
)
lazy from domain.character_source import active_character_engine_profile


class _ActiveBindingMap(Mapping[str, str]):
    """Read one mapping from the currently injected character profile."""

    def __init__(self, section: str) -> None:
        self._section = section

    def _values(self) -> Mapping[str, str]:
        bindings = active_character_engine_profile().runtime_bindings
        return getattr(bindings, self._section)

    def __getitem__(self, key: str) -> str:
        return self._values()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values())

    def __len__(self) -> int:
        return len(self._values())


class _ActiveLayerOrder(Sequence[str]):
    """Expose layer order without caching one character at module import."""

    @staticmethod
    def _values() -> tuple[str, ...]:
        return active_character_engine_profile().rig_manifest.layer_z_order

    def __getitem__(self, index: int | slice) -> str | tuple[str, ...]:
        return self._values()[index]

    def __len__(self) -> int:
        return len(self._values())

    def __iter__(self) -> Iterator[str]:
        return iter(self._values())


CHARACTER_ASSET_PATHS: Mapping[str, str] = _ActiveBindingMap("asset_paths")
CHARACTER_POSE_ROLES: Mapping[str, str] = _ActiveBindingMap("pose_roles")
CHARACTER_EXPRESSION_ROLES: Mapping[str, str] = _ActiveBindingMap("expression_roles")
CHARACTER_LAYER_ROLES: Mapping[str, str] = _ActiveBindingMap("layer_roles")
FULL_BODY_LAYER_Z_ORDER: Sequence[str] = _ActiveLayerOrder()


def character_rig_manifest() -> CharacterRigManifest:
    """Return the rig selected by the product composition root."""

    return active_character_engine_profile().rig_manifest


def character_face_calibration() -> FaceCalibrationSpec:
    """Return face calibration for the selected character."""

    return character_rig_manifest().face_calibration


def pose_atlas_generation() -> int:
    """Return the product-injected generation of the active full-body atlas."""

    return active_character_engine_profile().pose_atlas_generation


def pose_atlas_relative_root() -> str:
    """Return the product-injected static PoseAtlas root."""

    return active_character_engine_profile().pose_atlas_relative_root


def pose_atlas_layered_relative_root() -> str:
    """Return the product-injected layered PoseAtlas root."""

    return active_character_engine_profile().pose_atlas_layered_relative_root


def pose_atlas_root_name() -> str:
    """Return the final directory name of the static PoseAtlas root."""

    return PurePosixPath(pose_atlas_relative_root()).name


def pose_atlas_layered_root_name() -> str:
    """Return the final directory name of the layered PoseAtlas root."""

    return PurePosixPath(pose_atlas_layered_relative_root()).name


__all__ = (
    "CHARACTER_ASSET_PATHS",
    "CHARACTER_EXPRESSION_ROLES",
    "CHARACTER_LAYER_ROLES",
    "CHARACTER_POSE_ROLES",
    "FULL_BODY_LAYER_Z_ORDER",
    "character_face_calibration",
    "character_rig_manifest",
    "pose_atlas_generation",
    "pose_atlas_layered_relative_root",
    "pose_atlas_layered_root_name",
    "pose_atlas_relative_root",
    "pose_atlas_root_name",
)
