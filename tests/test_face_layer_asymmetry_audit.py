from __future__ import annotations

lazy from pathlib import Path

lazy import cv2
lazy import numpy as np

lazy from tools.audit_face_layer_asymmetry import audit_motion_series, audit_pair


ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(path), image)


def test_exact_mirrored_pair_fails_runtime_authority_contract(
    tmp_path: Path,
) -> None:
    left = np.zeros((40, 60, 4), dtype=np.uint8)
    left[8:30, 10:34] = (20, 40, 80, 255)
    left[12:18, 13:17] = (80, 120, 180, 255)
    right = cv2.flip(left, 1)
    left_path = tmp_path / "front_iris_left.png"
    right_path = tmp_path / "front_iris_right.png"
    _write(left_path, left)
    _write(right_path, right)
    issues = audit_pair(
        left_path,
        right_path,
        view_id="front",
        feature="iris",
    )
    assert [issue.code for issue in issues] == ["paired-layer-exact-mirror"]


def test_authority_derived_micro_difference_passes(tmp_path: Path) -> None:
    left = np.zeros((40, 60, 4), dtype=np.uint8)
    left[8:30, 10:34] = (20, 40, 80, 255)
    right = cv2.flip(left, 1)
    right[20, 40] = (25, 45, 85, 255)
    left_path = tmp_path / "front_brow_left.png"
    right_path = tmp_path / "front_brow_right.png"
    _write(left_path, left)
    _write(right_path, right)
    assert not audit_pair(
        left_path,
        right_path,
        view_id="front",
        feature="brow",
    )


def test_windows_build_blocks_exact_symmetry_before_packaging() -> None:
    script = (ROOT / "build.ps1").read_text(encoding="utf-8")
    gate = "-m tools.audit_face_layer_asymmetry"
    for later in (
        "tools/build_pyinstaller_jit_bootloader.py",
        "tools/build_native_acceleration.py",
        "-m PyInstaller",
    ):
        assert script.index(gate) < script.index(later)
    assert "$FaceAsymmetryAuditExitCode = $LASTEXITCODE" in script
    assert "if ($FaceAsymmetryAuditExitCode -ne 0)" in script


def test_single_frame_control_pop_and_jerk_fail() -> None:
    issues = audit_motion_series((0.0, 0.0, 1.0, 1.0))
    assert "control-single-frame-pop" in issues
    assert "control-acceleration-spike" in issues
    assert "control-jerk-spike" in issues


def test_linear_50hz_micro_transition_passes() -> None:
    assert not audit_motion_series((0.0, 0.2, 0.4, 0.6, 0.8, 1.0))
