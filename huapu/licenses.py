"""Caller-owned allowlist checks for character-component license claims."""

from __future__ import annotations

lazy from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LicenseClaim:
    """One component's declared status and optional license expression."""

    component: str
    status: str
    license_expression: str | None


@dataclass(frozen=True, slots=True)
class LicensePolicy:
    """An injected policy; Huapu does not select distribution permissions."""

    allowed_statuses: frozenset[str]
    allowed_expressions: frozenset[str]
    statuses_requiring_expression: frozenset[str] = frozenset({"licensed"})


@dataclass(frozen=True, slots=True)
class LicenseCheckResult:
    """Deterministic license-policy findings."""

    allowed: bool
    issues: tuple[str, ...]


def check_license_allowlist(
    claims: tuple[LicenseClaim, ...],
    policy: LicensePolicy,
) -> LicenseCheckResult:
    """Check claims without treating pending owner decisions as permissions."""
    issues: list[str] = []
    seen: set[str] = set()
    for claim in sorted(claims, key=lambda item: item.component):
        if not claim.component or claim.component in seen:
            issues.append(f"duplicate_or_empty_component:{claim.component}")
            continue
        seen.add(claim.component)
        if claim.status not in policy.allowed_statuses:
            issues.append(f"status_not_allowed:{claim.component}:{claim.status}")
        expression = claim.license_expression
        if claim.status in policy.statuses_requiring_expression and not expression:
            issues.append(f"license_expression_required:{claim.component}")
        if expression is not None and expression not in policy.allowed_expressions:
            issues.append(f"license_expression_not_allowed:{claim.component}:{expression}")
    return LicenseCheckResult(not issues, tuple(issues))
