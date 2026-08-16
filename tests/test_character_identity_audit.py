from __future__ import annotations

lazy import sys
lazy from dataclasses import replace
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from character_identity_audit import (
    SIGNATURE_FIELDS,
    CharacterIdentityEvidence,
    FaceGeometrySignature,
    FaceVisibility,
    audit_character_identity,
    expected_visibility,
)
lazy from character_pose import CANONICAL_YAWS, canonical_view_id


def signature(change: tuple[str, float] | None = None) -> FaceGeometrySignature:
    values = {name: 0.5 for name in SIGNATURE_FIELDS}
    if change is not None:
        values[change[0]] = change[1]
    return FaceGeometrySignature(frozendict(values))


def evidence(yaw: int) -> CharacterIdentityEvidence:
    visibility = expected_visibility(yaw)
    rear = visibility is FaceVisibility.REAR
    return CharacterIdentityEvidence(
        canonical_view_id(yaw),
        yaw,
        visibility,
        None if rear else signature(),
        (
            None
            if rear
            or visibility in {
                FaceVisibility.PROFILE,
                FaceVisibility.REAR_THREE_QUARTER,
            }
            else (1.0, 0.0, 0.0)
        ),
        visibility not in {
            FaceVisibility.REAR,
            FaceVisibility.REAR_THREE_QUARTER,
        },
        f"identity-proof:{yaw:+04d}",
    )


def ring() -> tuple[CharacterIdentityEvidence, ...]:
    return tuple(evidence(yaw) for yaw in CANONICAL_YAWS)


def heights(value: float = 1453.0) -> frozendict[int, float]:
    return frozendict({yaw: value for yaw in CANONICAL_YAWS})


def assert_complete_identity_ring_passes() -> None:
    report = audit_character_identity(ring(), normalized_subject_heights=heights())
    assert report.passed
    assert len(report.views) == 24


def assert_missing_duplicate_and_rear_face_fail() -> None:
    items = ring()
    report = audit_character_identity(items[:-1], normalized_subject_heights=heights())
    assert "missing_identity_view:+165" in report.problems
    report = audit_character_identity((*items, items[0]), normalized_subject_heights=heights())
    assert "duplicate_identity_view:-180" in report.problems
    try:
        replace(
            items[0],
            geometry=signature(),
            embedding=(1.0, 0.0, 0.0),
            face_features_visible=True,
        )
    except ValueError as exc:
        assert "Rear evidence" in str(exc)
    else:
        raise AssertionError("rear-facing identity evidence must reject facial features")


def assert_mirror_geometry_and_embedding_drift_fail() -> None:
    items = list(ring())
    index = CANONICAL_YAWS.index(45)
    items[index] = replace(
        items[index],
        geometry=signature(("jaw_taper", 0.61)),
        embedding=(0.0, 1.0, 0.0),
    )
    report = audit_character_identity(tuple(items), normalized_subject_heights=heights())
    view_id = canonical_view_id(45)
    assert f"face_geometry_drift:{view_id}" in report.problems
    assert f"face_embedding_drift:{view_id}" in report.problems


def assert_scale_drift_and_missing_registration_fail() -> None:
    report = audit_character_identity(ring())
    assert "missing_subject_registration" in report.problems
    changed = dict(heights())
    changed[90] = 1480.0
    changed[-90] = 1429.0
    report = audit_character_identity(
        ring(),
        normalized_subject_heights=frozendict(changed),
    )
    assert "subject_scale_drift:+090" in report.problems
    assert "mirror_scale_drift:+090" in report.problems


def run() -> None:
    assert_complete_identity_ring_passes()
    assert_missing_duplicate_and_rear_face_fail()
    assert_mirror_geometry_and_embedding_drift_fail()
    assert_scale_drift_and_missing_registration_fail()
    print("CHARACTER_IDENTITY_AUDIT_OK")


if __name__ == "__main__":
    run()
