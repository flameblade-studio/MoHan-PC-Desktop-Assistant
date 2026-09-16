"""golden 建置器跨素體世代保持背面與空實體層契約。

2026-09-02 二代素體驗證：
1. yaw+120 的耳朵／下顎曾被 YuNet 判成臉（信心 ≥ 0.75），造成背面
   貼入虹膜 24 px、上唇 107 px。背面空臉層由 |yaw| 契約明確決定。
2. 無袖素體的手臂皮膚曾進入 sleeve_* 並隨 _sleeve_lift 移動。
   empty_layers 明確宣告空實體層，讓對應原始像素回到固定 body。

兩項測試皆使用既有 v4 資產。
"""
from __future__ import annotations

lazy import sys
lazy from pathlib import Path

lazy import numpy as np
lazy import pytest

ROOT = Path(__file__).resolve().parents[1]
FRONT = "yaw+000-pitch+00"
REAR = "yaw+120-pitch+00"
SLEEVES = ("sleeve_left", "sleeve_right")


def _alpha(path: Path) -> np.ndarray:
    import cv2

    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    assert image is not None, path
    return image[:, :, 3]


@pytest.fixture(scope="module")
def builder():
    sys.path.insert(0, str(ROOT))
    from tools import build_yaw000_golden_template as module

    return module


def test_rear_view_face_layers_are_empty_even_when_a_face_is_detectable(
    builder, tmp_path: Path
) -> None:
    """背面視角以 |yaw| 為準留空，不賭偵測器。

    權威故意用正面圖（臉一定偵測得到）配上背面視角 id：舊行為會把臉貼上去，
    契約行為必須留空。
    """
    face_bearing_authority = ROOT / "assets/pose-atlas/v4" / f"{FRONT}.png"
    out = tmp_path / "rear"
    builder.build(ROOT, out, view=REAR, authority_path=face_bearing_authority)
    for layer in builder.FACE_REMAP_LAYERS:
        count = int((_alpha(out / f"{REAR}_{layer}.png") > 0).sum())
        assert count == 0, f"背面視角的 {layer} 仍有 {count} px——臉部層沒有依契約留空"


def test_front_view_face_layers_still_populate(builder, tmp_path: Path) -> None:
    """正例：契約只針對背面；正面的臉部層必須仍有像素。"""
    out = tmp_path / "front"
    builder.build(ROOT, out, view=FRONT)
    for layer in ("iris_left", "iris_right", "lip_upper", "brow_left"):
        assert int((_alpha(out / f"{FRONT}_{layer}.png") > 0).sum()) > 0, f"{layer} 變空了"


def test_empty_layers_return_pixels_to_body_losslessly(builder, tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    sleeveless = tmp_path / "sleeveless"
    builder.build(ROOT, baseline, view=FRONT)
    builder.build(ROOT, sleeveless, view=FRONT, empty_layers=SLEEVES)

    baseline_sleeves = sum(int((_alpha(baseline / f"{FRONT}_{s}.png") > 0).sum()) for s in SLEEVES)
    assert baseline_sleeves > 0, "基線的袖層本來就是空的，這個測試證明不了任何事"
    for s in SLEEVES:
        assert int((_alpha(sleeveless / f"{FRONT}_{s}.png") > 0).sum()) == 0, f"{s} 未歸零"

    def gain(layer: str) -> int:
        return int((_alpha(sleeveless / f"{FRONT}_{layer}.png") > 0).sum()) - int(
            (_alpha(baseline / f"{FRONT}_{layer}.png") > 0).sum()
        )

    body_gain, hair_back_gain = gain("body"), gain("hair_back")
    # 依 _exclusive_ownership，待分配像素在 HAIR_BODY_SPLIT_Y 以上交 hair_back、
    # 以下交 body。v4 yaw+000 袖層有 61 px 位於肩頸分割線上方。
    # 兩個接收層皆保持固定位置；每個像素須完整保留在固定承載層。
    assert body_gain + hair_back_gain == baseline_sleeves, (
        f"袖層釋出 {baseline_sleeves} px，但 body +{body_gain}、hair_back +{hair_back_gain}"
        "——有像素流向別處或消失"
    )
    assert body_gain >= baseline_sleeves * 0.95, f"大部分袖像素應回到 body，實際只有 {body_gain}"
    untouched = [
        layer for layer in builder.LAYERS
        if layer not in (*SLEEVES, "body", "hair_back") and gain(layer) != 0
    ]
    assert not untouched, f"袖層歸零不該影響這些層：{untouched}"

    # 無損重組：25 層 alpha 聯集等於權威 alpha，每個來源像素恰好歸屬一次。
    authority = _alpha(ROOT / "assets/pose-atlas/v4-working" / f"{FRONT}.user-approved-generated-alpha-clean-v3-20260823.png") > 0
    union = np.zeros_like(authority)
    total = 0
    for layer in builder.LAYERS:
        mask = _alpha(sleeveless / f"{FRONT}_{layer}.png") > 0
        union |= mask
        total += int(mask.sum())
    assert bool((union == authority).all()), "圖層聯集與權威 alpha 不一致——重組有損"
    assert total == int(authority.sum()), "圖層之間有重疊像素——歸屬不再互斥"


def test_unknown_empty_layer_fails_closed(builder, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown layer"):
        builder.build(ROOT, tmp_path / "bad", view=FRONT, empty_layers=("sleeve_middle",))
