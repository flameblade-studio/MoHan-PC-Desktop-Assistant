from __future__ import annotations

lazy import math
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np
lazy import pytest

lazy from tools import build_pose_atlas_identity_candidate as candidate_builder
lazy from tools.measure_face_identity import _embedding, cosine_similarity


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "assets" / "vision-models"
DETECTOR_MODEL = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
RECOGNIZER_MODEL = MODEL_DIR / "face_recognition_sface_2021dec.onnx"
AUTHORITY_PATH = ROOT / "assets" / "expressions" / "idle_front.png"
TARGET_PATH = ROOT / "assets" / "pose-atlas" / "v4" / "yaw+000-pitch+00.png"
MIN_IDENTITY_IMPROVEMENT = 0.05
MIN_CANDIDATE_SIMILARITY = 0.8
SOURCE_SENTINEL_BLUE = 10


def _face(
    box: tuple[float, float, float, float],
    landmarks: tuple[tuple[float, float], ...],
) -> np.ndarray:
    return np.array([*box, *(value for point in landmarks for value in point), 0.99])


SOURCE_FACE = _face(
    (24.0, 20.0, 64.0, 72.0),
    ((42.0, 42.0), (70.0, 42.0), (56.0, 57.0), (44.0, 74.0), (68.0, 74.0)),
)
TARGET_FACE = _face(
    (42.0, 20.0, 32.0, 36.0),
    ((51.0, 31.0), (65.0, 31.0), (58.0, 38.5), (52.0, 47.0), (64.0, 47.0)),
)


def _write_rgba_inputs(tmp_path: Path) -> tuple[Path, Path]:
    authority = np.zeros((128, 128, 4), dtype=np.uint8)
    authority[:, :, :3] = (SOURCE_SENTINEL_BLUE, 40, 210)
    authority[:, :, 3] = 255
    target = np.zeros((128, 128, 4), dtype=np.uint8)
    target[:, :, 0] = np.arange(128, dtype=np.uint8)[None, :]
    target[:, :, 1] = np.arange(128, dtype=np.uint8)[:, None]
    target[:, :, 2] = 90
    target[:, :, 3] = 255
    target[:5, :, 3] = 0
    authority_path = tmp_path / "authority.png"
    target_path = tmp_path / "target.png"
    assert cv2.imwrite(str(authority_path), authority)
    assert cv2.imwrite(str(target_path), target)
    return authority_path, target_path


def _fake_detect(image: np.ndarray, _model: Path) -> np.ndarray:
    return (
        SOURCE_FACE.copy()
        if int(image[0, 0, 0]) == SOURCE_SENTINEL_BLUE
        else TARGET_FACE.copy()
    )


def test_candidate_is_deterministic_and_preserves_registered_pixels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority_path, target_path = _write_rgba_inputs(tmp_path)
    first = tmp_path / "candidate-first.png"
    second = tmp_path / "candidate-second.png"
    monkeypatch.setattr(candidate_builder, "_detect", _fake_detect)

    for output in (first, second):
        candidate_builder.build_candidate(
            authority_path,
            target_path,
            output,
            tmp_path / "unused.onnx",
        )

    assert first.read_bytes() == second.read_bytes()
    authority = cv2.imread(str(authority_path), cv2.IMREAD_UNCHANGED)
    target = cv2.imread(str(target_path), cv2.IMREAD_UNCHANGED)
    result = cv2.imread(str(first), cv2.IMREAD_UNCHANGED)
    assert authority is not None and target is not None and result is not None
    assert np.array_equal(result[:, :, 3], target[:, :, 3])

    source_landmarks = candidate_builder._landmarks(SOURCE_FACE)
    target_landmarks = candidate_builder._landmarks(TARGET_FACE)
    matrix, _ = cv2.estimateAffinePartial2D(
        source_landmarks,
        target_landmarks,
        method=cv2.LMEDS,
    )
    assert matrix is not None
    source_mask = candidate_builder._face_mask(authority.shape[:2], SOURCE_FACE)
    warped_mask = cv2.warpAffine(
        source_mask,
        matrix,
        (target.shape[1], target.shape[0]),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
    )
    warped_alpha = cv2.warpAffine(
        authority[:, :, 3],
        matrix,
        (target.shape[1], target.shape[0]),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
    )
    outside_mask = cv2.min(warped_mask, warped_alpha) == 0
    assert np.array_equal(result[outside_mask], target[outside_mask])


