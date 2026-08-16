from __future__ import annotations

lazy import hashlib
lazy from collections import Counter
lazy from dataclasses import dataclass
lazy from typing import Protocol

lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id

REQUIRED_LAYER_RESPONSIBILITIES = frozendict(
    {
        "hair-back": "hair",
        "body": "core-body",
        "garment": "garment",
        "arm-left": "left-arm",
        "arm-right": "right-arm",
        "hand-left": "left-hand",
        "hand-right": "right-hand",
        "weapon": "weapon",
        "headwear": "headwear",
        "hair-front": "hair",
    }
)
BACK_YAWS = frozenset({-180})


@dataclass(frozen=True, slots=True)
class AtlasLayerEvidence:
    role: str
    depth: int
    owner: str
    manifest_evidence: str


@dataclass(frozen=True, slots=True)
class AtlasViewEvidence:
    view_id: str
    yaw_degrees: int
    width: int
    height: int
    anchor_x: int
    anchor_y: int
    alpha_bounds: tuple[int, int, int, int]
    identity_lock_evidence: str
    rgba: bytes
    layers: tuple[AtlasLayerEvidence, ...]

    @property
    def rgba_sha256(self) -> str:
        return hashlib.sha256(self.rgba).hexdigest()


@dataclass(frozen=True, slots=True)
class AdjacentViewMetric:
    first_yaw: int
    second_yaw: int
    outline_displacement: int
    mean_color_delta: float


@dataclass(frozen=True, slots=True)
class PoseAtlasAuditPolicy:
    max_outline_displacement: int = 1
    max_color_delta: float = 24.0


DEFAULT_POSE_ATLAS_AUDIT_POLICY = PoseAtlasAuditPolicy()


@dataclass(frozen=True, slots=True)
class PoseAtlasAuditReport:
    passed: bool
    views: tuple[AtlasViewEvidence, ...]
    adjacent_metrics: tuple[AdjacentViewMetric, ...]
    problems: tuple[str, ...]
    identity_problems: tuple[IdentityAuditProblem, ...] = ()
    body_problems: tuple[BodyAuditProblem, ...] = ()


