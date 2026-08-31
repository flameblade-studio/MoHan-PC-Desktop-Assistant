"""量 candidate3 四肢的實際圍度，作為擴充形變的基準。

不用幾何包絡猜部位——`skin-weight-parts-agent-a` 已從 MHR FBX 的 127 個真實
skin cluster 推出逐頂點解剖分區（明確覆蓋 97.97%、模糊 375 頂點），直接用它。

手臂在 A-pose 下是斜的，水平切面量到的是斜截面、比真實圍度大。所以切面必須
垂直於骨骼軸：上臂取 l_uparm→l_lowarm，前臂取 l_lowarm→l_wrist，
大腿取 l_upleg→l_lowleg，小腿取 l_lowleg→l_foot。

周長沿用既有 exact_sections 的嚴謹度：三角形與平面的精確交線、連成封閉環、
取最大環的周長；不用凸包近似（凸包會高估內凹處）。
"""
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from thresholds import SECTION_SELF_CHECK_TOLERANCE_CM, SEGMENT_ENDPOINTS, SHOULDER_BAND_CM

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
EXTRACT = ROOT / "artifacts/pose-atlas-rebuild/2026-08-25/ufbx-lod1-extractor-agent-a"
PARTS = ROOT / "artifacts/pose-atlas-rebuild/2026-08-25/skin-weight-parts-agent-a"
OUT = ROOT / "work/second-gen-body/limb-morph"
TARGET_HEIGHT = 168.0

# part_id 對應見 skin-weight-parts-agent-a/REPORT.md
SEGMENTS = {
    "左上臂": (3, "l_uparm", "l_lowarm"),
    "左前臂": (4, "l_lowarm", "l_wrist"),
    "左大腿": (9, "l_upleg", "l_lowleg"),
    "左小腿": (10, "l_lowleg", "l_foot"),
    "右上臂": (6, "r_uparm", "r_lowarm"),
    "右前臂": (7, "r_lowarm", "r_wrist"),
    "右大腿": (12, "r_upleg", "r_lowleg"),
    "右小腿": (13, "r_lowleg", "r_foot"),
}
AMBIGUOUS = 255
# part_id 常數（見 skin-weight-parts-agent-a/REPORT.md）
TORSO_PART = 2
LEFT_UPPER_ARM_PART = 3
RIGHT_UPPER_ARM_PART = 6


def load_obj(path: Path) -> tuple[np.ndarray, np.ndarray]:
    vertices, faces = [], []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("v "):
                vertices.append([float(v) for v in line.split()[1:4]])
            elif line.startswith("f "):
                faces.append([int(tok.split("/")[0]) - 1 for tok in line.split()[1:4]])
    return np.asarray(vertices, np.float64), np.asarray(faces, np.int64)


def load_part_ids(path: Path, count: int) -> np.ndarray:
    ids = np.zeros(count, np.int32)
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            ids[int(row["vertex_index"])] = int(row["part_id"])
    return ids


def load_joints(path: Path, scale: float) -> dict[str, np.ndarray]:
    joints = {}
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            joints[row["bone_name"]] = np.asarray(
                [float(row["x"]), float(row["y"]), float(row["z"])], np.float64
            ) * scale
    return joints


def plane_perimeter(
    vertices: np.ndarray, faces: np.ndarray, origin: np.ndarray, normal: np.ndarray
) -> float | None:
    """三角形與平面的精確交線，連成封閉環後取最大環的周長。"""
    distance = (vertices - origin) @ normal
    segments = []
    for face in faces:
        d = distance[face]
        if np.all(d > 0) or np.all(d < 0):
            continue
        points = []
        for i in range(3):
            a, b = face[i], face[(i + 1) % 3]
            da, db = distance[a], distance[b]
            if da == 0.0:
                points.append(vertices[a])
            if (da > 0) != (db > 0) and da != db:
                points.append(vertices[a] + (vertices[b] - vertices[a]) * (da / (da - db)))
        if len(points) >= SEGMENT_ENDPOINTS:
            segments.append((points[0], points[1]))
    if not segments:
        return None

    # 以量化座標當節點鍵把線段接成環；容差取 1e-6 cm，遠小於網格邊長
    def key(point):
        return tuple(np.round(point, 6))

    adjacency = defaultdict(list)
    for a, b in segments:
        adjacency[key(a)].append((key(b), float(np.linalg.norm(b - a))))
        adjacency[key(b)].append((key(a), float(np.linalg.norm(b - a))))
    seen, best, best_closed = set(), 0.0, False
    for start in adjacency:
        if start in seen:
            continue
        stack, total, nodes = [start], 0.0, []
        seen.add(start)
        while stack:
            node = stack.pop()
            nodes.append(node)
            for neighbour, length in adjacency[node]:
                total += length
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        length = total / 2.0                 # 每條邊被兩端各數一次
        # 封閉環的每個節點度數都是 2。度數 1 代表鏈是斷的——那是手臂與軀幹
        # 交界被分區切開所致，開放鏈的長度不是圍度，回報時必須標示出來。
        closed = all(
            len(adjacency[node]) == SEGMENT_ENDPOINTS for node in nodes)
        if length > best:
            best, best_closed = length, closed
    return (best, best_closed) if best > 0 else None


