"""Versioned visible-observation identity audit.

The earlier strict contract required one complete 18-field signature per
non-rear view. This module adds a versioned companion that accepts per-field
evidence states instead. A value exists only where every required vertex is
supported by authored artwork evidence; a model-projected point whose
visibility cannot be supported is never reported as "observed", and painted
hair is never reported as "unoccluded".

Three separations are enforced here:

* measured pass / over-threshold are compared against the existing numeric
  thresholds, unchanged;
* unverified means the evidence was insufficient, unknown, missing, or
  explicitly not applicable inside a required band - it can never pass;
* not applicable is only legal where the field is outside the view's band.

An empty or sparse comparable set is reported through coverage problems and can
never produce a pass. This module makes no biometric certification claim.
"""

from __future__ import annotations

lazy import math
lazy import re
lazy from collections.abc import Mapping
lazy from dataclasses import dataclass
lazy from enum import StrEnum
lazy from types import MappingProxyType

lazy from domain.character_identity_audit import (
    DEFAULT_IDENTITY_AUDIT_POLICY,
    SIGNATURE_FIELDS,
    FaceVisibility,
    IdentityAuditPolicy,
    expected_visibility,
)
lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id

SCHEMA = "mohan.pose-atlas-visible-identity-audit.v1"
CERTIFICATION_CLAIM = (
    "none: this audit reports authored-evidence measurements of model-projected "
    "landmarks and is not a biometric identity certification"
)
MODEL_DERIVED_BASIS = "model_derived_projected_measurement"
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


class FieldStatus(StrEnum):
    MEASURED = "measured"
    OCCLUDED = "occluded"
    UNSUPPORTED_SOURCE = "unsupported_source"
    NOT_APPLICABLE = "not_applicable"
    MISSING = "missing"


class VerdictOutcome(StrEnum):
    PASSED = "passed"
    OVER_THRESHOLD = "over_threshold"
    UNVERIFIED = "unverified"
    NOT_APPLICABLE = "not_applicable"


REASON_MISSING_IN_BAND = "missing_in_band_field"
REASON_NOT_APPLICABLE_IN_BAND = "not_applicable_in_required_band"

FRONTAL_FIELDS = SIGNATURE_FIELDS[:10]
PROFILE_FIELDS = (
    "face_length_width",
    "nose_length_face",
    "chin_length_face",
    "jaw_taper",
    "nose_projection",
    "lip_projection",
    "chin_projection",
    "forehead_slope",
)
REAR_PROFILE_FIELDS = SIGNATURE_FIELDS[-4:]
BAND_FIELDS: Mapping[FaceVisibility, tuple[str, ...]] = MappingProxyType({
    FaceVisibility.FRONT: FRONTAL_FIELDS,
    FaceVisibility.THREE_QUARTER: FRONTAL_FIELDS,
    FaceVisibility.PROFILE: PROFILE_FIELDS,
    FaceVisibility.REAR_THREE_QUARTER: REAR_PROFILE_FIELDS,
    FaceVisibility.REAR: (),
})


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


@dataclass(frozen=True, slots=True)
class VisibleFieldRecord:
    """One field of one view, with the evidence state that produced it."""

    field: str
    status: FieldStatus
    value: float | None
    method: str
    source_path: str | None
    source_sha256: str | None
    reason: str | None = None
    hidden_vertices: tuple[int, ...] = ()
    model_inferred_value: float | None = None
    measurement_basis: str = MODEL_DERIVED_BASIS

    def __post_init__(self) -> None:
        if self.field not in SIGNATURE_FIELDS:
            raise ValueError(f"Unknown canonical field: {self.field}")
        if not isinstance(self.status, FieldStatus):
            raise ValueError("Field status must be a FieldStatus member.")
        if not isinstance(self.method, str) or not self.method.strip():
            raise ValueError("A field record requires a non-empty method.")
        if self.status is FieldStatus.MEASURED:
            if not _is_finite_number(self.value):
                raise ValueError("A measured field requires a finite numeric value.")
            if self.hidden_vertices:
                raise ValueError("A measured field cannot hide a required vertex.")
        elif self.value is not None:
            raise ValueError("Only measured fields may carry the observed value.")
        if self.model_inferred_value is not None and not _is_finite_number(
            self.model_inferred_value
        ):
            raise ValueError("model_inferred_value must be finite or absent.")
        if self.status is FieldStatus.NOT_APPLICABLE:
            if self.source_sha256 is not None:
                raise ValueError("A not-applicable field must not claim a source digest.")
        elif not isinstance(self.source_sha256, str) or not SHA256_PATTERN.fullmatch(
            self.source_sha256
        ):
            raise ValueError("A field record requires a lowercase SHA-256 source digest.")


