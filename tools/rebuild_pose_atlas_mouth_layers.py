"""Rebuild PoseAtlas speech layers from each view's own authority portrait.

Only pixels from the matching PoseAtlas authority image are used. The original
lip line is gently opened in place and its own crease pixels are extended into
the tiny aperture. No cross-pose mouth, procedural black cavity, painted tooth,
or foreign skin colour enters the result.

Extreme profile and rear views intentionally remain transparent because their
projected mouth area is too small for an additional overlay to remain natural.
"""

from __future__ import annotations

lazy from pathlib import Path

lazy import cv2
lazy import numpy as np


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_DIR = ROOT / "assets" / "pose-atlas" / "v4"
LAYER_DIR = ROOT / "assets" / "pose-atlas" / "v4-layered"
CANVAS_WIDTH = 1024
CANVAS_HEIGHT = 1536
EXPECTED_CHANNEL_COUNT = 4
EXPECTED_VIEW_COUNT = 24
MOUTH_PADDING_X = 6
MOUTH_PADDING_Y = 6

# Bundled 468-point Face Mesh mouth bounds measured on enlarged crops of the
# exact authority portrait. Values are left, top, right, bottom in canvas
# pixels. Views beyond ±60 degrees keep their authority profile unchanged.
MOUTH_BOUNDS = frozendict({
    "yaw-060-pitch+00": (527.5, 263.4, 556.6, 276.7),
    "yaw-045-pitch+00": (482.1, 274.7, 510.4, 288.0),
    "yaw-030-pitch+00": (480.7, 266.7, 509.5, 280.4),
    "yaw-015-pitch+00": (481.9, 271.0, 510.3, 285.4),
    "yaw+000-pitch+00": (494.7, 281.4, 529.2, 293.4),
    "yaw+015-pitch+00": (467.6, 277.5, 495.5, 290.4),
    "yaw+030-pitch+00": (461.2, 276.7, 489.0, 290.0),
    "yaw+045-pitch+00": (462.7, 277.9, 489.7, 291.3),
    "yaw+060-pitch+00": (452.6, 276.3, 478.1, 290.4),
})


def _surface() -> np.ndarray:
    return np.zeros(
        (CANVAS_HEIGHT, CANVAS_WIDTH, EXPECTED_CHANNEL_COUNT),
        dtype=np.uint8,
    )


def _deform_lips(
    crop: np.ndarray,
    center_x: float,
    center_y: float,
    mouth_width: float,
    mouth_height: float,
) -> np.ndarray:
    crop_height, crop_width = crop.shape[:2]
    yy, xx = np.indices((crop_height, crop_width), dtype=np.float32)
    horizontal = (xx - center_x) / max(1.0, mouth_width * 0.58)
    vertical = (yy - center_y) / max(1.0, mouth_height * 0.90)
    influence = np.exp(-(horizontal * horizontal + vertical * vertical) * 1.6)
    displacement = max(0.75, min(1.65, mouth_height * 0.105))
    upper = yy < center_y
    map_y = yy.copy()
    map_y[upper] += displacement * influence[upper]
    map_y[~upper] -= displacement * influence[~upper]
    return cv2.remap(
        crop,
        xx,
        map_y,
        interpolation=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REFLECT_101,
    )


def _extend_authority_crease(
    opened: np.ndarray,
    crop: np.ndarray,
    center_x: float,
    center_y: float,
    mouth_width: float,
    mouth_height: float,
) -> None:
    crop_height, crop_width = crop.shape[:2]
    crease_y = max(1, min(crop_height - 2, round(center_y)))
    aperture_height = max(2, min(4, round(mouth_height * 0.22)))
    crease = cv2.resize(
        crop[crease_y - 1:crease_y + 2],
        (crop_width, aperture_height),
        interpolation=cv2.INTER_LANCZOS4,
    )
    crease_top = max(0, round(center_y - aperture_height / 2.0))
    crease_bottom = min(crop_height, crease_top + aperture_height)
    crease = crease[:crease_bottom - crease_top]
    aperture_mask = np.zeros((crop_height, crop_width), dtype=np.uint8)
    cv2.ellipse(
        aperture_mask,
        (round(center_x), round(center_y)),
        (
            max(1, round(mouth_width * 0.34)),
            max(1, round(aperture_height * 0.55)),
        ),
        0,
        0,
        360,
        220,
        -1,
        cv2.LINE_AA,
    )
    aperture_mask = cv2.GaussianBlur(aperture_mask, (0, 0), 0.65)
    alpha = (
        aperture_mask[crease_top:crease_bottom].astype(np.float32) / 255.0
    )[:, :, None]
    target = opened[crease_top:crease_bottom].astype(np.float32)
    opened[crease_top:crease_bottom] = (
        target * (1.0 - alpha) + crease.astype(np.float32) * alpha
    ).astype(np.uint8)


