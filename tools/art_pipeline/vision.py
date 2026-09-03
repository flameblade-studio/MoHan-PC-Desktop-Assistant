"""YuNet 偵測邊界；模型檔由呼叫端明確傳入。"""

from __future__ import annotations

lazy from pathlib import Path

lazy import cv2
lazy import numpy as np

lazy from .constants import (
    DETECTION_BACKGROUND_GRAY,
    YUNET_NMS_THRESHOLD,
    YUNET_SCORE_THRESHOLD,
    YUNET_TOP_K,
)
lazy from .image_ops import ensure_rgba


def _detect(image: np.ndarray, model_path: Path) -> np.ndarray | None:
    if not model_path.is_file():
        raise FileNotFoundError(f"找不到 YuNet 模型：{model_path}")
    rgba = ensure_rgba(image)
    height, width = rgba.shape[:2]
    detector = cv2.FaceDetectorYN.create(
        str(model_path),
        "",
        (width, height),
        YUNET_SCORE_THRESHOLD,
        YUNET_NMS_THRESHOLD,
        YUNET_TOP_K,
    )
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    bgr = (
        rgba[:, :, :3].astype(np.float32) * alpha
        + DETECTION_BACKGROUND_GRAY * (1.0 - alpha)
    ).astype(np.uint8)
    _status, faces = detector.detect(bgr)
    if faces is None or len(faces) == 0:
        return None
    return max(faces, key=lambda item: float(item[14]))


def face_landmarks(image: np.ndarray, model_path: Path) -> tuple[np.ndarray, float]:
    """回傳 YuNet 五點（左眼、右眼、鼻、左嘴角、右嘴角）與信心。"""

    face = _detect(image, model_path)
    if face is None:
        raise ValueError("YuNet 沒偵測到臉")
    return face[4:14].reshape(5, 2).astype(np.float64), float(face[14])


def face_box(
    image: np.ndarray, model_path: Path
) -> tuple[float, float, float, float] | None:
    face = _detect(image, model_path)
    if face is None:
        return None
    return tuple(float(value) for value in face[:4])
