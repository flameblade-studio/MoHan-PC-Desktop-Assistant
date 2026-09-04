"""不含路徑策略的 RGBA、鍵色與預乘 alpha 影像操作。"""

from __future__ import annotations

lazy from pathlib import Path

lazy import cv2
lazy import numpy as np

lazy from .constants import (
    ALPHA_EPSILON,
    BGR_CHANNELS,
    CHROMA_HARD_THRESHOLD,
    IMAGE_DIMENSIONS,
    MAGENTA_BGR,
    CHROMA_SPILL_THRESHOLD,
    RGBA_CHANNELS,
)


def ensure_rgba(image: np.ndarray) -> np.ndarray:
    """將 OpenCV 的 BGR/BGRA 陣列轉成連續的 BGRA uint8 陣列。"""

    if image is None or image.ndim != IMAGE_DIMENSIONS:
        raise ValueError("影像必須是有色彩通道的陣列")
    if image.shape[2] == BGR_CHANNELS:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    elif image.shape[2] != RGBA_CHANNELS:
        raise ValueError(f"影像必須是 BGR 或 BGRA，得到 {image.shape}")
    return np.ascontiguousarray(image, dtype=np.uint8)


def load_image(path: Path, *, unchanged: bool = True) -> np.ndarray:
    """以支援非 ASCII 路徑的方式解碼 PNG/JPEG。"""

    data = np.fromfile(str(path), dtype=np.uint8)
    flags = cv2.IMREAD_UNCHANGED if unchanged else cv2.IMREAD_COLOR
    image = cv2.imdecode(data, flags)
    if image is None:
        raise ValueError(f"讀不到影像：{path}")
    return image


def load_rgba(path: Path) -> np.ndarray:
    return ensure_rgba(load_image(path))


def load_bgr(path: Path) -> np.ndarray:
    image = load_image(path, unchanged=False)
    if image.ndim != IMAGE_DIMENSIONS or image.shape[2] != BGR_CHANNELS:
        raise ValueError(f"影像不是 BGR：{path}")
    return np.ascontiguousarray(image, dtype=np.uint8)


