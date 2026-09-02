"""golden 建置器對「另一代素體」必須守住的兩個契約。

2026-09-02 用二代素體重切圖層時發現：

1. 背面視角的臉部層依賴「YuNet 偵測不到臉」才留空。v4 的背面剛好偵測不到；
   二代素體 yaw+120 的耳朵／下顎一小片被判成臉（信心 ≥ 0.75），半身正面遮罩
   就被貼上去（虹膜 24 px、上唇 107 px）。契約應以 |yaw| 為準，與語意稽核的
   背面裁決一致。
2. 遮罩轉貼不知道權威沒有袖子。無袖素體的手臂皮膚被切進 sleeve_*，而渲染器的
   _sleeve_lift 會隨手勢把袖層獨立平移——皮膚跟著離開身體。`empty_layers`
   讓呼叫端宣告權威沒有的實體層，像素交還 body。

兩個測試都只用 v4 的既有資產，不依賴任何新素體檔案。
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
    # 無主像素依 _exclusive_ownership 的規則：HAIR_BODY_SPLIT_Y 以上交 hair_back、
    # 以下交 body。實測 v4 yaw+000 的袖層有 61 px 落在肩頸交界的分割線之上。
    # 兩者都是不會隨手勢平移的層，所以這個分配是可接受的；不可接受的是像素
    # 消失、或流進會動的層／臉部層。
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

    # 無損重組：25 層 alpha 的聯集必須等於權威的 alpha（一個像素都不能掉、不能重複）。
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
