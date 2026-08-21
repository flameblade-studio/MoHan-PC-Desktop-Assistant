from __future__ import annotations

lazy import hashlib
lazy import json
lazy import sys
lazy from dataclasses import dataclass, replace
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from character_pose import CANONICAL_YAWS, canonical_view_id
lazy from full_body_asset_audit import FullBodyViewEvidence
lazy from full_body_asset_evidence import FullBodyAssetEvidenceResult
lazy from pose_atlas_release_gate import (
    PoseAtlasAuditInputs,
    PoseLoadReleaseEvidence,
    PoseReleaseViewInput,
    audit_pose_atlas_release,
    manifest_sha256,
)
lazy from pose_runtime_loader import PoseAtlasManifest, PoseViewSpec

VIEW_COUNT = 24


@dataclass(frozen=True)
class Report:
    passed: bool
    problems: tuple[str, ...] = ()
    embedding: tuple[float, ...] = (0.1, 0.2)


@dataclass(frozen=True)
class HandReport:
    passed: bool
    landmarks: tuple[float, ...] = (1.2, 3.4)


@dataclass(frozen=True)
class GateOptions:
    load: PoseLoadReleaseEvidence | None = None
    body: Report | None = None
    identity: Report | None = None
    pose: Report | None = None


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def manifest() -> PoseAtlasManifest:
    views = tuple(
        PoseViewSpec(
            canonical_view_id(yaw), yaw, f"assets/{canonical_view_id(yaw)}.png",
            digest(f"rgba:{yaw}"), 1000, 1000, "identity-proof", "source-proof",
            "mohan-body-v1", "mohan-full-body-v1", (1, 2),
            frozenset({
                "left-leg-correction", "right-leg-correction",
                "left-foot-correction", "right-foot-correction",
                "left-sole-correction", "right-sole-correction",
            }),
        )
        for yaw in CANONICAL_YAWS
    )
    return PoseAtlasManifest(
        "atlas-v4", "source-proof", views, "full-body-v4", 2,
        "mohan-body-v1", (1, 2), "mohan-full-body-v1", (1, 2),
    )


def body_evidence(yaw: int) -> FullBodyAssetEvidenceResult:
    evidence = FullBodyViewEvidence(
        yaw, 1000, 1000, 100, 50, 900, 949, 500.0, 540.0,
        949, 949, True, True, True, True, True, True, True, True,
    )
    return FullBodyAssetEvidenceResult(True, evidence, ())


def release_views() -> tuple[PoseReleaseViewInput, ...]:
    return tuple(
        PoseReleaseViewInput(
            canonical_view_id(yaw), yaw, digest(f"rgba:{yaw}"),
            digest(f"sidecar:{yaw}"), digest(f"hands:{yaw}"),
            body_evidence(yaw), HandReport(True),
        )
        for yaw in CANONICAL_YAWS
    )


def load_evidence(value: PoseAtlasManifest) -> PoseLoadReleaseEvidence:
    return PoseLoadReleaseEvidence(True, manifest_sha256(value), digest("revision"))


def gate(value=None, views=None, options: GateOptions | None = None):
    selected = value or manifest()
    chosen = options or GateOptions(None, Report(True), Report(True), Report(True))
    return audit_pose_atlas_release(
        selected,
        chosen.load if chosen.load is not None else load_evidence(selected),
        views if views is not None else release_views(),
        PoseAtlasAuditInputs(chosen.body, chosen.identity, chosen.pose),
    )


def assert_complete_evidence_is_releasable_and_deterministic() -> None:
    first = gate()
    second = gate()
    assert first.releasable
    assert len(first.views) == VIEW_COUNT
    assert first.issues == ()
    assert first.to_json() == second.to_json()
    payload = json.loads(first.to_json())
    assert payload["status"] == "releasable"
    assert tuple(view["yaw_degrees"] for view in payload["views"]) == CANONICAL_YAWS


def assert_every_layer_is_mandatory() -> None:
    cases = (
        (GateOptions(None, None, Report(True), Report(True)), "full_body_audit_missing"),
        (GateOptions(None, Report(True), None, Report(True)), "identity_audit_missing"),
        (GateOptions(None, Report(True), Report(True), None), "pose_atlas_audit_missing"),
        (GateOptions(PoseLoadReleaseEvidence(False, "", ""), Report(True), Report(True), Report(True)), "load_evidence_failed"),
    )
    for options, expected in cases:
        result = gate(options=options)
        assert not result.releasable
        assert expected in {issue.code for issue in result.issues}
        assert result.views == ()


def assert_each_view_requires_physical_asset_and_hand_evidence() -> None:
    views = list(release_views())
    target = canonical_view_id(0)
    index = CANONICAL_YAWS.index(0)
    views[index] = replace(views[index], asset_evidence=None)
    result = gate(views=tuple(views))
    assert not result.releasable
    assert any(
        issue.code == "physical_asset_evidence_failed" and issue.view_id == target
        for issue in result.issues
    )
    views = list(release_views())
    views[index] = replace(views[index], hand_audit=None)
    result = gate(views=tuple(views))
    assert any(
        issue.code == "hand_audit_missing" and issue.view_id == target
        for issue in result.issues
    )


def assert_hash_and_manifest_mismatch_fail_closed() -> None:
    value = manifest()
    views = list(release_views())
    views[2] = replace(views[2], rgba_sha256=digest("wrong"))
    result = gate(value, tuple(views))
    assert "physical_rgba_hash_mismatch" in {issue.code for issue in result.issues}
    wrong_load = replace(load_evidence(value), manifest_sha256=digest("wrong-manifest"))
    result = gate(value, options=GateOptions(wrong_load, Report(True), Report(True), Report(True)))
    assert "load_manifest_hash_mismatch" in {issue.code for issue in result.issues}


def assert_reports_are_sanitized_and_json_has_no_paths_or_biometrics() -> None:
    result = gate(options=GateOptions(None, Report(True), Report(False, ("face_embedding_drift:C:/private/face.bin",)), Report(False, ("outline_jump:yaw+000-pitch+00",))))
    output = result.to_json()
    assert not result.releasable
    assert "identity_face_embedding_drift" in output
    for forbidden in ("C:/", "private", "embedding\":", "landmarks", "0.1", "1.2"):
        assert forbidden not in output


def assert_noncanonical_or_incomplete_input_never_publishes_records() -> None:
    result = gate(views=release_views()[:-1])
    assert not result.releasable
    assert result.views == ()
    assert any(issue.code == "physical_view_missing" for issue in result.issues)


def assert_missing_manifest_is_blocked_without_view_records() -> None:
    result = audit_pose_atlas_release(
        None,
        None,
        release_views(),
        PoseAtlasAuditInputs(Report(True), Report(True), Report(True)),
    )
    assert not result.releasable
    assert result.manifest_sha256 is None
    assert result.views == ()
    codes = {issue.code for issue in result.issues}
    assert "manifest_missing" in codes
    assert "load_evidence_missing" in codes


def run() -> None:
    assert_complete_evidence_is_releasable_and_deterministic()
    assert_every_layer_is_mandatory()
    assert_each_view_requires_physical_asset_and_hand_evidence()
    assert_hash_and_manifest_mismatch_fail_closed()
    assert_reports_are_sanitized_and_json_has_no_paths_or_biometrics()
    assert_noncanonical_or_incomplete_input_never_publishes_records()
    assert_missing_manifest_is_blocked_without_view_records()
    print("POSE_ATLAS_RELEASE_GATE_OK")


if __name__ == "__main__":
    run()
