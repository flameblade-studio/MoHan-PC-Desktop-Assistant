"""Product-neutral release-gate orchestration around an injected audit backend."""

from __future__ import annotations

lazy import json
lazy import re
lazy from collections.abc import Callable
lazy from pathlib import Path

VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-rc\.[1-9]\d*)?$")
ReleaseAudit = Callable[[Path, dict[str, object]], tuple[int, str]]


def requires_release_gate(
    version: str,
    *,
    minimum: tuple[int, int, int],
    explicit_flag: bool = False,
) -> bool:
    """Return whether the configured release series requires its audit backend."""
    match = VERSION_PATTERN.fullmatch(version)
    if match is None:
        raise ValueError("invalid_release_version")
    return explicit_flag or tuple(int(value) for value in match.groups()) >= minimum


def run_release_preflight(
    version: str,
    asset_root: Path,
    audit_evidence_path: Path,
    *,
    minimum: tuple[int, int, int],
    release_audit: ReleaseAudit,
    explicit_flag: bool = False,
) -> tuple[int, str]:
    """Load data-only evidence and delegate product semantics to an adapter."""
    if not requires_release_gate(version, minimum=minimum, explicit_flag=explicit_flag):
        return 0, _json({"schema_version": 1, "status": "not-required", "version": version})
    try:
        bundle = _read_bundle(audit_evidence_path)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        return 1, _blocked("audit_evidence_invalid")
    return release_audit(asset_root, bundle)


def _read_bundle(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("unsupported_audit_evidence")
    return payload


def _blocked(*codes: str) -> str:
    return _json(
        {
            "schema_version": 1,
            "status": "blocked",
            "issues": [{"code": code} for code in dict.fromkeys(codes)],
        }
    )


def _json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