class HandAuditPort(Protocol):
    def passed(self, view_id: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class IdentityAuditProblem:
    code: str
    view_id: str | None = None


class IdentityAuditReportPort(Protocol):
    passed: bool
    problems: tuple[str, ...]


class IdentityAuditPort(Protocol):
    def audit(
        self,
        views: tuple[AtlasViewEvidence, ...],
    ) -> IdentityAuditReportPort: ...


@dataclass(frozen=True, slots=True)
class BodyAuditProblem:
    code: str
    yaw_degrees: int | None = None


class BodyAuditReportPort(Protocol):
    passed: bool
    problems: tuple[str, ...]


class BodyAuditPort(Protocol):
    def audit(
        self,
        views: tuple[AtlasViewEvidence, ...],
    ) -> BodyAuditReportPort | None: ...


def audit_pose_atlas(
    views: tuple[AtlasViewEvidence, ...],
    hand_audit: HandAuditPort,
    policy: PoseAtlasAuditPolicy = DEFAULT_POSE_ATLAS_AUDIT_POLICY,
    *,
    identity_audit: IdentityAuditPort | None = None,
    body_audit: BodyAuditPort | None = None,
) -> PoseAtlasAuditReport:
    problems: list[str] = []
    counts = Counter(view.yaw_degrees for view in views)
    for yaw in CANONICAL_YAWS:
        if counts[yaw] == 0:
            problems.append(f"missing_yaw:{yaw:+04d}")
        elif counts[yaw] > 1:
            problems.append(f"duplicate_yaw:{yaw:+04d}")
    problems.extend(
        f"noncanonical_yaw:{yaw:+04d}"
        for yaw in sorted(set(counts) - set(CANONICAL_YAWS))
    )
    unique = {
        view.yaw_degrees: view
        for view in views
        if counts[view.yaw_degrees] == 1 and view.yaw_degrees in CANONICAL_YAWS
    }
    ordered = tuple(unique[yaw] for yaw in CANONICAL_YAWS if yaw in unique)
    reference = ordered[0] if ordered else None
    for view in ordered:
        _audit_view(view, reference, hand_audit, problems)
    metrics = (
        _adjacent_metrics(ordered)
        if len(ordered) == len(CANONICAL_YAWS)
        and _metric_inputs_are_compatible(ordered)
        else ()
    )
    for metric in metrics:
        edge = f"{metric.first_yaw:+04d}->{metric.second_yaw:+04d}"
        if metric.outline_displacement > policy.max_outline_displacement:
            problems.append(f"outline_jump:{edge}")
        if metric.mean_color_delta > policy.max_color_delta:
            problems.append(f"color_jump:{edge}")
    identity_problems = _identity_gate(ordered, identity_audit, problems)
    body_problems = _body_gate(ordered, body_audit, problems)
    return PoseAtlasAuditReport(
        not problems,
        ordered,
        metrics,
        tuple(problems),
        identity_problems,
        body_problems,
    )


def _body_gate(
    views: tuple[AtlasViewEvidence, ...],
    body_audit: BodyAuditPort | None,
    problems: list[str],
) -> tuple[BodyAuditProblem, ...]:
    if body_audit is None:
        return ()
    if len(views) != len(CANONICAL_YAWS):
        return ()
    report = body_audit.audit(views)
    if report is None:
        summary = BodyAuditProblem("missing_report")
        problems.append("body_audit_failed:missing_report")
        return (summary,)
    summaries = tuple(_body_problem(problem) for problem in report.problems)
    if not report.passed:
        if not summaries:
            summaries = (BodyAuditProblem("unspecified_body_failure"),)
        problems.extend(f"body_audit_failed:{item.code}" for item in summaries)
    return summaries


def _body_problem(problem: str) -> BodyAuditProblem:
    code, separator, detail = str(problem).partition(":")
    safe_code = code.strip() or "unspecified_body_failure"
    candidate = detail.strip() if separator else ""
    yaw = int(candidate) if _safe_canonical_yaw(candidate) else None
    return BodyAuditProblem(safe_code, yaw)


def _safe_canonical_yaw(detail: str) -> bool:
    return bool(
        len(detail) == 4
        and detail[0] in "+-"
        and detail[1:].isdigit()
        and int(detail) in CANONICAL_YAWS
    )


def _identity_gate(
    views: tuple[AtlasViewEvidence, ...],
    identity_audit: IdentityAuditPort | None,
    problems: list[str],
) -> tuple[IdentityAuditProblem, ...]:
    if identity_audit is None:
        return ()
    if len(views) != len(CANONICAL_YAWS):
        return ()
    report = identity_audit.audit(views)
    summaries = tuple(_identity_problem(problem) for problem in report.problems)
    if not report.passed:
        if not summaries:
            summaries = (IdentityAuditProblem("unspecified_identity_failure"),)
        problems.extend(
            f"identity_audit_failed:{summary.code}" for summary in summaries
        )
    return summaries


def _identity_problem(problem: str) -> IdentityAuditProblem:
    code, separator, detail = str(problem).partition(":")
    safe_code = code.strip() or "unspecified_identity_failure"
    candidate = detail.strip() if separator else ""
    safe_detail = candidate if _safe_identity_detail(candidate) else None
    return IdentityAuditProblem(safe_code, safe_detail)


def _safe_identity_detail(detail: str) -> bool:
    if detail in {canonical_view_id(yaw) for yaw in CANONICAL_YAWS}:
        return True
    return bool(
        len(detail) == 4
        and detail[0] in "+-"
        and detail[1:].isdigit()
        and int(detail) in CANONICAL_YAWS
    )


def _audit_view(
    view: AtlasViewEvidence,
    reference: AtlasViewEvidence | None,
    hand_audit: HandAuditPort,
    problems: list[str],
) -> None:
    expected_id = canonical_view_id(view.yaw_degrees)
    if view.view_id != expected_id:
        problems.append(f"noncanonical_name:{view.view_id}:{expected_id}")
    if reference is not None and (view.width, view.height) != (
        reference.width,
        reference.height,
    ):
        problems.append(f"canvas_mismatch:{view.view_id}")
    if reference is not None and (view.anchor_x, view.anchor_y) != (
        reference.anchor_x,
        reference.anchor_y,
    ):
        problems.append(f"anchor_mismatch:{view.view_id}")
    if len(view.rgba) != view.width * view.height * 4:
        problems.append(f"rgba_size_mismatch:{view.view_id}")
    if not _valid_alpha_bounds(view):
        problems.append(f"invalid_alpha_bounds:{view.view_id}")
    if not view.identity_lock_evidence.strip():
        problems.append(f"missing_identity_evidence:{view.view_id}")
    _audit_layers(view, problems)
    if not hand_audit.passed(view.view_id):
        problems.append(f"hand_audit_failed:{view.view_id}")


def _audit_layers(view: AtlasViewEvidence, problems: list[str]) -> None:
    by_role = {layer.role: layer for layer in view.layers}
    if len(by_role) != len(view.layers):
        problems.append(f"duplicate_layer_role:{view.view_id}")
    depths = [layer.depth for layer in view.layers]
    if len(set(depths)) != len(depths):
        problems.append(f"duplicate_layer_depth:{view.view_id}")
    for role, owner in REQUIRED_LAYER_RESPONSIBILITIES.items():
        layer = by_role.get(role)
        if layer is None:
            problems.append(f"missing_layer_responsibility:{view.view_id}:{role}")
        elif layer.owner != owner or not layer.manifest_evidence.strip():
            problems.append(f"invalid_layer_responsibility:{view.view_id}:{role}")
    if view.yaw_degrees in BACK_YAWS and "face" in by_role:
        problems.append(f"back_view_exposes_face:{view.view_id}")
    ordered_roles = tuple(layer.role for layer in sorted(view.layers, key=lambda item: item.depth))
    required_order = tuple(REQUIRED_LAYER_RESPONSIBILITIES)
    positions = [ordered_roles.index(role) for role in required_order if role in ordered_roles]
    if positions != sorted(positions):
        problems.append(f"invalid_layer_depth_order:{view.view_id}")


def _valid_alpha_bounds(view: AtlasViewEvidence) -> bool:
    if len(view.rgba) != view.width * view.height * 4:
        return False
    left, top, width, height = view.alpha_bounds
    if left < 0 or top < 0 or width <= 0 or height <= 0:
        return False
    if left + width > view.width or top + height > view.height:
        return False
    actual = _alpha_bounds(view.rgba, view.width, view.height)
    return actual == view.alpha_bounds


def _alpha_bounds(rgba: bytes, width: int, height: int) -> tuple[int, int, int, int]:
    visible = [
        (index % width, index // width)
        for index in range(width * height)
        if rgba[index * 4 + 3]
    ]
    if not visible:
        return (0, 0, 0, 0)
    xs = [point[0] for point in visible]
    ys = [point[1] for point in visible]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    return left, top, right - left + 1, bottom - top + 1


def _adjacent_metrics(
    views: tuple[AtlasViewEvidence, ...],
) -> tuple[AdjacentViewMetric, ...]:
    metrics = []
    for index, first in enumerate(views):
        second = views[(index + 1) % len(views)]
        first_bounds = first.alpha_bounds
        second_bounds = second.alpha_bounds
        displacement = max(
            abs(first_bounds[position] - second_bounds[position])
            for position in range(4)
        )
        metrics.append(
            AdjacentViewMetric(
                first.yaw_degrees,
                second.yaw_degrees,
                displacement,
                _mean_visible_color_delta(first, second),
            )
        )
    return tuple(metrics)


def _metric_inputs_are_compatible(
    views: tuple[AtlasViewEvidence, ...],
) -> bool:
    width, height = views[0].width, views[0].height
    expected_bytes = width * height * 4
    return all(
        view.width == width
        and view.height == height
        and len(view.rgba) == expected_bytes
        for view in views
    )


def _mean_visible_color_delta(
    first: AtlasViewEvidence,
    second: AtlasViewEvidence,
) -> float:
    total = 0
    count = 0
    for index in range(first.width * first.height):
        first_offset = index * 4
        second_offset = index * 4
        if not (first.rgba[first_offset + 3] or second.rgba[second_offset + 3]):
            continue
        total += sum(
            abs(first.rgba[first_offset + channel] - second.rgba[second_offset + channel])
            for channel in range(3)
        ) / 3
        count += 1
    return total / count if count else 0.0
