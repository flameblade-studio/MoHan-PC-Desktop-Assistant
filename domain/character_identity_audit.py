from __future__ import annotations

lazy import math
lazy from collections.abc import Mapping
lazy from dataclasses import dataclass
lazy from enum import StrEnum

lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id
lazy from domain.vision_domain import cosine_similarity


class FaceVisibility(StrEnum):
    FRONT = "front"
    THREE_QUARTER = "three-quarter"
    PROFILE = "profile"
    REAR_THREE_QUARTER = "rear-three-quarter"
    REAR = "rear"


REAR_YAW = 180
REAR_THREE_QUARTER_YAW = 120
PROFILE_YAW = 75
THREE_QUARTER_YAW = 30


SIGNATURE_FIELDS = (
    "face_length_width",
    "eye_spacing_width",
    "eye_height_balance",
    "brow_eye_spacing",
    "nose_length_face",
    "nose_width_face",
    "mouth_width_face",
    "nose_mouth_spacing",
    "chin_length_face",
    "jaw_taper",
    "nose_projection",
    "lip_projection",
    "chin_projection",
    "forehead_slope",
    "cranial_height_width",
    "ear_height_head",
    "jaw_neck_transition",
    "hairline_nape",
)

_FRONTAL_FIELDS = SIGNATURE_FIELDS[:10]
_PROFILE_FIELDS = (
    "face_length_width",
    "nose_length_face",
    "chin_length_face",
    "jaw_taper",
    "nose_projection",
    "lip_projection",
    "chin_projection",
    "forehead_slope",
)
_REAR_PROFILE_FIELDS = SIGNATURE_FIELDS[-4:]


@dataclass(frozen=True, slots=True)
class FaceGeometrySignature:
    """Scale-independent identity geometry measured from one authored view."""

    values: Mapping[str, float]

    def __post_init__(self) -> None:
        if set(self.values) != set(SIGNATURE_FIELDS):
            raise ValueError("Face signature must contain every canonical field.")
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            for value in self.values.values()
        ):
            raise ValueError("Face signature values must be finite numbers.")


@dataclass(frozen=True, slots=True)
class CharacterIdentityEvidence:
    view_id: str
    yaw_degrees: int
    visibility: FaceVisibility
    geometry: FaceGeometrySignature | None
    embedding: tuple[float, ...] | None
    face_features_visible: bool
    evidence_id: str

    def __post_init__(self) -> None:
        if self.yaw_degrees not in CANONICAL_YAWS:
            raise ValueError("Identity evidence must use a canonical yaw.")
        if self.view_id != canonical_view_id(self.yaw_degrees):
            raise ValueError("Identity evidence view ID does not match its yaw.")
        if not self.evidence_id.strip():
            raise ValueError("Identity evidence requires a traceable identifier.")
        if self.visibility is FaceVisibility.REAR:
            if self.face_features_visible or self.geometry is not None or self.embedding:
                raise ValueError("Rear evidence must not expose or encode a face.")
        elif self.geometry is None:
            raise ValueError("Every non-rear view requires measured identity geometry.")
        elif (
            self.visibility is not FaceVisibility.REAR_THREE_QUARTER
            and not self.face_features_visible
        ):
            raise ValueError("Visible-face evidence must confirm facial features.")
        if self.embedding is not None and (
            not self.embedding
            or any(not math.isfinite(float(value)) for value in self.embedding)
        ):
            raise ValueError("Face embedding must contain finite values.")


@dataclass(frozen=True, slots=True)
class IdentityAuditPolicy:
    maximum_pair_geometry_delta: float = 0.035
    maximum_front_geometry_delta: float = 0.055
    minimum_embedding_similarity: float = 0.38
    maximum_height_scale_delta: float = 0.01

    def __post_init__(self) -> None:
        if not 0.0 < self.maximum_pair_geometry_delta < 1.0:
            raise ValueError("Pair geometry threshold must be within 0..1.")
        if not 0.0 < self.maximum_front_geometry_delta < 1.0:
            raise ValueError("Front geometry threshold must be within 0..1.")
        if not -1.0 <= self.minimum_embedding_similarity <= 1.0:
            raise ValueError("Embedding threshold must be within -1..1.")
        if not 0.0 <= self.maximum_height_scale_delta < 1.0:
            raise ValueError("Height scale threshold must be within 0..1.")


DEFAULT_IDENTITY_AUDIT_POLICY = IdentityAuditPolicy()


@dataclass(frozen=True, slots=True)
class IdentityViewResult:
    view_id: str
    geometry_delta: float | None
    embedding_similarity: float | None
    problems: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.problems


@dataclass(frozen=True, slots=True)
class CharacterIdentityAuditReport:
    passed: bool
    views: tuple[IdentityViewResult, ...]
    problems: tuple[str, ...]


def expected_visibility(yaw_degrees: int) -> FaceVisibility:
    absolute = abs(yaw_degrees)
    if absolute == REAR_YAW:
        return FaceVisibility.REAR
    if absolute >= REAR_THREE_QUARTER_YAW:
        return FaceVisibility.REAR_THREE_QUARTER
    if absolute >= PROFILE_YAW:
        return FaceVisibility.PROFILE
    if absolute >= THREE_QUARTER_YAW:
        return FaceVisibility.THREE_QUARTER
    return FaceVisibility.FRONT


