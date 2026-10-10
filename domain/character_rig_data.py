"""MoHan compatibility facade for character-rig data."""

from __future__ import annotations

lazy from functools import lru_cache

lazy from domain.character_default_paths import DEFAULT_RIG_MANIFEST_PATH
lazy from domain.character_pack.character_data_models import (
    FULL_BODY_LAYER_COUNT,
    FULL_VIEW_COUNT,
    HAND_LANDMARK_COUNT,
    MAX_PITCH_DEGREES,
    MAX_YAW_DEGREES,
    MIN_PITCH_DEGREES,
    RIG_SCHEMA,
    SCHEMA_VERSION,
    ArmSpec,
    BodyMeasurementsSpec,
    BodyProportionsSpec,
    CharacterDataError,
    CharacterRigManifest,
    FaceCalibrationSpec,
    FullBodyCalibrationSpec,
    PhysicsSpec,
    PoseSpec,
    ViewportSpec,
    ViewRingSpec,
)
lazy from domain.character_rig_data_loader import load_rig_manifest


@lru_cache(maxsize=1)
def default_rig_manifest() -> CharacterRigManifest:
    """Return the validated bundled rig; disk is read at most once per process."""

    return load_rig_manifest(DEFAULT_RIG_MANIFEST_PATH)


__all__ = (
    "DEFAULT_RIG_MANIFEST_PATH",
    "FULL_BODY_LAYER_COUNT",
    "FULL_VIEW_COUNT",
    "HAND_LANDMARK_COUNT",
    "MAX_PITCH_DEGREES",
    "MAX_YAW_DEGREES",
    "MIN_PITCH_DEGREES",
    "RIG_SCHEMA",
    "SCHEMA_VERSION",
    "ArmSpec",
    "BodyMeasurementsSpec",
    "BodyProportionsSpec",
    "CharacterDataError",
    "CharacterRigManifest",
    "FaceCalibrationSpec",
    "FullBodyCalibrationSpec",
    "PhysicsSpec",
    "PoseSpec",
    "ViewRingSpec",
    "ViewportSpec",
    "default_rig_manifest",
    "load_rig_manifest",
)
