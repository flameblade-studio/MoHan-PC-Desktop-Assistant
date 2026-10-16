"""Regression checks for pixel ownership and safe single-source review export."""

from __future__ import annotations

lazy import hashlib
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
lazy from tools.art_pipeline import partition_layers
lazy from tools.art_pipeline.partition_layers import (
    OWNER_PALETTE,
    export_review,
    load_review_source,
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


def test_native_alpha_export_preserves_colored_hair_and_soft_edges(tmp_path: Path) -> None:
    source = _canvas()
    source[4:20, 4:20] = (220, 20, 210, HALF_ALPHA)
    semantic = _canvas()
    semantic[4:20, 4:20, :3] = OWNER_PALETTE[HAIR]
    source_path, semantic_path = tmp_path / "native.png", tmp_path / "semantic.png"
    save_png(source_path, source)
    save_png(semantic_path, semantic)
    # This deliberately magenta foreground would disappear in the legacy keyer.
    assert not key_file(source_path)[:, :, 3].any()
    output = tmp_path / "native-review"
    source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    report = export_review(source_path, semantic_path, output, source_mode="native-alpha",
                           expected_source_sha256=source_digest)
    assert np.array_equal(load_rgba(output / "reconstruction.png"), source)
    assert np.array_equal(load_rgba(output / "hair.png"), source)
    assert report["chroma_key_applied"] is False
    assert report["expected_source_sha256"] == source_digest


def test_source_replaced_after_review_is_rejected_before_output(tmp_path: Path) -> None:
    source_path = tmp_path / "candidate.png"
    source_path.write_bytes(b"reviewed candidate")
    reviewed_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    source_path.write_bytes(b"replacement candidate")
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="differs from the reviewed candidate"):
        export_review(source_path, tmp_path / "unused.png", output,
                      expected_source_sha256=reviewed_digest)
    assert not output.exists()


@pytest.mark.parametrize("changed_input", ["source", "semantic"])
def test_input_changed_during_partition_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed_input: str,
) -> None:
    source = _canvas()
    source[4:20, 4:20] = (32, 62, 94, OPAQUE)
    semantic = _canvas()
    semantic[4:20, 4:20, :3] = OWNER_PALETTE[GARMENT]
    paths = {"source": tmp_path / "source.png", "semantic": tmp_path / "semantic.png"}
    save_png(paths["source"], source)
    save_png(paths["semantic"], semantic)
    original_reconstruct = partition_layers.reconstruct

    def replace_input_after_decode(layers: dict[str, np.ndarray]) -> np.ndarray:
        result = original_reconstruct(layers)
        paths[changed_input].write_bytes(b"concurrently replaced")
        return result

    monkeypatch.setattr(partition_layers, "reconstruct", replace_input_after_decode)
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="changed during processing"):
        export_review(paths["source"], paths["semantic"], output, source_mode="native-alpha")
    assert not output.exists()


def test_native_alpha_rejects_rgb_checkerboard_before_writing(tmp_path: Path) -> None:
    checker = np.indices((SIZE, SIZE)).sum(axis=0) % 2 * 80 + 160
    source = np.repeat(checker[:, :, None], 3, axis=2).astype(np.uint8)
    path = tmp_path / "checkerboard.png"
    save_png(path, source)
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="requires 8-bit BGRA with explicit transparency"):
        export_review(path, tmp_path / "unused.png", output, source_mode="native-alpha")
    assert not output.exists()


@pytest.mark.parametrize("alpha", [0, OPAQUE])
def test_native_alpha_rejects_missing_foreground_or_background(tmp_path: Path, alpha: int) -> None:
    source = _canvas()
    source[:, :, 3] = alpha
    path = tmp_path / "invalid.png"
    save_png(path, source)
    with pytest.raises(ValueError, match="visible foreground and transparent background"):
        load_review_source(path, "native-alpha")


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
