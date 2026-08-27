"""Fail-closed geometric audit for the profile nose-to-lip transition.

The contract is deliberately computed from landmarks rather than recorded as
metadata.  It aligns a candidate with a proper (non-reflecting) similarity
transform, then adds the required 2% curvature penalty for MediaPipe points
4 (nose tip), 94 (subnasale), and 0 (upper-lip centre).
"""

from __future__ import annotations

lazy from dataclasses import asdict, dataclass

lazy import numpy as np


LANDMARK_INDICES = (4, 94, 0)
CURVATURE_PENALTY_COEFFICIENT = 0.02
MAX_NORMALIZED_RMS = 0.015
MAX_CURVATURE_DELTA_RADIANS = 0.08
MAX_CONTRACT_SCORE = 0.0166
MIN_SEGMENT_RATIO = 1.0e-4


@dataclass(frozen=True, slots=True)
class NoseLipContractReport:
    passed: bool
    metrics: dict[str, float]
    issues: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


POINT_ARRAY_NDIM = 2
POINT_MIN_COMPONENTS = 2


def _points(value: np.ndarray, label: str) -> np.ndarray:
    points = np.asarray(value, dtype=np.float64)
    if points.ndim != POINT_ARRAY_NDIM or points.shape[1] < POINT_MIN_COMPONENTS:
        raise ValueError(f"{label} must have shape (N, >=2)")
    if points.shape[0] <= max(LANDMARK_INDICES):
        raise ValueError(f"{label} must contain landmark index 94")
    points = points[:, :2]
    if not np.isfinite(points).all():
        raise ValueError(f"{label} contains NaN or Inf")
    return points


def _proper_similarity(source: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, float]:
    source_center = source.mean(axis=0)
    target_center = target.mean(axis=0)
    x = source - source_center
    y = target - target_center
    variance = float(np.sum(x * x))
    if variance <= np.finfo(np.float64).eps:
        raise ValueError("degenerate candidate geometry")
    u, singular, vt = np.linalg.svd(x.T @ y)
    if singular[0] <= np.finfo(np.float64).eps:
        raise ValueError("degenerate nose-lip covariance")
    rotation = u @ vt
    if np.linalg.det(rotation) <= 0.0:
        raise ValueError("reflection is forbidden by the identity contract")
    scale = float(singular.sum() / variance)
    if not np.isfinite(scale) or scale <= 0.0:
        raise ValueError("invalid similarity scale")
    aligned = (source - source_center) @ rotation * scale + target_center
    return aligned, scale


def _curvature(points: np.ndarray) -> float:
    nose, subnasale, upper_lip = points[list(LANDMARK_INDICES)]
    first = subnasale - nose
    second = upper_lip - subnasale
    first_length = float(np.linalg.norm(first))
    second_length = float(np.linalg.norm(second))
    extent = max(float(np.ptp(points[:, 0])), float(np.ptp(points[:, 1])), 1.0)
    if min(first_length, second_length) / extent < MIN_SEGMENT_RATIO:
        raise ValueError("nose-lip segment is degenerate")
    cosine = float(np.dot(first, second) / (first_length * second_length))
    return float(np.arccos(np.clip(cosine, -1.0, 1.0)))


def audit_nose_lip_contract(
    authority: np.ndarray,
    candidate: np.ndarray,
    *,
    max_normalized_rms: float = MAX_NORMALIZED_RMS,
    max_curvature_delta_radians: float = MAX_CURVATURE_DELTA_RADIANS,
    max_contract_score: float = MAX_CONTRACT_SCORE,
) -> NoseLipContractReport:
    """Audit candidate landmarks, returning a report for valid inputs.

    Invalid dimensions, non-finite data, reflections, and degenerate geometry
    raise ``ValueError``.  Callers must treat that exception as a rejected
    frame; there is intentionally no permissive fallback.
    """

    reference = _points(authority, "authority")
    observed = _points(candidate, "candidate")
    if reference.shape != observed.shape:
        raise ValueError("authority and candidate shapes differ")
    selected_reference = reference[list(LANDMARK_INDICES)]
    selected_observed = observed[list(LANDMARK_INDICES)]
    aligned_selected, _ = _proper_similarity(selected_observed, selected_reference)
    extent = max(float(np.ptp(selected_reference[:, 0])), float(np.ptp(selected_reference[:, 1])), 1.0)
    normalized_rms = float(np.sqrt(np.mean((aligned_selected - selected_reference) ** 2)) / extent)
    authority_curvature = _curvature(reference)
    candidate_curvature = _curvature(observed)
    curvature_delta = abs(candidate_curvature - authority_curvature)
    contract_score = normalized_rms + CURVATURE_PENALTY_COEFFICIENT * curvature_delta
    issues: list[str] = []
    if normalized_rms > max_normalized_rms:
        issues.append("nose_lip_alignment_rms")
    if curvature_delta > max_curvature_delta_radians:
        issues.append("nose_lip_curvature_discontinuity")
    if contract_score > max_contract_score:
        issues.append("nose_lip_penalized_score")
    return NoseLipContractReport(
        passed=not issues,
        metrics={
            "alignment_rms_normalized": normalized_rms,
            "authority_curvature_radians": authority_curvature,
            "candidate_curvature_radians": candidate_curvature,
            "curvature_delta_radians": curvature_delta,
            "curvature_penalty_coefficient": CURVATURE_PENALTY_COEFFICIENT,
            "contract_score": contract_score,
        },
        issues=tuple(issues),
    )