@dataclass(frozen=True, slots=True)
class VisibleViewRecord:
    """One view's visible-observation records."""

    view_id: str
    yaw_degrees: int
    visibility: FaceVisibility
    fields: dict[str, VisibleFieldRecord]

    def __post_init__(self) -> None:
        if self.yaw_degrees not in CANONICAL_YAWS:
            raise ValueError("Visible identity evidence must use a canonical yaw.")
        if self.view_id != canonical_view_id(self.yaw_degrees):
            raise ValueError("Visible identity view ID does not match its yaw.")
        if self.visibility is not expected_visibility(self.yaw_degrees):
            raise ValueError("Declared visibility does not match the view yaw band.")
        unknown = set(self.fields) - set(SIGNATURE_FIELDS)
        if unknown:
            raise ValueError(f"Unknown canonical field in view record: {sorted(unknown)}")
        for name, record in self.fields.items():
            if record.field != name:
                raise ValueError(f"Field key and record disagree: {name}")

    def status_for(self, field: str) -> FieldStatus:
        """A required field that is absent is ``missing``, never not-applicable."""

        record = self.fields.get(field)
        return FieldStatus.MISSING if record is None else record.status

    def coverage(self) -> dict[str, int]:
        counts = {
            FieldStatus.MEASURED.value: 0,
            FieldStatus.OCCLUDED.value: 0,
            FieldStatus.UNSUPPORTED_SOURCE.value: 0,
            FieldStatus.NOT_APPLICABLE.value: 0,
            FieldStatus.MISSING.value: 0,
        }
        for field in BAND_FIELDS[self.visibility]:
            counts[self.status_for(field).value] += 1
        return counts


@dataclass(frozen=True, slots=True)
class VisibleFieldComparison:
    """One field comparison against the mirrored or front reference view."""

    view_id: str
    field: str
    reference_view_id: str | None
    outcome: VerdictOutcome
    delta: float | None
    limit: float
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class VisibleIdentityAuditReport:
    schema: str
    passed: bool
    certification_claim: str
    comparisons: tuple[VisibleFieldComparison, ...]
    problems: tuple[str, ...]
    outcome_counts: dict[str, int]
    coverage: dict[str, dict[str, int]]
    over_threshold: tuple[VisibleFieldComparison, ...]
    unverified: tuple[VisibleFieldComparison, ...]

    def comparisons_for(self, view_id: str) -> tuple[VisibleFieldComparison, ...]:
        return tuple(item for item in self.comparisons if item.view_id == view_id)


def _limit_for(
    target: VisibleViewRecord,
    counterpart: VisibleViewRecord | None,
    policy: IdentityAuditPolicy,
) -> float:
    paired = (
        counterpart is not None
        and counterpart.view_id != target.view_id
        and counterpart.visibility is target.visibility
    )
    return (
        policy.maximum_pair_geometry_delta
        if paired
        else policy.maximum_front_geometry_delta
    )


