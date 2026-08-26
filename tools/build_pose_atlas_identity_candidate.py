from __future__ import annotations

lazy import argparse
lazy import math
lazy import os
lazy import re
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np


MIN_AFFINE_SCALE = 0.15
MAX_AFFINE_SCALE = 0.75
MAX_AFFINE_ROTATION_DEGREES = 25.0
MAX_AFFINE_TRANSLATION_X_RATIO = 0.65
MAX_AFFINE_TRANSLATION_Y_RATIO = 0.35
MAX_LANDMARK_RMSE_FACE_RATIO = 0.12
DEFAULT_MAX_ABS_TARGET_YAW = 15
MAX_ABS_TARGET_YAW = 180
IMAGE_DIMENSIONS = 3
RGBA_CHANNEL_COUNT = 4
POSE_ATLAS_VIEW_PATTERN = re.compile(
    r"^yaw(?P<yaw>[+-]\d{3})-pitch[+-]\d{2}$",
)


def _detect(image: np.ndarray, model: Path) -> np.ndarray:
    detector = cv2.FaceDetectorYN.create(
        str(model),
        "",
        (image.shape[1], image.shape[0]),
        0.75,
        0.3,
        100,
    )
    _status, faces = detector.detect(image[:, :, :3])
    if faces is None or len(faces) != 1:
        count = 0 if faces is None else len(faces)
        raise ValueError(f"expected one face, detected {count}")
    return faces[0]


def _landmarks(face: np.ndarray) -> np.ndarray:
    # YuNet: right eye, left eye, nose, right mouth, left mouth.
    return face[4:14].reshape(5, 2).astype(np.float32)


def _load_rgba_png(path: Path, *, label: str) -> np.ndarray:
    if path.suffix.lower() != ".png":
        raise ValueError(f"{label} must be a PNG file: {path}")
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"{label} must be a decodable PNG file: {path}")
    if image.ndim != IMAGE_DIMENSIONS or image.shape[2] != RGBA_CHANNEL_COUNT:
        raise ValueError(f"{label} must be an RGBA PNG file: {path}")
    return image


def _normalized_path(path: Path) -> str:
    return os.path.normcase(str(path.expanduser().resolve()))


def _validate_output_path(
    authority_path: Path,
    target_path: Path,
    output_path: Path,
) -> None:
    if output_path.suffix.lower() != ".png":
        raise ValueError(f"output must be a PNG file: {output_path}")
    output = _normalized_path(output_path)
    if output in {
        _normalized_path(authority_path),
        _normalized_path(target_path),
    }:
        raise ValueError("output must not overwrite authority or target")


def _validate_target_pose(target_path: Path, max_abs_target_yaw: int) -> None:
    if not 0 <= max_abs_target_yaw <= MAX_ABS_TARGET_YAW:
        raise ValueError("max_abs_target_yaw must be between 0 and 180")
    match = POSE_ATLAS_VIEW_PATTERN.fullmatch(target_path.stem)
    if match is None:
        return
    target_yaw = int(match.group("yaw"))
    if abs(target_yaw) > max_abs_target_yaw:
        raise ValueError(
            f"target yaw {target_yaw:+d} exceeds the safe identity-transfer limit "
            f"of {max_abs_target_yaw} degrees"
        )


def _validate_affine(
    matrix: np.ndarray,
    source_landmarks: np.ndarray,
    target_landmarks: np.ndarray,
    target_face: np.ndarray,
    target_shape: tuple[int, int],
) -> None:
    if matrix.shape != (2, 3) or not np.isfinite(matrix).all():
        raise ValueError("identity alignment produced an invalid affine matrix")
    scale = math.hypot(float(matrix[0, 0]), float(matrix[1, 0]))
    rotation = abs(
        math.degrees(math.atan2(float(matrix[1, 0]), float(matrix[0, 0])))
    )
    height, width = target_shape
    translate_x_ratio = abs(float(matrix[0, 2])) / width
    translate_y_ratio = abs(float(matrix[1, 2])) / height
    if not MIN_AFFINE_SCALE <= scale <= MAX_AFFINE_SCALE:
        raise ValueError(f"identity alignment scale is unsafe: {scale:.6f}")
    if rotation > MAX_AFFINE_ROTATION_DEGREES:
        raise ValueError(f"identity alignment rotation is unsafe: {rotation:.6f}")
    if translate_x_ratio > MAX_AFFINE_TRANSLATION_X_RATIO:
        raise ValueError(
            f"identity alignment horizontal translation is unsafe: "
            f"{translate_x_ratio:.6f}"
        )
    if translate_y_ratio > MAX_AFFINE_TRANSLATION_Y_RATIO:
        raise ValueError(
            f"identity alignment vertical translation is unsafe: "
            f"{translate_y_ratio:.6f}"
        )
    transformed = cv2.transform(source_landmarks[None, :, :], matrix)[0]
    residuals = transformed - target_landmarks
    rmse = float(np.sqrt(np.mean(np.sum(residuals * residuals, axis=1))))
    face_extent = max(float(target_face[2]), float(target_face[3]), 1.0)
    if rmse / face_extent > MAX_LANDMARK_RMSE_FACE_RATIO:
        raise ValueError(
            f"identity alignment landmark residual is unsafe: {rmse / face_extent:.6f}"
        )


