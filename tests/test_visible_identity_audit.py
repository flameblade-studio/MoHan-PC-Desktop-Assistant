"""Contract tests for the versioned visible-observation identity audit."""

from __future__ import annotations

import pytest

from domain.character_identity_audit import (
    DEFAULT_IDENTITY_AUDIT_POLICY,
    FaceVisibility,
    expected_visibility,
)
from domain.character_pose import canonical_view_id
from domain import character_identity_audit as strict_audit
from domain import visible_identity_audit as audit

GOOD_SHA = "a" * 64
MIRROR_PAIR = (15, -15)
OVER_PAIR_LIMIT = DEFAULT_IDENTITY_AUDIT_POLICY.maximum_pair_geometry_delta + 0.01
OVER_FRONT_LIMIT = DEFAULT_IDENTITY_AUDIT_POLICY.maximum_front_geometry_delta + 0.01
ALL_YAWS = tuple(range(-180, 180, 15))


def field_record(
    name: str,
    status: audit.FieldStatus,
    value: float | None = None,
) -> audit.VisibleFieldRecord:
    return audit.VisibleFieldRecord(
        field=name,
        status=status,
        value=value,
        method="fixture-ratio",
        source_path=f"fixture/{name}.json",
        source_sha256=None if status is audit.FieldStatus.NOT_APPLICABLE else GOOD_SHA,
        reason=None if status is audit.FieldStatus.MEASURED else f"fixture_{status.value}",
        hidden_vertices=(234,) if status is audit.FieldStatus.OCCLUDED else (),
        model_inferred_value=0.5 if status is audit.FieldStatus.OCCLUDED else None,
    )


def view(
    yaw: int,
    fields: dict[str, audit.VisibleFieldRecord],
) -> audit.VisibleViewRecord:
    return audit.VisibleViewRecord(
        view_id=canonical_view_id(yaw),
        yaw_degrees=yaw,
        visibility=expected_visibility(yaw),
        fields=fields,
    )


def band_fields(yaw: int) -> tuple[str, ...]:
    return audit.BAND_FIELDS[expected_visibility(yaw)]


def full_band(yaw: int, status: audit.FieldStatus) -> dict[str, audit.VisibleFieldRecord]:
    return {name: field_record(name, status) for name in band_fields(yaw)}


def complete_view(yaw: int, value: float) -> audit.VisibleViewRecord:
    return view(
        yaw,
        {name: field_record(name, audit.FieldStatus.MEASURED, value)
         for name in band_fields(yaw)},
    )


def complete_series(value: float = 0.5) -> list[audit.VisibleViewRecord]:
    return [complete_view(yaw, value) for yaw in ALL_YAWS]


def test_band_fields_match_the_strict_contract_subsets() -> None:
    assert tuple(strict_audit._FRONTAL_FIELDS) == audit.FRONTAL_FIELDS
    assert tuple(strict_audit._PROFILE_FIELDS) == audit.PROFILE_FIELDS
    assert tuple(strict_audit._REAR_PROFILE_FIELDS) == audit.REAR_PROFILE_FIELDS
    assert audit.BAND_FIELDS[FaceVisibility.REAR] == ()


def test_all_occluded_view_cannot_pass_and_reports_vacuity() -> None:
    views = tuple(
        view(yaw, full_band(yaw, audit.FieldStatus.OCCLUDED)) for yaw in ALL_YAWS
    )

    report = audit.audit_visible_identity(views)

    assert report.passed is False
    assert report.outcome_counts[audit.VerdictOutcome.PASSED.value] == 0
    assert report.outcome_counts[audit.VerdictOutcome.OVER_THRESHOLD.value] == 0
    assert any(p.startswith("no_visible_observation:") for p in report.problems)
    assert any(p.startswith("no_comparable_visible_field:") for p in report.problems)
    assert report.certification_claim.startswith("none:")


def test_unsupported_and_not_applicable_cannot_pass() -> None:
    for status in (audit.FieldStatus.UNSUPPORTED_SOURCE, audit.FieldStatus.NOT_APPLICABLE):
        views = tuple(view(yaw, full_band(yaw, status)) for yaw in ALL_YAWS)

        report = audit.audit_visible_identity(views)

        assert report.passed is False
        assert report.outcome_counts[audit.VerdictOutcome.PASSED.value] == 0


def test_missing_in_band_field_is_a_problem_and_never_passes() -> None:
    views = complete_series()
    target = canonical_view_id(30)
    trimmed = [
        view(item.yaw_degrees, {
            name: record for name, record in item.fields.items() if name != "jaw_taper"
        }) if item.view_id == target else item
        for item in views
    ]

    report = audit.audit_visible_identity(tuple(trimmed))

    assert f"missing_in_band_field:{target}" in report.problems
    assert any(
        item.field == "jaw_taper"
        and item.outcome is audit.VerdictOutcome.UNVERIFIED
        and item.reason == "target_missing"
        for item in report.comparisons
    )
    assert report.passed is False


def test_front_view_coverage_is_counted_not_skipped() -> None:
    views = complete_series()
    front = canonical_view_id(0)
    trimmed = [
        view(item.yaw_degrees, {
            name: record for name, record in item.fields.items()
            if not (item.view_id == front and name == "eye_spacing_width")
        }) if item.view_id == front else item
        for item in views
    ]

    report = audit.audit_visible_identity(tuple(trimmed))

    assert f"missing_in_band_field:{front}" in report.problems
    assert report.coverage[front][audit.FieldStatus.MISSING.value] == 1
    assert report.passed is False


