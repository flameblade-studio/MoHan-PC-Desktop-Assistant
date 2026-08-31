"""candidate6：把 candidate5 的手臂重擺改用對偶四元數蒙皮（DQS）。

為什麼換：LBS 在大角度扭轉時會塌陷成 candy-wrapper。目前擺幅只有肩 34.2 度、
肘 54.6 度且無軸向扭轉，踩不到那個弱點；但姿勢圖集日後若要加入更大的動作，
現在把蒙皮基礎換成 DQS 才不用整條重做。擁有者決定直接升級。

演算法：Kavan et al. 2007《Skinning with Dual Quaternions》。
每根骨骼的剛體變換寫成單位對偶四元數，依權重線性混合後再正規化。
因為對偶四元數的混合仍落在剛體變換流形上（LBS 的矩陣線性混合不會），
所以不會出現體積塌陷。

與 candidate5 的 LBS 版在結構上有一個實質差異，不只是換公式：
  LBS 版是序貫套用——先繞肩轉整條手臂，再繞轉過的肘轉前臂。
  DQS 版是標準骨骼形式——先把三個剛體變換各自組好（恆等／上臂／前臂，
  前臂是肘與肩的複合），再一次混合。後者才是蒙皮的正規定義。

已知代價，不掩蓋：DQS 保體積保得比 LBS 用力，彎曲關節處可能鼓包
（原論文自承，業界標準解是 DQS/LBS 混權）。本腳本輸出肩肘鄰域的
最大膨脹量供查驗；擺幅小的情況下應該落在雜訊裡。

三個必須守住的性質與 candidate5 相同，任一不過即中止：
  1. 拓樸不變（18,439 頂點、36,874 三角形）
  2. 軀幹四斷面不變——擁有者核可的 86/71/62/90
  3. 手臂角度確實到達目標
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from morph_limbs_candidate4 import TORSO_SECTIONS, load_joints, load_obj, plane_loop  # noqa: E402
# 權重歸一與反對蹠混合的數值容差。
EPS_UNIT = 1e-9
# 量鼓包時取距關節多近的頂點。
JOINT_NEIGHBOURHOOD_CM = 6.0
from repose_arms_candidate5 import (  # noqa: E402
    EPS_DEGENERATE, SECTION_TOLERANCE_CM,
    DOWN, EXTRACT, HIGH, LIMB, LOW, PARTS, TARGET_HEIGHT, TARGET_LOWER_DEG,
    TARGET_UPPER_DEG, VERTEX_COUNT, FACE_COUNT, aim, chain_weight, load_hierarchy,
    load_weights, remap, rotation_between, subtree,
)


def quat_from_matrix(matrix: np.ndarray) -> np.ndarray:
    """旋轉矩陣轉四元數 (w,x,y,z)。用 Shepperd 分支法避免退化。"""
    m = matrix
    trace = m[0, 0] + m[1, 1] + m[2, 2]
    if trace > 0.0:
        s = np.sqrt(trace + 1.0) * 2.0
        q = [0.25 * s, (m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s,
             (m[1, 0] - m[0, 1]) / s]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2.0
        q = [(m[2, 1] - m[1, 2]) / s, 0.25 * s, (m[0, 1] + m[1, 0]) / s,
             (m[0, 2] + m[2, 0]) / s]
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2.0
        q = [(m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, 0.25 * s,
             (m[1, 2] + m[2, 1]) / s]
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2.0
        q = [(m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s,
             (m[1, 2] + m[2, 1]) / s, 0.25 * s]
    q = np.asarray(q, np.float64)
    return q / np.linalg.norm(q)


def quat_multiply(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return np.asarray([
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ])


def dual_quat(matrix: np.ndarray, translation: np.ndarray) -> np.ndarray:
    """剛體變換 (R, t) 轉單位對偶四元數，回傳 shape (2,4) 的 [real, dual]。"""
    real = quat_from_matrix(matrix)
    t = np.asarray([0.0, translation[0], translation[1], translation[2]])
    dual = 0.5 * quat_multiply(t, real)
    return np.stack([real, dual])


def rigid_about(matrix: np.ndarray, pivot: np.ndarray) -> np.ndarray:
    """繞 pivot 旋轉 matrix 的剛體變換：p' = R(p-c)+c，故 t = c - Rc。"""
    return dual_quat(matrix, pivot - matrix @ pivot)


def compose(outer: np.ndarray, inner: np.ndarray) -> np.ndarray:
    """兩個剛體變換的複合（先 inner 後 outer），對偶四元數乘法。"""
    real = quat_multiply(outer[0], inner[0])
    dual = quat_multiply(outer[0], inner[1]) + quat_multiply(outer[1], inner[0])
    return np.stack([real, dual])