def audit_visible_identity(
    views: tuple[VisibleViewRecord, ...],
    *,
    policy: IdentityAuditPolicy = DEFAULT_IDENTITY_AUDIT_POLICY,
) -> VisibleIdentityAuditReport:
    """Compare only supported observations; everything else stays unverified."""

    problems: list[str] = []
    by_yaw: dict[int, VisibleViewRecord] = {}
    for view in views:
        if view.yaw_degrees in by_yaw:
            problems.append(f"duplicate_visible_view:{view.yaw_degrees:+04d}")
        else:
            by_yaw[view.yaw_degrees] = view
    problems.extend(
        f"missing_visible_view:{yaw:+04d}" for yaw in CANONICAL_YAWS if yaw not in by_yaw
    )
    front = by_yaw.get(0)
    if front is None:
        problems.append("missing_front_visible_reference")

    comparisons: list[VisibleFieldComparison] = []
    coverage: dict[str, dict[str, int]] = {}
    for yaw in CANONICAL_YAWS:
        view = by_yaw.get(yaw)
        if view is None:
            continue
        counts = view.coverage()
        coverage[view.view_id] = counts
        if view.visibility is FaceVisibility.REAR:
            continue
        required = len(BAND_FIELDS[view.visibility])
        problems.extend(
            f"incomplete_visible_coverage:{view.view_id}"
            for _ in range(counts[FieldStatus.MEASURED.value] < required)
        )
        problems.extend(
            f"missing_in_band_field:{view.view_id}"
            for _ in range(counts[FieldStatus.MISSING.value])
        )
        problems.extend(
            f"not_applicable_in_required_band:{view.view_id}"
            for _ in range(counts[FieldStatus.NOT_APPLICABLE.value])
        )
        comparisons.extend(_compare_view(view, by_yaw, front, policy))

    counts: dict[str, int] = {outcome.value: 0 for outcome in VerdictOutcome}
    for comparison in comparisons:
        counts[comparison.outcome.value] += 1
    observed = [
        view.view_id
        for yaw, view in sorted(by_yaw.items())
        if view.visibility is not FaceVisibility.REAR
        and view.coverage()[FieldStatus.MEASURED.value] == 0
    ]
    problems.extend(f"no_visible_observation:{view}" for view in observed)
    vacuous = [
        view.view_id
        for yaw, view in sorted(by_yaw.items())
        if view.visibility is not FaceVisibility.REAR
        and yaw != 0
        and not any(
            item.outcome in {VerdictOutcome.PASSED, VerdictOutcome.OVER_THRESHOLD}
            for item in comparisons
            if item.view_id == view.view_id
        )
    ]
    problems.extend(f"no_comparable_visible_field:{view}" for view in vacuous)
    over_threshold = tuple(
        item for item in comparisons if item.outcome is VerdictOutcome.OVER_THRESHOLD
    )
    unverified = tuple(
        item for item in comparisons if item.outcome is VerdictOutcome.UNVERIFIED
    )
    passed = not problems and not over_threshold and not unverified
    return VisibleIdentityAuditReport(
        schema=SCHEMA,
        passed=passed,
        certification_claim=CERTIFICATION_CLAIM,
        comparisons=tuple(comparisons),
        problems=tuple(problems),
        outcome_counts=counts,
        coverage=coverage,
        over_threshold=over_threshold,
        unverified=unverified,
    )


def _compare_view(
    view: VisibleViewRecord,
    by_yaw: dict[int, VisibleViewRecord],
    front: VisibleViewRecord | None,
    policy: IdentityAuditPolicy,
) -> list[VisibleFieldComparison]:
    if view.visibility is FaceVisibility.REAR:
        return []
    counterpart = by_yaw.get(-view.yaw_degrees) if view.yaw_degrees else None
    if counterpart is not None and counterpart.view_id == view.view_id:
        counterpart = None
    # The front view is the reference itself, so its own coverage is reported
    # through the coverage counts rather than a self-comparison.
    if view.yaw_degrees == 0:
        return []
    reference = counterpart if counterpart is not None else front
    if reference is None or reference.view_id == view.view_id:
        return [
            VisibleFieldComparison(
                view.view_id, field, None, VerdictOutcome.UNVERIFIED, None,
                policy.maximum_front_geometry_delta, "reference_view_missing",
            )
            for field in BAND_FIELDS[view.visibility]
        ]
    limit = _limit_for(view, counterpart, policy)
    results: list[VisibleFieldComparison] = []
    for field in BAND_FIELDS[view.visibility]:
        target_status = view.status_for(field)
        reference_status = reference.status_for(field)
        if (
            target_status is FieldStatus.NOT_APPLICABLE
            or reference_status is FieldStatus.NOT_APPLICABLE
        ):
            results.append(VisibleFieldComparison(
                view.view_id, field, reference.view_id, VerdictOutcome.UNVERIFIED,
                None, limit, REASON_NOT_APPLICABLE_IN_BAND,
            ))
            continue
        if target_status is not FieldStatus.MEASURED:
            results.append(VisibleFieldComparison(
                view.view_id, field, reference.view_id, VerdictOutcome.UNVERIFIED,
                None, limit, f"target_{target_status.value}",
            ))
            continue
        if reference_status is not FieldStatus.MEASURED:
            results.append(VisibleFieldComparison(
                view.view_id, field, reference.view_id, VerdictOutcome.UNVERIFIED,
                None, limit, f"reference_{reference_status.value}",
            ))
            continue
        target = view.fields[field]
        other = reference.fields[field]
        delta = abs(float(target.value) - float(other.value))
        outcome = (
            VerdictOutcome.PASSED if delta <= limit else VerdictOutcome.OVER_THRESHOLD
        )
        results.append(VisibleFieldComparison(
            view.view_id, field, reference.view_id, outcome, delta, limit, None,
        ))
    return results
