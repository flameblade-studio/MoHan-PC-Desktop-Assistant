"""以每張圖的背景色重新計算 IoU，並先驗證指標。

原探針底板色為 (196,198,200)，模型背景實測為 (177,189,194)，
色差 34 與固定門檻 45 的餘裕為 11。此版採用四角中位色作為背景，
並依該圖色差分布決定門檻。

指標通過下列三項驗證後採用：
1. 前景佔比落在合理區間，背景保留其背景分類。
2. 控制圖與自身的 IoU 為 1.0，提供上界參考。
3. 純 t2i 的 IoU 提供一般人物重疊的下界參考。
"""
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from thresholds import (
    BACKGROUND_DISTANCE,
    BINARY_MIDPOINT,
    CHROMA_GAIN,
    FOREGROUND_FRAC_MAX,
    FOREGROUND_FRAC_MIN,
    IOU_GAIN_MIN,
    SILHOUETTE_ON,
)

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
PROBE = ROOT / "work/second-gen-body/strength-iou-probe"


def foreground(path: Path) -> tuple[np.ndarray, tuple[int, int, int], float]:
    array = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
    corners = np.concatenate([
        array[:40, :40].reshape(-1, 3), array[:40, -40:].reshape(-1, 3),
        array[-40:, :40].reshape(-1, 3), array[-40:, -40:].reshape(-1, 3),
    ])
    background = np.median(corners, axis=0)
    distance = np.abs(array - background).sum(axis=2)
    mask = distance > BACKGROUND_DISTANCE
    return mask, tuple(int(v) for v in background), float(mask.mean())


def iou(a: np.ndarray, b: np.ndarray) -> float:
    union = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum()) / union if union else 0.0


def chroma(path: Path, mask: np.ndarray) -> float:
    """量測前景平均彩度，與 IoU 共同評估幾何及上色。

    s0.55 的 IoU 曾達 0.919，但輸出仍保留灰模色彩。彩度量測補充
    色彩轉換證據，供判讀同時符合幾何及上色條件的強度。
    """
    array = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    high = array.max(axis=2)
    low = array.min(axis=2)
    saturation = np.where(high > 0, (high - low) / np.maximum(high, 1.0), 0.0)
    return float(saturation[mask].mean()) if mask.any() else 0.0


def true_control() -> np.ndarray:
    """控制遮罩取自 bundle 的 silhouette，不用門檻從灰模推。

    用門檻推是錯的：灰模的亮部與淺灰底板顏色太接近會被判成背景，
    實測灰模初始圖與染色初始圖（幾何完全相同）的門檻剪影只有 0.915 的 IoU，
    可見門檻法把灰模的剪影侵蝕掉約 8%。silhouette 是渲染器直接輸出的，精確。
    """
    sys.path.insert(0, str(Path(__file__).parent))
    from tinted_init import tinted_init  # noqa: F401  只為共用同一套裁切幾何
    from produce_v10_geo import BUNDLES

    folder = BUNDLES / "yaw+090-pitch+00"
    mask = Image.open(folder / f"{folder.name}_silhouette.png").convert("L")
    inside = np.asarray(mask) > SILHOUETTE_ON
    box = Image.fromarray((inside * 255).astype(np.uint8)).getbbox()
    left, top, right, bottom = box
    pad_x, pad_y = int((right - left) * 0.16), int((bottom - top) * 0.05)
    left, top = max(0, left - pad_x), max(0, top - pad_y)
    right, bottom = min(mask.width, right + pad_x), min(mask.height, bottom + pad_y)
    ratio = 832 / 1248
    if (right - left) / (bottom - top) < ratio:
        need = int((bottom - top) * ratio) - (right - left)
        left = max(0, left - need // 2)
        right = min(mask.width, right + need - need // 2)
    cropped = Image.fromarray((inside * 255).astype(np.uint8)).crop(
        (left, top, right, bottom)
    )
    if cropped.width / cropped.height < ratio:
        board = Image.new("L", (int(cropped.height * ratio), cropped.height), 0)
        board.paste(cropped, ((board.width - cropped.width) // 2, 0))
        cropped = board
    return np.asarray(cropped.resize((832, 1248), Image.NEAREST)) > BINARY_MIDPOINT


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    init = PROBE / "_init.png"
    if not init.exists():
        print("探針尚未產出初始圖")
        return
    control = true_control()
    _threshold_mask, bg, frac = foreground(init)
    print("── 指標自我驗證 ──")
    print(f"控制遮罩取自 bundle silhouette，佔畫面 {control.mean()*100:.1f}%")
    print(f"（對照：門檻法從灰模推出來是 {frac*100:.1f}%，會侵蝕剪影）")
    frac = control.mean()
    print(f"控制遮罩對自己的 IoU = {iou(control, control):.3f}（必須是 1.000，否則切法有誤）")
    inverted = np.logical_not(control)
    print(f"控制圖對其補集的 IoU = {iou(control, inverted):.3f}（必須是 0.000）")
    if not (FOREGROUND_FRAC_MIN < frac < FOREGROUND_FRAC_MAX):
        print("！前景佔比不在合理區間，切法可能把背景算進去了，以下數字不採信")
        return

    mesh_chroma = chroma(init, control)
    print(f"灰模自身彩度 {mesh_chroma:.3f}（幾何軸的上界參考，也是風格軸的下界）")

    print("\n── 幾何保真 × 風格轉換 ──")
    rows = []
    for path in sorted(PROBE.glob("*.png")):
        if path.name == "_init.png":
            continue
        mask, bg, frac = foreground(path)
        label = "純 t2i 基準" if "baseline" in path.name else path.stem
        rows.append((label, iou(mask, control), chroma(path, mask), frac))

    base = next((v for lab, v, _, _ in rows if "基準" in lab), None)
    skin = next((c for lab, _, c, _ in rows if "基準" in lab), None)
    print(f"{'':14s} {'IoU':>6s} {'彩度':>7s}    判讀")
    for label, value, colour, frac in sorted(rows, key=lambda r: r[0]):
        if colour <= mesh_chroma * 1.35:
            note = "仍是灰模，沒上色"
        elif base is not None and value - base < IOU_GAIN_MIN:
            note = "幾何沒進去，等同純 t2i"
        else:
            note = "兩者兼具"
        print(f"  {label:12s} {value:6.3f} {colour:7.3f}    {note}")

    if base is None or skin is None:
        return
    usable = [
        (lab, v, c) for lab, v, c, _ in rows
        if "基準" not in lab and c > mesh_chroma * CHROMA_GAIN
        and v - base >= IOU_GAIN_MIN
    ]
    print()
    if usable:
        best = max(usable, key=lambda r: r[1])
        print(f"→ 同時守住幾何與完成上色的強度：{[u[0] for u in usable]}；"
              f"其中幾何最強者為 {best[0]}（IoU {best[1]:.3f}）")
    else:
        print("→ 沒有任何單一強度同時成立：低強度是灰模原樣通過，"
              "高強度是幾何完全沒進去。單段 img2img 解不了，需要分兩段。")


if __name__ == "__main__":
    main()
