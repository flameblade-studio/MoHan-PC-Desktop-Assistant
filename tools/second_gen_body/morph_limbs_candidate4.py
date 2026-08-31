"""candidate4：在 candidate3 的軀幹成果之上，加上四肢圍度形變。

為什麼要做：幾何條件化的成品會忠實繼承控制網格的一切。candidate3 的軀幹已調到
86/71/62/90（誤差 ≤0.5 cm），但形變器只動得了 1,731 個軀幹頂點，四肢原封不動。
量測顯示上臂圍 34.4 cm，落在中國成人女性 20-29 歲常模的第 94 百分位，
而軀幹的腰圍 62 cm 約在第 10 百分位——這個不一致就是成品體態讀起來怪的來源。

做法沿用 candidate3 的形狀：沿一條軸做連續的局部縮放，只是軸從「垂直的 y」
換成「沿骨鏈的弧長」。分區用 skin-weight-parts 的逐頂點解剖 ID，不用幾何猜測。

三個必須守住的性質，每一個都在最後逐項驗證，任一不過就中止：
  1. 軀幹四個斷面完全不變——大腿頂端（88.1 cm）高於臀圍量測面（84 cm），
     兩者重疊，所以大腿縮放必須在髖關節收斂回 1.0
  2. 拓樸不變：18,439 頂點、36,874 三角形
  3. 非四肢頂點位移恆為零
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
EXTRACT = ROOT / "artifacts/pose-atlas-rebuild/2026-08-25/ufbx-lod1-extractor-agent-a"
PARTS = ROOT / "artifacts/pose-atlas-rebuild/2026-08-25/skin-weight-parts-agent-a"
OUT = ROOT / "work/second-gen-body/limb-morph"
TARGET_HEIGHT = 168.0
VERTEX_COUNT, FACE_COUNT = 18_439, 36_874

# 官方斷面（candidate3-report.json），本形變不得改變任何一個
TORSO_SECTIONS = {
    "hip": (0.50, 90.06925217482814),
    "waist": (0.62, 62.21390939635582),
    "underbust": (0.70, 70.97000216616336),
    "bust": (0.74, 86.31052117057369),
}

# 常模：Alpha3Ds 3D 體掃，中國成人女性 20-29 歲（n=215）的分位數，單位 cm
NORMS = {
    "uparm": (21.64, 24.37, 26.76, 30.15, 34.58),
    "lowarm": (20.74, 22.52, 23.91, 25.67, 28.54),
    "upleg": (47.44, 51.58, 54.82, 59.21, 66.94),
    "lowleg": (32.05, 34.88, 36.86, 39.34, 44.67),
}
PERCENTILE_POINTS = (5, 25, 50, 75, 95)

# candidate3 實測的最大封閉截面圍度，連同「量在骨段的哪個位置」一起記下來。
# 位置必須記住：第一版驗證取 t=0.35/0.50/0.65 的最大值，而基準是在各自的
# 最大位置量的，兩者不是同一點——上臂因此被誤報成只達成 -13.7%，
# 實際上該點的截面已從 11.47x10.34 縮到 8.16x7.35 cm，正好命中目標。
CURRENT = {
    "uparm": (34.4, 0.50),
    "lowarm": (26.3, 0.25),
    "upleg": (56.9, 0.25),
    "lowleg": (37.7, 0.25),
}

# 每條肢鏈：部位 ID 序列與對應的骨骼節點。末端（手／腳）不縮放，
# 鏈的兩端把縮放收斂回 1.0，避免在肩、腕、髖、踝留下接縫。
CHAINS = {
    "l_arm": ([3, 4], ["l_uparm", "l_lowarm", "l_wrist"], ["uparm", "lowarm"]),
    "r_arm": ([6, 7], ["r_uparm", "r_lowarm", "r_wrist"], ["uparm", "lowarm"]),
    "l_leg": ([9, 10], ["l_upleg", "l_lowleg", "l_foot"], ["upleg", "lowleg"]),
    "r_leg": ([12, 13], ["r_upleg", "r_lowleg", "r_foot"], ["upleg", "lowleg"]),
}
TAPER = 0.18          # 鏈兩端各 18% 弧長內把縮放平滑收回 1.0
AMBIGUOUS = 255


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_obj(path: Path) -> tuple[np.ndarray, np.ndarray]:
    vertices, faces = [], []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("v "):
                vertices.append([float(v) for v in line.split()[1:4]])
            elif line.startswith("f "):
                faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:4]])
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
                [float(row["x"]), float(row["y"]), float(row["z"])], np.float64) * scale
    return joints


def plane_loop(vertices, faces, origin, normal):
    """三角形與平面的精確交線，回傳（最大環周長, 是否封閉）。"""
    from collections import defaultdict
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
        if len(points) >= 2:
            segments.append((points[0], points[1]))
    if not segments:
        return None
    key = lambda p: tuple(np.round(p, 6))
    adjacency = defaultdict(list)
    for a, b in segments:
        length = float(np.linalg.norm(b - a))
        adjacency[key(a)].append((key(b), length))
        adjacency[key(b)].append((key(a), length))
    seen, best, closed_best = set(), 0.0, False
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
        if total / 2.0 > best:
            best = total / 2.0
            closed_best = all(len(adjacency[n]) == 2 for n in nodes)
    return (best, closed_best) if best > 0 else None


def project_to_chain(points: np.ndarray, nodes: np.ndarray):
    """把頂點投影到骨鏈折線，回傳（弧長參數 0..1, 徑向向量, 軸上最近點）。"""
    lengths = np.linalg.norm(np.diff(nodes, axis=0), axis=1)
    cumulative = np.concatenate([[0.0], np.cumsum(lengths)])
    total = float(cumulative[-1])
    best_distance = np.full(len(points), np.inf)
    best_arc = np.zeros(len(points))
    best_foot = np.zeros_like(points)
    for index in range(len(nodes) - 1):
        a, b = nodes[index], nodes[index + 1]
        direction = b - a
        span = float(np.dot(direction, direction))
        t = np.clip(((points - a) @ direction) / span, 0.0, 1.0)
        foot = a + t[:, None] * direction
        distance = np.linalg.norm(points - foot, axis=1)
        better = distance < best_distance
        best_distance[better] = distance[better]
        best_arc[better] = (cumulative[index] + t[better] * lengths[index]) / total
        best_foot[better] = foot[better]
    return best_arc, points - best_foot, best_foot


def scale_field(arc: np.ndarray, segment_scales: list[float],
                taper_start: float = 0.0) -> np.ndarray:
    """沿弧長的連續縮放場：兩端收斂回 1.0，段間平滑過渡。

    節點取 [0, 0.5/n, 1.5/n, ..., 1]，值取 [1, s1, s2, ..., 1]，
    再以 smoothstep 在節點間插值——比線性插值少一階不連續，
    不會在肘、膝留下折線。
    """
    count = len(segment_scales)
    knots = [0.0] + [(i + 0.5) / count for i in range(count)] + [1.0]
    values = [1.0] + list(segment_scales) + [1.0]
    result = np.ones_like(arc)
    for index in range(len(knots) - 1):
        low, high = knots[index], knots[index + 1]
        inside = (arc >= low) & (arc <= high)
        if not inside.any():
            continue
        t = (arc[inside] - low) / max(high - low, 1e-9)
        smooth = t * t * (3.0 - 2.0 * t)
        result[inside] = values[index] + (values[index + 1] - values[index]) * smooth
    # 端點附近再乘一層收斂，確保與軀幹／手腳的接縫處完全不動。
    # taper_start 讓收斂的起點往後推：腿鏈的臀圍量測面落在弧長約 5% 處，
    # 若從 0 起算，收斂還沒完成就跨過量測面，臀圍會被改掉 0.15 cm——
    # 而 90.07 是擁有者核可的數字，不可動。
    head = np.clip((arc - taper_start) / TAPER, 0.0, 1.0)
    tail = np.clip((1.0 - arc) / TAPER, 0.0, 1.0)
    edge = np.minimum(head, tail)
    edge = edge * edge * (3.0 - 2.0 * edge)
    return 1.0 + (result - 1.0) * edge


def targets_at(percentile: float) -> dict[str, float]:
    return {name: float(np.interp(percentile, PERCENTILE_POINTS, NORMS[name]))
            for name in NORMS}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--percentile", type=float, required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    base, faces = load_obj(EXTRACT / "body-morph-candidate3/candidate3.obj")
    if base.shape != (VERTEX_COUNT, 3) or faces.shape != (FACE_COUNT, 3):
        raise SystemExit(f"意外的網格規模 {base.shape} {faces.shape}")
    part_ids = load_part_ids(PARTS / "vertex-part-ids.tsv", len(base))
    raw = np.loadtxt(EXTRACT / "run-fixed-clone/mhr-lod1.vertices.tsv",
                     delimiter="\t", dtype=np.float64)[:, 1:]
    scale = TARGET_HEIGHT / float(np.ptp(raw[:, 1]))
    joints = load_joints(EXTRACT / "candidate2-anatomy-audit/mhr-official-127-skeleton.tsv",
                         scale)

    goals = targets_at(args.percentile)
    ratios = {name: goals[name] / CURRENT[name][0] for name in goals}
    print(f"目標百分位 P{args.percentile:g}")
    for name in ("uparm", "lowarm", "upleg", "lowleg"):
        print(f"  {name:7s} {CURRENT[name][0]:6.1f} → {goals[name]:6.1f} cm"
              f"   縮放 {ratios[name]:.4f}（{ratios[name]-1:+.1%}）")

    # 375 個關節模糊頂點（part 255）必須跟著最近的那條肢鏈一起動。
    # 第一版把它們排除在形變之外、卻納入量測，結果上臂只達成 -13.7%
    # 而非目標的 -29.2%，而且會在肘、膝留下摺痕。
    chain_nodes = {name: np.asarray([joints[b] for b in bones])
                   for name, (_, bones, _) in CHAINS.items()}
    ambiguous_index = np.flatnonzero(part_ids == AMBIGUOUS)
    ambiguous_owner: dict[str, list[int]] = {name: [] for name in CHAINS}
    if len(ambiguous_index):
        distances = {}
        for name, nodes in chain_nodes.items():
            _arc, radial, _foot = project_to_chain(base[ambiguous_index], nodes)
            distances[name] = np.linalg.norm(radial, axis=1)
        stacked = np.vstack([distances[name] for name in CHAINS])
        nearest = np.asarray(list(CHAINS))[stacked.argmin(axis=0)]
        for name in CHAINS:
            ambiguous_owner[name] = ambiguous_index[nearest == name].tolist()

    result = base.copy()
    touched = np.zeros(len(base), bool)
    floor_probe = float(base[:, 1].min())
    height_probe = float(np.ptp(base[:, 1]))
    hip_plane_y = floor_probe + TORSO_SECTIONS["hip"][0] * height_probe
    for chain, (part_sequence, bone_sequence, norm_sequence) in CHAINS.items():
        nodes = chain_nodes[chain]
        index = np.concatenate([
            np.flatnonzero(np.isin(part_ids, part_sequence)),
            np.asarray(ambiguous_owner[chain], dtype=np.int64),
        ]).astype(np.int64)
        arc, radial, foot = project_to_chain(base[index], nodes)
        taper_start = 0.0
        if chain.endswith("_leg"):
            # 把收斂起點推到臀圍量測面之下，該面以上完全不動
            leg_arc, _r, _f = project_to_chain(
                np.asarray([[nodes[0][0], hip_plane_y, nodes[0][2]]]), nodes)
            taper_start = float(leg_arc[0]) + 0.015
        field = scale_field(arc, [ratios[name] for name in norm_sequence], taper_start)
        result[index] = foot + radial * field[:, None]
        touched[index] = True
    print(f"\n受影響頂點 {int(touched.sum())}（四肢＋關節模糊帶），"
          f"未受影響 {int((~touched).sum())}")

    displacement = np.linalg.norm(result - base, axis=1)
    problems = []
    if float(displacement[~touched].max(initial=0.0)) != 0.0:
        problems.append("非四肢頂點被移動")
    print(f"非四肢頂點最大位移 {displacement[~touched].max(initial=0.0):.10f} cm")

    print("\n── 軀幹斷面必須完全不變 ──")
    floor = float(result[:, 1].min())
    height = float(np.ptp(result[:, 1]))
    up = np.asarray([0.0, 1.0, 0.0])
    sections = {}
    for name, (fraction, official) in TORSO_SECTIONS.items():
        found = plane_loop(result, faces, np.asarray([0.0, floor + fraction * height, 0.0]), up)
        measured = found[0] if found else None
        delta = abs(measured - official) if measured else float("inf")
        sections[name] = {"official": official, "after": measured, "delta_cm": delta}
        flag = "OK" if delta <= 0.01 else "← 已改變"
        if delta > 0.01:
            problems.append(f"軀幹斷面 {name} 改變 {delta:.3f} cm")
        print(f"  {name:10s} {official:7.2f} → {measured:7.2f}  差 {delta:.4f} cm  {flag}")

    print("\n── 四肢是否命中目標 ──")
    achieved = {}
    for chain, (part_sequence, bone_sequence, norm_sequence) in CHAINS.items():
        if not chain.startswith("l_"):
            continue
        nodes = np.asarray([joints[name] for name in bone_sequence])
        for position, (part_id, norm_name) in enumerate(zip(part_sequence, norm_sequence)):
            a, b = nodes[position], nodes[position + 1]
            axis = (b - a) / np.linalg.norm(b - a)
            member = (part_ids == part_id) | (part_ids == AMBIGUOUS)
            local = faces[member[faces].all(axis=1)]
            # 量在與基準完全相同的位置，否則比較的不是同一件事
            spot = CURRENT[norm_name][1]
            found = plane_loop(result, local, a + axis * (np.linalg.norm(b - a) * spot), axis)
            value = found[0] if (found and found[1]) else None
            achieved[norm_name] = value
            if value is None:
                print(f"  {norm_name:7s} t={spot:.2f} 處量不到封閉環")
                continue
            print(f"  {norm_name:7s} t={spot:.2f}  基準 {CURRENT[norm_name][0]:6.1f}"
                  f"  目標 {goals[norm_name]:6.1f}  實得 {value:6.1f} cm"
                  f"   差 {value - goals[norm_name]:+5.1f}")

    if problems:
        print("\n驗證未通過：" + "；".join(problems))
        raise SystemExit(1)

    stem = OUT / f"candidate4-{args.tag}"
    with (stem.with_suffix(".obj")).open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(f"# MHR candidate4 limb morph P{args.percentile:g} on candidate3 torso\n")
        stream.write("o mhr_body_candidate4\n")
        for vertex in result:
            stream.write(f"v {vertex[0]:.10f} {vertex[1]:.10f} {vertex[2]:.10f}\n")
        for face in faces:
            stream.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
    report = {
        "status": "CANDIDATE_4_LIMB_MORPH_PENDING_OWNER_REVIEW",
        "base": "candidate3.obj",
        "base_sha256": sha256(EXTRACT / "body-morph-candidate3/candidate3.obj"),
        "percentile": args.percentile,
        "norm_source": ("Alpha3Ds 3D body scanning normative values, Chinese adults, "
                        "female 20-29 (n=215); PMC12620412"),
        "norm_caveat": ("該研究未公布各圍度的解剖量測點；本工具量的是垂直骨軸的"
                        "最大封閉截面，定義可能不完全相同，比較為指示性"),
        "current_cm": {k: v[0] for k, v in CURRENT.items()},
        "measured_at_t": {k: v[1] for k, v in CURRENT.items()},
        "target_cm": goals,
        "scale_ratio": ratios,
        "achieved_cm": achieved,
        "torso_sections": sections,
        "touched_vertices": int(touched.sum()),
        "untouched_max_displacement_cm": float(displacement[~touched].max(initial=0.0)),
        "topology": {"vertices": VERTEX_COUNT, "triangles": FACE_COUNT, "unchanged": True},
        "height_cm": height,
    }
    stem.with_suffix(".json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n寫入 {stem.with_suffix('.obj')}")
    print("CANDIDATE4_OK")


if __name__ == "__main__":
    main()
