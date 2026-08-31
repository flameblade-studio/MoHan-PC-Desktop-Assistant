"""分開量「頭髮造成的差異」與「姿勢造成的差異」。

染色＋髮量提示在 s0.85 的 IoU 是 0.606，灰模版同強度是 0.839。看起來像退步，
但控制剪影是光頭的——輸出只要長出頭髮，就必然多出控制圖沒有的像素，
IoU 一定往下掉。這是指標的結構性混淆項，不是幾何退步。

所以這裡切成兩段各自量：
  頭部區（站姿全高的前 13%）  差異主要來自頭髮，本來就該不一樣
  頸部以下                    差異才是真正的姿勢與體型偏移

只有下半段的數字才能用來判斷幾何條件化守住了沒有。
"""
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from thresholds import GEOMETRY_IOU_MIN, LOWER_BODY_GOOD
from recompute_iou import foreground, iou, true_control  # noqa: E402

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
PANELS = [
    (ROOT / "work/second-gen-body/strength-iou-probe/baseline-t2i.png", "純 t2i 基準"),
    (ROOT / "work/second-gen-body/strength-iou-probe/s085.png", "灰模 s0.85"),
    (ROOT / "work/second-gen-body/tinted-strength-probe/tinted-hair-s085.png",
     "染色+髮 s0.85"),
    (ROOT / "work/second-gen-body/tinted-strength-probe/tinted-hair-s080.png",
     "染色+髮 s0.80"),
    (ROOT / "work/second-gen-body/tinted-strength-probe/tinted-s085.png", "染色 s0.85"),
]


def split_rows(mask: np.ndarray) -> int:
    rows = np.where(mask.any(axis=1))[0]
    if not rows.size:
        return 0
    top, bottom = int(rows[0]), int(rows[-1])
    return int(top + (bottom - top) * 0.13)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    control = true_control()
    neck = split_rows(control)
    print(f"控制剪影的頸線在第 {neck} 列（全高的 13%）\n")
    print(f"{'':16s} {'全身 IoU':>9s} {'頸下 IoU':>9s}   判讀")
    for path, label in PANELS:
        if not path.exists():
            print(f"  {label:14s} 尚未產出")
            continue
        mask, _bg, _frac = foreground(path)
        whole = iou(mask, control)
        below = iou(mask[neck:], control[neck:])
        note = "幾何守住" if below >= LOWER_BODY_GOOD else (
            "姿勢明顯偏移" if below >= GEOMETRY_IOU_MIN else "幾何沒進去")
        print(f"  {label:14s} {whole:9.3f} {below:9.3f}   {note}")


if __name__ == "__main__":
    main()