def _face_mask(shape: tuple[int, int], face: np.ndarray) -> np.ndarray:
    height, width = shape
    x, y, box_width, box_height = face[:4]
    mask = np.zeros((height, width), dtype=np.uint8)
    center = (
        int(round(x + box_width * 0.5)),
        int(round(y + box_height * 0.54)),
    )
    axes = (
        max(1, int(round(box_width * 0.43))),
        max(1, int(round(box_height * 0.48))),
    )
    cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1, cv2.LINE_AA)
    # A soft edge prevents a sticker-like transition into the target hairline.
    return cv2.GaussianBlur(mask, (0, 0), 3.0)


def build_candidate(
    authority_path: Path,
    target_path: Path,
    output_path: Path,
    detector_model: Path,
    *,
    mirror_authority: bool = False,
    max_abs_target_yaw: int = DEFAULT_MAX_ABS_TARGET_YAW,
) -> None:
    _validate_output_path(authority_path, target_path, output_path)
    _validate_target_pose(target_path, max_abs_target_yaw)
    authority = _load_rgba_png(authority_path, label="authority")
    target = _load_rgba_png(target_path, label="target")
    if mirror_authority:
        authority = cv2.flip(authority, 1)

    source_face = _detect(authority, detector_model)
    target_face = _detect(target, detector_model)
    source_landmarks = _landmarks(source_face)
    target_landmarks = _landmarks(target_face)
    matrix, _inliers = cv2.estimateAffinePartial2D(
        source_landmarks,
        target_landmarks,
        method=cv2.LMEDS,
    )
    if matrix is None:
        raise ValueError("could not estimate identity alignment")
    _validate_affine(
        matrix,
        source_landmarks,
        target_landmarks,
        target_face,
        target.shape[:2],
    )

    source_mask = _face_mask(authority.shape[:2], source_face)
    size = (target.shape[1], target.shape[0])
    warped_face = cv2.warpAffine(
        authority[:, :, :3],
        matrix,
        size,
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
    )
    warped_mask = cv2.warpAffine(
        source_mask,
        matrix,
        size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
    )
    warped_alpha = cv2.warpAffine(
        authority[:, :, 3],
        matrix,
        size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
    )
    warped_mask = cv2.min(warped_mask, warped_alpha)

    # Blend the gamma-encoded image channels with a soft alpha weight. The
    # target alpha and every pixel outside the local face mask remain
    # byte-for-byte unchanged.
    weight = warped_mask.astype(np.float32)[:, :, None] / 255.0
    candidate = target.copy()
    candidate[:, :, :3] = np.clip(
        warped_face.astype(np.float32) * weight
        + target[:, :, :3].astype(np.float32) * (1.0 - weight),
        0,
        255,
    ).astype(np.uint8)
    candidate[:, :, 3] = target[:, :, 3]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), candidate):
        raise OSError(f"could not write {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a non-destructive PoseAtlas identity candidate."
    )
    parser.add_argument("authority", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--detector-model",
        type=Path,
        default=Path("assets/vision-models/face_detection_yunet_2023mar.onnx"),
    )
    parser.add_argument(
        "--mirror-authority",
        action="store_true",
        help="Mirror the authority before local facial alignment.",
    )
    parser.add_argument(
        "--max-abs-target-yaw",
        type=int,
        default=DEFAULT_MAX_ABS_TARGET_YAW,
        help=(
            "Fail closed when a PoseAtlas target exceeds this absolute yaw; "
            "defaults to 15 degrees to prevent oval face-patch transfers."
        ),
    )
    args = parser.parse_args()
    build_candidate(
        args.authority,
        args.target,
        args.output,
        args.detector_model,
        mirror_authority=args.mirror_authority,
        max_abs_target_yaw=args.max_abs_target_yaw,
    )


if __name__ == "__main__":
    main()
