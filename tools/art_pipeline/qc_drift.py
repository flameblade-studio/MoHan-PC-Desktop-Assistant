"""Output drift checker for face-only edits.

The script compares generated outputs against a base per view/expression pair and
reports drift percentages inside and outside a face box.
"""

from __future__ import annotations

lazy import argparse
lazy import sys
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np

lazy from .image_ops import load_bgr
lazy from .constants import BGR_CHANNELS


DEFAULT_VIEWS = (
    "yaw-045",
    "yaw-015",
    "yaw+000",
    "yaw+015",
    "yaw+045",
)
DEFAULT_EXPRESSIONS = (
    "gentle_smile",
    "happy",
    "proud",
    "shy_cute",
    "determined",
    "thinking",
    "worried",
    "tired",
)
# 1.5% 是實測 39 張樣本的散布上緣。
DEFAULT_OUTSIDE_THRESHOLD = 1.5
DEFAULT_FACE_BOX = (0.06, 0.24, 0.30, 0.70)
DEFAULT_PIXEL_DIFFERENCE = 18
EXIT_SUCCESS = 0
EXIT_DRIFT_FOUND = 1
EXIT_INVALID_INPUT = 2


def _face_box_coordinates(
    shape: tuple[int, int],
    face_box: tuple[float, float, float, float],
) -> tuple[int, int, int, int]:
    height, width = shape
    top_ratio, bottom_ratio, left_ratio, right_ratio = face_box
    for value in face_box:
        if not 0.0 <= value <= 1.0:
            raise ValueError("face_box values must be in [0, 1]")
    y0 = int(height * top_ratio)
    y1 = int(height * bottom_ratio)
    x0 = int(width * left_ratio)
    x1 = int(width * right_ratio)
    if y0 >= y1 or x0 >= x1:
        raise ValueError("face_box range is invalid for image shape")
    if y1 > height:
        y1 = height
    if x1 > width:
        x1 = width
    return y0, y1, x0, x1


def _render_base_path(pattern: Path, view: str) -> Path:
    try:
        return Path(str(pattern).format(view=view))
    except KeyError as error:
        raise ValueError(
            "base template must include a {view} placeholder"
        ) from error


def compare_images(
    base_path: Path,
    output_path: Path,
    *,
    face_box: tuple[float, float, float, float] = DEFAULT_FACE_BOX,
    pixel_threshold: int = DEFAULT_PIXEL_DIFFERENCE,
) -> tuple[float, float]:
    base = load_bgr(base_path)
    candidate = load_bgr(output_path)
    if candidate.shape[:2] != base.shape[:2]:
        candidate = cv2.resize(
            candidate,
            (base.shape[1], base.shape[0]),
            interpolation=cv2.INTER_AREA,
        )
    if base.shape[2] != BGR_CHANNELS or candidate.shape[2] != BGR_CHANNELS:
        raise ValueError("input images must contain 3 BGR channels")
    y0, y1, x0, x1 = _face_box_coordinates(base.shape[:2], face_box)
    diff = (
        np.abs(candidate.astype(np.int16) - base.astype(np.int16)).max(axis=2)
        > pixel_threshold
    )
    outside = diff.copy()
    outside[y0:y1, x0:x1] = False
    inside = diff[y0:y1, x0:x1]
    return float(outside.mean()) * 100.0, float(inside.mean()) * 100.0


def run_check(
    base_pattern: Path,
    output_directory: Path,
    *,
    views: tuple[str, ...],
    expressions: tuple[str, ...],
    face_box: tuple[float, float, float, float],
    outside_threshold: float,
    pixel_threshold: int,
) -> tuple[int, list[str]]:
    bad: list[str] = []
    for view in views:
        base_path = _render_base_path(base_pattern, view)
        if not base_path.is_file():
            raise FileNotFoundError(f"missing base image: {base_path}")
        for expr in expressions:
            output_path = output_directory / f"bodyexpr_{view}_{expr}.png"
            if not output_path.is_file():
                raise FileNotFoundError(f"missing output image: {output_path}")
            outside, inside = compare_images(
                base_path,
                output_path,
                face_box=face_box,
                pixel_threshold=pixel_threshold,
            )
            print(
                f"{view:8s} {expr:18s} outside={outside:5.2f}% inside={inside:5.2f}%"
            )
            if outside > outside_threshold:
                bad.append(f"{view} {expr}: outside drift {outside:.2f}%")
    print()
    print(f"bad={bad}" if bad else "good")
    return (EXIT_DRIFT_FOUND if bad else EXIT_SUCCESS), bad


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path, help="Base template path, supports {view}")
    parser.add_argument(
        "output",
        type=Path,
        help="Directory containing bodyexpr_{view}_{expr}.png",
    )
    parser.add_argument(
        "--views",
        nargs="+",
        default=DEFAULT_VIEWS,
        help="View names to check",
    )
    parser.add_argument(
        "--expressions",
        nargs="+",
        default=DEFAULT_EXPRESSIONS,
        help="Expression names to check",
    )
    parser.add_argument(
        "--face-box",
        nargs=4,
        type=float,
        default=DEFAULT_FACE_BOX,
        metavar=("TOP", "BOTTOM", "LEFT", "RIGHT"),
        help="Face box ratio [top bottom left right] in [0, 1]",
    )
    parser.add_argument(
        "--outside-threshold",
        type=float,
        default=DEFAULT_OUTSIDE_THRESHOLD,
        help="Outside box drift percentage limit",
    )
    parser.add_argument(
        "--pixel-threshold",
        type=int,
        default=DEFAULT_PIXEL_DIFFERENCE,
        help="Per-channel difference threshold for drift",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        returncode, _ = run_check(
            args.base,
            args.output,
            views=tuple(args.views),
            expressions=tuple(args.expressions),
            face_box=tuple(args.face_box),
            outside_threshold=args.outside_threshold,
            pixel_threshold=args.pixel_threshold,
        )
    except (FileNotFoundError, ValueError, OSError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return EXIT_INVALID_INPUT
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
