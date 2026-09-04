"""分層美術產線的離線回歸測試。"""

from __future__ import annotations

lazy import subprocess
lazy from pathlib import Path

lazy import numpy as np

lazy from tools.art_pipeline.constants import (
    CANVAS_SIZE,
    CHROMA_SPILL_THRESHOLD,
    MAGENTA_BGR,
)
lazy from tools.art_pipeline import align_to_template as align_module
lazy from tools.art_pipeline.derive_variants import outside_difference, paste_rect
lazy from tools.art_pipeline import extract_layers as extract_module
lazy from tools.art_pipeline.extract_layers import diff_mask, makeup_slot_masks
lazy from tools.art_pipeline.image_ops import chroma_key, load_rgba, save_png, warp_rgba
lazy from tools.art_pipeline.references import GitReference


def test_premultiplied_alignment_zeroes_transparent_rgb() -> None:
    source = np.zeros((32, 32, 4), dtype=np.uint8)
    source[:, :, :3] = (255, 0, 255)
    source[8:24, 8:24, :3] = (20, 80, 150)
    source[8:24, 8:24, 3] = 255
    matrix = np.array([[1, 0, 0], [0, 1, 0]], dtype=np.float32)

    aligned = warp_rgba(source, matrix, (32, 32))

    transparent = aligned[:, :, 3] == 0
    assert transparent.any()
    assert np.all(aligned[transparent, :3] == 0)


def test_alignment_api_preserves_zero_rgb_contract(monkeypatch) -> None:
    generated = np.zeros((CANVAS_SIZE, CANVAS_SIZE, 4), dtype=np.uint8)
    generated[:, :, :3] = MAGENTA_BGR
    generated[300:900, 400:850, :3] = (20, 80, 150)
    generated[300:900, 400:850, 3] = 255
    template = generated.copy()
    points = np.array(
        [[500, 500], [700, 500], [600, 600], [540, 760], [660, 760]],
        dtype=np.float64,
    )
    identity = np.array([[1, 0, 0], [0, 1, 0]], dtype=np.float32)
    monkeypatch.setattr(
        align_module, "face_landmarks", lambda image, model: (points, 0.99)
    )
    monkeypatch.setattr(
        align_module, "similarity_matrix", lambda source, target: identity
    )

    aligned, report = align_module.align_rgba(
        generated,
        template,
        model_path=Path("unused.onnx"),
    )

    transparent = aligned[:, :, 3] == 0
    assert report["transparent_rgb_zero"] is True
    assert np.all(aligned[transparent, :3] == 0)


