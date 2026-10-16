from __future__ import annotations

lazy import json
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np

lazy import hashlib

lazy from domain.constants import POSE_ATLAS_ROOT_NAME
lazy from tools.audit_pose_atlas_identity import (
    AUDIT_SCHEMA,
    BASELINE_SCHEMA,
    FaceEvidence,
    audit_pose_atlas_identity,
    load_identity_baseline,
    preflight_exit_code,
)


ROOT = Path(__file__).resolve().parents[1]
SIZE = (128, 192)
VIEW = "yaw+060-pitch+00"
# Historical archive fixture: the 2026-09 batch recorded two outward-bulge
# waivers on the then-current sources. This is a preserved record, not a fresh
# audit of today's files, so it keeps its own constants.
HISTORICAL_WAIVER_COUNT = 2
HISTORICAL_WAIVED_CODES = {
    "forehead_outward_bulge": 2,
}
# Current owner-accepted v5-base pins. These are literals on purpose: the
# baseline file must match this expectation, never the other way around.
CURRENT_PINNED_BASELINE = {
    "yaw+060-pitch+00": (
        "4950e3c185310ae5e91d0b3da8164cbef50c7801c0033ff0670cd40c5f124a8e",
        frozenset({"forehead_curvature_discontinuity", "forehead_outward_bulge"}),
    ),
    "yaw+090-pitch+00": (
        "504e7d072f382e6cfc7b80fde8d4b446954a7d9841602d4b6d2b29489d45b152",
        frozenset({"forehead_curvature_discontinuity", "forehead_outward_bulge"}),
    ),
    "yaw-060-pitch+00": (
        "4a09b1b7100092ce5091a72e8f7cd68c952188a4f1c0fb25bbefbb56f1e18bca",
        frozenset({"forehead_curvature_discontinuity"}),
    ),
    "yaw-075-pitch+00": (
        "7f9c1c0ca8246caccdc52e30f619223c259b2b344a44264df8cfe88369256a52",
        frozenset({"forehead_curvature_discontinuity", "forehead_outward_bulge"}),
    ),
    "yaw-090-pitch+00": (
        "d699e4e51c508a25c7bacdfac0cc923fad4ea03ebd721f749be5c621f7c5a44b",
        frozenset({"forehead_curvature_discontinuity", "forehead_outward_bulge"}),
    ),
}
CURRENT_PINNED_WAIVER_TOTAL = 9
CURRENT_AVAILABLE_NATIVE_FACE_LANDMARKS = 17
ALLOWED_WAIVER_CODES = frozenset(
    {"forehead_curvature_discontinuity", "forehead_outward_bulge"}
)
EXPECTED_NEW_PROFILE_FINDINGS = {
    "yaw+090-pitch+00": ["forehead_curvature_discontinuity"],
    "yaw-090-pitch+00": [
        "forehead_curvature_discontinuity",
        "forehead_outward_bulge",
    ],
}
OWNER_APPROVAL_STATUS = "new_profile_source_appearance_accepted_exact_sha_findings_pinned"
HISTORICAL_ABSENT_RECORD = "ART/owner-visible-batch-approval-20260908-side-01.json"
FACE = FaceEvidence(
    box=(40.0, 20.0, 48.0, 70.0),
    landmarks=(
        (52.0, 45.0),
        (72.0, 45.0),
        (44.0, 57.0),
        (56.0, 70.0),
        (68.0, 70.0),
    ),
    confidence=0.99,
)


def _image() -> np.ndarray:
    image = np.zeros((SIZE[1], SIZE[0], 4), dtype=np.uint8)
    image[20:90, 40:88] = (150, 180, 220, 255)
    return image


def _write(root: Path, image: np.ndarray) -> None:
    root.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(root / f"{VIEW}.png"), image)


def _audit(root: Path):
    return audit_pose_atlas_identity(
        root,
        root / "unused.onnx",
        view_ids=(VIEW,),
        expected_size=SIZE,
        face_evidence={VIEW: FACE},
    )


def test_smooth_registered_profile_passes(tmp_path: Path) -> None:
    _write(tmp_path, _image())
    report = _audit(tmp_path)
    assert report.schema == AUDIT_SCHEMA
    assert report.passed
    assert preflight_exit_code(report) == 0