def test_explicit_not_applicable_inside_the_band_is_unverified() -> None:
    views = complete_series()
    target = canonical_view_id(-30)
    swapped = [
        view(item.yaw_degrees, {
            **item.fields,
            "jaw_taper": field_record("jaw_taper", audit.FieldStatus.NOT_APPLICABLE),
        }) if item.view_id == target else item
        for item in views
    ]

    report = audit.audit_visible_identity(tuple(swapped))

    assert f"not_applicable_in_required_band:{target}" in report.problems
    assert any(
        item.field == "jaw_taper"
        and item.outcome is audit.VerdictOutcome.UNVERIFIED
        and item.reason == audit.REASON_NOT_APPLICABLE_IN_BAND
        for item in report.comparisons
    )
    assert report.passed is False


def test_sparse_single_field_view_cannot_vacuous_pass() -> None:
    sparse = [complete_view(yaw, 0.5) for yaw in (0, 30)]
    sparse[1] = view(30, {"jaw_taper": field_record(
        "jaw_taper", audit.FieldStatus.MEASURED, 0.5
    )})

    report = audit.audit_visible_identity(tuple(sparse))

    assert f"incomplete_visible_coverage:{canonical_view_id(30)}" in report.problems
    assert report.passed is False
    assert report.coverage[canonical_view_id(30)][audit.FieldStatus.MEASURED.value] == 1


def test_complete_series_can_pass_and_over_threshold_fails() -> None:
    passing = audit.audit_visible_identity(tuple(complete_series()))
    assert passing.passed is True
    assert passing.problems == ()

    target, _reference = MIRROR_PAIR
    views = [
        complete_view(yaw, 0.5 + OVER_PAIR_LIMIT if yaw == target else 0.5)
        for yaw in ALL_YAWS
    ]
    report = audit.audit_visible_identity(tuple(views))

    assert report.passed is False
    assert report.outcome_counts[audit.VerdictOutcome.OVER_THRESHOLD.value] > 0
    assert all(item.limit == (
        DEFAULT_IDENTITY_AUDIT_POLICY.maximum_pair_geometry_delta
    ) for item in report.over_threshold)


def test_front_limit_is_used_when_no_mirror_exists() -> None:
    views = [complete_view(0, 0.5), complete_view(15, 0.5 + OVER_FRONT_LIMIT)]

    report = audit.audit_visible_identity(tuple(views))

    assert {item.limit for item in report.over_threshold} == {
        DEFAULT_IDENTITY_AUDIT_POLICY.maximum_front_geometry_delta
    }


def test_duplicate_and_missing_views_are_problems() -> None:
    report = audit.audit_visible_identity((complete_view(0, 0.5), complete_view(0, 0.5)))

    assert "duplicate_visible_view:+000" in report.problems
    assert any(p.startswith("missing_visible_view:") for p in report.problems)
    assert report.passed is False


def test_invalid_records_are_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown canonical field"):
        view(0, {"not_a_field": field_record(
            "face_length_width", audit.FieldStatus.MEASURED, 1.0
        )} | {"not_a_field": audit.VisibleFieldRecord(
            field="face_length_width",
            status=audit.FieldStatus.MEASURED,
            value=1.0,
            method="fixture",
            source_path=None,
            source_sha256=GOOD_SHA,
        )})
    for bad_value in (float("nan"), float("inf"), True, "0.5"):
        with pytest.raises(ValueError, match="finite numeric value"):
            audit.VisibleFieldRecord(
                field="face_length_width",
                status=audit.FieldStatus.MEASURED,
                value=bad_value,
                method="fixture",
                source_path=None,
                source_sha256=GOOD_SHA,
            )
    with pytest.raises(ValueError, match="FieldStatus member"):
        audit.VisibleFieldRecord(
            field="face_length_width",
            status="measured",
            value=1.0,
            method="fixture",
            source_path=None,
            source_sha256=GOOD_SHA,
        )
    for bad_sha in ("", "abc", "A" * 64, "z" * 64):
        with pytest.raises(ValueError, match="SHA-256"):
            audit.VisibleFieldRecord(
                field="face_length_width",
                status=audit.FieldStatus.UNSUPPORTED_SOURCE,
                value=None,
                method="fixture",
                source_path=None,
                source_sha256=bad_sha,
            )
    with pytest.raises(ValueError, match="non-empty method"):
        audit.VisibleFieldRecord(
            field="face_length_width",
            status=audit.FieldStatus.MEASURED,
            value=1.0,
            method="   ",
            source_path=None,
            source_sha256=GOOD_SHA,
        )
    with pytest.raises(ValueError, match="not claim a source digest"):
        audit.VisibleFieldRecord(
            field="face_length_width",
            status=audit.FieldStatus.NOT_APPLICABLE,
            value=None,
            method="fixture",
            source_path=None,
            source_sha256=GOOD_SHA,
        )


def test_measured_record_cannot_hide_a_vertex() -> None:
    with pytest.raises(ValueError, match="cannot hide a required vertex"):
        audit.VisibleFieldRecord(
            field="face_length_width",
            status=audit.FieldStatus.MEASURED,
            value=1.0,
            method="fixture",
            source_path=None,
            source_sha256=GOOD_SHA,
            hidden_vertices=(234,),
        )


def test_visibility_band_must_match_the_yaw_and_key_must_match_field() -> None:
    with pytest.raises(ValueError, match="visibility does not match"):
        audit.VisibleViewRecord(
            view_id=canonical_view_id(0),
            yaw_degrees=0,
            visibility=FaceVisibility.REAR,
            fields={},
        )
    with pytest.raises(ValueError, match="key and record disagree"):
        view(0, {"face_length_width": field_record(
            "eye_spacing_width", audit.FieldStatus.MEASURED, 1.0
        )})
