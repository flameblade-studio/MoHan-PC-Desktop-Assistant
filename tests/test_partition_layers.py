"""Regression checks for pixel ownership and safe single-source review export."""

from __future__ import annotations

lazy import json
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy import numpy as np
lazy import pytest

lazy from tools.art_pipeline.image_ops import key_file, load_rgba, save_png
lazy from tools.art_pipeline.partition_layers import (
    OWNER_PALETTE,
    export_review,
    ownership_map,
    partition_rgba,
    reconstruct,
)

SIZE = 24
CHANNELS = 4
OPAQUE = 255
HALF_ALPHA = 127
HAIR = 1
HEADWEAR = 2
GARMENT = 4


def _canvas() -> np.ndarray:
    return np.zeros((SIZE, SIZE, CHANNELS), dtype=np.uint8)


def test_partition_preserves_partial_alpha_and_discards_invisible_color() -> None:
    source = _canvas()
    source[4:12, 4:12] = (23, 42, 71, HALF_ALPHA)
    source[12:20, 4:12] = (88, 132, 189, OPAQUE)
    source[0, 0] = (250, 0, 250, 0)
    owners = np.zeros(source.shape[:2], dtype=np.uint8)
    owners[4:12, 4:12] = HAIR
    owners[12:20, 4:12] = GARMENT
    layers = partition_rgba(source, owners)
    combined = reconstruct(layers)
    expected = source.copy()
    expected[0, 0] = 0
    assert np.array_equal(combined, expected)
    assert int(combined[4, 4, 3]) == HALF_ALPHA
    assert not np.any(layers["headwear"])
    assert tuple(source[0, 0]) == (250, 0, 250, 0)


def test_mixed_red_green_boundary_never_becomes_garment() -> None:
    source = _canvas()
    source[:, :] = (20, 30, 40, OPAQUE)
    semantic = _canvas()
    semantic[:, :10, :3] = OWNER_PALETTE[HAIR]
    semantic[:, 14:, :3] = OWNER_PALETTE[HEADWEAR]
    semantic[:, 10:14, :3] = (0, 127, 127)
    owners, _ = ownership_map(source, semantic)
    assert set(np.unique(owners)) == {HAIR, HEADWEAR}


def test_dark_yellow_edge_inherits_garment_instead_of_hair() -> None:
    source = _canvas()
    source[4:20, 4:20] = (100, 110, 130, OPAQUE)
    semantic = _canvas()
    semantic[4:20, 4:20, :3] = OWNER_PALETTE[GARMENT]
    semantic[4:20, 4, :3] = (0, 128, 128)
    owners, _ = ownership_map(source, semantic)
    assert np.all(owners[4:20, 4:20] == GARMENT)


def test_missing_large_foreground_is_rejected() -> None:
    source = _canvas()
    source[4:20, 4:20] = (20, 30, 40, OPAQUE)
    semantic = _canvas()
    semantic[4:8, 4:8, :3] = OWNER_PALETTE[HAIR]
    with pytest.raises(ValueError, match="edge band"):
        ownership_map(source, semantic)
    with pytest.raises(ValueError, match="foreground owners"):
        ownership_map(source, _canvas())


def test_invalid_ownership_and_overlapping_layers_are_rejected() -> None:
    source = _canvas()
    source[5:10, 5:10] = (10, 20, 30, OPAQUE)
    owners = np.zeros(source.shape[:2], dtype=np.uint8)
    with pytest.raises(ValueError, match="valid owner"):
        partition_rgba(source, owners)
    with pytest.raises(ValueError, match="dimensions"):
        ownership_map(source, source[:8])
    with pytest.raises(ValueError, match="overlap"):
        reconstruct({"first": source, "second": source})


def test_export_records_source_and_refuses_existing_output(tmp_path: Path) -> None:
    source = _canvas()
    source[4:20, 4:20] = (32, 62, 94, OPAQUE)
    semantic = _canvas()
    semantic[4:20, 4:20, :3] = OWNER_PALETTE[GARMENT]
    source_path, semantic_path = tmp_path / "source.png", tmp_path / "semantic.png"
    save_png(source_path, source)
    save_png(semantic_path, semantic)
    output = tmp_path / "review"
    report = export_review(source_path, semantic_path, output)
    assert report["reconstruction_rgba_changed_pixels"] == 0
    assert np.array_equal(load_rgba(output / "reconstruction.png"), key_file(source_path))
    persisted = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert persisted == report
    before = {path.name: path.read_bytes() for path in output.iterdir()}
    with pytest.raises(FileExistsError):
        export_review(tmp_path / "missing.png", semantic_path, output)
    assert before == {path.name: path.read_bytes() for path in output.iterdir()}


def main() -> int:
    test_partition_preserves_partial_alpha_and_discards_invisible_color()
    test_mixed_red_green_boundary_never_becomes_garment()
    test_dark_yellow_edge_inherits_garment_instead_of_hair()
    test_missing_large_foreground_is_rejected()
    test_invalid_ownership_and_overlapping_layers_are_rejected()
    with TemporaryDirectory() as directory:
        test_export_records_source_and_refuses_existing_output(Path(directory))
    print("PARTITION_LAYERS_TESTS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
