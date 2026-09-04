"""Synthetic tests for the official outfit-pack QC judges."""

from __future__ import annotations

lazy import cv2
lazy import pytest
lazy import sys
lazy import zipfile
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy import numpy as np

lazy from tools import qc_official_pack as qc


EXPECTED_ONE = 1
EXPECTED_EIGHT_PIXEL_AREA = 8
EXPECTED_ALPHA_RESIDUE = 1
EXPECTED_SHORT_TASSEL_HEIGHT = 40
EXPECTED_TOP_RESIDUE_AREA = 100
EXPECTED_TOP_RESIDUE_BBOX = (630, 100, 10, 10)
VALID_TASSEL_HEIGHT = 100
OPAQUE_ALPHA = 255


def _canvas() -> np.ndarray:
    return np.zeros(
        (qc.CANVAS_SIZE, qc.CANVAS_SIZE, qc.RGBA_CHANNELS),
        dtype=np.uint8,
    )


def _valid_headwear() -> np.ndarray:
    image = _canvas()
    image[200:200 + VALID_TASSEL_HEIGHT, 760:764, qc.ALPHA_CHANNEL] = 255
    return image


def _encode(image: np.ndarray) -> bytes:
    encoded_ok, encoded = cv2.imencode(".png", image)
    assert encoded_ok
    return encoded.tobytes()


def _pack(tmp_path: Path, layers: dict[str, np.ndarray]) -> Path:
    path = tmp_path / "synthetic.mohan-outfit"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for key, image in layers.items():
            archive.writestr(f"assets/synthetic-{key}", _encode(image))
    return path


def _clean_layers() -> dict[str, np.ndarray]:
    return {
        qc.FRONT_LAYER_KEY: _canvas(),
        qc.BACK_LAYER_KEY: _canvas(),
        qc.HEADWEAR_LAYER_KEY: _valid_headwear(),
    }


def _alpha_layers(layers: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        key: image[:, :, qc.ALPHA_CHANNEL]
        for key, image in layers.items()
    }


def _write_composite(tmp_path: Path, image: np.ndarray) -> Path:
    path = tmp_path / "composite.png"
    assert cv2.imwrite(str(path), image)
    return path


def test_clean_layers_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pack = _pack(tmp_path, _clean_layers())
    composite = _write_composite(tmp_path, _canvas())

    assert qc.main([str(pack), "--composite", str(composite)]) == 0
    assert capsys.readouterr().out.rstrip().endswith("OFFICIAL_PACK_QC_OK")


def test_eight_pixel_isolated_point_fails_and_reports_one() -> None:
    rgba_layers = _clean_layers()
    layers = _alpha_layers(rgba_layers)
    point = layers[qc.FRONT_LAYER_KEY]
    point[300:302, 400:404] = OPAQUE_ALPHA

    measured = qc.judge_pack_isolated_specks(layers)

    assert EXPECTED_EIGHT_PIXEL_AREA == int(
        (point[300:302, 400:404] > qc.SOLID_ALPHA_THRESHOLD).sum()
    )
    assert measured[qc.FRONT_LAYER_KEY] == EXPECTED_ONE
    assert measured[qc.FRONT_LAYER_KEY] != qc.REQUIRED_ZERO_COUNT


def test_alpha_twenty_residue_fails() -> None:
    layers = _alpha_layers(_clean_layers())
    layers[qc.FRONT_LAYER_KEY][300, 400] = 20

    measured = qc.judge_pack_low_alpha_residue(layers)

    assert measured[qc.FRONT_LAYER_KEY] == EXPECTED_ALPHA_RESIDUE
    assert measured[qc.FRONT_LAYER_KEY] != qc.REQUIRED_ZERO_COUNT


def test_short_tassel_component_fails() -> None:
    headwear = _canvas()[:, :, qc.ALPHA_CHANNEL]
    headwear[200:240, 760:764] = OPAQUE_ALPHA

    measured = qc.judge_tassel_height(headwear)

    assert measured.component_count == EXPECTED_ONE
    assert measured.heights == (EXPECTED_SHORT_TASSEL_HEIGHT,)
    assert measured.heights[0] < qc.TASSEL_MIN_HEIGHT


def test_top_residue_fails_and_prints_bbox(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    layers = _clean_layers()
    headwear = layers[qc.HEADWEAR_LAYER_KEY]
    headwear[300:330, 300:330, qc.ALPHA_CHANNEL] = OPAQUE_ALPHA
    headwear[EXPECTED_TOP_RESIDUE_BBOX[1] : EXPECTED_TOP_RESIDUE_BBOX[1] + 10,
             EXPECTED_TOP_RESIDUE_BBOX[0] : EXPECTED_TOP_RESIDUE_BBOX[0] + 10,
             qc.ALPHA_CHANNEL] = OPAQUE_ALPHA
    pack = _pack(tmp_path, layers)

    assert qc.main([str(pack)]) == 1
    output = capsys.readouterr().out
    assert (
        "TOP_RESIDUE area=100 bbox=x630..640 y100..110"
        in output
    )
    assert output.rstrip().endswith("OFFICIAL_PACK_QC_FAIL")
    residues = qc.judge_top_residue(headwear[:, :, qc.ALPHA_CHANNEL])
    assert len(residues) == EXPECTED_ONE
    assert residues[0].area == EXPECTED_TOP_RESIDUE_AREA
    assert residues[0].bbox == EXPECTED_TOP_RESIDUE_BBOX


def test_cropped_layer_is_padded_at_top_left_and_warns(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    layers = _clean_layers()
    cropped = np.zeros((20, 30, qc.RGBA_CHANNELS), dtype=np.uint8)
    cropped[5, 6, qc.ALPHA_CHANNEL] = 255
    layers[qc.FRONT_LAYER_KEY] = cropped
    pack = _pack(tmp_path, layers)

    loaded = qc.load_pack_full_canvas_alphas(pack)

    output = capsys.readouterr().out
    assert "pasted at top-left" in output
    assert loaded[qc.FRONT_LAYER_KEY].shape == qc.CANVAS_SHAPE
    assert loaded[qc.FRONT_LAYER_KEY][5, 6] == OPAQUE_ALPHA
    assert loaded[qc.FRONT_LAYER_KEY][6, 5] == 0


def main() -> int:
    result = pytest.main([str(Path(__file__)), "-q", "-p", "no:cacheprovider"])
    if result == 0:
        print("QC_OFFICIAL_PACK_TESTS_OK")
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
