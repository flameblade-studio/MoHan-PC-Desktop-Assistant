from __future__ import annotations

lazy from dataclasses import dataclass

lazy from domain.character_runtime_data import default_rig_manifest


@dataclass(frozen=True, slots=True)
class BodyMeasurements:
    """Canonical adult body measurements used by MoHan's art pipeline."""

    height_cm: int
    weight_kg: int
    bust_cm: int
    underbust_cm: int
    waist_cm: int
    hips_cm: int


@dataclass(frozen=True, slots=True)
class CharacterBodyProfile:
    """Versioned geometry identity shared by every outfit and pose."""

    profile_id: str
    version: int
    measurements: BodyMeasurements
    art_direction: str


_RIG_MANIFEST = default_rig_manifest()
_MEASUREMENTS = _RIG_MANIFEST.body_measurements
MOHAN_BODY_PROFILE = CharacterBodyProfile(
    profile_id=_RIG_MANIFEST.body_profile_id,
    version=_RIG_MANIFEST.body_profile_version,
    measurements=BodyMeasurements(
        height_cm=_MEASUREMENTS.height_cm,
        weight_kg=_MEASUREMENTS.weight_kg,
        bust_cm=_MEASUREMENTS.bust_cm,
        underbust_cm=_MEASUREMENTS.underbust_cm,
        waist_cm=_MEASUREMENTS.waist_cm,
        hips_cm=_MEASUREMENTS.hips_cm,
    ),
    art_direction=_RIG_MANIFEST.body_art_direction,
)


def body_profile_reference() -> frozendict[str, object]:
    """Return the immutable compatibility identity exposed to outfit packs."""

    return frozendict(
        {
            "id": MOHAN_BODY_PROFILE.profile_id,
            "version": MOHAN_BODY_PROFILE.version,
        }
    )
