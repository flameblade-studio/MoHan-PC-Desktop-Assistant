from __future__ import annotations

lazy import sys
lazy from dataclasses import dataclass, replace
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from character_pose import CANONICAL_YAWS, canonical_view_id
lazy from pose_atlas_audit import (
    AtlasLayerEvidence,
    AtlasViewEvidence,
    BodyAuditPort,
    HandAuditPort,
    IdentityAuditPort,
    PoseAtlasAuditPolicy,
    audit_pose_atlas,
)
lazy from tools.build_pose_contact_sheet import build_contact_sheet

WIDTH = 6
HEIGHT = 6
REAR_YAW = -180
VIEW_COUNT = 24
YAW_DEGREES = 45
EXPECTED_ROLES = (
    ("hair-back", 10, "hair"),
    ("body", 20, "core-body"),
    ("garment", 30, "garment"),
    ("arm-left", 40, "left-arm"),
    ("arm-right", 50, "right-arm"),
    ("hand-left", 60, "left-hand"),
    ("hand-right", 70, "right-hand"),
    ("weapon", 80, "weapon"),
    ("headwear", 90, "headwear"),
    ("hair-front", 100, "hair"),
)


class Hands(HandAuditPort):
    def __init__(self, failed: frozenset[str] = frozenset()) -> None:
        self.failed = failed

    def passed(self, view_id: str) -> bool:
        return view_id not in self.failed


@dataclass(frozen=True, slots=True)
class IdentityReport:
    passed: bool
    problems: tuple[str, ...] = ()
    embedding: tuple[float, ...] = (0.1, 0.2)


class Identity(IdentityAuditPort):
    def __init__(self, report: IdentityReport | None = None) -> None:
        self.report = report or IdentityReport(True)
        self.calls: list[tuple[str, ...]] = []

    def audit(self, views: tuple[AtlasViewEvidence, ...]) -> IdentityReport:
        self.calls.append(tuple(item.view_id for item in views))
        return self.report


class BodyReport:
    def __init__(self, passed: bool, problems: tuple[str, ...] = ()) -> None:
        self.passed = passed
        self.problems = problems
        self.raw_image = b"must-not-leak"


class Body(BodyAuditPort):
    def __init__(self, report: BodyReport | None) -> None:
        self.report = report
        self.calls = 0

    def audit(self, _views: tuple[AtlasViewEvidence, ...]) -> BodyReport | None:
        self.calls += 1
        return self.report


