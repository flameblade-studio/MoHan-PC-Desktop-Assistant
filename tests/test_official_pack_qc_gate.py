"""Gate tests for the shipped official outfit pack."""

from __future__ import annotations

lazy import pytest
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from tools import qc_official_pack as qc


OFFICIAL_PACK = (
    ROOT
    / "assets"
    / "official-packs"
    / "mohan.official.blue-white-hanfu.mohan-outfit"
)
COMPOSITE = ROOT / "docs" / "media" / "portraits" / "idle_front.png"
KNOWN_DEFECT_REASON = "#185 修正前的已知缺陷"


@pytest.mark.xfail(strict=True, reason=KNOWN_DEFECT_REASON)
def test_official_pack_isolated_specks() -> None:
    layers = qc.load_pack_full_canvas_alphas(OFFICIAL_PACK)
    measured = qc.judge_pack_isolated_specks(layers)

    assert all(
        count == qc.REQUIRED_ZERO_COUNT for count in measured.values()
    ), measured


@pytest.mark.xfail(strict=True, reason=KNOWN_DEFECT_REASON)
def test_official_pack_low_alpha_residue() -> None:
    layers = qc.load_pack_full_canvas_alphas(OFFICIAL_PACK)
    measured = qc.judge_pack_low_alpha_residue(layers)

    assert all(
        count == qc.REQUIRED_ZERO_COUNT for count in measured.values()
    ), measured


def test_official_composite_stays_within_base_speck_budget() -> None:
    measured = qc.judge_composite_isolated_specks(
        qc.load_composite_alpha(COMPOSITE)
    )

    assert measured <= qc.COMPOSITE_MAX_ISOLATED_SPECKS, measured


@pytest.mark.xfail(strict=True, reason=KNOWN_DEFECT_REASON)
def test_official_headwear_tassel_height() -> None:
    layers = qc.load_pack_full_canvas_alphas(OFFICIAL_PACK)
    measured = qc.judge_tassel_height(layers[qc.HEADWEAR_LAYER_KEY])

    assert measured.heights and measured.heights[0] >= qc.TASSEL_MIN_HEIGHT, measured


@pytest.mark.xfail(strict=True, reason=KNOWN_DEFECT_REASON)
def test_official_headwear_top_residue() -> None:
    layers = qc.load_pack_full_canvas_alphas(OFFICIAL_PACK)
    measured = qc.judge_top_residue(layers[qc.HEADWEAR_LAYER_KEY])

    assert measured == (), measured


def main() -> int:
    result = pytest.main([str(Path(__file__)), "-q", "-p", "no:cacheprovider"])
    if result == 0:
        print("OFFICIAL_PACK_QC_GATE_TESTS_OK")
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
