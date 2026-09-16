"""分開量測頭髮差異與身體姿勢差異。

s0.85 的染色加髮量版本 IoU 為 0.606，灰模版為 0.839。控制剪影是光頭，
生成頭髮會新增像素並降低全身 IoU，因此量測分成兩段：
- 站姿全高前 13%：以頭髮差異為主。
- 頸部以下：用於判讀姿勢與體型的幾何一致性。
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
