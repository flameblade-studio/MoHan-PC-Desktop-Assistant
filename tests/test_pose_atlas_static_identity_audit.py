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


def test_current_evidence_passes_via_owner_accepted_baseline() -> None:
    evidence_path = (
        ROOT
        / "docs/release-evidence/pose-atlas-static-identity-audit/"
        "pose-atlas-static-identity-audit.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["schema"] == AUDIT_SCHEMA
    assert evidence["passed"] is True
    assert evidence["issue_count"] == 0
    assert evidence["waived_issue_count"] > 0
    # Generation 2 (v5-base, owner-accepted 2026-09-02): the waived classes are
    # the bare-forehead profile bulge and the non-monotonic head-turn pairs.
    # v4's green/cyan mouth pixels do not exist in v5-base, so nothing waives
    # them; every waived code must still be one the pinned baseline names.
    assert evidence["waived_issues_by_code"]["forehead_outward_bulge"] > 0
    assert evidence["waived_issues_by_code"]["adjacent_face_registration_jump"] > 0
    atlas_root = ROOT / "assets" / "pose-atlas" / POSE_ATLAS_ROOT_NAME
    baseline = load_identity_baseline(atlas_root / "identity-audit-baseline.json")
    assert baseline
    baseline_codes: set[str] = set()
    for view_id, (sha256, codes) in baseline.items():
        path = atlas_root / f"{view_id}.png"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha256
        baseline_codes |= codes
    assert set(evidence["waived_issues_by_code"]) <= baseline_codes
    assert evidence["waived_issue_count"] == sum(
        evidence["waived_issues_by_code"].values()
    )
    raw = json.loads(
        (atlas_root / "identity-audit-baseline.json").read_text(encoding="utf-8")
    )
    assert raw["schema"] == BASELINE_SCHEMA
    assert POSE_ATLAS_ROOT_NAME in evidence["atlas_root"]


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
