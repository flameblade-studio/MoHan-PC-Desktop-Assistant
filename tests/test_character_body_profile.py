from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from character_body_profile import (
    MOHAN_BODY_PROFILE,
    body_profile_reference,
)


def test_mohan_body_profile_is_the_fixed_adult_art_contract() -> None:
    profile = MOHAN_BODY_PROFILE
    measurements = profile.measurements

    assert body_profile_reference() == {
        "id": "mohan-body-v1",
        "version": 1,
    }
    assert (
        measurements.height_cm,
        measurements.weight_kg,
        measurements.bust_cm,
        measurements.underbust_cm,
        measurements.waist_cm,
        measurements.hips_cm,
    ) == (168, 54, 86, 71, 62, 90)
    assert "Adult East Asian woman" in profile.art_direction
    assert "never the core skeleton or body geometry" in profile.art_direction


if __name__ == "__main__":
    test_mohan_body_profile_is_the_fixed_adult_art_contract()
    print("CHARACTER_BODY_PROFILE_OK")