def test_nearly_transparent_rgb_fringe_is_audited_at_composited_intensity(
    tmp_path: Path,
) -> None:
    image = _image()
    image[70, 62] = (100, 130, 80, 19)
    _write(tmp_path, image)

    report = _audit(tmp_path)

    assert report.passed
    assert "mouth_green_cyan_pixels" not in report.issues_by_code


def test_forehead_spike_and_green_mouth_pixel_block_packaging(tmp_path: Path) -> None:
    image = _image()
    # For this left-facing profile the outward silhouette is the minimum x.
    image[35:38, 34:40] = (150, 180, 220, 255)
    # One red-deficient cyan/green pixel within the landmark-derived mouth ROI.
    image[70, 62] = (100, 130, 80, 255)
    _write(tmp_path, image)
    report = _audit(tmp_path)
    assert preflight_exit_code(report) == 1
    assert "forehead_outward_bulge" in report.issues_by_code
    assert "mouth_green_cyan_pixels" in report.issues_by_code


def test_adjacent_registration_jump_reports_both_views(tmp_path: Path) -> None:
    left_view = "yaw+015-pitch+00"
    right_view = "yaw+030-pitch+00"
    right_face = FaceEvidence(
        box=(60.0, 20.0, 48.0, 70.0),
        landmarks=tuple((x + 20.0, y) for x, y in FACE.landmarks),
        confidence=0.99,
    )
    left_image = _image()
    right_image = np.zeros((SIZE[1], SIZE[0], 4), dtype=np.uint8)
    right_image[20:90, 60:108] = (150, 180, 220, 255)
    tmp_path.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(tmp_path / f"{left_view}.png"), left_image)
    assert cv2.imwrite(str(tmp_path / f"{right_view}.png"), right_image)
    report = audit_pose_atlas_identity(
        tmp_path,
        tmp_path / "unused.onnx",
        view_ids=(left_view, right_view),
        expected_size=SIZE,
        face_evidence={left_view: FACE, right_view: right_face},
    )
    jump_views = sorted(
        issue.view_id
        for issue in report.issues
        if issue.code == "adjacent_face_registration_jump"
    )
    # The pair jump must pin BOTH sides so a baseline waiver only holds
    # while neither owner-accepted file changes.
    assert jump_views == [left_view, right_view]
    assert preflight_exit_code(report) == 1


def test_baseline_waives_only_exact_accepted_bytes(tmp_path: Path) -> None:
    image = _image()
    image[35:38, 34:40] = (150, 180, 220, 255)
    image[70, 62] = (100, 130, 80, 255)
    _write(tmp_path, image)
    file_sha = hashlib.sha256((tmp_path / f"{VIEW}.png").read_bytes()).hexdigest()
    unwaived = _audit(tmp_path)
    codes = frozenset(issue.code for issue in unwaived.issues)
    assert {"forehead_outward_bulge", "mouth_green_cyan_pixels"} <= codes
    accepted = audit_pose_atlas_identity(
        tmp_path,
        tmp_path / "unused.onnx",
        view_ids=(VIEW,),
        expected_size=SIZE,
        face_evidence={VIEW: FACE},
        baseline={VIEW: (file_sha, codes)},
    )
    assert accepted.passed
    assert preflight_exit_code(accepted) == 0
    assert accepted.issue_count == 0
    assert accepted.waived_issue_count == unwaived.issue_count
    assert set(accepted.waived_issues_by_code) == set(codes)
    changed = audit_pose_atlas_identity(
        tmp_path,
        tmp_path / "unused.onnx",
        view_ids=(VIEW,),
        expected_size=SIZE,
        face_evidence={VIEW: FACE},
        baseline={VIEW: ("0" * 64, codes)},
    )
    assert not changed.passed
    assert preflight_exit_code(changed) == 1
    assert changed.waived_issue_count == 0


