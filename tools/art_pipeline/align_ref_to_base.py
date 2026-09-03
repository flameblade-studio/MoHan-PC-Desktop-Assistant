"""先把 git 鎖定的樣式參考圖對齊到 base 的臉中心與腳底。"""

from __future__ import annotations

lazy import argparse
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np

lazy from .image_ops import (
    chroma_key,
    flatten_on_magenta,
    load_image,
    resize_rgba,
    save_png,
    transparent_rgb_zero,
    warp_rgba,
)
lazy from .constants import (
    ANCHOR_SPAN_MIN_PIXELS,
    BGR_CHANNELS,
    HEAD_ANCHOR_SCAN_ROWS,
    IMAGE_DIMENSIONS,
)
lazy from .references import GitReference
lazy from .vision import face_box


def load_for_alignment(path: Path) -> np.ndarray:
    source = load_image(path)
    if source.ndim == IMAGE_DIMENSIONS and source.shape[2] == BGR_CHANNELS:
        return chroma_key(source)
    return transparent_rgb_zero(source)


def face_center(image: np.ndarray, model_path: Path) -> tuple[float, float] | None:
    box = face_box(image, model_path)
    if box is None:
        return None
    x, y, width, height = box
    return x + width / 2.0, y + height / 2.0


def head_anchor(image: np.ndarray) -> tuple[float, float]:
    """無臉視角使用最上緣 12 px 的剪影水平中心與頭頂。"""

    alpha = image[:, :, 3] > 0
    rows = np.where(alpha.any(axis=1))[0]
    if rows.size == 0:
        raise ValueError("影像沒有可用剪影")
    top = int(rows.min())
    columns = np.where(alpha[top : top + HEAD_ANCHOR_SCAN_ROWS].any(axis=0))[0]
    if columns.size == 0:
        raise ValueError("影像頭頂沒有可用剪影")
    return float((columns.min() + columns.max()) / 2.0), float(top)


def bottom(image: np.ndarray) -> float:
    rows = np.where((image[:, :, 3] > 0).any(axis=1))[0]
    if rows.size == 0:
        raise ValueError("影像沒有可用剪影")
    return float(rows.max())


def align_reference(
    base: np.ndarray,
    reference: np.ndarray,
    *,
    model_path: Path,
) -> tuple[np.ndarray, dict[str, object]]:
    base = transparent_rgb_zero(base)
    reference = transparent_rgb_zero(reference)
    if reference.shape[:2] != base.shape[:2]:
        reference = resize_rgba(reference, (base.shape[1], base.shape[0]))
    base_anchor = face_center(base, model_path)
    reference_anchor = face_center(reference, model_path)
    mode = "face"
    if base_anchor is None or reference_anchor is None:
        base_anchor = head_anchor(base)
        reference_anchor = head_anchor(reference)
        mode = "head-top"
    base_x, base_y = base_anchor
    reference_x, reference_y = reference_anchor
    base_bottom = bottom(base)
    reference_bottom = bottom(reference)
    scale = (base_bottom - base_y) / max(
        reference_bottom - reference_y, ANCHOR_SPAN_MIN_PIXELS
    )
    matrix = np.array(
        [
            [scale, 0.0, base_x - scale * reference_x],
            [0.0, scale, base_y - scale * reference_y],
        ],
        dtype=np.float32,
    )
    warped = warp_rgba(
        reference,
        matrix,
        (base.shape[1], base.shape[0]),
        interpolation=cv2.INTER_LANCZOS4,
    )
    result = flatten_on_magenta(warped)
    report = {
        "mode": mode,
        "scale": round(float(scale), 4),
        "base_anchor": [round(base_x, 1), round(base_y, 1)],
        "base_bottom": round(base_bottom, 1),
        "warped_bottom": round(bottom(warped), 1),
    }
    return result, report


def _run_materialized(
    base_path: Path,
    reference_path: Path,
    output_path: Path,
    *,
    model_path: Path,
    reference_name: str,
) -> dict[str, object]:
    result, report = align_reference(
        load_for_alignment(base_path),
        load_for_alignment(reference_path),
        model_path=model_path,
    )
    report.update({
        "base": str(base_path),
        "reference": reference_name,
        "output": str(output_path),
    })
    save_png(output_path, result)
    print(" ".join(f"{key}={value}" for key, value in report.items()))
    return report


def run_from_git_reference(
    base_path: Path,
    output_path: Path,
    *,
    reference: GitReference,
    model_path: Path,
) -> dict[str, object]:
    with reference.temporary_file() as reference_path:
        return _run_materialized(
            base_path,
            reference_path,
            output_path,
            model_path=model_path,
            reference_name=f"{reference.ref}:{reference.path}",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument(
        "reference_path", help="repo-relative git 參考路徑，不是工作樹檔案"
    )
    parser.add_argument("output", type=Path)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--reference-ref", required=True)
    parser.add_argument("--model", type=Path, required=True)
    args = parser.parse_args(argv)
    run_from_git_reference(
        args.base,
        args.output,
        reference=GitReference(args.repo, args.reference_ref, args.reference_path),
        model_path=args.model,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
