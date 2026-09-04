"""以 YuNet 五點與預乘 alpha 將半身圖對位到固定模板。

CLI 保留三個輸入/輸出位置參數；第二個位置不是工作樹檔案，而是交由
``git show <reference-ref>:<template-path>`` 取出的 repo-relative 參考路徑。
"""

from __future__ import annotations

lazy import argparse
lazy import json
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np

lazy from .constants import CANVAS_SIZE, RUNTIME_SIZE
lazy from .image_ops import (
    chroma_key,
    ensure_rgba,
    load_rgba,
    resize_rgba,
    save_png,
    transparent_rgb_zero,
    warp_rgba,
)
lazy from .references import GitReference
lazy from .vision import face_landmarks


def anchors(points: np.ndarray) -> np.ndarray:
    eyes = (points[0] + points[1]) / 2.0
    mouth = (points[3] + points[4]) / 2.0
    return np.stack((eyes, mouth))


def similarity_matrix(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    matrix, _inliers = cv2.estimateAffinePartial2D(
        source.reshape(-1, 1, 2).astype(np.float32),
        target.reshape(-1, 1, 2).astype(np.float32),
        method=cv2.LMEDS,
    )
    if matrix is None:
        raise ValueError("相似變換估計失敗")
    return matrix


def align_rgba(
    generated: np.ndarray,
    template: np.ndarray,
    *,
    model_path: Path,
) -> tuple[np.ndarray, dict[str, object]]:
    """回傳對位圖與可序列化的量測報告。"""

    template = load_rgba_from_array(template)
    keyed = key_file_from_array(generated)
    if template.shape[:2] != (CANVAS_SIZE, CANVAS_SIZE):
        raise ValueError(f"模板必須是 {CANVAS_SIZE}x{CANVAS_SIZE}")
    if keyed.shape[:2] != (CANVAS_SIZE, CANVAS_SIZE):
        keyed = resize_rgba(keyed, (CANVAS_SIZE, CANVAS_SIZE))

    template_points, template_score = face_landmarks(template, model_path)
    generated_points, generated_score = face_landmarks(keyed, model_path)
    matrix = similarity_matrix(anchors(generated_points), anchors(template_points))
    scale = float(np.hypot(matrix[0, 0], matrix[1, 0]))
    aligned = warp_rgba(
        keyed,
        matrix,
        (CANVAS_SIZE, CANVAS_SIZE),
        interpolation=cv2.INTER_LINEAR,
    )
    aligned_points, _aligned_score = face_landmarks(aligned, model_path)
    residual = np.abs(aligned_points - template_points) * (RUNTIME_SIZE / CANVAS_SIZE)
    report: dict[str, object] = {
        "scale": round(scale, 4),
        "rotation_deg": round(
            float(np.degrees(np.arctan2(matrix[1, 0], matrix[0, 0]))), 3
        ),
        "translation_px": [
            round(float(matrix[0, 2]), 1),
            round(float(matrix[1, 2]), 1),
        ],
        "yunet_score": {
            "template": round(template_score, 3),
            "generated": round(generated_score, 3),
        },
        "residual_465px": {
            name: [round(float(value), 2) for value in point]
            for name, point in zip(
                ("eye_left", "eye_right", "nose", "mouth_left", "mouth_right"),
                residual,
                strict=True,
            )
        },
        "opaque_ratio": round(float((aligned[:, :, 3] > 0).mean()), 4),
        "transparent_rgb_zero": bool(np.all(aligned[aligned[:, :, 3] == 0, :3] == 0)),
    }
    return aligned, report


def load_rgba_from_array(image: np.ndarray) -> np.ndarray:
    """將測試或 API 提供的陣列整理成零透明 RGB 的 BGRA。"""
    return transparent_rgb_zero(ensure_rgba(image))


def key_file_from_array(image: np.ndarray) -> np.ndarray:
    return chroma_key(image)


def _run_materialized(
    generated_path: Path,
    template_path: Path,
    output_path: Path,
    *,
    model_path: Path,
    report_path: Path | None = None,
    template_ref: str | None = None,
) -> dict[str, object]:
    generated = load_rgba(generated_path)
    template = load_rgba(template_path)
    aligned, report = align_rgba(generated, template, model_path=model_path)
    report.update({
        "generated": str(generated_path),
        "template": template_ref or str(template_path),
        "output": str(output_path),
    })
    save_png(output_path, aligned)
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def run_from_git_reference(
    generated_path: Path,
    output_path: Path,
    *,
    reference: GitReference,
    model_path: Path,
    report_path: Path | None = None,
) -> dict[str, object]:
    with reference.temporary_file() as template_path:
        return _run_materialized(
            generated_path,
            template_path,
            output_path,
            model_path=model_path,
            report_path=report_path,
            template_ref=f"{reference.ref}:{reference.path}",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("generated", type=Path)
    parser.add_argument(
        "template_path", help="repo-relative git 參考路徑，不是工作樹檔案"
    )
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--repo", type=Path, required=True, help="git repository 根目錄"
    )
    parser.add_argument(
        "--reference-ref", required=True, help="參考圖所在提交、tag 或 ref"
    )
    parser.add_argument("--model", type=Path, required=True, help="YuNet ONNX 模型路徑")
    parser.add_argument("--report", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reference = GitReference(args.repo, args.reference_ref, args.template_path)
    run_from_git_reference(
        args.generated,
        args.output,
        reference=reference,
        model_path=args.model,
        report_path=args.report,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
