"""Create a non-destructive B00 derivative with isolated hand specks repaired."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


SIZE = (1024, 1536)
HAND_ROIS = ((220, 730, 310, 860), (715, 730, 810, 860))


def visible_skin(rgb: np.ndarray) -> np.ndarray:
    red = rgb[:, :, 0].astype(np.int16)
    green = rgb[:, :, 1].astype(np.int16)
    blue = rgb[:, :, 2].astype(np.int16)
    maximum = np.maximum(np.maximum(red, green), blue)
    minimum = np.minimum(np.minimum(red, green), blue)
    return (
        (red > 72)
        & (green > 30)
        & (blue > 18)
        & ((maximum - minimum) > 12)
        & ((red - green) > 7)
        & (red > blue)
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite derivative: {args.output}")

    with Image.open(args.input) as image:
        if image.mode != "RGBA" or image.size != SIZE:
            raise ValueError(f"expected RGBA {SIZE}: {args.input}")
        source = np.asarray(image, dtype=np.uint8).copy()

    foreground = source[:, :, 3] > 0
    skin = visible_skin(source[:, :, :3]) & foreground
    candidate = np.zeros(foreground.shape, dtype=bool)
    for x0, y0, x1, y1 in HAND_ROIS:
        local = skin[y0:y1, x0:x1].astype(np.uint8)
        closed = cv2.morphologyEx(
            local, cv2.MORPH_CLOSE, np.ones((3, 3), dtype=np.uint8)
        )
        candidate[y0:y1, x0:x1] |= (closed > 0) & ~(local > 0)
    maximum = source[:, :, :3].max(axis=2)
    repair = candidate & (maximum < 90)
    repair_count = int(np.count_nonzero(repair))
    if repair_count != 2:
        raise RuntimeError(f"expected two isolated B00 hand specks, got {repair_count}")

    bgr = cv2.cvtColor(source[:, :, :3], cv2.COLOR_RGB2BGR)
    repaired_rgb = cv2.cvtColor(
        cv2.inpaint(bgr, repair.astype(np.uint8) * 255, 2, cv2.INPAINT_TELEA),
        cv2.COLOR_BGR2RGB,
    )
    output = source.copy()
    output[repair, :3] = repaired_rgb[repair]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(output, "RGBA").save(args.output)

    alpha_diff = int(np.count_nonzero(source[:, :, 3] != output[:, :, 3]))
    outside_diff = int(
        np.count_nonzero(np.any(source[:, :, :3] != output[:, :, :3], axis=2) & ~repair)
    )
    black_after = int(np.count_nonzero(repair & (output[:, :, :3].max(axis=2) < 90)))
    if alpha_diff or outside_diff or black_after:
        raise RuntimeError(
            f"repair invariant failed: alpha={alpha_diff} outside={outside_diff} "
            f"black_after={black_after}"
        )
    print(
        "PASS_B00_HAND_DECONTAMINATION "
        f"repaired_pixels={repair_count} black_before=2 black_after=0 "
        f"alpha_diff=0 rgb_outside_diff=0 sha256={sha256(args.output)} "
        f"output={args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
