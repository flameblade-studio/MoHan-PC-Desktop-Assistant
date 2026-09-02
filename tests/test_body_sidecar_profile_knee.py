"""露腿權威在純側面時，膝登錄點不得讓整組 24 視角的建置中止。

2026-09-02 以二代素體跑 build_pose_atlas_release_assets.build()：24 張只有 ±090
兩個純側面失敗，錯誤是 alpha_registration_point_missing，落在膝（高度比例 0.78）。
成因：膝的目標是「髖與腳掌中心的中點」，這個幾何假設穿長袍——v4 的側面把腿包住，
中點永遠打得到 alpha；露腿的側面姿勢裡髖在腿前方一段距離、腳掌在腿正下方，
中點落在小腿前方的空氣裡，最近 alpha 56–58 px，超過搜尋半徑 48。

修正：中點找不到就退回「腳掌中心正上方」（側面時小腿在腳的正上方）；兩者都找不到
才記為不可達的 occluded landmark，而不是中止。這裡用合成剪影，不依賴任何素材；
剪影是兩條腿，讓 _foot_side_map 兩側都找得到腳，不會觸發既有的整側遮擋路徑。
"""
from __future__ import annotations

lazy import hashlib
lazy import sys
lazy from pathlib import Path

lazy import numpy as np
lazy import pytest

ROOT = Path(__file__).resolve().parents[1]
W, H = 1024, 1536
TOP, BOTTOM = 80, 1480
LEG_X = (450, 590)          # 兩條腿的中心 x（左右）
VISIBLE_SIDES = len(LEG_X)  # 兩側都可見 → 應有兩個膝登錄點
LEG_HALF_WIDTH = 28
FOOT_HALF_LENGTH = 40       # 腳掌以腿為中心前後各 40 px
KNEE_TOLERANCE_PX = 40      # 膝必須落在腿寬（56 px）加上搜尋誤差之內
SKIN = (200, 180, 170, 255)


@pytest.fixture(scope="module")
def module():
    sys.path.insert(0, str(ROOT / "tools"))
    import build_pose_atlas_release_assets as m

    return m


def _silhouette(*, hip_forward: int) -> np.ndarray:
    """側面剪影：頭與軀幹整體向前（+x）偏移 hip_forward，兩條腿垂直，腳掌在腿正下方。

    hip_forward 越大，「髖與腳掌中心的中點」離小腿越遠。
    """
    rgba = np.zeros((H, W, 4), np.uint8)
    hip_y = round(TOP + (BOTTOM - TOP) * 0.56)
    torso_center = (LEG_X[0] + LEG_X[1]) // 2 + hip_forward
    yy, xx = np.mgrid[0:H, 0:W]
    rgba[((xx - torso_center) ** 2 + (yy - (TOP + 60)) ** 2) < 55 ** 2] = SKIN
    rgba[TOP + 110: hip_y + 40, torso_center - 90: torso_center + 90] = SKIN
    for x in LEG_X:
        rgba[hip_y: BOTTOM - 20, x - LEG_HALF_WIDTH: x + LEG_HALF_WIDTH] = SKIN
        rgba[BOTTOM - 20: BOTTOM + 1, x - FOOT_HALF_LENGTH: x + FOOT_HALF_LENGTH] = SKIN
    return rgba


def _source(module, rgba: np.ndarray, view_id: str, yaw: int, tmp_path: Path):
    import cv2

    path = tmp_path / f"{view_id}.png"
    assert cv2.imwrite(str(path), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
    left, top, right, bottom = module._alpha_bounds(rgba)
    return module._SourceImage(
        view_id, yaw, path, hashlib.sha256(path.read_bytes()).hexdigest(),
        rgba, top, bottom, left, right,
    )


def _knees(sidecar):
    return {k: v for k, v in sidecar["landmarks"].items() if k.endswith("_knee")}


def _unreachable_knees(sidecar):
    return [o for o in sidecar["occluded_landmarks"] if o["name"].endswith("_knee")]


def test_forward_hip_knee_falls_back_to_above_the_foot(module, tmp_path: Path) -> None:
    """髖前移：中點在空氣裡，膝必須退回腳掌正上方的小腿，而非中止或記為不可達。"""
    rgba = _silhouette(hip_forward=260)
    source = _source(module, rgba, "yaw+090-pitch+00", 90, tmp_path)
    sidecar = module._body_sidecar(source, rgba, source.height, source.source_sha256)
    knees = _knees(sidecar)
    assert len(knees) == VISIBLE_SIDES, f"兩側都可見，應有兩個膝：{sorted(sidecar['landmarks'])}"
    assert not _unreachable_knees(sidecar), "退回目標明明有 alpha，膝卻被記為不可達"
    for name, (x, _y) in knees.items():
        assert min(abs(x - lx) for lx in LEG_X) <= KNEE_TOLERANCE_PX, (
            f"{name} 落在 x={x}，不在任一條腿上（腿在 x≈{LEG_X}）"
        )


def test_upright_hip_keeps_the_original_midpoint_target(module, tmp_path: Path) -> None:
    """正例：髖在腿正上方時中點就在腿上，行為與修正前相同。"""
    rgba = _silhouette(hip_forward=0)
    source = _source(module, rgba, "yaw+090-pitch+00", 90, tmp_path)
    sidecar = module._body_sidecar(source, rgba, source.height, source.source_sha256)
    assert len(_knees(sidecar)) == VISIBLE_SIDES
    assert not _unreachable_knees(sidecar)


def test_unreachable_knee_is_recorded_not_raised(module, tmp_path: Path) -> None:
    """兩個目標都打不到時記為不可達，整組建置不得因此中止。"""
    rgba = _silhouette(hip_forward=260)
    knee_y = round(TOP + (BOTTOM - TOP) * 0.78)
    rgba[knee_y - 80: knee_y + 80, :, :] = 0      # 把膝高度一帶整列挖空
    source = _source(module, rgba, "yaw+090-pitch+00", 90, tmp_path)
    sidecar = module._body_sidecar(source, rgba, source.height, source.source_sha256)
    unreachable = _unreachable_knees(sidecar)
    assert len(unreachable) == VISIBLE_SIDES, f"兩個目標都找不到卻沒有記為不可達：{unreachable}"
    assert all(o["occluder_id"] == "knee-target-unreachable" for o in unreachable)


def test_registration_error_names_the_target(module) -> None:
    """錯誤訊息必須帶座標：整組失敗時才知道是哪一張、哪個點。"""
    mask = np.zeros((H, W), bool)
    mask[100:200, 100:200] = True
    with pytest.raises(
        module.BuildError, match=r"alpha_registration_point_missing:target=\(900,1400\)"
    ):
        module._alpha_point(mask, 900, 1400, 0, 0, W - 1, H - 1)