def _feather_registration(
    opened: np.ndarray,
    center_x: float,
    center_y: float,
) -> None:
    crop_height, crop_width = opened.shape[:2]
    mask = np.zeros((crop_height, crop_width), dtype=np.uint8)
    cv2.ellipse(
        mask,
        (round(center_x), round(center_y)),
        (
            max(2, round(crop_width * 0.47)),
            max(2, round(crop_height * 0.46)),
        ),
        0,
        0,
        360,
        255,
        -1,
        cv2.LINE_AA,
    )
    mask = cv2.GaussianBlur(mask, (0, 0), 1.35)
    opened[:, :, 3] = (
        opened[:, :, 3].astype(np.uint16) * mask.astype(np.uint16) // 255
    ).astype(np.uint8)


def _authority_mouth(view_id: str) -> np.ndarray:
    bounds = MOUTH_BOUNDS.get(view_id)
    if bounds is None:
        return _surface()
    authority = cv2.imread(
        str(AUTHORITY_DIR / f"{view_id}.png"),
        cv2.IMREAD_UNCHANGED,
    )
    if authority is None or authority.shape[2] < EXPECTED_CHANNEL_COUNT:
        raise RuntimeError(f"missing RGBA authority portrait: {view_id}")

    left, top, right, bottom = bounds
    crop_left = max(0, round(left) - MOUTH_PADDING_X)
    crop_top = max(0, round(top) - MOUTH_PADDING_Y)
    crop_right = min(CANVAS_WIDTH, round(right) + MOUTH_PADDING_X)
    crop_bottom = min(CANVAS_HEIGHT, round(bottom) + MOUTH_PADDING_Y)
    crop = authority[crop_top:crop_bottom, crop_left:crop_right].copy()
    center_x = (left + right) * 0.5 - crop_left
    center_y = (top + bottom) * 0.5 - crop_top
    mouth_width = max(2.0, right - left)
    mouth_height = max(2.0, bottom - top)
    opened = _deform_lips(
        crop,
        center_x,
        center_y,
        mouth_width,
        mouth_height,
    )

    # Extend the portrait's own closed-lip crease into the small new aperture.
    # This preserves the exact per-view hue and avoids synthetic black shapes.
    _extend_authority_crease(
        opened,
        crop,
        center_x,
        center_y,
        mouth_width,
        mouth_height,
    )

    # Feather only the outer registration edge. Interior lip pixels stay fully
    # opaque so the original closed mouth cannot show through as a double mouth.
    _feather_registration(opened, center_x, center_y)

    surface = _surface()
    surface[crop_top:crop_bottom, crop_left:crop_right] = opened
    return surface


def rebuild() -> int:
    view_ids = sorted(
        path.name.removesuffix("_lip_upper.png")
        for path in LAYER_DIR.glob("yaw*_lip_upper.png")
    )
    if len(view_ids) != EXPECTED_VIEW_COUNT:
        raise RuntimeError(f"expected 24 PoseAtlas views, found {len(view_ids)}")
    for view_id in view_ids:
        mouth = _authority_mouth(view_id)
        transparent_teeth = _surface()
        if not cv2.imwrite(
            str(LAYER_DIR / f"{view_id}_oral_cavity.png"),
            mouth,
        ):
            raise RuntimeError(f"failed to save mouth for {view_id}")
        if not cv2.imwrite(
            str(LAYER_DIR / f"{view_id}_teeth_tongue.png"),
            transparent_teeth,
        ):
            raise RuntimeError(f"failed to clear procedural teeth for {view_id}")
    return len(view_ids) * 2


if __name__ == "__main__":
    print(f"rebuilt {rebuild()} per-view authority mouth layers")
