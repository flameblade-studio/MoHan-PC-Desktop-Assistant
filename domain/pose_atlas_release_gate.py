from __future__ import annotations

lazy import hashlib
lazy import json
lazy from collections import Counter
lazy from dataclasses import dataclass
lazy from typing import Literal, Protocol

lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id
lazy from domain.full_body_asset_evidence import FullBodyAssetEvidenceResult
lazy from domain.pose_runtime_loader import PoseAtlasManifest

ReleaseStatus = Literal["releasable", "blocked"]


class AuditReportPort(Protocol):
    passed: bool
    problems: tuple[str, ...]


class HandAuditReportPort(Protocol):
    passed: bool


@dataclass(frozen=True, slots=True)
class PoseAtlasAuditInputs:
    full_body: AuditReportPort | None
    identity: AuditReportPort | None
    pose_atlas: AuditReportPort | None


@dataclass(frozen=True, slots=True)
class PoseLoadReleaseEvidence:
    passed: bool
    manifest_sha256: str
    source_revision_sha256: str
    problems: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PoseReleaseViewInput:
    view_id: str
    yaw_degrees: int
    rgba_sha256: str
    sidecar_sha256: str
    hands_sha256: str
    asset_evidence: FullBodyAssetEvidenceResult | None
    hand_audit: HandAuditReportPort | None


@dataclass(frozen=True, slots=True)
class PoseReleaseViewRecord:
    view_id: str
    yaw_degrees: int
    rgba_sha256: str
    sidecar_sha256: str
    hands_sha256: str


@dataclass(frozen=True, slots=True)
class PoseReleaseIssue:
    code: str
    view_id: str | None = None


