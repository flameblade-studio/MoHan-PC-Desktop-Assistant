"""Tests for `tools.art_pipeline.qc_drift`."""

from __future__ import annotations

lazy import numpy as np
lazy from pathlib import Path

lazy from tools.art_pipeline.image_ops import save_png
lazy from tools.art_pipeline import qc_drift


def _make_canvas(size: tuple[int, int] = (120, 120), color: tuple[int, int, int] = (20, 20, 20)) -> np.ndarray:
    image = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    image[:, :] = color
    return image


def _face_slice(shape: tuple[int, int], face_box: tuple[float, float, float, float]) -> tuple[slice, slice]:
    width, height = shape
    top_ratio, bottom_ratio, left_ratio, right_ratio = face_box
    y0 = int(height * top_ratio)
    y1 = int(height * bottom_ratio)
    x0 = int(width * left_ratio)
    x1 = int(width * right_ratio)
    return slice(y0, y1), slice(x0, x1)


def test_qc_drift_passes_when_only_face_region_changes(tmp_path: Path) -> None:
    base_pattern = tmp_path / "{view}-base.png"
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    view = "yaw+000"
    expr = "happy"
    faces = _face_slice((120, 120), qc_drift.DEFAULT_FACE_BOX)
    for current_view in (view,):
        save_png(base_pattern.with_name(base_pattern.name.format(view=current_view)), _make_canvas())
    output = _make_canvas()
    output[faces[0], faces[1]] = (255, 0, 255)
    save_png(
        output_dir / f"bodyexpr_{view}_{expr}.png",
        output,
    )

    assert (
        qc_drift.main(
            [
                str(base_pattern),
                str(output_dir),
                "--views",
                view,
                "--expressions",
                expr,
            ]
        )
        == 0
    )


def test_qc_drift_fails_when_outside_area_changes(tmp_path: Path) -> None:
    base_pattern = tmp_path / "{view}-base.png"
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    view = "yaw+000"
    expr = "happy"
    save_png(base_pattern.with_name(base_pattern.name.format(view=view)), _make_canvas())

    output = _make_canvas()
    faces = _face_slice((120, 120), qc_drift.DEFAULT_FACE_BOX)
    output[:25, :, :] = (255, 255, 255)
    output[faces[0], faces[1], :] = (20, 20, 20)
    save_png(output_dir / f"bodyexpr_{view}_{expr}.png", output)

    assert (
        qc_drift.main(
            [
                str(base_pattern),
                str(output_dir),
                "--views",
                view,
                "--expressions",
                expr,
            ]
        )
        == 1
    )


def test_qc_drift_reports_missing_output(tmp_path: Path, capsys) -> None:
    base_pattern = tmp_path / "{view}-base.png"
    view = "yaw+000"
    expr = "happy"
    save_png(base_pattern.with_name(base_pattern.name.format(view=view)), _make_canvas())
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    code = qc_drift.main(
        [
            str(base_pattern),
            str(output_dir),
            "--views",
            view,
            "--expressions",
            expr,
        ]
    )
    captured = capsys.readouterr()
    assert code == qc_drift.EXIT_INVALID_INPUT
    assert "missing output image" in captured.err
