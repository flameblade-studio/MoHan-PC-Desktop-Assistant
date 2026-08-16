from __future__ import annotations

lazy from dataclasses import dataclass


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


MOHAN_BODY_PROFILE = CharacterBodyProfile(
    profile_id="mohan-body-v1",
    version=1,
    measurements=BodyMeasurements(
        height_cm=168,
        weight_kg=54,
        bust_cm=86,
        underbust_cm=71,
        waist_cm=62,
        hips_cm=90,
    ),
    art_direction=(
        "Adult East Asian woman with a tall, slender frame and a natural, "
        "centered, supported C70-equivalent bust contour. Garments may alter "
        "drape and support, but never the core skeleton or body geometry."
    ),
)


def body_profile_reference() -> frozendict[str, object]:
    """Return the immutable compatibility identity exposed to outfit packs."""

    return frozendict(
        {
            "id": MOHAN_BODY_PROFILE.profile_id,
            "version": MOHAN_BODY_PROFILE.version,
        }
    )