def self_check(vertices: np.ndarray, faces: np.ndarray) -> bool:
    """先用已知答案驗證這支切面程式，通過才採信四肢的數字。

    candidate3 報告記載的軀幹斷面是官方結果，且已被獨立稽核。拿同一套
    plane_perimeter 去量水平斷面，量得出同樣的值，才代表這支工具可信。
    今晚已有三次「指標未自我驗證就報數字」的前例，不能再犯。
    """
    known = {
        "bust": (0.74, 86.31052117057369),
        "underbust": (0.70, 70.97000216616336),
        "waist": (0.62, 62.21390939635582),
        "hip": (0.50, 90.06925217482814),
    }
    floor = float(vertices[:, 1].min())
    height = float(np.ptp(vertices[:, 1]))
    up = np.asarray([0.0, 1.0, 0.0])
    print("── 量測工具自我驗證（對照 candidate3 官方斷面）──")
    passed = True
    for name, (fraction, official) in known.items():
        origin = np.asarray([0.0, floor + fraction * height, 0.0])
        found = plane_perimeter(vertices, faces, origin, up)
        measured = found[0] if found else None
        delta = abs(measured - official) if measured else float("inf")
        ok = delta <= SECTION_SELF_CHECK_TOLERANCE_CM
        passed &= ok
        print(f"  {name:10s} 官方 {official:7.2f}  本工具 "
              f"{measured:7.2f}  差 {delta:5.3f} cm  {'OK' if ok else '← 不符'}"
              if measured else f"  {name:10s} 量不到")
    print("  → 工具可信\n" if passed else "  → 工具不可信，以下四肢數字一律不採信\n")
    return passed


def _measure_shoulder(vertices, part_ids, joints, results) -> None:
    """肩關節高度上的軀幹＋上臂最大左右跨距。

    這個量測有已知限制：A-pose 下手臂在該高度已略微外展，量到的不是
    純粹的肩寬（biacromial），而是含三角肌的跨距，僅供版本間比較。
    """
    shoulder_y = float(joints["l_uparm"][1])
    band = np.abs(vertices[:, 1] - shoulder_y) < SHOULDER_BAND_CM
    limb = np.isin(part_ids, [TORSO_PART, LEFT_UPPER_ARM_PART,
                              RIGHT_UPPER_ARM_PART, AMBIGUOUS])
    if not (band & limb).any():
        return
    span = float(np.ptp(vertices[band & limb, 0]))
    results["肩寬"] = {"cm": span, "measured_at_y": shoulder_y}
    print(f"\n  肩寬（肩關節高 {shoulder_y:.1f} cm 處的最大左右跨距）：{span:.1f} cm")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    vertices, faces = load_obj(EXTRACT / "body-morph-candidate3/candidate3.obj")
    part_ids = load_part_ids(PARTS / "vertex-part-ids.tsv", len(vertices))
    raw = np.loadtxt(EXTRACT / "run-fixed-clone/mhr-lod1.vertices.tsv",
                     delimiter="\t", dtype=np.float64)[:, 1:]
    scale = TARGET_HEIGHT / float(np.ptp(raw[:, 1]))
    joints = load_joints(EXTRACT / "candidate2-anatomy-audit/mhr-official-127-skeleton.tsv",
                         scale)
    print(f"candidate3：{len(vertices)} 頂點、{len(faces)} 三角形、"
          f"高度 {np.ptp(vertices[:, 1]):.2f} cm\n")

    if not self_check(vertices, faces):
        return

    results = {}
    print(f"{'部位':8s}{'骨長':>7s}  " + "".join(f"{f'{t:.0%}':>8s}" for t in (0.25, 0.5, 0.75))
          + f"{'最大':>8s}")
    for name, (part_id, bone_a, bone_b) in SEGMENTS.items():
        if bone_a not in joints or bone_b not in joints:
            print(f"  {name}: 缺骨骼 {bone_a}/{bone_b}")
            continue
        start, end = joints[bone_a], joints[bone_b]
        axis = end - start
        length = float(np.linalg.norm(axis))
        axis = axis / length
        member = (part_ids == part_id) | (part_ids == AMBIGUOUS)
        local = faces[member[faces].all(axis=1)]
        row = {}
        for t in (0.25, 0.50, 0.75):
            found = plane_perimeter(vertices, local, start + axis * (length * t), axis)
            row[f"t{int(t * 100)}"] = found[0] if found else None
            row[f"t{int(t * 100)}_closed"] = bool(found[1]) if found else False
        closed_only = [row[f"t{int(t*100)}"] for t in (0.25, 0.50, 0.75)
                       if row[f"t{int(t*100)}"] and row[f"t{int(t*100)}_closed"]]
        row["max_closed"] = max(closed_only) if closed_only else None
        row["max"] = row["max_closed"]
        row["bone_length_cm"] = length
        row["faces"] = int(len(local))
        results[name] = row
        cells = "".join(
            (f"{row[f't{int(t*100)}']:7.1f}" + ("*" if not row[f"t{int(t*100)}_closed"] else " "))
            if row[f"t{int(t*100)}"] else f"{'—':>8s}"
            for t in (0.25, 0.50, 0.75))
        print(f"  {name:8s}{length:7.1f}{cells}"
              + (f"{row['max']:8.1f}" if row["max"] else f"{'—':>8s}"))

    _measure_shoulder(vertices, part_ids, joints, results)

    (OUT / "candidate3-limb-measurements.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n寫入 {OUT / 'candidate3-limb-measurements.json'}")


if __name__ == "__main__":
    main()