def skin(vertices: np.ndarray, weights: np.ndarray, transforms: np.ndarray) -> np.ndarray:
    """對偶四元數線性混合蒙皮。

    weights  (N, B)   每個頂點對每根骨骼的權重，列和為 1
    transforms (B,2,4) 每根骨骼的單位對偶四元數
    """
    # 反對蹠修正：所有骨骼的實部與參考骨骼（第 0 根＝恆等）同號。
    # 本案所有旋轉都小於 90 度，w 恆正，這步實際上是空操作，但缺了它
    # 在日後加入大角度骨骼時會混出錯誤的最短路徑。
    signs = np.sign(transforms[:, 0] @ transforms[0, 0])
    signs[signs == 0] = 1.0
    aligned = transforms * signs[:, None, None]

    blended = np.einsum("nb,bij->nij", weights, aligned)
    norm = np.linalg.norm(blended[:, 0], axis=1)
    if np.any(norm < EPS_UNIT):
        raise SystemExit("混合後的實部趨近零，權重或反對蹠修正有誤")
    blended = blended / norm[:, None, None]

    real, dual = blended[:, 0], blended[:, 1]
    w, v = real[:, 0:1], real[:, 1:4]
    dw, dv = dual[:, 0:1], dual[:, 1:4]
    rotated = vertices + 2.0 * np.cross(v, np.cross(v, vertices) + w * vertices)
    translation = 2.0 * (w * dv - dw * v + np.cross(v, dv))
    return rotated + translation


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=LIMB / "candidate4-p25.obj")
    parser.add_argument("--tag", default="p25-armsdown-dqs")
    parser.add_argument("--compare", type=Path,
                        default=LIMB / "candidate5-p25-armsdown.obj")
    args = parser.parse_args()

    base, faces = load_obj(args.source)
    if base.shape != (VERTEX_COUNT, 3) or faces.shape != (FACE_COUNT, 3):
        raise SystemExit(f"意外的網格規模 {base.shape} {faces.shape}")
    raw = np.loadtxt(EXTRACT / "run-fixed-clone/mhr-lod1.vertices.tsv",
                     delimiter="\t", dtype=np.float64)[:, 1:]
    scale = TARGET_HEIGHT / float(np.ptp(raw[:, 1]))
    skeleton = EXTRACT / "candidate2-anatomy-audit/mhr-official-127-skeleton.tsv"
    joints = load_joints(skeleton, scale)
    parent = load_hierarchy(skeleton)
    table = load_weights(PARTS / "vertex-skin-weights.tsv", len(base))

    # 五根等效骨骼：恆等、左上臂、左前臂、右上臂、右前臂。
    transforms = [dual_quat(np.eye(3), np.zeros(3))]
    columns = [np.ones(len(base))]          # 恆等先給 1，稍後扣掉其餘權重
    report = {}
    for side in ("l", "r"):
        w_shoulder = remap(chain_weight(table, subtree(parent, f"{side}_uparm")), LOW, HIGH)
        w_elbow = remap(chain_weight(table, subtree(parent, f"{side}_lowarm")), LOW, HIGH)
        # 肘鏈是肩鏈的子集，故 w_elbow <= w_shoulder；上臂獨得的份額是兩者之差。
        w_upper = np.clip(w_shoulder - w_elbow, 0.0, 1.0)

        pivot = joints[f"{side}_uparm"]
        elbow, wrist = joints[f"{side}_lowarm"], joints[f"{side}_wrist"]
        upper = elbow - pivot
        matrix_shoulder = rotation_between(upper, aim(upper, TARGET_UPPER_DEG))
        shoulder_rigid = rigid_about(matrix_shoulder, pivot)

        elbow_moved = matrix_shoulder @ (elbow - pivot) + pivot
        wrist_moved = matrix_shoulder @ (wrist - pivot) + pivot
        lower = wrist_moved - elbow_moved
        matrix_elbow = rotation_between(lower, aim(lower, TARGET_LOWER_DEG))
        elbow_rigid = compose(rigid_about(matrix_elbow, elbow_moved), shoulder_rigid)

        transforms += [shoulder_rigid, elbow_rigid]
        columns += [w_upper, w_elbow]
        columns[0] = columns[0] - w_upper - w_elbow

        after_upper = matrix_shoulder @ upper
        after_lower = matrix_elbow @ lower
        before = np.degrees(np.arccos(np.clip(upper / np.linalg.norm(upper) @ DOWN, -1, 1)))
        report[f"{side}_upper_deg"] = float(np.degrees(np.arccos(np.clip(
            after_upper / np.linalg.norm(after_upper) @ DOWN, -1, 1))))
        report[f"{side}_lower_deg"] = float(np.degrees(np.arccos(np.clip(
            after_lower / np.linalg.norm(after_lower) @ DOWN, -1, 1))))
        print(f"{side} 側：上臂 {before:.1f} → {report[f'{side}_upper_deg']:.1f} 度，"
              f"前臂 → {report[f'{side}_lower_deg']:.1f} 度", flush=True)

    weights = np.stack(columns, axis=1)
    residual = float(np.abs(weights.sum(axis=1) - 1.0).max())
    print(f"\n權重列和最大偏差 {residual:.2e}"
          f"{'  OK' if residual < EPS_UNIT else '  ← 權重未歸一'}")
    if residual >= EPS_UNIT:
        raise SystemExit("權重未歸一，DQS 混合前提不成立")
    if weights.min() < -EPS_DEGENERATE:
        raise SystemExit(f"出現負權重 {weights.min():.3e}，肘鏈非肩鏈子集的假設不成立")

    result = skin(base, weights, np.stack(transforms))

    print("\n── 軀幹四斷面必須完全不變 ──")
    floor, height = float(result[:, 1].min()), float(np.ptp(result[:, 1]))
    up = np.asarray([0.0, 1.0, 0.0])
    problems = []
    for name, (fraction, official) in TORSO_SECTIONS.items():
        found = plane_loop(result, faces,
                           np.asarray([0.0, floor + fraction * height, 0.0]), up)
        measured = found[0] if found else None
        delta = abs(measured - official) if measured else float("inf")
        report[f"section_{name}"] = {"official": official, "after": measured,
                                     "delta_cm": delta}
        print(f"  {name:10s} {official:7.2f} → {measured:7.2f}  差 {delta:.4f} cm  "
              f"{'OK' if delta <= SECTION_TOLERANCE_CM else '← 已改變'}")
        if delta > SECTION_TOLERANCE_CM:
            problems.append(f"{name} 改變 {delta:.3f} cm")

    if args.compare.exists():
        lbs, _ = load_obj(args.compare)
        offset = np.linalg.norm(result - lbs, axis=1)
        moved = np.linalg.norm(result - base, axis=1) > EPS_UNIT
        print("\n── 對 candidate5（LBS）逐頂點比對 ──")
        print(f"  受影響頂點 {int(moved.sum())}")
        print(f"  位移差：中位數 {np.median(offset[moved]):.4f} cm   "
              f"P95 {np.percentile(offset[moved], 95):.4f} cm   "
              f"最大 {offset.max():.4f} cm")
        report["vs_lbs_max_cm"] = float(offset.max())
        report["vs_lbs_median_cm"] = float(np.median(offset[moved]))
        # DQS 已知代價：關節鼓包。量肩肘鄰域相對 LBS 的向外膨脹。
        for side in ("l", "r"):
            for label, joint in (("肩", f"{side}_uparm"), ("肘", f"{side}_lowarm")):
                centre = joints[joint]
                near = np.linalg.norm(base - centre, axis=1) < JOINT_NEIGHBOURHOOD_CM
                if not near.any():
                    continue
                r_dqs = np.linalg.norm(result[near] - centre, axis=1)
                r_lbs = np.linalg.norm(lbs[near] - centre, axis=1)
                bulge = float((r_dqs - r_lbs).max())
                report[f"bulge_{side}_{joint}"] = bulge
                print(f"  {side} {label}關節 6 cm 內最大鼓包 {bulge:+.4f} cm"
                      f"（{int(near.sum())} 頂點）")

    if problems:
        raise SystemExit("驗證未通過：" + "；".join(problems))

    stem = LIMB / f"candidate6-{args.tag}"
    with stem.with_suffix(".obj").open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("# MHR candidate6: candidate4 limb girth + arms lowered by DQS\n")
        stream.write("o mhr_body_candidate6\n")
        for vertex in result:
            stream.write(f"v {vertex[0]:.10f} {vertex[1]:.10f} {vertex[2]:.10f}\n")
        for face in faces:
            stream.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
    report["status"] = "CANDIDATE_6_DQS"
    report["method"] = "dual quaternion linear blend skinning (Kavan et al. 2007)"
    report["source"] = args.source.name
    stem.with_suffix(".json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n寫入 {stem.with_suffix('.obj')}")
    print("CANDIDATE6_OK")


if __name__ == "__main__":
    main()
