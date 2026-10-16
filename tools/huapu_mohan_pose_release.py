"""MoHan runtime adapter for the product-neutral Huapu pose release gate."""

from __future__ import annotations

lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from domain.full_body_asset_audit import audit_full_body_assets
lazy from domain.pose_atlas_manifest_builder import (
    PoseAtlasBuildConfig,
    build_pose_atlas_manifest,
)
lazy from domain.pose_atlas_release_gate import (
    PoseAtlasAuditInputs,
    PoseLoadReleaseEvidence,
    audit_pose_atlas_release,
    manifest_sha256,
)
lazy from huapu.pose_release import _blocked

VERSION_RANGE_LENGTH = 2


@dataclass(frozen=True, slots=True)
class SummaryReport:
    passed: bool
    problems: tuple[str, ...] = ()


def run_mohan_release_audit(
    asset_root: Path,
    bundle: dict[str, object],
) -> tuple[int, str]:
    """Compose existing runtime auditors without exposing them to Huapu core."""
    try:
        config = _build_config(bundle)
    except (KeyError, TypeError, ValueError):
        return 1, _blocked("audit_evidence_invalid")
    build = build_pose_atlas_manifest(asset_root, config)
    if not build.passed or build.manifest is None:
        codes = tuple(issue.code for issue in build.issues) or ("manifest_build_failed",)
        return 1, _blocked(*codes)
    evidence_by_view = dict(build.asset_evidence)
    body_report = audit_full_body_assets(
        tuple(
            evidence_by_view[record.view_id].evidence
            for record in build.records
            if evidence_by_view[record.view_id].evidence is not None
        )
    )
    try:
        identity = _summary(bundle, "identity")
        pose_atlas = _summary(bundle, "pose_atlas")
        load = _load_evidence(bundle, build.manifest)
    except (KeyError, TypeError, ValueError):
        return 1, _blocked("audit_evidence_incomplete")
    result = audit_pose_atlas_release(
        build.manifest,
        load,
        build.release_views(),
        PoseAtlasAuditInputs(body_report, identity, pose_atlas),
    )
    return (0 if result.releasable else 1), result.to_json()


def _build_config(bundle: dict[str, object]) -> PoseAtlasBuildConfig:
    manifest = _object(bundle, "manifest")
    return PoseAtlasBuildConfig(
        _text(manifest, "pack_id"),
        _text(manifest, "source_evidence"),
        _text(manifest, "identity_evidence"),
        _text(manifest, "body_profile_id"),
        _version_range(manifest, "body_profile_version_range"),
        _text(manifest, "rig_id"),
        _version_range(manifest, "rig_version_range"),
    )


def _summary(bundle: dict[str, object], name: str) -> SummaryReport:
    payload = _object(bundle, name)
    passed = payload.get("passed")
    problems = payload.get("problems", [])
    if not isinstance(passed, bool) or not _string_list(problems):
        raise TypeError("invalid_audit_summary")
    return SummaryReport(passed, tuple(problems))


def _load_evidence(
    bundle: dict[str, object],
    manifest,
) -> PoseLoadReleaseEvidence:
    payload = _object(bundle, "load")
    passed = payload.get("passed")
    revision = payload.get("source_revision_sha256")
    problems = payload.get("problems", [])
    if not isinstance(passed, bool) or not isinstance(revision, str) or not _string_list(problems):
        raise TypeError("invalid_load_evidence")
    return PoseLoadReleaseEvidence(
        passed,
        manifest_sha256(manifest),
        revision,
        tuple(problems),
    )


def _object(parent: dict[str, object], name: str) -> dict[str, object]:
    value = parent.get(name)
    if not isinstance(value, dict):
        raise TypeError(f"invalid_{name}")
    return value


def _text(parent: dict[str, object], name: str) -> str:
    value = parent.get(name)
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"invalid_{name}")
    return value


def _version_range(parent: dict[str, object], name: str) -> tuple[int, int]:
    value = parent.get(name)
    if (
        not isinstance(value, list)
        or len(value) != VERSION_RANGE_LENGTH
        or any(not isinstance(item, int) or isinstance(item, bool) for item in value)
        or value[0] >= value[1]
    ):
        raise TypeError(f"invalid_{name}")
    return value[0], value[1]


def _string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)
