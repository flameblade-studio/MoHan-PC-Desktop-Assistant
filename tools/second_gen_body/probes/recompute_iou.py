"""用自我校準的背景色重算 IoU，並先驗證這個指標本身站得住腳。

探針內建的切法是「與我填的底板色 (196,198,200) 差 > 45」。實測模型畫出來的
背景是 (177,189,194)，與底板差 34——只差 11 就會把整片背景誤判成人物。
邊際太薄，改成用每張圖自己四角的中位色當背景，門檻用該圖的色差分布決定。

指標在報數字之前必須先過三關，任一關不過就不採信：
  1. 背景不能被算成前景——切出的前景佔比要落在合理區間
  2. 要有上界參考——控制圖自己跟自己的 IoU 必為 1.0
  3. 要有下界參考——純 t2i 的 IoU 就是「隨便畫個人剛好重疊」的基準
"""
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

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
    mask = distance > 40
    return mask, tuple(int(v) for v in background), float(mask.mean())


def iou(a: np.ndarray, b: np.ndarray) -> float:
    union = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum()) / union if union else 0.0


def chroma(path: Path, mask: np.ndarray) -> float:
    """前景的平均彩度。灰模是無彩的，膚色不是，所以這一軸量的是風格轉過去了沒有。

    IoU 單獨一軸會選出最差的答案：s0.55 的 IoU 高達 0.919，但那是因為輸出
    根本就還是那尊灰模（光頭、灰黏土）。兩軸一起看才問得出真正的問題——
    有沒有哪個強度同時守住幾何又完成上色。
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
    inside = np.asarray(mask) > 24
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
    return np.asarray(cropped.resize((832, 1248), Image.NEAREST)) > 127


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
    if not (0.05 < frac < 0.35):
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
        elif base is not None and value - base < 0.05:
            note = "幾何沒進去，等同純 t2i"
        else:
            note = "兩者兼具"
        print(f"  {label:12s} {value:6.3f} {colour:7.3f}    {note}")

    if base is None or skin is None:
        return
    usable = [
        (lab, v, c) for lab, v, c, _ in rows
        if "基準" not in lab and c > mesh_chroma * 1.35 and v - base >= 0.05
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
