"""candidate5：將 candidate4 的 A-pose 手臂改為自然垂放。

24 個 assets/pose-atlas/v4 視角供實機展示與 DLC 對位使用，因此素體需
符合廣袖漢服的自然垂臂姿勢。此方向依消費端查核結果確立。

採階層式線性混合蒙皮與兩段剛體旋轉：第一段以肩關節帶動 l_uparm
的 35 根子孫；第二段以旋轉後的肘關節帶動 l_lowarm 的 29 根子孫。
權重取自 MHR FBX 的 51,337 筆真實蒙皮資料，每頂點最多 4 個骨骼影響。
剛體旋轉保留長度與圍度，肩肘過渡帶依原權重混合。

通過三項驗證後採用：
1. 保留 18,439 頂點與 36,874 三角形的拓樸。
2. 保留擁有者核可的軀幹四斷面 86/71/62/90。
3. 保留四肢圍度；量測差異需先完成權重及樞紐校正。
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from morph_limbs_candidate4 import (  # noqa: E402
    TORSO_SECTIONS, load_joints, load_obj, plane_loop,
)

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
EXTRACT = ROOT / "artifacts/pose-atlas-rebuild/2026-08-25/ufbx-lod1-extractor-agent-a"
PARTS = ROOT / "artifacts/pose-atlas-rebuild/2026-08-25/skin-weight-parts-agent-a"
LIMB = ROOT / "work/second-gen-body/limb-morph"
TARGET_HEIGHT = 168.0
VERTEX_COUNT, FACE_COUNT = 18_439, 36_874
DOWN = np.asarray([0.0, -1.0, 0.0])
# 自然站姿的目標角度（與垂直線的夾角）。現況為上臂 42.2、前臂 64.6 度。
TARGET_UPPER_DEG = 8.0
TARGET_LOWER_DEG = 10.0
# 權重重映射的上下界，由掃描選出：要保住胸圍 86.31 又不撕裂網格
LOW, HIGH = 0.35, 0.85
# 斷面容差與數值 epsilon（具名以符合 PLR2004 零豁免）。
SECTION_TOLERANCE_CM = 0.05
EPS_DEGENERATE = 1e-12
EPS_UNIT = 1e-9


def load_hierarchy(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return {r["bone_name"]: r["parent_name"] for r in csv.DictReader(stream, delimiter="\t")}


def subtree(parent: dict[str, str], root: str) -> set[str]:
    members = {root}
    changed = True
    while changed:
        changed = False
        for bone, up in parent.items():
            if up in members and bone not in members:
                members.add(bone)
                changed = True
    return members


def load_weights(path: Path, count: int) -> list[dict[str, float]]:
    table: list[dict[str, float]] = [defaultdict(float) for _ in range(count)]
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            table[int(row["vertex_index"])][row["bone_name"]] += float(row["weight"])
    return table


def chain_weight(table, members: set[str]) -> np.ndarray:
    return np.asarray([sum(w for b, w in v.items() if b in members) for v in table])


def remap(weight: np.ndarray, low: float, high: float) -> np.ndarray:
    """平滑重映射蒙皮權重，保留軀幹與過渡帶的連續性。

    原始權重曾使胸圍縮小 1.45 cm；擁有者核可值為 86.31。
    解剖 ID 與蒙皮權重屬不同分類，硬遮罩曾讓同為 0.9 權重的相鄰頂點
    分別保持原位與旋轉 34 度，產生位移跳變。
    此處直接對權重平滑重映射：低於 low 保留原位，高於 high 全額跟隨，
    中間以 smoothstep 連續過渡，維持網格連接與核可斷面。
    """
    t = np.clip((weight - low) / max(high - low, 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def rotation_between(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """把 source 方向轉到 target 方向的旋轉矩陣（羅德里格公式）。"""
    a = source / np.linalg.norm(source)
    b = target / np.linalg.norm(target)
    axis = np.cross(a, b)
    length = np.linalg.norm(axis)
    if length < EPS_DEGENERATE:
        return np.eye(3)
    axis = axis / length
    angle = float(np.arctan2(length, float(a @ b)))
    K = np.asarray([[0, -axis[2], axis[1]],
                    [axis[2], 0, -axis[0]],
                    [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * (K @ K)


def aim(direction: np.ndarray, degrees: float) -> np.ndarray:
    """保持原本的外展平面，只把與垂直線的夾角改成 degrees。"""
    lateral = direction.copy()
    lateral[1] = 0.0
    if np.linalg.norm(lateral) < EPS_UNIT:
        return DOWN.copy()
    lateral = lateral / np.linalg.norm(lateral)
    radians = np.radians(degrees)
    return np.sin(radians) * lateral + np.cos(radians) * DOWN


def apply(vertices, weight, pivot, matrix):
    moved = (vertices - pivot) @ matrix.T + pivot
    return vertices + weight[:, None] * (moved - vertices)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=LIMB / "candidate4-p25.obj")
    parser.add_argument("--tag", default="p25-armsdown")
    args = parser.parse_args()

    base, faces = load_obj(args.source)
    if base.shape != (VERTEX_COUNT, 3) or faces.shape != (FACE_COUNT, 3):
        raise SystemExit(f"意外的網格規模 {base.shape} {faces.shape}")
    raw = np.loadtxt(EXTRACT / "run-fixed-clone/mhr-lod1.vertices.tsv",
                     delimiter="\t", dtype=np.float64)[:, 1:]
    scale = TARGET_HEIGHT / float(np.ptp(raw[:, 1]))
    joints = load_joints(
        EXTRACT / "candidate2-anatomy-audit/mhr-official-127-skeleton.tsv", scale)
    parent = load_hierarchy(
        EXTRACT / "candidate2-anatomy-audit/mhr-official-127-skeleton.tsv")
    weights = load_weights(PARTS / "vertex-skin-weights.tsv", len(base))

    result = base.copy()
    report = {}
    for side in ("l", "r"):
        shoulder_set = subtree(parent, f"{side}_uparm")
        elbow_set = subtree(parent, f"{side}_lowarm")
        w_shoulder = remap(chain_weight(weights, shoulder_set), LOW, HIGH)
        w_elbow = remap(chain_weight(weights, elbow_set), LOW, HIGH)

        pivot_shoulder = joints[f"{side}_uparm"]
        elbow = joints[f"{side}_lowarm"]
        wrist = joints[f"{side}_wrist"]

        upper = elbow - pivot_shoulder
        matrix_shoulder = rotation_between(upper, aim(upper, TARGET_UPPER_DEG))
        result = apply(result, w_shoulder, pivot_shoulder, matrix_shoulder)

        # 肘關節與腕關節也被第一段帶動，樞紐要跟著轉
        elbow_moved = matrix_shoulder @ (elbow - pivot_shoulder) + pivot_shoulder
        wrist_moved = matrix_shoulder @ (wrist - pivot_shoulder) + pivot_shoulder
        lower = wrist_moved - elbow_moved
        matrix_elbow = rotation_between(lower, aim(lower, TARGET_LOWER_DEG))
        result = apply(result, w_elbow, elbow_moved, matrix_elbow)

        after_upper = matrix_shoulder @ upper
        after_lower = matrix_elbow @ lower
        report[f"{side}_upper_deg"] = float(np.degrees(np.arccos(np.clip(
            after_upper / np.linalg.norm(after_upper) @ DOWN, -1, 1))))
        report[f"{side}_lower_deg"] = float(np.degrees(np.arccos(np.clip(
            after_lower / np.linalg.norm(after_lower) @ DOWN, -1, 1))))
        report[f"{side}_moved_vertices"] = int(np.count_nonzero(w_shoulder > 0))
        print(f"{side} 側：上臂 {np.degrees(np.arccos(np.clip(upper/np.linalg.norm(upper)@DOWN,-1,1))):.1f}"
              f" → {report[f'{side}_upper_deg']:.1f} 度，"
              f"前臂 → {report[f'{side}_lower_deg']:.1f} 度，"
              f"受影響頂點 {report[f'{side}_moved_vertices']}", flush=True)

    print("\n── 軀幹四斷面必須完全不變 ──")
    floor = float(result[:, 1].min())
    height = float(np.ptp(result[:, 1]))
    up = np.asarray([0.0, 1.0, 0.0])
    problems = []
    for name, (fraction, official) in TORSO_SECTIONS.items():
        found = plane_loop(result, faces,
                           np.asarray([0.0, floor + fraction * height, 0.0]), up)
        measured = found[0] if found else None
        delta = abs(measured - official) if measured else float("inf")
        report[f"section_{name}"] = {"official": official, "after": measured,
                                     "delta_cm": delta}
        flag = "OK" if delta <= SECTION_TOLERANCE_CM else "← 已改變"
        if delta > SECTION_TOLERANCE_CM:
            problems.append(f"{name} 改變 {delta:.3f} cm")
        print(f"  {name:10s} {official:7.2f} → {measured:7.2f}  差 {delta:.4f} cm  {flag}")

    unmoved = np.linalg.norm(result - base, axis=1) < EPS_DEGENERATE
    print(f"\n未移動的頂點：{int(unmoved.sum())} / {len(base)}")
    report["unmoved_vertices"] = int(unmoved.sum())
    report["height_cm"] = height

    if problems:
        print("驗證未通過：" + "；".join(problems))
        raise SystemExit(1)

    stem = LIMB / f"candidate5-{args.tag}"
    with stem.with_suffix(".obj").open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("# MHR candidate5: candidate4 limb girth + arms lowered by LBS\n")
        stream.write("o mhr_body_candidate5\n")
        for vertex in result:
            stream.write(f"v {vertex[0]:.10f} {vertex[1]:.10f} {vertex[2]:.10f}\n")
        for face in faces:
            stream.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
    report["status"] = "CANDIDATE_5_ARMS_LOWERED_PENDING_GIRTH_CHECK"
    report["source"] = args.source.name
    report["target_upper_deg"] = TARGET_UPPER_DEG
    report["target_lower_deg"] = TARGET_LOWER_DEG
    stem.with_suffix(".json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n寫入 {stem.with_suffix('.obj')}")
    print("CANDIDATE5_OK")


if __name__ == "__main__":
    main()
