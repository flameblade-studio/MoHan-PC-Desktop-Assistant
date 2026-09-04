from __future__ import annotations

lazy import json
lazy import subprocess
lazy import sys
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "build_v120_physics_layers.py"

POSES = (
    ("", "idle.png"),
    ("_lean", "idle_lean.png"),
    ("_front", "idle_front.png"),
)
LAYERS = ("sleeve_left", "sleeve_right", "hair_left", "hair_right", "ornament")
CANVAS = (32, 24)
KNOWN_RECT = (8, 6, 24, 18)


def _rgba_alpha(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)[:, :, 3]


def _expected_output_paths(output_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for suffix, _ in POSES:
        for layer in LAYERS:
            paths.append(output_dir / f"v120_{layer}{suffix}.png")
    return paths


def _write_rgba_source(path: Path, visible: tuple[int, int, int, int] | None) -> None:
    width, height = CANVAS
    x0, y0, x1, y1 = visible if visible is not None else (0, 0, 0, 0)
    canvas = np.zeros((height, width, 4), dtype=np.uint8)
    if visible is not None and x0 < x1 and y0 < y1:
        canvas[y0:y1, x0:x1, :3] = (120, 70, 30)
        canvas[y0:y1, x0:x1, 3] = 255
    Image.fromarray(canvas, "RGBA").save(path, optimize=True)


def _write_alpha_mask(path: Path, opaque: tuple[int, int, int, int] | None) -> None:
    width, height = CANVAS
    x0, y0, x1, y1 = opaque if opaque is not None else (0, 0, 0, 0)
    mask = np.zeros((height, width, 4), dtype=np.uint8)
    if opaque is not None and x0 < x1 and y0 < y1:
        mask[y0:y1, x0:x1, :3] = (255, 255, 255)
        mask[y0:y1, x0:x1, 3] = 255
    Image.fromarray(mask, "RGBA").save(path, optimize=True)


def _build_assets(output_dir: Path, layer_rects: dict[str, tuple[int, int, int, int] | None]) -> None:
    for _, source_name in POSES:
        _write_rgba_source(output_dir / source_name, KNOWN_RECT)
    for suffix, _ in POSES:
        for layer in LAYERS:
            _write_alpha_mask(
                output_dir / f"physics_{layer}{suffix}.png",
                layer_rects.get(layer),
            )


def _run_builder(output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(output_dir)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _within_rect(alpha: np.ndarray, rect: tuple[int, int, int, int]) -> bool:
    x0, y0, x1, y1 = rect
    ys, xs = np.where(alpha > 0)
    if len(xs) == 0:
        return False
    return (
        bool((xs >= x0).all())
        and bool((xs < x1).all())
        and bool((ys >= y0).all())
        and bool((ys < y1).all())
    )


def _read_report_files(path: Path) -> list[str] | None:
    report = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(report, dict):
        files = report.get("files")
        if isinstance(files, list) and all(isinstance(item, str) for item in files):
            return sorted(files)
        if isinstance(files, dict):
            values = sorted({k for k in files if isinstance(k, str)})
            if values:
                return values
        poses = report.get("poses")
        if isinstance(poses, list):
            names: list[str] = []
            for item in poses:
                if not isinstance(item, dict):
                    continue
                for name in item.get("files", {}):
                    if isinstance(name, str):
                        names.append(name)
            if names:
                return sorted(set(names))
    return None


def test_legal_empty_layer_still_outputs_full_transparent_layer(tmp_path: Path) -> None:
    _build_assets(tmp_path, {"hair_left": None, "ornament": KNOWN_RECT, "sleeve_left": KNOWN_RECT, "sleeve_right": KNOWN_RECT, "hair_right": KNOWN_RECT})
    completed = _run_builder(tmp_path)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    for path in _expected_output_paths(tmp_path):
        assert path.is_file(), path
        alpha = _rgba_alpha(path)
        if path.name.startswith("v120_hair_left"):
            assert alpha.sum() == 0, path
        else:
            assert alpha.sum() > 0, path


def test_non_empty_layer_pixels_stay_in_source_bbox(tmp_path: Path) -> None:
    target = "hair_left"
    _build_assets(tmp_path, {layer: (KNOWN_RECT if layer == target else None) for layer in LAYERS})
    completed = _run_builder(tmp_path)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    for suffix, _ in POSES:
        output = _rgba_alpha(tmp_path / f"v120_{target}{suffix}.png")
        assert output.sum() > 0
        assert _within_rect(output, KNOWN_RECT), tmp_path / f"v120_{target}{suffix}.png"
        x0, y0, x1, y1 = KNOWN_RECT
        outside = np.ones_like(output, dtype=bool)
        outside[y0:y1, x0:x1] = False
        assert int((output[outside] != 0).sum()) == 0


def test_missing_physics_layer_file_causes_failure_with_filename(tmp_path: Path) -> None:
    _build_assets(tmp_path, {layer: KNOWN_RECT for layer in LAYERS})
    missing = tmp_path / "physics_hair_left.png"
    missing.unlink()
    completed = _run_builder(tmp_path)
    assert completed.returncode != 0, completed.returncode
    output = (completed.stdout + completed.stderr).replace("\r", "")
    assert str(missing) in output or missing.name in output


def test_report_or_manifest_if_present_matches_outputs(tmp_path: Path) -> None:
    _build_assets(tmp_path, {layer: KNOWN_RECT for layer in LAYERS})
    completed = _run_builder(tmp_path)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    report_paths = sorted(
        set(tmp_path.glob("*manifest*.json")) | set(tmp_path.glob("*report*.json"))
    )
    if not report_paths:
        return
    expected = sorted(path.name for path in _expected_output_paths(tmp_path))
    for report_path in report_paths:
        report_files = _read_report_files(report_path)
        assert report_files is not None, report_path
        assert sorted(set(report_files)) == expected, report_path