@pytest.mark.parametrize("conflict", ["authority", "target"])
def test_candidate_refuses_to_overwrite_inputs(
    tmp_path: Path,
    conflict: str,
) -> None:
    authority_path, target_path = _write_rgba_inputs(tmp_path)
    output_path = authority_path if conflict == "authority" else target_path
    with pytest.raises(ValueError, match="must not overwrite"):
        candidate_builder.build_candidate(
            authority_path,
            target_path,
            output_path,
            tmp_path / "unused.onnx",
        )


def test_candidate_requires_png_output(tmp_path: Path) -> None:
    authority_path, target_path = _write_rgba_inputs(tmp_path)
    with pytest.raises(ValueError, match="output must be a PNG"):
        candidate_builder.build_candidate(
            authority_path,
            target_path,
            tmp_path / "candidate.jpg",
            tmp_path / "unused.onnx",
        )


def test_candidate_rejects_large_pose_mismatch_by_default(tmp_path: Path) -> None:
    authority_path, generated_target = _write_rgba_inputs(tmp_path)
    target_path = tmp_path / "yaw+030-pitch+00.png"
    generated_target.replace(target_path)
    with pytest.raises(ValueError, match="safe identity-transfer limit"):
        candidate_builder.build_candidate(
            authority_path,
            target_path,
            tmp_path / "candidate.png",
            tmp_path / "unused.onnx",
        )


@pytest.mark.parametrize("kind", ["broken", "grayscale", "rgb"])
def test_candidate_rejects_invalid_authority_images(
    tmp_path: Path,
    kind: str,
) -> None:
    _authority_path, target_path = _write_rgba_inputs(tmp_path)
    authority_path = tmp_path / f"{kind}.png"
    if kind == "broken":
        authority_path.write_bytes(b"not a png")
    elif kind == "grayscale":
        assert cv2.imwrite(str(authority_path), np.zeros((32, 32), dtype=np.uint8))
    else:
        assert cv2.imwrite(str(authority_path), np.zeros((32, 32, 3), dtype=np.uint8))
    with pytest.raises(ValueError, match="authority must be"):
        candidate_builder.build_candidate(
            authority_path,
            target_path,
            tmp_path / "candidate.png",
            tmp_path / "unused.onnx",
        )


@pytest.mark.parametrize(
    ("matrix", "reason"),
    [
        (np.array([[0.05, 0.0, 0.0], [0.0, 0.05, 0.0]]), "scale"),
        (np.array([[0.9, 0.0, 0.0], [0.0, 0.9, 0.0]]), "scale"),
        (
            np.array(
                [
                    [0.5 * math.cos(math.radians(40)), -0.5 * math.sin(math.radians(40)), 0.0],
                    [0.5 * math.sin(math.radians(40)), 0.5 * math.cos(math.radians(40)), 0.0],
                ]
            ),
            "rotation",
        ),
        (np.array([[0.5, 0.0, 100.0], [0.0, 0.5, 0.0]]), "horizontal"),
        (np.array([[0.5, 0.0, 0.0], [0.0, 0.5, 60.0]]), "vertical"),
    ],
)
def test_affine_safety_limits_fail_closed(matrix: np.ndarray, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        candidate_builder._validate_affine(
            matrix,
            candidate_builder._landmarks(SOURCE_FACE),
            candidate_builder._landmarks(TARGET_FACE),
            TARGET_FACE,
            (128, 128),
        )


def test_affine_landmark_residual_fails_closed() -> None:
    matrix = np.array([[0.5, 0.0, 30.0], [0.0, 0.5, 10.0]])
    bad_target = candidate_builder._landmarks(TARGET_FACE).copy()
    bad_target[-1] += (30.0, 30.0)
    with pytest.raises(ValueError, match="landmark residual"):
        candidate_builder._validate_affine(
            matrix,
            candidate_builder._landmarks(SOURCE_FACE),
            bad_target,
            TARGET_FACE,
            (128, 128),
        )


def test_authority_candidate_improves_face_identity(tmp_path: Path) -> None:
    output_path = tmp_path / "candidate.png"
    candidate_builder.build_candidate(
        AUTHORITY_PATH,
        TARGET_PATH,
        output_path,
        DETECTOR_MODEL,
    )
    reference = _embedding(AUTHORITY_PATH, DETECTOR_MODEL, RECOGNIZER_MODEL)
    before = cosine_similarity(
        reference,
        _embedding(TARGET_PATH, DETECTOR_MODEL, RECOGNIZER_MODEL),
    )
    after = cosine_similarity(
        reference,
        _embedding(output_path, DETECTOR_MODEL, RECOGNIZER_MODEL),
    )
    assert after >= MIN_CANDIDATE_SIMILARITY
    assert after - before >= MIN_IDENTITY_IMPROVEMENT
