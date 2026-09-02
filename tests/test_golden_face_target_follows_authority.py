"""golden 建置器的臉部目標必須解在權威圖上，而不是寫死的 v4 canonical。

2026-09-02 為二代素體重切圖層時發現：`_remap_face_candidates()` 的目標臉框
一律讀 `assets/pose-atlas/v4/{view}.png`，與 `--authority` 傳進來的圖無關。
兩代素體的臉位置不同（實測 yaw+045 的 y 差 36 px、眼睛 landmark 差約 20 px），
五點仿射會對著 v4 的臉解、再把遮罩貼到新權威上——虹膜與嘴唇落在新臉之外，
或被臉部區域裁成空。

這裡不依賴任何新素體檔案：把 v4 canonical 平移一個已知位移當作「另一個權威」，
斷言重建出的虹膜層跟著位移走。沒給權威時行為必須與原本相同。
"""
from __future__ import annotations

lazy import inspect
lazy import sys
lazy from pathlib import Path

lazy import numpy as np
lazy import pytest

ROOT = Path(__file__).resolve().parents[1]
VIEW = "yaw+000-pitch+00"
RGBA_CHANNELS = 4
SHIFT = (40, 30)          # (dx, dy) 像素；canonical 四周邊距足夠容納
# 位移後 YuNet 會在新圖上重新偵測，landmark 有幾 px 抖動，再經 warpAffine 取樣；
# 嘴唇層之後還過 oral-clamp／skin-reclaim 對權威像素重切，實測 lip_upper 殘差 7.5 px
# （虹膜 ≤ 3.5 px）。判別的重點不在絕對精度，而在「Δ 是否跟著位移走」——若目標
# 仍解在 v4 上，Δ 會是 0；下面另有 residual < moved/3 的判別式守住這一點。
FOLLOW_TOLERANCE_PX = 10.0
V4_FRONT_LEFT_EYE = (492, 216)   # v4 canonical yaw+000 的 YuNet 左眼 landmark 實測
DEFAULT_CENTROID_TOLERANCE_PX = 12


def _load_rgba(path: Path) -> np.ndarray:
    import cv2

    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    assert image is not None and image.shape[2] == RGBA_CHANNELS, path
    return image


def _alpha_centroid(path: Path) -> tuple[float, float]:
    alpha = _load_rgba(path)[:, :, 3]
    ys, xs = np.nonzero(alpha)
    assert len(xs) > 0, f"{path.name} 的 alpha 全空"
    weights = alpha[ys, xs].astype(np.float64)
    return float((xs * weights).sum() / weights.sum()), float((ys * weights).sum() / weights.sum())


@pytest.fixture(scope="module")
def builder():
    sys.path.insert(0, str(ROOT))
    from tools import build_yaw000_golden_template as module

    return module


def test_face_layers_follow_a_shifted_authority(builder, tmp_path: Path) -> None:
    import cv2

    canonical = _load_rgba(ROOT / "assets/pose-atlas/v4" / f"{VIEW}.png")
    dx, dy = SHIFT
    shifted = np.zeros_like(canonical)
    shifted[dy:, dx:] = canonical[: canonical.shape[0] - dy, : canonical.shape[1] - dx]
    authority = tmp_path / "shifted-authority.png"
    assert cv2.imwrite(str(authority), shifted)

    baseline_dir = tmp_path / "baseline"
    shifted_dir = tmp_path / "shifted"
    builder.build(ROOT, baseline_dir, view=VIEW)
    builder.build(ROOT, shifted_dir, view=VIEW, authority_path=authority)

    for layer in ("iris_left", "iris_right", "lip_upper"):
        bx, by = _alpha_centroid(baseline_dir / f"{VIEW}_{layer}.png")
        sx, sy = _alpha_centroid(shifted_dir / f"{VIEW}_{layer}.png")
        moved = np.hypot(sx - bx, sy - by)
        residual = np.hypot((sx - bx) - dx, (sy - by) - dy)
        assert residual <= FOLLOW_TOLERANCE_PX, (
            f"{layer} 未跟著權威位移：基線 ({bx:.1f},{by:.1f}) → 位移後 ({sx:.1f},{sy:.1f})，"
            f"期望位移 {SHIFT}，殘差 {residual:.1f} px"
        )
        # 判別式：跟著走的 Δ 必須遠比「沒動」更接近期望位移，否則只是抖動碰巧過關。
        assert residual < moved / 3, (
            f"{layer} 的位移 {moved:.1f} px 與期望位移的殘差 {residual:.1f} px 不成比例；"
            "臉部目標可能仍解在 v4 canonical 上"
        )


def test_default_authority_path_is_unchanged(builder, tmp_path: Path) -> None:
    """沒給權威時必須走原本的 v4 路徑，v4 重建結果位元不變。"""
    parameters = inspect.signature(builder._remap_face_candidates).parameters
    assert "authority_path" in parameters
    assert parameters["authority_path"].default is None, "預設必須是 None（退回 v4 路徑）"
    source = inspect.getsource(builder._remap_face_candidates)
    assert 'repo / "assets/pose-atlas/v4" / f"{view}.png"' in source

    out = tmp_path / "default"
    builder.build(ROOT, out, view=VIEW)
    iris = out / f"{VIEW}_iris_left.png"
    assert iris.is_file()
    x, y = _alpha_centroid(iris)
    ex, ey = V4_FRONT_LEFT_EYE
    assert abs(x - ex) < DEFAULT_CENTROID_TOLERANCE_PX and abs(y - ey) < DEFAULT_CENTROID_TOLERANCE_PX, (
        f"預設路徑的虹膜質心異常 ({x:.1f},{y:.1f})，應在 v4 左眼 landmark {V4_FRONT_LEFT_EYE} 附近"
    )
