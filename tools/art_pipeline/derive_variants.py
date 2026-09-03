"""只在既定嘴框/眼框內合成半身說話與眨眼變體。"""

from __future__ import annotations

lazy import argparse
lazy from pathlib import Path

lazy import numpy as np

lazy from .constants import (
    BLINK_RECTS,
    CANVAS_SIZE,
    RECT_FEATHER_PIXELS,
    RECT_INSET_PIXELS,
    RUNTIME_SIZE,
)
lazy from .image_ops import load_rgba, resize_rgba, save_png


def rgba(path: Path) -> np.ndarray:
    image = load_rgba(path)
    if image.shape[:2] != (CANVAS_SIZE, CANVAS_SIZE):
        if image.shape[0] != image.shape[1]:
            raise ValueError(f"{path} 不是正方形：{image.shape[:2]}")
        image = resize_rgba(image, (CANVAS_SIZE, CANVAS_SIZE))
    return image.copy()


def rect_1254(x: int, y: int, width: int, height: int) -> tuple[int, int, int, int]:
    """將 465 空間矩形換算為只在內側取樣的 1254 空間矩形。"""

    x0 = int(round(x * (CANVAS_SIZE / RUNTIME_SIZE))) + RECT_INSET_PIXELS
    y0 = int(round(y * (CANVAS_SIZE / RUNTIME_SIZE))) + RECT_INSET_PIXELS
    x1 = int(round((x + width) * (CANVAS_SIZE / RUNTIME_SIZE))) - RECT_INSET_PIXELS
    y1 = int(round((y + height) * (CANVAS_SIZE / RUNTIME_SIZE))) - RECT_INSET_PIXELS
    return x0, y0, x1, y1


def inner_feather_mask(height: int, width: int) -> np.ndarray:
    """矩形內側羽化權重，權重永遠不會寫到矩形外。"""

    yy = np.arange(height, dtype=np.float32)
    xx = np.arange(width, dtype=np.float32)
    feather = float(RECT_FEATHER_PIXELS)
    fy = np.minimum(np.minimum(yy + 1, height - yy), feather) / feather
    fx = np.minimum(np.minimum(xx + 1, width - xx), feather) / feather
    return np.clip(np.outer(fy, fx), 0.0, 1.0)[:, :, None]


def paste_rect(
    base: np.ndarray,
    source: np.ndarray,
    rect465: tuple[int, int, int, int],
) -> np.ndarray:
    """將 source 的指定矩形混入 base；矩形外逐像素沿用 base。"""

    output = base.copy()
    x0, y0, x1, y1 = rect_1254(*rect465)
    if not (0 <= x0 < x1 <= base.shape[1] and 0 <= y0 < y1 <= base.shape[0]):
        raise ValueError(f"矩形超出畫布：{rect465}")
    weight = inner_feather_mask(y1 - y0, x1 - x0)
    base_region = base[y0:y1, x0:x1].astype(np.float32)
    source_region = source[y0:y1, x0:x1].astype(np.float32)
    output[y0:y1, x0:x1] = np.round(
        source_region * weight + base_region * (1.0 - weight)
    ).astype(np.uint8)
    return output


def outside_difference(
    base: np.ndarray,
    variant: np.ndarray,
    rect465: tuple[int, int, int, int],
) -> int:
    x0, y0, x1, y1 = rect_1254(*rect465)
    difference = np.any(base != variant, axis=2)
    difference[y0:y1, x0:x1] = False
    return int(difference.sum())


def outside_difference_many(
    base: np.ndarray,
    variant: np.ndarray,
    rects465: tuple[tuple[int, int, int, int], ...],
) -> int:
    difference = np.any(base != variant, axis=2)
    for rect in rects465:
        x0, y0, x1, y1 = rect_1254(*rect)
        difference[y0:y1, x0:x1] = False
    return int(difference.sum())


def speech_rect(expression: str) -> tuple[int, int, int, int]:
    from domain.companion_animation_contract import EXPRESSION_SPEECH_MOUTH_RECTS

    rect = EXPRESSION_SPEECH_MOUTH_RECTS[expression]
    return rect.x(), rect.y(), rect.width(), rect.height()


def blink_rects(pose: str) -> tuple[tuple[int, int, int, int], ...]:
    try:
        return BLINK_RECTS[pose]
    except KeyError as error:
        raise ValueError(f"未知姿勢：{pose}") from error


def _speech(
    expression_path: Path,
    source_path: Path,
    expression: str,
    output_path: Path,
) -> int:
    base, source = rgba(expression_path), rgba(source_path)
    rect = speech_rect(expression)
    result = paste_rect(base, source, rect)
    outside = outside_difference(base, result, rect)
    save_png(output_path, result)
    print(f"speech {output_path.name}: rect465={rect} outside_diff={outside}")
    return 0 if outside == 0 else 1


def _blink(
    expression_path: Path,
    source_path: Path,
    pose: str,
    output_path: Path,
) -> int:
    base, source = rgba(expression_path), rgba(source_path)
    result = base
    rects = blink_rects(pose)
    for rect in rects:
        result = paste_rect(result, source, rect)
    outside = outside_difference_many(base, result, rects)
    save_png(output_path, result)
    print(f"blink {output_path.name}: outside_diff={outside}")
    return 0 if outside == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    speech_parser = subparsers.add_parser("speech")
    speech_parser.add_argument("expression", type=Path)
    speech_parser.add_argument("mouth_source", type=Path)
    speech_parser.add_argument("expression_name")
    speech_parser.add_argument("output", type=Path)
    blink_parser = subparsers.add_parser("blink")
    blink_parser.add_argument("expression", type=Path)
    blink_parser.add_argument("blink_source", type=Path)
    blink_parser.add_argument("pose", choices=tuple(BLINK_RECTS))
    blink_parser.add_argument("output", type=Path)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("base", type=Path)
    verify_parser.add_argument("variant", type=Path)
    verify_parser.add_argument("rect", type=int, nargs=4, metavar=("X", "Y", "W", "H"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "speech":
        return _speech(
            args.expression, args.mouth_source, args.expression_name, args.output
        )
    if args.mode == "blink":
        return _blink(args.expression, args.blink_source, args.pose, args.output)
    base, variant = rgba(args.base), rgba(args.variant)
    outside = outside_difference(base, variant, tuple(args.rect))
    print(f"outside_diff = {outside}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# Scratchpad-compatible names retained for callers that imported the old helper
# functions directly; the implementation remains in the explicit public names.
_rgba = rgba
_rect_1254 = rect_1254
_inner_feather_mask = inner_feather_mask
verify = outside_difference
_speech_rect = speech_rect
_blink_rects = blink_rects
