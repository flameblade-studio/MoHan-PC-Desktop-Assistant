"""量化幾何條件化是否解決了「角度壓縮成三群」。

v9 純文生圖的核心失敗：提示詞寫 15 度、30 度、45 度，出來的圖只落在
正面／四分之三／側面三群，中間角度根本沒有。若幾何條件化有效，
量出來的臉部朝向應該隨 yaw 單調變化，而不是階梯狀跳三格。

指標只用一個——鼻尖相對兩眼中點的水平偏移，除以兩眼間距做正規化。
這是先前唯一通過自我驗證的量測；肩寬比與剪影面積兩個指標當時都被
證明會量出矛盾結果（正面比側面窄、抓到雜訊區塊），已作廢不用。

臉偵測不到的角度（背面段）沒有數字，這本身就是資訊：那些視角
真的把臉轉走了。
"""
import re
import os
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
YUNET = ROOT / "assets/vision-models/face_detection_yunet_2023mar.onnx"


def nose_offset(path: Path) -> float | None:
    """鼻尖相對兩眼中點的水平偏移，以兩眼間距正規化。正面約 0，側面絕對值大。"""
    bgr = cv2.imread(str(path))
    if bgr is None:
        return None
    height, width = bgr.shape[:2]
    detector = cv2.FaceDetectorYN.create(str(YUNET), "", (320, 320), 0.5, 0.3, 5000)
    detector.setInputSize((width, height))
    _, faces = detector.detect(bgr)
    if faces is None or len(faces) == 0:
        return None
    face = max(faces, key=lambda f: f[2] * f[3])
    # YuNet 的 5 個關鍵點：右眼、左眼、鼻、右嘴角、左嘴角
    right_eye = np.array(face[4:6])
    left_eye = np.array(face[6:8])
    nose = np.array(face[8:10])
    eye_span = float(np.linalg.norm(left_eye - right_eye))
    if eye_span < 1.0:
        return None
    centre = (right_eye + left_eye) / 2.0
    return float(nose[0] - centre[0]) / eye_span


def sweep(folder: Path, label: str) -> list[tuple[int, float | None]]:
    rows = []
    for path in sorted(folder.glob("body2-yaw*.png")):
        match = re.search(r"yaw([+-]\d+)", path.name)
        if not match:
            continue
        rows.append((int(match.group(1)), nose_offset(path)))
    rows.sort(key=lambda r: r[0])
    print(f"\n── {label}（{len(rows)} 張）──")
    for yaw, value in rows:
        bar = "偵測不到臉" if value is None else f"{value:+.3f}"
        print(f"  yaw{yaw:+05d}   {bar}")
    return rows


def verdict(rows: list[tuple[int, float | None]], label: str) -> None:
    pairs = [(y, v) for y, v in rows if v is not None and 0 <= y <= 90]
    if len(pairs) < 4:
        print(f"{label}：正面到側面的可測樣本不足（{len(pairs)} 張），不下判定")
        return
    values = [v for _, v in pairs]
    spread = max(values) - min(values)
    # 單調性：相鄰差值同號的比例
    diffs = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    forward = sum(1 for d in diffs if d > 0)
    monotonic = max(forward, len(diffs) - forward) / len(diffs)
    # 分群：把數值排序後看最大間隙佔全距的比例，階梯狀會有大間隙
    ordered = sorted(values)
    gaps = [ordered[i + 1] - ordered[i] for i in range(len(ordered) - 1)]
    biggest = max(gaps) / spread if spread > 0 else 1.0
    print(f"\n{label} 判定（yaw 0–90，{len(pairs)} 張）")
    print(f"  全距 {spread:.3f}   單調比例 {monotonic:.0%}   最大間隙佔全距 {biggest:.0%}")
    if monotonic >= 0.75 and biggest <= 0.35:
        print("  → 角度隨 yaw 連續變化，未見階梯狀分群")
    else:
        print("  → 仍有分群或非單調跡象")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    base = ROOT / "work/second-gen-body"
    v9 = sweep(base / "chroma-views-v9", "v9 純文生圖")
    v10 = sweep(base / "chroma-views-v10-geo", "v10 幾何條件化")
    verdict(v9, "v9")
    verdict(v10, "v10")


if __name__ == "__main__":
    main()
