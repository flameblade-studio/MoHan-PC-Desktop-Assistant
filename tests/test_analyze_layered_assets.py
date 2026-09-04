from __future__ import annotations

lazy import sys
lazy from pathlib import Path as _BootstrapPath
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[1]))

lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image

lazy from tools.analyze_layered_assets import (
    LAYER_NAMES,
    REFERENCE_LAYER,
    VIEW_IDS,
    analyze,
)


CANVAS_SIZE = (64, 64)
CANVAS_WIDTH, CANVAS_HEIGHT = CANVAS_SIZE
ANOMALY_VIEW_IDS = (
    VIEW_IDS[0],
    VIEW_IDS[1],
    VIEW_IDS[2],
)
CENTRE_VIEW_ID = VIEW_IDS[11]
BODY_BOX = (8, 10, 44, 52)
LAYER_BOX = (18, 16, 40, 32)


def _empty_canvas() -> np.ndarray:
    return np.zeros((CANVAS_HEIGHT, CANVAS_WIDTH, 4), dtype=np.uint8)


def _write_layer(
    path: Path,
    box: tuple[int, int, int, int],
    colour: tuple[int, int, int, int],
) -> None:
    left, top, right, bottom = box
    image = _empty_canvas()
    image[top:bottom, left:right] = colour
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image, mode="RGBA").save(path)


def _build_clean_asset_dir(
    base_dir: Path,
    view_ids: tuple[str, ...] = VIEW_IDS,
) -> None:
    for view_id in view_ids:
        for layer in LAYER_NAMES:
            if layer == REFERENCE_LAYER:
                _write_layer(
                    base_dir / f"{view_id}_{layer}.png",
                    BODY_BOX,
                    (225, 194, 144, 255),
                )
                continue

            if layer == "hair_left":
                colour = (60, 50, 35, 255)
            elif layer == "hair_right":
                colour = (70, 45, 30, 255)
            elif layer == "blush_left":
                colour = (225, 130, 150, 255)
            else:
                colour = (200, 200, 200, 255)

            _write_layer(
                base_dir / f"{view_id}_{layer}.png",
                LAYER_BOX,
                colour,
            )


def _overwrite_layer_box(
    path: Path,
    box: tuple[int, int, int, int],
    colour: tuple[int, int, int, int],
) -> None:
    _write_layer(path, box, colour)


def _poke_pixel(path: Path, position: tuple[int, int], colour: tuple[int, int, int, int]) -> None:
    x, y = position
    image = np.array(Image.open(path).convert("RGBA"))
    image[y, x] = colour
    Image.fromarray(image, mode="RGBA").save(path)


def test_clean_layered_assets_are_reported_as_normal(tmp_path: Path) -> None:
    asset_dir = tmp_path / "clean"
    _build_clean_asset_dir(asset_dir)

    report = analyze(asset_dir)

    assert report["views_found"] == sorted(VIEW_IDS)
    assert report["outliers"] == []
    assert report["outlier_count"] == 0
    assert report["missing_layers"] == {}
    assert report["unparsed_files"] == []


def test_contaminated_layer_causes_detectable_outlier(tmp_path: Path) -> None:
    asset_dir = tmp_path / "contaminated"
    _build_clean_asset_dir(asset_dir)
    contam_view = ANOMALY_VIEW_IDS[1]
    contam_layer = "hair_left"
    contam_path = asset_dir / f"{contam_view}_{contam_layer}.png"
    _poke_pixel(contam_path, (56, 56), (0, 255, 0, 255))

    report = analyze(asset_dir)
    outliers = [
        entry
        for entry in report["outliers"]
        if entry["view_id"] == contam_view and entry["layer"] == contam_layer
    ]

    assert len(outliers) == 1
    assert outliers[0]["jump_pixels"] > report["outlier_threshold_pixels"]


def test_gap_in_layer_coverage_is_flagged_by_continuity(tmp_path: Path) -> None:
    asset_dir = tmp_path / "with_gap"
    _build_clean_asset_dir(asset_dir)
    gap_view = CENTRE_VIEW_ID
    gap_layer = "hair_right"
    gap_path = asset_dir / f"{gap_view}_{gap_layer}.png"
    _overwrite_layer_box(gap_path, (30, 16, 40, 32), (70, 45, 30, 255))

    report = analyze(asset_dir)
    outliers = [
        entry
        for entry in report["outliers"]
        if entry["view_id"] == gap_view and entry["layer"] == gap_layer
    ]

    assert len(outliers) == 1
    assert outliers[0]["jump_pixels"] > report["outlier_threshold_pixels"]


def test_invalid_or_missing_files_are_reported_explicitly(tmp_path: Path) -> None:
    asset_dir = tmp_path / "with_errors"
    _build_clean_asset_dir(asset_dir)
    corrupt_path = asset_dir / f"{VIEW_IDS[0]}_hair_back.png"
    corrupt_path.unlink()
    invalid_path = asset_dir / "not-a-layer.png"
    invalid_path.write_bytes(b"not-an-image")

    report = analyze(asset_dir)

    assert "hair_back" in report["missing_layers"][VIEW_IDS[0]]
    assert invalid_path.name in report["unparsed_files"]


def main() -> int:
    for check in (test_clean_layered_assets_are_reported_as_normal, test_contaminated_layer_causes_detectable_outlier, test_gap_in_layer_coverage_is_flagged_by_continuity, test_invalid_or_missing_files_are_reported_explicitly):
        with TemporaryDirectory(prefix="mohan-analyze-layered-") as scratch:
            check(Path(scratch))
    print("ANALYZE_LAYERED_ASSETS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
