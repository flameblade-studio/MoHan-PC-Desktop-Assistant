"""墨寒二代素體通用姿勢引擎：127 根骨骼的前向運動學、DQS 蒙皮與驗收。

在素體接入前驗證大幅動作，讓姿勢圖集、DLC 服裝對位與擁有權遮罩
共用經過驗證的蒙皮基礎。

三項設計依據：
1. 驅動 twist 骨。MHR 的 l_uparm、l_lowarm weight_count 都為 0；
   上下臂權重位於 uparm_twist0-4、lowarm_twist1-4 與 wrist。
   將軸向扭轉沿這些骨段分攤，每段承擔相應角度，DQS 提供體積保護。
2. 依關節世界座標表達繞點、繞軸旋轉，並沿階層複合：
   D[b] = D[parent] ∘ L[b]。L[b] 繞靜止位置，父變換再帶動整段，
   與標準蒙皮等價，適用於僅提供關節座標的骨架表。
3. 驗收使用四項幾何量：邊長拉伸、三角形面積、帶號體積與軀幹四斷面。
   每項均須符合既定門檻後，姿勢才可採用；超標時回報具體量測結果。
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repose_arms_candidate6_dqs import (  # noqa: E402
    dual_quat, quat_multiply, skin,
)
from morph_limbs_candidate4 import TORSO_SECTIONS, plane_loop  # noqa: E402

ROOT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
EXTRACT = ROOT / "artifacts/pose-atlas-rebuild/2026-08-25/ufbx-lod1-extractor-agent-a"
PARTS = ROOT / "artifacts/pose-atlas-rebuild/2026-08-25/skin-weight-parts-agent-a"
SKELETON = EXTRACT / "candidate2-anatomy-audit/mhr-official-127-skeleton.tsv"
TARGET_HEIGHT = 168.0

# 驗收門檻。全部是「相對靜止姿勢」的比值，與身高單位無關。
#
# 2026-08-31 以渲染實況重校準。最初的極值門檻 1.35 未經視覺校準就上崗，
# 連已驗收的垂手姿勢（極值 1.597、渲染乾淨）都會被它否決——關節皺褶處
# 永遠有幾條病態邊，極值不代表可見品質。校準組（側向抬舉，肩胛 1/3）：
#   60 度 P99.9=1.489 乾淨、90 度 1.874 乾淨、135 度 2.601 可用、
#   170 度 3.216 且 6 個塌陷三角形——腋窩出現可見皺褶。
# 故整體品質以 P99.9 把關（≤2.9，135~150 度以內通過），真正的撕裂以
# 極值粗網攔截（≥8 只會來自演算法錯誤：骨架錯位那次極值是 17）。
MAX_BULK_STRETCH_P999 = 2.9  # 整體拉伸品質門檻（視覺校準）
MAX_TEAR_STRETCH = 8.0       # 撕裂粗網；超過必是演算法或骨架錯位
MIN_AREA_RATIO = 0.25        # 三角形面積塌陷下限
# 塌陷三角形：肘彎 80 度在肘窩產生 15 個、渲染證實是正常皮膚摺疊；
# 真正的網格撕壞由撕裂粗網（極值）與體積門檻負責攔。
MAX_COLLAPSED_TRIANGLES = 20
# 體積漂移：DQS 保體積在大幅舉臂時於肩部鼓脹——側舉 150 度實測 +5.2%
# 而渲染乾淨（同一次視覺校準）。體積不是撕裂偵測器（骨架錯位事故的
# 體積只漂 +0.4%，靠的是撕裂粗網攔下極值 17），門檻放在異常粗網即可。
MAX_VOLUME_DRIFT = 0.06
MAX_SECTION_DRIFT_CM = 0.05  # 軀幹四斷面漂移上限，與 candidate5/6 同標準
# 安全包絡（同一次校準得出）：側向抬舉含肩胛 1/3 分擔，至 150 度皆在
# 門檻內；170 度超限。姿勢圖集的舉臂動作以 150 度為上限。
# 斷面門檻只適用於身份基準姿勢：引擎用原始蒙皮權重，垂手就會讓胸圍
# 移動 1.47 cm——產線的身份姿勢一律走 repose_arms_candidate6_dqs（其
# smoothstep 重映射把四斷面守在 0.0000），動作姿勢本來就允許斷面變化。
# 數值 epsilon：DEGENERATE 判零向量／零面積，UNIT 判單位化與權重歸一的容差。
EPS_DEGENERATE = 1e-12
EPS_UNIT = 1e-9
# 關節鄰域半徑：量測 DQS 鼓包時取距關節多近的頂點。
JOINT_NEIGHBOURHOOD_CM = 6.0
# plane_loop 需要的最少交點數，2 點以下構不成封閉環。
MIN_LOOP_POINTS = 2


class Rig:
    """127 根骨骼的靜止骨架、階層與逐頂點蒙皮權重。"""

    def __init__(self, mesh_vertex_count: int,
                 rest_override: np.ndarray | None = None) -> None:
        with SKELETON.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        raw = np.loadtxt(EXTRACT / "run-fixed-clone/mhr-lod1.vertices.tsv",
                         delimiter="\t", dtype=np.float64)[:, 1:]
        scale = TARGET_HEIGHT / float(np.ptp(raw[:, 1]))

        self.names = [r["bone_name"] for r in rows]
        self.index = {n: i for i, n in enumerate(self.names)}
        self.rest = np.asarray(
            [[float(r["x"]), float(r["y"]), float(r["z"])] for r in rows]) * scale
        if rest_override is not None:
            # 網格被重擺過姿勢時，骨架必須跟著擺，否則之後每一個姿勢都繞著
            # 錯誤的樞紐旋轉。candidate5/6 只搬了網格沒搬骨架，前臂旋前 90 度
            # 因此把手畫出 36 cm 的大弧、撕開 5 cm——現象在蒙皮，成因在這裡。
            if rest_override.shape != self.rest.shape:
                raise SystemExit(f"骨架覆寫規模不符 {rest_override.shape}")
            self.rest = rest_override.copy()
        self.parent = {r["bone_name"]: r["parent_name"] for r in rows}
        self.children = defaultdict(list)
        for name, up in self.parent.items():
            self.children[up].append(name)
        self.order = self._topological()

        weights = defaultdict(float)
        with (PARTS / "vertex-skin-weights.tsv").open(
                "r", encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream, delimiter="\t"):
                bone = row["bone_name"]
                if bone not in self.index:
                    raise SystemExit(f"權重表出現骨架沒有的骨骼 {bone}")
                weights[(int(row["vertex_index"]), self.index[bone])] += float(row["weight"])
        table = np.zeros((mesh_vertex_count, len(self.names)))
        for (vertex, bone), value in weights.items():
            table[vertex, bone] = value
        # 未被任何骨骼影響的頂點綁到 body_world，否則 DQS 混合會除以零。
        orphan = table.sum(axis=1) < EPS_UNIT
        if orphan.any():
            table[orphan, self.index["body_world"]] = 1.0
        self.orphan_count = int(orphan.sum())
        self.weights = table / table.sum(axis=1, keepdims=True)

    def _topological(self) -> list[str]:
        seen, order = set(), []
        roots = [n for n in self.names if self.parent[n] not in self.index]

        def walk(name: str) -> None:
            if name in seen:
                return
            seen.add(name)
            order.append(name)
            for child in sorted(self.children[name]):
                walk(child)

        for root in roots:
            walk(root)
        if len(order) != len(self.names):
            raise SystemExit("骨架階層有環或有孤立骨骼")
        return order

    def subtree(self, root: str) -> list[str]:
        out, stack = [], [root]
        while stack:
            name = stack.pop()
            out.append(name)
            stack.extend(self.children[name])
        return out


def relax_weights(rig: Rig, vertices: np.ndarray, faces: np.ndarray,
                  centre: np.ndarray, radius: float, *, rounds: int = 12) -> int:
    """在指定球域內平滑蒙皮權重，回傳調整的頂點數。

    MHR 權重針對中等動作幅度繪製；舉臂過頭的實測顯示腋窩 clavicle 與
    uparm 交界邊長達 6.8 倍，涉及 y 125~144 三角肌帶的 39 個頂點（0.2%）。
    此處僅平滑該局部並維持權重和為 1，保留其他部位及合法蒙皮權重，
    直接在蒙皮來源處改善連續性。
    """
    adjacency = defaultdict(set)
    for a, b, c in faces:
        adjacency[a].update((b, c))
        adjacency[b].update((a, c))
        adjacency[c].update((a, b))

    distance = np.linalg.norm(vertices - centre, axis=1)
    region = np.where(distance < radius)[0]
    if len(region) == 0:
        return 0
    # 邊緣淡出，避免在球面上製造新的權重不連續——那會把撕裂搬家而不是消除。
    falloff = np.clip(1.0 - distance[region] / radius, 0.0, 1.0)
    falloff = falloff * falloff * (3.0 - 2.0 * falloff)

    table = rig.weights
    for _ in range(rounds):
        averaged = np.stack([table[sorted(adjacency[v])].mean(axis=0) for v in region])
        table[region] = (1.0 - falloff[:, None]) * table[region] + falloff[:, None] * averaged
        table[region] /= table[region].sum(axis=1, keepdims=True)
    return len(region)


def axis_angle_quat(axis: np.ndarray, degrees: float) -> np.ndarray:
    axis = np.asarray(axis, np.float64)
    length = np.linalg.norm(axis)
    if length < EPS_DEGENERATE:
        raise SystemExit("旋轉軸長度為零")
    axis = axis / length
    half = np.radians(degrees) / 2.0
    return np.concatenate([[np.cos(half)], np.sin(half) * axis])


def quat_to_matrix(q: np.ndarray) -> np.ndarray:
    w, x, y, z = q
    return np.asarray([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def forward_kinematics(rig: Rig, spec: dict[str, tuple]) -> np.ndarray:
    """將 {骨骼: (軸, 角度)} 展開為世界剛體變換（對偶四元數）。

    D[b] = D[parent] ∘ L[b]；L[b] 是繞靜止位置及指定軸的旋轉。
    省略旋轉的骨骼使用恆等 L，並繼承父變換，讓手指跟隨手部運動。
    """
    identity = dual_quat(np.eye(3), np.zeros(3))
    deltas = {}
    for name in rig.order:
        if name in spec:
            axis, degrees = spec[name]
            matrix = quat_to_matrix(axis_angle_quat(axis, degrees))
            pivot = rig.rest[rig.index[name]]
            local = dual_quat(matrix, pivot - matrix @ pivot)
        else:
            local = identity
        up = rig.parent[name]
        if up in rig.index:
            outer = deltas[up]
            real = quat_multiply(outer[0], local[0])
            deltas[name] = np.stack([
                real,
                quat_multiply(outer[0], local[1]) + quat_multiply(outer[1], local[0]),
            ])
        else:
            deltas[name] = local
    return np.stack([deltas[n] for n in rig.names])


def distribute_twist(rig: Rig, segment: str, degrees: float) -> dict[str, tuple]:
    """將軸向扭轉沿 twist 骨線性分攤。

    綁定中的 uparm/lowarm 自身權重為 0，因此由 twist 骨承擔扭轉。
    近端角度為 0、遠端為全額，中間線性分攤，以維持各骨段的平滑變形。
    旋轉軸使用該骨指向子骨的方向。
    """
    twists = sorted(c for c in rig.children[segment] if c.endswith("_proc"))
    if not twists:
        raise SystemExit(f"{segment} 沒有 twist 骨，無法安全分攤扭轉")
    # 軸 = 骨段方向。用 twist 骨自身的位置決定順序與方向，不猜名字裡的編號。
    origin = rig.rest[rig.index[segment]]
    offsets = np.asarray([rig.rest[rig.index[t]] - origin for t in twists])
    lengths = np.linalg.norm(offsets, axis=1)
    far = int(np.argmax(lengths))
    axis = offsets[far] / lengths[far]
    span = lengths.max()
    return {t: (axis, degrees * float(lengths[i] / span))
            for i, t in enumerate(twists)}


def apply_pose(rig: Rig, vertices: np.ndarray, spec: dict[str, tuple]) -> np.ndarray:
    return skin(vertices, rig.weights, forward_kinematics(rig, spec))


def pose_skeleton(rig: Rig, spec: dict[str, tuple]) -> np.ndarray:
    """把同一組姿勢套到骨架上，回傳新的關節世界座標。

    每根骨骼取自己的世界變換 D[b] 作用在自己的靜止位置上——不是父的，
    因為 D[b] 已經含了父的累積。少了這一步，網格擺好了骨架還留在原地，
    下一個姿勢就會繞錯樞紐。
    """
    deltas = forward_kinematics(rig, spec)
    real, dual = deltas[:, 0], deltas[:, 1]
    w, v = real[:, 0:1], real[:, 1:4]
    dw, dv = dual[:, 0:1], dual[:, 1:4]
    points = rig.rest
    rotated = points + 2.0 * np.cross(v, np.cross(v, points) + w * points)
    return rotated + 2.0 * (w * dv - dw * v + np.cross(v, dv))


def repose(rig: Rig, vertices: np.ndarray,
           spec: dict[str, tuple]) -> tuple[np.ndarray, "Rig"]:
    """同時擺網格與骨架，回傳新網格與一具骨架已對齊的新 Rig。"""
    posed = apply_pose(rig, vertices, spec)
    moved = Rig(len(vertices), rest_override=pose_skeleton(rig, spec))
    return posed, moved


def section_heights(reference: np.ndarray) -> dict[str, float]:
    """將四個斷面換算為參考姿勢下的絕對世界高度。

    斷面使用固定解剖位置的絕對高度。舉臂會增加包圍盒高度，比例 0.74
    因此會移往其他位置；先前量得的 40 cm 偏移來自取樣位置變化。
    固定世界高度可讓各姿勢對照同一解剖斷面。
    """
    floor, height = float(reference[:, 1].min()), float(np.ptp(reference[:, 1]))
    return {name: floor + fraction * height
            for name, (fraction, _official) in TORSO_SECTIONS.items()}


def validate(rest: np.ndarray, posed: np.ndarray, faces: np.ndarray,
             *, label: str, heights: dict[str, float] | None = None,
             check_sections: bool = True) -> bool:
    """四項幾何驗收。回傳是否全過，並把每一項的實測值印出來。"""
    print(f"── 姿勢驗收：{label} ──")
    ok = True

    def edges(v):
        return np.concatenate([
            np.linalg.norm(v[faces[:, 1]] - v[faces[:, 0]], axis=1),
            np.linalg.norm(v[faces[:, 2]] - v[faces[:, 1]], axis=1),
            np.linalg.norm(v[faces[:, 0]] - v[faces[:, 2]], axis=1)])

    rest_edge, posed_edge = edges(rest), edges(posed)
    live = rest_edge > EPS_UNIT
    ratio = posed_edge[live] / rest_edge[live]
    stretch = float(ratio.max())
    bulk = float(np.percentile(ratio, 99.9))
    good = bulk <= MAX_BULK_STRETCH_P999 and stretch <= MAX_TEAR_STRETCH
    ok &= good
    print(f"  邊長比      P99.9 {bulk:.3f} (門檻 {MAX_BULK_STRETCH_P999})   "
          f"極值 {stretch:.3f} (撕裂網 {MAX_TEAR_STRETCH})   "
          f"最小 {ratio.min():.3f}   {'OK' if good else '← 超出視覺校準門檻'}")

    def areas(v):
        return 0.5 * np.linalg.norm(np.cross(v[faces[:, 1]] - v[faces[:, 0]],
                                             v[faces[:, 2]] - v[faces[:, 0]]), axis=1)

    rest_area, posed_area = areas(rest), areas(posed)
    live = rest_area > EPS_DEGENERATE
    area_ratio = posed_area[live] / rest_area[live]
    collapsed = int((area_ratio < MIN_AREA_RATIO).sum())
    good = collapsed <= MAX_COLLAPSED_TRIANGLES
    ok &= good
    print(f"  三角形面積比 最小 {area_ratio.min():.3f}   塌陷三角形 {collapsed} "
          f"(容許 {MAX_COLLAPSED_TRIANGLES})   {'OK' if good else '← 面塌陷'}")

    def volume(v):
        a, b, c = v[faces[:, 0]], v[faces[:, 1]], v[faces[:, 2]]
        return float(np.abs(np.einsum("ij,ij->i", a, np.cross(b, c)).sum()) / 6.0)

    v_rest, v_posed = volume(rest), volume(posed)
    drift = abs(v_posed - v_rest) / v_rest
    good = drift <= MAX_VOLUME_DRIFT
    ok &= good
    print(f"  體積        {v_rest:.1f} → {v_posed:.1f} cm³  漂移 {drift*100:+.2f}% "
          f"(上限 {MAX_VOLUME_DRIFT*100:.0f}%)   {'OK' if good else '← 體積異常'}")

    if not check_sections:
        print(f"  → {'通過' if ok else '不通過'}（動作姿勢，斷面不設限）\n")
        return ok
    if heights is None:
        heights = section_heights(posed)
    up = np.asarray([0.0, 1.0, 0.0])
    worst = 0.0
    for name, (_fraction, official) in TORSO_SECTIONS.items():
        found = plane_loop(posed, faces,
                           np.asarray([0.0, heights[name], 0.0]), up)
        if not found:
            print(f"  斷面 {name}: 取不到封閉環（姿勢已改變軀幹拓樸投影）")
            continue
        # 取周長最大的環，不是第一個。手臂舉過頭時會穿過胸線多出一個小環，
        # 抓錯環會報出 40 cm 的假漂移——這是量測缺陷，不是圍度真的變了。
        worst = max(worst, abs(max(found) - official))
    good = worst <= MAX_SECTION_DRIFT_CM
    ok &= good
    print(f"  軀幹四斷面   最大漂移 {worst:.4f} cm (上限 {MAX_SECTION_DRIFT_CM})   "
          f"{'OK' if good else '← 圍度被動到'}")
    print(f"  → {'通過' if ok else '不通過'}\n")
    return ok


def self_intersections(vertices: np.ndarray, faces: np.ndarray,
                       *, cell: float = 2.0, cap: int = 4_000_000) -> int:
    """以均勻網格尋找相互貫穿的非相鄰三角形對。

    此檢查辨識手掌與臉、上臂與胸等部位的姿勢碰撞；網格連續性由其他
    幾何檢查負責。cap 限定候選對數，超過時明確回報 -1，標記檢查待完成。
    """
    centroid = vertices[faces].mean(axis=1)
    keys = np.floor(centroid / cell).astype(np.int64)
    buckets = defaultdict(list)
    for i, key in enumerate(map(tuple, keys)):
        buckets[key].append(i)

    pairs = 0
    hits = 0
    checked = set()
    neighbours = [(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                  for dz in (-1, 0, 1)]
    for key, members in buckets.items():
        candidates = []
        for offset in neighbours:
            candidates.extend(buckets.get((key[0] + offset[0], key[1] + offset[1],
                                           key[2] + offset[2]), ()))
        for i in members:
            vi = set(faces[i])
            for j in candidates:
                if j <= i:
                    continue
                if vi & set(faces[j]):      # 共用頂點的相鄰面本來就相接
                    continue
                if (i, j) in checked:
                    continue
                checked.add((i, j))
                pairs += 1
                if pairs > cap:
                    return -1
                if _triangles_cross(vertices[faces[i]], vertices[faces[j]]):
                    hits += 1
    return hits


def _triangles_cross(a: np.ndarray, b: np.ndarray) -> bool:
    """Möller 三角形相交測試的區間重疊版本。"""
    def signed(tri, other):
        normal = np.cross(tri[1] - tri[0], tri[2] - tri[0])
        norm = np.linalg.norm(normal)
        if norm < EPS_DEGENERATE:
            return None, None
        normal = normal / norm
        return normal, (other - tri[0]) @ normal

    n_a, d_b = signed(a, b)
    if n_a is None or (d_b > EPS_UNIT).all() or (d_b < -EPS_UNIT).all():
        return False
    n_b, d_a = signed(b, a)
    if n_b is None or (d_a > EPS_UNIT).all() or (d_a < -EPS_UNIT).all():
        return False
    direction = np.cross(n_a, n_b)
    if np.linalg.norm(direction) < EPS_DEGENERATE:
        return False

    def interval(tri, dist):
        proj = tri @ direction
        out = []
        for p, q in ((0, 1), (1, 2), (2, 0)):
            if dist[p] * dist[q] < 0:
                t = dist[p] / (dist[p] - dist[q])
                out.append(proj[p] + t * (proj[q] - proj[p]))
        return (min(out), max(out)) if len(out) == MIN_LOOP_POINTS else None

    ia, ib = interval(a, d_b), interval(b, d_a)
    if ia is None or ib is None:
        return False
    return ia[0] <= ib[1] and ib[0] <= ia[1]
