"""從已對齊的洋紅參考圖切出衣身、髮飾與臉部局部。"""

from __future__ import annotations

lazy import argparse
lazy from pathlib import Path

lazy import numpy as np

lazy from .constants import (
    BGR_CHANNELS,
    HEAD_REGION_BOTTOM_FACE_FACTOR,
    IMAGE_DIMENSIONS,
    MAGENTA_DETECTION_GREEN_MAX,
    MAGENTA_DETECTION_RED_BLUE_MIN,
    REF_FACE_BOTTOM_FACTOR,
    REF_FACE_LEFT_FACTOR,
    REF_FACE_RIGHT_FACTOR,
    REF_FACE_TOP_FACTOR,
    REF_HEAD_BOTTOM_FACE_FACTOR,
    REF_HEAD_LEFT_FACE_FACTOR,
    REF_HEAD_RIGHT_FACE_FACTOR,
    REF_HEAD_TOP_FACE_FACTOR,
    SILHOUETTE_BODY_START_RATIO,
    SILHOUETTE_HEAD_HEIGHT_RATIO,
    SILHOUETTE_HEAD_LEFT_MULTIPLIER,
    SILHOUETTE_HEAD_RIGHT_MULTIPLIER,
    SILHOUETTE_HEAD_Y_RATIO,
)
lazy from .image_ops import ensure_rgba, load_image, save_png
lazy from .vision import face_box


def silhouette_box(bgr: np.ndarray) -> tuple[int, int, int, int]:
    mask = ~(
        (bgr[:, :, 2] > MAGENTA_DETECTION_RED_BLUE_MIN)
        & (bgr[:, :, 1] < MAGENTA_DETECTION_GREEN_MAX)
        & (bgr[:, :, 0] > MAGENTA_DETECTION_RED_BLUE_MIN)
    )
    ys, xs = np.where(mask)
    if xs.size == 0:
        raise ValueError("參考圖沒有非洋紅剪影")
    return (
        int(xs.min()),
        int(ys.min()),
        int(xs.max() - xs.min()),
        int(ys.max() - ys.min()),
    )


def crop_reference(
    reference: np.ndarray,
    prefix: Path,
    *,
    model_path: Path,
) -> dict[str, object]:
    if reference.ndim != IMAGE_DIMENSIONS or reference.shape[2] != BGR_CHANNELS:
        raise ValueError("參考圖必須是 BGR")
    height, width = reference.shape[:2]
    box = face_box(ensure_rgba(reference), model_path)
    if box is None:
        sx, sy, sw, sh = silhouette_box(reference)
        head_height = int(sh * SILHOUETTE_HEAD_HEIGHT_RATIO)
        x = sx + sw // 2 - head_height // 2
        y = sy + int(head_height * SILHOUETTE_HEAD_Y_RATIO)
        body_start = sy + int(sh * SILHOUETTE_BODY_START_RATIO)
        save_png(
            prefix.with_name(prefix.name + ".garment.png"),
            reference[body_start:height, :].copy(),
        )
        headwear = reference[
            sy:body_start,
            max(0, x - int(SILHOUETTE_HEAD_LEFT_MULTIPLIER * head_height)) : min(
                width, x + int(SILHOUETTE_HEAD_RIGHT_MULTIPLIER * head_height)
            ),
        ]
        save_png(prefix.with_name(prefix.name + ".headwear.png"), headwear.copy())
        return {
            "mode": "silhouette",
            "silhouette": [sx, sy, sw, sh],
            "garment_rows": [body_start, height],
            "face_written": False,
        }

    x, y, face_width, face_height = (int(value) for value in box)
    chin = min(height, y + int(face_height * HEAD_REGION_BOTTOM_FACE_FACTOR))
    save_png(
        prefix.with_name(prefix.name + ".garment.png"), reference[chin:height, :].copy()
    )
    top = max(0, y - int(face_height * REF_HEAD_TOP_FACE_FACTOR))
    headwear = reference[
        top : y + int(face_height * REF_HEAD_BOTTOM_FACE_FACTOR),
        max(0, x - int(face_width * REF_HEAD_LEFT_FACE_FACTOR)) : min(
            width, x + int(face_width * REF_HEAD_RIGHT_FACE_FACTOR)
        ),
    ]
    save_png(prefix.with_name(prefix.name + ".headwear.png"), headwear.copy())
    face = reference[
        max(0, y - int(face_height * REF_FACE_TOP_FACTOR)) : min(
            height, y + int(face_height * REF_FACE_BOTTOM_FACTOR)
        ),
        max(0, x - int(face_width * REF_FACE_LEFT_FACTOR)) : min(
            width, x + int(face_width * REF_FACE_RIGHT_FACTOR)
        ),
    ]
    save_png(prefix.with_name(prefix.name + ".face.png"), face.copy())
    return {
        "mode": "face",
        "face_box": [x, y, face_width, face_height],
        "garment_rows": [chin, height],
        "headwear_rows": [
            top,
            y + int(face_height * REF_HEAD_BOTTOM_FACE_FACTOR),
        ],
        "face_written": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("output_prefix", type=Path)
    parser.add_argument("--model", type=Path, required=True)
    args = parser.parse_args(argv)
    report = crop_reference(
        load_image(args.reference, unchanged=False),
        args.output_prefix,
        model_path=args.model,
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