def test_chroma_key_residual_is_below_spill_threshold() -> None:
    image = np.full((32, 32, 3), MAGENTA_BGR, dtype=np.uint8)
    image[10:22, 10:22] = (20, 80, 150)

    keyed = chroma_key(image)
    red = keyed[:, :, 2].astype(np.int16)
    green = keyed[:, :, 1].astype(np.int16)
    blue = keyed[:, :, 0].astype(np.int16)
    distance = np.maximum(0, np.minimum(red, blue) - green - np.abs(red - blue) // 2)
    visible = keyed[:, :, 3] > 0

    residual = int((visible & (distance >= CHROMA_SPILL_THRESHOLD)).sum())
    assert residual == 0
    assert int((keyed[:, :, 3] == 0).sum()) >= 32 * 32 - 12 * 12


def test_rectangle_composite_has_zero_difference_outside_contract() -> None:
    base = np.zeros((CANVAS_SIZE, CANVAS_SIZE, 4), dtype=np.uint8)
    base[:, :, :3] = (10, 20, 30)
    base[:, :, 3] = 255
    source = np.zeros_like(base)
    source[:, :, :3] = (100, 110, 120)
    source[:, :, 3] = 255
    rectangle = (170, 194, 60, 42)

    result = paste_rect(base, source, rectangle)

    assert outside_difference(base, result, rectangle) == 0
    assert np.any(result != base)
    allowed = np.zeros((CANVAS_SIZE, CANVAS_SIZE), dtype=bool)
    x0, y0, x1, y1 = (
        int(round(rectangle[0] * CANVAS_SIZE / 465)) + 2,
        int(round(rectangle[1] * CANVAS_SIZE / 465)) + 2,
        int(round((rectangle[0] + rectangle[2]) * CANVAS_SIZE / 465)) - 2,
        int(round((rectangle[1] + rectangle[3]) * CANVAS_SIZE / 465)) - 2,
    )
    allowed[y0:y1, x0:x1] = True
    assert np.all(np.any(result != base, axis=2) <= allowed)


def test_diff_mask_has_no_signal_outside_large_changed_region() -> None:
    previous = np.zeros((96, 96, 4), dtype=np.uint8)
    previous[:, :, 3] = 255
    current = previous.copy()
    current[30:66, 30:66, :3] = (80, 80, 80)

    mask = diff_mask(previous, current, "L1_makeup")

    assert not mask[:20].any()
    assert not mask[76:].any()
    assert not mask[:, :20].any()
    assert not mask[:, 76:].any()


def test_makeup_slots_are_mutually_exclusive() -> None:
    layer = np.zeros((32, 32, 4), dtype=np.uint8)
    layer[:, :, 3] = 255
    regions = {
        "slots": {
            "eyes": [[4, 4, 16, 16]],
            "lips": [[10, 10, 16, 16]],
            "cheeks": [[0, 0, 32, 32]],
        }
    }

    masks = makeup_slot_masks(layer, regions)
    ownership = sum(masks.values())

    assert np.all(ownership <= 1)
    assert masks["eyes"][8, 8]
    assert not masks["lips"][8, 8]
    assert not masks["cheeks"][8, 8]
    assert masks["cheeks"][31, 31]


def test_reference_is_materialized_from_git_commit(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(["git", "-C", str(repository), "init", "-q"], check=True)
    reference_path = repository / "assets" / "reference.bin"
    reference_path.parent.mkdir()
    reference_path.write_bytes(b"committed-reference")
    subprocess.run(
        ["git", "-C", str(repository), "add", "assets/reference.bin"], check=True
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=art-pipeline-test",
            "-c",
            "user.email=art-pipeline-test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    reference_path.write_bytes(b"worktree-must-not-be-read")

    reference = GitReference(repository, "HEAD", "assets/reference.bin")
    with reference.temporary_file() as materialized:
        assert materialized.read_bytes() == b"committed-reference"


def test_extract_writes_keyed_layers_and_reconstruction(
    tmp_path: Path,
    monkeypatch,
) -> None:
    size = 64
    base = np.full((size, size, 3), MAGENTA_BGR, dtype=np.uint8)
    base[8:56, 16:48] = (20, 80, 150)
    base_path = tmp_path / "base.magenta.png"
    source_directory = tmp_path / "source"
    output_root = tmp_path / "output"
    save_png(base_path, base)
    source_directory.mkdir()
    colours = ((30, 80, 180), (55, 85, 160), (90, 100, 140), (110, 95, 130))
    for step, colour in zip(extract_module.STEPS, colours, strict=True):
        current = base.copy()
        current[20:44, 20:44] = colour
        save_png(source_directory / f"demo.{step}.png", current)

    monkeypatch.setattr(
        extract_module,
        "makeup_region",
        lambda image, model: np.ones(image.shape[:2], dtype=np.uint8),
    )
    monkeypatch.setattr(
        extract_module,
        "head_region",
        lambda image, model: np.ones(image.shape[:2], dtype=np.uint8),
    )

    report = extract_module.extract(
        base_path,
        "demo",
        source_directory=source_directory,
        output_root=output_root,
        model_path=tmp_path / "unused.onnx",
    )

    result_directory = output_root / "demo"
    expected = {
        "base.png",
        "reconstruction.png",
        "final.png",
        "sheet.png",
        "report.json",
        *(f"{step}.keyed.png" for step in extract_module.STEPS),
        *(f"{step}.png" for step in extract_module.STEPS),
    }
    assert expected.issubset({path.name for path in result_directory.iterdir()})
    assert set(report["layers"]) == set(extract_module.STEPS)
    for path in result_directory.glob("*.png"):
        image = load_rgba(path)
        transparent = image[:, :, 3] == 0
        assert np.all(image[transparent, :3] == 0)