@dataclass(frozen=True, slots=True)
class PoseAtlasReleaseResult:
    status: ReleaseStatus
    manifest_sha256: str | None
    views: tuple[PoseReleaseViewRecord, ...]
    issues: tuple[PoseReleaseIssue, ...]

    @property
    def releasable(self) -> bool:
        return self.status == "releasable"

    def to_json(self) -> str:
        payload = {
            "schema_version": 1,
            "status": self.status,
            "manifest_sha256": self.manifest_sha256,
            "views": [
                {
                    "view_id": view.view_id,
                    "yaw_degrees": view.yaw_degrees,
                    "rgba_sha256": view.rgba_sha256,
                    "sidecar_sha256": view.sidecar_sha256,
                    "hands_sha256": view.hands_sha256,
                }
                for view in self.views
            ],
            "issues": [
                {"code": issue.code, "view_id": issue.view_id}
                for issue in self.issues
            ],
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def audit_pose_atlas_release(
    manifest: PoseAtlasManifest | None,
    load_evidence: PoseLoadReleaseEvidence | None,
    views: tuple[PoseReleaseViewInput, ...],
    audits: PoseAtlasAuditInputs,
) -> PoseAtlasReleaseResult:
    """Combine every v4 atlas proof into one privacy-safe release decision."""

    issues: list[PoseReleaseIssue] = []
    manifest_hash = _manifest_hash(manifest) if manifest is not None else None
    if manifest is None:
        issues.append(PoseReleaseIssue("manifest_missing"))
    else:
        _validate_manifest(manifest, issues)
    _validate_load_evidence(load_evidence, manifest_hash, issues)
    records = _validate_physical_views(manifest, views, issues)
    _require_audit("full_body", audits.full_body, issues)
    _require_audit("identity", audits.identity, issues)
    _require_audit("pose_atlas", audits.pose_atlas, issues)
    unique_issues = tuple(dict.fromkeys(issues))
    complete = len(records) == len(CANONICAL_YAWS)
    releasable = not unique_issues and complete
    return PoseAtlasReleaseResult(
        "releasable" if releasable else "blocked",
        manifest_hash,
        records if releasable else (),
        unique_issues,
    )


def _validate_manifest(
    manifest: PoseAtlasManifest,
    issues: list[PoseReleaseIssue],
) -> None:
    if manifest.contract != "full-body-v4":
        issues.append(PoseReleaseIssue("manifest_not_full_body_v4"))
    counts = Counter(view.yaw_degrees for view in manifest.views)
    if set(counts) != set(CANONICAL_YAWS) or any(count != 1 for count in counts.values()):
        issues.append(PoseReleaseIssue("manifest_incomplete_canonical_ring"))
    for view in manifest.views:
        expected = canonical_view_id(view.yaw_degrees) if view.yaw_degrees in CANONICAL_YAWS else None
        if expected is None or view.view_id != expected:
            issues.append(PoseReleaseIssue("manifest_noncanonical_view"))
        if not _safe_hash(view.sha256):
            issues.append(PoseReleaseIssue("manifest_invalid_view_hash", expected))
        if not view.identity_evidence.strip() or not view.source_evidence.strip():
            issues.append(PoseReleaseIssue("manifest_missing_view_evidence", expected))


def _validate_load_evidence(
    evidence: PoseLoadReleaseEvidence | None,
    manifest_hash: str | None,
    issues: list[PoseReleaseIssue],
) -> None:
    if evidence is None:
        issues.append(PoseReleaseIssue("load_evidence_missing"))
        return
    if not evidence.passed:
        issues.append(PoseReleaseIssue("load_evidence_failed"))
        issues.extend(_safe_report_issues("load", evidence.problems))
    if not _safe_hash(evidence.manifest_sha256) or evidence.manifest_sha256 != manifest_hash:
        issues.append(PoseReleaseIssue("load_manifest_hash_mismatch"))
    if not _safe_hash(evidence.source_revision_sha256):
        issues.append(PoseReleaseIssue("load_source_revision_missing"))


def _validate_physical_views(
    manifest: PoseAtlasManifest | None,
    inputs: tuple[PoseReleaseViewInput, ...],
    issues: list[PoseReleaseIssue],
) -> tuple[PoseReleaseViewRecord, ...]:
    counts = Counter(item.yaw_degrees for item in inputs)
    manifest_by_yaw = (
        {view.yaw_degrees: view for view in manifest.views}
        if manifest is not None
        else {}
    )
    records: list[PoseReleaseViewRecord] = []
    for yaw in CANONICAL_YAWS:
        view_id = canonical_view_id(yaw)
        if counts[yaw] != 1:
            code = "physical_view_missing" if counts[yaw] == 0 else "physical_view_duplicate"
            issues.append(PoseReleaseIssue(code, view_id))
            continue
        manifest_view = manifest_by_yaw.get(yaw)
        item = next(candidate for candidate in inputs if candidate.yaw_degrees == yaw)
        valid = _validate_physical_view(item, manifest_view, view_id, yaw, issues)
        if valid:
            records.append(
                PoseReleaseViewRecord(
                    view_id,
                    yaw,
                    item.rgba_sha256,
                    item.sidecar_sha256,
                    item.hands_sha256,
                )
            )
    if set(counts) - set(CANONICAL_YAWS):
        issues.append(PoseReleaseIssue("physical_noncanonical_view"))
    return tuple(records)


def _validate_physical_view(item, manifest_view, view_id, yaw, issues) -> bool:
    checks = (
        (item.view_id == view_id, "physical_view_identity_mismatch"),
        (manifest_view is not None and manifest_view.view_id == view_id, "physical_view_manifest_missing"),
        (_safe_hash(item.rgba_sha256) and manifest_view is not None and item.rgba_sha256 == manifest_view.sha256, "physical_rgba_hash_mismatch"),
        (_safe_hash(item.sidecar_sha256), "physical_sidecar_hash_missing"),
        (_safe_hash(item.hands_sha256), "physical_hands_hash_missing"),
    )
    valid = True
    for passed, code in checks:
        if not passed:
            issues.append(PoseReleaseIssue(code, view_id))
            valid = False
    evidence = item.asset_evidence
    if evidence is None or not evidence.passed or evidence.evidence is None or evidence.evidence.yaw_degrees != yaw:
        issues.append(PoseReleaseIssue("physical_asset_evidence_failed", view_id))
        if evidence is not None:
            issues.extend(_safe_report_issues("asset", evidence.problems, view_id))
        valid = False
    if item.hand_audit is None or not item.hand_audit.passed:
        code = "hand_audit_missing" if item.hand_audit is None else "hand_audit_failed"
        issues.append(PoseReleaseIssue(code, view_id))
        valid = False
    return valid


def _require_audit(
    namespace: str,
    report: AuditReportPort | None,
    issues: list[PoseReleaseIssue],
) -> None:
    if report is None:
        issues.append(PoseReleaseIssue(f"{namespace}_audit_missing"))
        return
    if not report.passed:
        issues.append(PoseReleaseIssue(f"{namespace}_audit_failed"))
        issues.extend(_safe_report_issues(namespace, report.problems))


def _safe_report_issues(
    namespace: str,
    problems: tuple[str, ...],
    default_view_id: str | None = None,
) -> tuple[PoseReleaseIssue, ...]:
    result = []
    for problem in problems:
        code, separator, detail = str(problem).partition(":")
        safe_code = _safe_code(code) or "unspecified"
        view_id = _safe_view_id(detail.strip()) if separator else default_view_id
        result.append(PoseReleaseIssue(f"{namespace}_{safe_code}", view_id))
    return tuple(result)


def _safe_code(value: str) -> str:
    return "".join(character for character in value.strip().lower().replace("-", "_") if character.isalnum() or character == "_")


def _safe_view_id(value: str) -> str | None:
    canonical = {canonical_view_id(yaw) for yaw in CANONICAL_YAWS}
    if value in canonical:
        return value
    if len(value) == 4 and value[:1] in "+-" and value[1:].isdigit():
        yaw = int(value)
        return canonical_view_id(yaw) if yaw in CANONICAL_YAWS else None
    return None


def _safe_hash(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _manifest_hash(manifest: PoseAtlasManifest) -> str:
    payload = {
        "pack_id": manifest.pack_id,
        "source_evidence": manifest.source_evidence,
        "contract": manifest.contract,
        "schema_version": manifest.schema_version,
        "body_profile_id": manifest.body_profile_id,
        "body_profile_version_range": manifest.body_profile_version_range,
        "rig_id": manifest.rig_id,
        "rig_version_range": manifest.rig_version_range,
        "views": [
            {
                "view_id": view.view_id,
                "yaw_degrees": view.yaw_degrees,
                "path": view.path,
                "sha256": view.sha256,
                "width": view.width,
                "height": view.height,
                "identity_evidence": view.identity_evidence,
                "source_evidence": view.source_evidence,
                "body_profile_id": view.body_profile_id,
                "rig_id": view.rig_id,
                "rig_version_range": view.rig_version_range,
                "correction_layers": sorted(view.correction_layers),
            }
            for view in sorted(manifest.views, key=lambda item: item.yaw_degrees)
        ],
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def manifest_sha256(manifest: PoseAtlasManifest) -> str:
    """Return the deterministic digest expected in load evidence."""

    return _manifest_hash(manifest)