def rgba(yaw: int, *, jump: bool = False) -> bytes:
    shade = 230 if jump else 80 + ((yaw + 180) // 15) % 3
    data = bytearray(WIDTH * HEIGHT * 4)
    for y in range(1, 5):
        for x in range(1, 5):
            index = (y * WIDTH + x) * 4
            data[index : index + 4] = bytes((shade, 90, 110, 255))
    return bytes(data)


def layers(yaw: int) -> tuple[AtlasLayerEvidence, ...]:
    result = tuple(
        AtlasLayerEvidence(role, depth, owner, f"proof:{yaw}:{role}")
        for role, depth, owner in EXPECTED_ROLES
    )
    if yaw == REAR_YAW:
        return result
    return (*result, AtlasLayerEvidence("face", 85, "core-identity", f"face:{yaw}"))


def view(yaw: int, *, jump: bool = False) -> AtlasViewEvidence:
    return AtlasViewEvidence(
        view_id=canonical_view_id(yaw),
        yaw_degrees=yaw,
        width=WIDTH,
        height=HEIGHT,
        anchor_x=0,
        anchor_y=0,
        alpha_bounds=(1, 1, 4, 4),
        identity_lock_evidence="identity-lock-v1",
        rgba=rgba(yaw, jump=jump),
        layers=layers(yaw),
    )


def complete_ring() -> tuple[AtlasViewEvidence, ...]:
    return tuple(view(yaw) for yaw in CANONICAL_YAWS)


def assert_complete_ring_passes_with_adjacent_metrics() -> None:
    identity = Identity()
    report = audit_pose_atlas(complete_ring(), Hands(), identity_audit=identity)
    assert report.passed
    assert len(report.views) == VIEW_COUNT
    assert len(report.adjacent_metrics) == VIEW_COUNT
    assert report.problems == ()
    assert report.identity_problems == ()
    assert report.adjacent_metrics[-1].second_yaw == REAR_YAW
    assert len(identity.calls[0]) == VIEW_COUNT


def assert_identity_failures_are_hard_gates_without_embedding_leakage() -> None:
    cases = (
        ("face_embedding_drift:yaw+000-pitch+00", "face_embedding_drift"),
        ("face_geometry_drift:yaw-045-pitch+00", "face_geometry_drift"),
        ("rear_exposes_face:yaw-180-pitch+00", "rear_exposes_face"),
        ("subject_scale_drift:+060", "subject_scale_drift"),
    )
    for raw_problem, expected_code in cases:
        identity = Identity(IdentityReport(False, (raw_problem,)))
        report = audit_pose_atlas(
            complete_ring(),
            Hands(),
            identity_audit=identity,
        )
        assert not report.passed
        assert report.identity_problems[0].code == expected_code
        assert report.identity_problems[0].view_id
        assert f"identity_audit_failed:{expected_code}" in report.problems
        serialized = repr(report)
        assert "0.1" not in serialized
        assert "0.2" not in serialized
    private_detail = Identity(
        IdentityReport(False, ("face_embedding_drift:0.1,0.2,0.3",))
    )
    report = audit_pose_atlas(
        complete_ring(), Hands(), identity_audit=private_detail
    )
    assert report.identity_problems[0].code == "face_embedding_drift"
    assert report.identity_problems[0].view_id is None
    assert "0.1" not in repr(report)


def assert_legacy_call_shape_remains_compatible() -> None:
    report = audit_pose_atlas(complete_ring(), Hands())
    assert report.passed
    assert report.identity_problems == ()
    assert report.body_problems == ()


def assert_body_audit_is_an_opt_in_hard_gate() -> None:
    body = Body(BodyReport(True))
    report = audit_pose_atlas(complete_ring(), Hands(), body_audit=body)
    assert report.passed
    assert body.calls == 1
    assert report.body_problems == ()

    failed = Body(BodyReport(False, ("height_median_drift:+045",)))
    report = audit_pose_atlas(complete_ring(), Hands(), body_audit=failed)
    assert not report.passed
    assert report.body_problems[0].code == "height_median_drift"
    assert report.body_problems[0].yaw_degrees == YAW_DEGREES
    assert "body_audit_failed:height_median_drift" in report.problems
    assert "must-not-leak" not in repr(report)

    unsafe = Body(BodyReport(False, ("height_median_drift:private-data",)))
    report = audit_pose_atlas(complete_ring(), Hands(), body_audit=unsafe)
    assert report.body_problems[0].yaw_degrees is None
    assert "private-data" not in repr(report)

    missing = Body(None)
    report = audit_pose_atlas(complete_ring(), Hands(), body_audit=missing)
    assert not report.passed
    assert "body_audit_failed:missing_report" in report.problems


def assert_missing_and_duplicate_angles_fail() -> None:
    ring = complete_ring()
    missing = audit_pose_atlas(ring[:-1], Hands())
    assert "missing_yaw:+165" in missing.problems
    duplicate = audit_pose_atlas((*ring, ring[0]), Hands())
    assert "duplicate_yaw:-180" in duplicate.problems


def assert_back_face_layer_fails() -> None:
    ring = list(complete_ring())
    back = ring[0]
    ring[0] = replace(
        back,
        layers=(*back.layers, AtlasLayerEvidence("face", 85, "core-identity", "bad")),
    )
    report = audit_pose_atlas(tuple(ring), Hands())
    assert "back_view_exposes_face:yaw-180-pitch+00" in report.problems


def assert_visual_jump_and_identity_proof_fail() -> None:
    ring = list(complete_ring())
    index = CANONICAL_YAWS.index(0)
    ring[index] = view(0, jump=True)
    report = audit_pose_atlas(tuple(ring), Hands())
    assert any(problem.startswith("color_jump:") for problem in report.problems)
    ring[index] = replace(view(0), identity_lock_evidence="")
    report = audit_pose_atlas(tuple(ring), Hands())
    assert "missing_identity_evidence:yaw+000-pitch+00" in report.problems


def assert_failed_hand_report_and_layer_contract_fail() -> None:
    target = canonical_view_id(45)
    report = audit_pose_atlas(complete_ring(), Hands(frozenset({target})))
    assert f"hand_audit_failed:{target}" in report.problems
    ring = list(complete_ring())
    index = CANONICAL_YAWS.index(45)
    ring[index] = replace(
        ring[index],
        layers=tuple(layer for layer in ring[index].layers if layer.role != "weapon"),
    )
    report = audit_pose_atlas(tuple(ring), Hands())
    assert f"missing_layer_responsibility:{target}:weapon" in report.problems


def assert_naming_dimensions_anchor_alpha_and_thresholds_fail_closed() -> None:
    policy = PoseAtlasAuditPolicy(max_outline_displacement=0, max_color_delta=1.0)
    ring = list(complete_ring())
    ring[2] = replace(ring[2], view_id="left-wrong")
    ring[3] = replace(ring[3], width=WIDTH + 1)
    ring[4] = replace(ring[4], anchor_x=2)
    ring[5] = replace(ring[5], alpha_bounds=(0, 0, 9, 9))
    report = audit_pose_atlas(tuple(ring), Hands(), policy)
    assert any(problem.startswith("noncanonical_name:") for problem in report.problems)
    assert any(problem.startswith("canvas_mismatch:") for problem in report.problems)
    assert any(problem.startswith("anchor_mismatch:") for problem in report.problems)
    assert any(problem.startswith("invalid_alpha_bounds:") for problem in report.problems)


def assert_contact_sheet_is_created_without_modifying_sources() -> None:
    views = complete_ring()
    before = tuple(view.rgba_sha256 for view in views)
    report = audit_pose_atlas(views, Hands())
    with TemporaryDirectory() as temporary:
        output = Path(temporary) / "pose-contact-sheet.png"
        build_contact_sheet(report, output)
        assert output.is_file()
        assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert tuple(view.rgba_sha256 for view in views) == before


def run() -> None:
    assert_complete_ring_passes_with_adjacent_metrics()
    assert_identity_failures_are_hard_gates_without_embedding_leakage()
    assert_legacy_call_shape_remains_compatible()
    assert_body_audit_is_an_opt_in_hard_gate()
    assert_missing_and_duplicate_angles_fail()
    assert_back_face_layer_fails()
    assert_visual_jump_and_identity_proof_fail()
    assert_failed_hand_report_and_layer_contract_fail()
    assert_naming_dimensions_anchor_alpha_and_thresholds_fail_closed()
    assert_contact_sheet_is_created_without_modifying_sources()
    print("POSE_ATLAS_AUDIT_OK")


if __name__ == "__main__":
    run()