def audit_character_identity(
    evidence: tuple[CharacterIdentityEvidence, ...],
    *,
    normalized_subject_heights: Mapping[int, float] | None = None,
    policy: IdentityAuditPolicy = DEFAULT_IDENTITY_AUDIT_POLICY,
) -> CharacterIdentityAuditReport:
    """Fail closed unless every view is the same identity at one registration."""

    problems: list[str] = []
    by_yaw: dict[int, CharacterIdentityEvidence] = {}
    for item in evidence:
        if item.yaw_degrees in by_yaw:
            problems.append(f"duplicate_identity_view:{item.yaw_degrees:+04d}")
        else:
            by_yaw[item.yaw_degrees] = item
    problems.extend(
        f"missing_identity_view:{yaw:+04d}"
        for yaw in CANONICAL_YAWS
        if yaw not in by_yaw
    )

    front = by_yaw.get(0)
    if front is None or front.visibility is not FaceVisibility.FRONT:
        problems.append("missing_front_identity_reference")

    results: list[IdentityViewResult] = []
    for yaw in CANONICAL_YAWS:
        item = by_yaw.get(yaw)
        if item is None:
            continue
        result = _audit_identity_view(item, by_yaw, front, policy)
        results.append(result)
        problems.extend(f"{problem}:{item.view_id}" for problem in result.problems)

    _audit_subject_height(normalized_subject_heights, policy, problems)
    return CharacterIdentityAuditReport(
        not problems,
        tuple(results),
        tuple(problems),
    )


def _audit_identity_view(
    item: CharacterIdentityEvidence,
    by_yaw: Mapping[int, CharacterIdentityEvidence],
    front: CharacterIdentityEvidence | None,
    policy: IdentityAuditPolicy,
) -> IdentityViewResult:
    item_problems = [
        "visibility_band"
        for _ in range(item.visibility is not expected_visibility(item.yaw_degrees))
    ]
    if item.visibility is FaceVisibility.REAR:
        if item.face_features_visible or item.geometry is not None or item.embedding:
            item_problems.append("rear_exposes_face")
        return IdentityViewResult(item.view_id, None, None, tuple(item_problems))
    counterpart = by_yaw.get(-item.yaw_degrees) if item.yaw_degrees else front
    geometry_reference = _geometry_reference(counterpart, front, item.visibility)
    geometry_delta = (
        _signature_delta(item.geometry, geometry_reference, _fields_for(item.visibility))
        if item.geometry is not None and geometry_reference is not None
        else None
    )
    geometry_limit = (
        policy.maximum_pair_geometry_delta
        if counterpart is not None and counterpart is not item
        else policy.maximum_front_geometry_delta
    )
    if geometry_delta is None:
        item_problems.append("missing_geometry")
    elif geometry_delta > geometry_limit:
        item_problems.append("face_geometry_drift")
    embedding_reference = (
        counterpart.embedding
        if counterpart is not None and counterpart.embedding is not None
        else front.embedding if front is not None else None
    )
    similarity = _embedding_similarity(item.embedding, embedding_reference)
    if _embedding_drifted(item, embedding_reference, similarity, policy):
        item_problems.append("face_embedding_drift")
    return IdentityViewResult(item.view_id, geometry_delta, similarity, tuple(item_problems))


def _geometry_reference(
    counterpart: CharacterIdentityEvidence | None,
    front: CharacterIdentityEvidence | None,
    visibility: FaceVisibility,
) -> FaceGeometrySignature | None:
    if (
        counterpart is not None
        and counterpart.visibility is visibility
        and counterpart.geometry is not None
    ):
        return counterpart.geometry
    return front.geometry if front is not None else None


def _embedding_drifted(
    item: CharacterIdentityEvidence,
    reference: tuple[float, ...] | None,
    similarity: float | None,
    policy: IdentityAuditPolicy,
) -> bool:
    return (
        item.visibility is not FaceVisibility.PROFILE
        and item.embedding is not None
        and reference is not None
        and similarity is not None
        and similarity < policy.minimum_embedding_similarity
    )


def _signature_delta(
    left: FaceGeometrySignature,
    right: FaceGeometrySignature,
    fields: tuple[str, ...],
) -> float:
    return max(
        abs(float(left.values[name]) - float(right.values[name]))
        for name in fields
    )


def _fields_for(visibility: FaceVisibility) -> tuple[str, ...]:
    if visibility is FaceVisibility.PROFILE:
        return _PROFILE_FIELDS
    if visibility is FaceVisibility.REAR_THREE_QUARTER:
        return _REAR_PROFILE_FIELDS
    return _FRONTAL_FIELDS


def _embedding_similarity(
    left: tuple[float, ...] | None,
    right: tuple[float, ...] | None,
) -> float | None:
    if left is None or right is None or len(left) != len(right):
        return None
    return cosine_similarity(left, right)


def _audit_subject_height(
    heights: Mapping[int, float] | None,
    policy: IdentityAuditPolicy,
    problems: list[str],
) -> None:
    if heights is None:
        problems.append("missing_subject_registration")
        return
    if set(heights) != set(CANONICAL_YAWS):
        problems.append("incomplete_subject_registration")
        return
    values = tuple(float(heights[yaw]) for yaw in CANONICAL_YAWS)
    if any(not math.isfinite(value) or value <= 0.0 for value in values):
        problems.append("invalid_subject_registration")
        return
    median = sorted(values)[len(values) // 2]
    for yaw, height in zip(CANONICAL_YAWS, values, strict=True):
        if abs(height / median - 1.0) > policy.maximum_height_scale_delta:
            problems.append(f"subject_scale_drift:{yaw:+04d}")
    for yaw in CANONICAL_YAWS:
        if yaw <= 0 or -yaw not in heights:
            continue
        pair_mean = (float(heights[yaw]) + float(heights[-yaw])) / 2.0
        pair_delta = abs(float(heights[yaw]) - float(heights[-yaw])) / pair_mean
        if pair_delta > policy.maximum_height_scale_delta:
            problems.append(f"mirror_scale_drift:{yaw:+04d}")