def test_historical_release_evidence_fixture_is_intact() -> None:
    """The archived 2026-09 evidence is a record, not a fresh audit."""

    evidence_path = (
        ROOT
        / "docs/release-evidence/pose-atlas-static-identity-audit/"
        "pose-atlas-static-identity-audit.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["schema"] == AUDIT_SCHEMA
    assert evidence["passed"] is True
    assert evidence["issue_count"] == 0
    assert evidence["waived_issue_count"] == HISTORICAL_WAIVER_COUNT
    assert evidence["waived_issues_by_code"] == HISTORICAL_WAIVED_CODES
    assert len(evidence["waived_issues"]) == HISTORICAL_WAIVER_COUNT
    assert {
        issue["code"] for issue in evidence["waived_issues"]
    } == set(HISTORICAL_WAIVED_CODES)
    assert not Path(evidence["atlas_root"]).is_absolute()
    assert all(
        not Path(issue["path"]).is_absolute()
        for issue in evidence["waived_issues"]
    )


def test_current_baseline_pins_and_owner_chain_are_exact() -> None:
    """Current pins are asserted as literals and the owner chain is verified."""

    atlas_root = ROOT / "assets" / "pose-atlas" / POSE_ATLAS_ROOT_NAME
    baseline_path = atlas_root / "identity-audit-baseline.json"
    baseline = load_identity_baseline(baseline_path)
    raw = json.loads(baseline_path.read_text(encoding="utf-8"))

    assert raw["schema"] == BASELINE_SCHEMA
    assert baseline == CURRENT_PINNED_BASELINE
    assert sum(len(codes) for _sha, codes in baseline.values()) == (
        CURRENT_PINNED_WAIVER_TOTAL
    )
    waived_codes: set[str] = set()
    for view_id, (sha256, codes) in baseline.items():
        assert codes <= ALLOWED_WAIVER_CODES, view_id
        path = atlas_root / f"{view_id}.png"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha256
        waived_codes |= codes
    assert waived_codes == ALLOWED_WAIVER_CODES

    audit_evidence = raw["audit_evidence"]
    assert audit_evidence["new_profile_findings"] == EXPECTED_NEW_PROFILE_FINDINGS
    assert audit_evidence["derived_mirror"] == {
        "derived_plus090_is_exact_mirror_of_minus090": True,
        "differing_pixels_after_flip": 0,
    }
    assert audit_evidence["raw_metrics_retained"] is True
    for key in ("raw_report_path", "raw_report_sha256"):
        assert audit_evidence[key]
    raw_report = ROOT / audit_evidence["raw_report_path"]
    if raw_report.is_file():
        assert (
            hashlib.sha256(raw_report.read_bytes()).hexdigest()
            == audit_evidence["raw_report_sha256"]
        )
    derivation = audit_evidence["alpha_cleanup_derivation"]
    derivation_path = ROOT / derivation["path"]
    assert derivation_path.is_file()
    assert hashlib.sha256(derivation_path.read_bytes()).hexdigest() == (
        derivation["sha256"]
    )
    assert "alpha-only" in derivation["rule"]

    contract = raw["measurement_contract"]
    assert contract["status"] == "pending_algorithm_measurement_data"
    assert contract["available_native_face_landmarks"] == (
        CURRENT_AVAILABLE_NATIVE_FACE_LANDMARKS
    )

    approval = raw["owner_approval"]
    assert approval["status"] == OWNER_APPROVAL_STATUS
    assert any(
        entry["path"] == HISTORICAL_ABSENT_RECORD
        and entry["status"] == "historical_record_path_currently_absent"
        for entry in approval["evidence"]
    )
    for entry in approval["evidence"]:
        if entry.get("status") == "historical_record_path_currently_absent":
            assert not (ROOT / entry["path"]).exists()
            continue
        record_path = ROOT / entry["path"]
        assert record_path.is_file(), entry["path"]
        assert hashlib.sha256(record_path.read_bytes()).hexdigest() == entry["sha256"]


def test_windows_build_places_static_identity_gate_before_packaging() -> None:
    script = (ROOT / "build.ps1").read_text(encoding="utf-8")
    gate = "-m tools.audit_pose_atlas_identity"
    for later in (
        "tools/build_pyinstaller_jit_bootloader.py",
        "tools/build_native_acceleration.py",
        "-m PyInstaller",
    ):
        assert script.index(gate) < script.index(later)
    assert "$StaticIdentityAuditExitCode = $LASTEXITCODE" in script
    assert "if ($StaticIdentityAuditExitCode -ne 0)" in script