def save_png(path: Path, image: np.ndarray) -> None:
    """寫出 PNG；輸出目錄由呼叫端指定，不隱含工作樹路徑。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(".png", np.ascontiguousarray(image))
    if not ok:
        raise OSError(f"寫不出 PNG：{path}")
    encoded.tofile(str(path))


def transparent_rgb_zero(image: np.ndarray) -> np.ndarray:
    """清除所有 alpha=0 像素的 RGB，避免後續插值帶入鍵色。"""

    result = ensure_rgba(image).copy()
    result[result[:, :, 3] == 0, :3] = 0
    return result


def chroma_key(
    image: np.ndarray,
    *,
    spill_threshold: int = CHROMA_SPILL_THRESHOLD,
    hard_threshold: int = CHROMA_HARD_THRESHOLD,
) -> np.ndarray:
    """依 repo 既有鍵色規則把洋紅背景轉成 alpha。

    輸入使用 OpenCV 的 BGR(A) 排列。半透明邊緣會保留並去除部分洋紅，
    最後保證完全透明像素的 RGB 為零。
    """

    if hard_threshold >= spill_threshold:
        raise ValueError("hard_threshold 必須小於 spill_threshold")
    source = ensure_rgba(image)
    result = source.copy()
    blue = source[:, :, 0].astype(np.int32)
    green = source[:, :, 1].astype(np.int32)
    red = source[:, :, 2].astype(np.int32)
    magenta = np.minimum(red, blue) - green
    balance = np.abs(red - blue)
    distance = np.maximum(0, magenta - balance // 2)

    keyed_alpha = np.where(
        distance >= spill_threshold,
        0,
        np.where(
            distance <= hard_threshold,
            255,
            np.rint(
                255.0
                * (spill_threshold - distance)
                / (spill_threshold - hard_threshold)
            ),
        ),
    ).astype(np.uint8)
    source_alpha = source[:, :, 3].astype(np.uint16)
    result[:, :, 3] = (source_alpha * keyed_alpha.astype(np.uint16) + 127) // 255

    intermediate = (distance > hard_threshold) & (distance < spill_threshold)
    corrected_blue = np.minimum(blue, green + np.maximum(0, blue - red))
    corrected_red = np.minimum(red, green + np.maximum(0, red - blue))
    result[:, :, 0][intermediate] = corrected_blue[intermediate].astype(np.uint8)
    result[:, :, 2][intermediate] = corrected_red[intermediate].astype(np.uint8)
    return transparent_rgb_zero(result)


def key_file(path: Path) -> np.ndarray:
    return chroma_key(load_image(path))


def resize_rgba(
    image: np.ndarray, size: tuple[int, int], *, interpolation: int = cv2.INTER_LANCZOS4
) -> np.ndarray:
    """以預乘 alpha 縮放，避免透明鍵色滲入新邊界。"""

    source = transparent_rgb_zero(image)
    alpha = source[:, :, 3:4].astype(np.float32) / 255.0
    premultiplied = np.dstack((
        source[:, :, :3].astype(np.float32) * alpha,
        alpha * 255.0,
    ))
    warped = cv2.resize(premultiplied, size, interpolation=interpolation)
    return _unpremultiply(warped)


def warp_rgba(
    image: np.ndarray,
    matrix: np.ndarray,
    size: tuple[int, int],
    *,
    interpolation: int = cv2.INTER_LINEAR,
) -> np.ndarray:
    """以預乘 alpha 套用 affine warp，回傳 straight-alpha BGRA。"""

    source = transparent_rgb_zero(image)
    alpha = source[:, :, 3:4].astype(np.float32) / 255.0
    premultiplied = np.dstack((
        source[:, :, :3].astype(np.float32) * alpha,
        alpha * 255.0,
    ))
    warped = cv2.warpAffine(
        premultiplied,
        matrix,
        size,
        flags=interpolation,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    return _unpremultiply(warped)


def _unpremultiply(premultiplied: np.ndarray) -> np.ndarray:
    alpha = np.clip(premultiplied[:, :, 3], 0.0, 255.0)
    safe_alpha = np.maximum(alpha, ALPHA_EPSILON)[:, :, None]
    rgb = np.clip(premultiplied[:, :, :3] * 255.0 / safe_alpha, 0.0, 255.0)
    result = np.dstack((rgb, alpha)).astype(np.uint8)
    return transparent_rgb_zero(result)


def flatten_on_magenta(image: np.ndarray) -> np.ndarray:
    """將 BGRA 鋪回不透明洋紅 BGR，供編輯/模型輸入使用。"""

    source = ensure_rgba(image)
    alpha = source[:, :, 3:4].astype(np.float32) / 255.0
    background = np.empty_like(source[:, :, :3])
    background[:, :] = MAGENTA_BGR  # BGR 洋紅，來源同 scratchpad 編輯流程
    return np.clip(
        source[:, :, :3].astype(np.float32) * alpha
        + background.astype(np.float32) * (1.0 - alpha),
        0,
        255,
    ).astype(np.uint8)


def composite_over(destination: np.ndarray, source: np.ndarray) -> np.ndarray:
    """以既有層包覆規則合成兩張同尺寸 BGRA 圖。"""

    dst = ensure_rgba(destination).astype(np.float32)
    src = ensure_rgba(source)
    alpha = src[:, :, 3:4].astype(np.float32) / 255.0
    dst[:, :, :3] = src[:, :, :3].astype(np.float32) * alpha + dst[:, :, :3] * (
        1.0 - alpha
    )
    dst[:, :, 3:4] = np.maximum(dst[:, :, 3:4], src[:, :, 3:4])
    return transparent_rgb_zero(np.clip(dst, 0, 255).astype(np.uint8))
