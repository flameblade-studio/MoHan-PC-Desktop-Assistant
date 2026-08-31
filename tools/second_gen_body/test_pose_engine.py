"""姿勢引擎的驗收測試：從恆等一路壓到極端動作，看它在哪裡才壞。

測試順序刻意由弱到強。先確認恆等姿勢逐位元還原——這一項不過，後面所有
數字都沒有意義。再逐步加大幅度，找出這具綁定的實際極限在哪裡，
而不是宣稱「可以做大動作」就算完成。
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from morph_limbs_candidate4 import load_obj  # noqa: E402
from pose_engine import (  # noqa: E402
    Rig, apply_pose, distribute_twist, repose, section_heights,
    self_intersections, validate,
)

LIMB = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13"
            r"\mohan-multisensory-vision\work\second-gen-body\limb-morph")
DOWN = np.asarray([0.0, -1.0, 0.0])
# 逐位元還原與零向量判定的容差。
EPS_UNIT = 1e-9
EPS_DEGENERATE = 1e-12


def aim_bone(rig: Rig, bone: str, child: str, target: np.ndarray) -> tuple:
    """把 bone→child 這一段的靜止方向轉到 target，回傳 (軸, 角度)。

    以靜止方向作起點是對的：前向運動學裡父變換會再疊上來，
    所以每根骨的局部旋轉都該用未變形的骨段方向來算。
    """
    current = rig.rest[rig.index[child]] - rig.rest[rig.index[bone]]
    current = current / np.linalg.norm(current)
    target = np.asarray(target, np.float64)
    target = target / np.linalg.norm(target)
    axis = np.cross(current, target)
    length = np.linalg.norm(axis)
    if length < EPS_DEGENERATE:
        return np.asarray([0.0, 1.0, 0.0]), 0.0
    return axis / length, float(np.degrees(np.arctan2(length, current @ target)))


def elevate(rig: Rig, side: str, target, scapular: float = 1.0 / 3.0) -> dict:
    """把上臂舉到 target，並依肩胛肱骨節律把一部分角度交給鎖骨。

    節律 2:1 是骨科的標準描述（Inman 等人 1944 起的一系列量測）：
    肩關節總抬舉裡約三分之一來自肩胛帶旋轉。綁定裡有 clavicle 這根骨，
    就是為了讓這三分之一有地方去。不用它，剩下的角度全部由盂肱關節吸收，
    腋下的權重過渡帶被拉爆。
    """
    axis, angle = aim_bone(rig, f"{side}_uparm", f"{side}_lowarm", target)
    return {f"{side}_clavicle": (axis, angle * scapular),
            f"{side}_uparm": (axis, angle * (1.0 - scapular))}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    # 從 candidate4（A-pose）起跑，因為官方骨架記錄的就是 A-pose 的關節座標。
    # 直接吃 candidate6 會讓網格與骨架錯位——那正是先前 36 cm 大弧的成因。
    apose, faces = load_obj(LIMB / "candidate4-p25.obj")
    rig = Rig(len(apose))
    print(f"骨架 {len(rig.names)} 根，權重表 {rig.weights.shape}，"
          f"無骨骼影響的頂點 {rig.orphan_count}\n")

    print("── 測試 0：恆等姿勢必須逐位元還原 ──")
    same = apply_pose(rig, apose, {})
    offset = float(np.abs(same - apose).max())
    print(f"  最大逐座標偏差 {offset:.3e} cm  "
          f"{'OK' if offset < EPS_UNIT else '← 引擎有誤，中止'}")
    if offset >= EPS_UNIT:
        raise SystemExit(1)
    print()

    print("── 測試 0.5：用引擎把手放下，網格與骨架一起走 ──")
    down = {}
    for side in ("l", "r"):
        upper = rig.rest[rig.index[f"{side}_lowarm"]] - rig.rest[rig.index[f"{side}_uparm"]]
        lateral = np.asarray([upper[0], 0.0, upper[2]])
        lateral = lateral / np.linalg.norm(lateral)
        for bone, child, degrees in ((f"{side}_uparm", f"{side}_lowarm", 8.0),
                                     (f"{side}_lowarm", f"{side}_wrist", 10.0)):
            target = np.sin(np.radians(degrees)) * lateral + np.cos(np.radians(degrees)) * DOWN
            down[bone] = aim_bone(rig, bone, child, target)
    rest, rig = repose(rig, apose, down)
    heights = section_heights(rest)
    for side in ("l", "r"):
        vector = rig.rest[rig.index[f"{side}_lowarm"]] - rig.rest[rig.index[f"{side}_uparm"]]
        angle = np.degrees(np.arccos(np.clip(vector / np.linalg.norm(vector) @ DOWN, -1, 1)))
        print(f"  {side} 側骨架上臂與垂直線夾角 {angle:.2f} 度（目標 8.00）")
    base_ok = validate(apose, rest, faces,
                       label="A-pose → 手臂垂下（引擎版，真實權重）",
                       heights=section_heights(apose))

    cases: list[tuple[str, dict]] = []

    # 1 前臂旋前 90 度：twist 骨若沒分攤，這裡就會出現教科書級 candy-wrapper。
    cases.append(("前臂旋前 90 度（twist 骨分攤）",
                  distribute_twist(rig, "r_lowarm", 90.0)))

    # 2 同樣 90 度但全部灌到最遠端一根 twist 骨——刻意製造反例。
    spread = distribute_twist(rig, "r_lowarm", 90.0)
    far = max(spread, key=lambda t: spread[t][1])
    cases.append(("前臂旋前 90 度（全灌最遠端一根，反例）",
                  {far: (spread[far][0], 90.0)}))

    # 3 側舉 150 度＝安全包絡的上緣（2026-08-31 渲染校準：150 度內乾淨、
    # 170 度腋窩出現可見皺褶）。必須帶鎖骨：肩胛肱骨節律 2:1，綁定裡的
    # clavicle 就是給那三分之一用的。
    up_lateral = rig.rest[rig.index["r_lowarm"]] - rig.rest[rig.index["r_uparm"]]
    lateral = np.asarray([up_lateral[0], 0.0, up_lateral[2]])
    lateral = lateral / np.linalg.norm(lateral)
    r150 = np.radians(150.0)
    target150 = np.sin(r150) * lateral + np.cos(r150) * DOWN
    cases.append(("側舉 150 度（含鎖骨 1/3，包絡上緣）",
                  elevate(rig, "r", target150)))

    # 4 對照組：同一個 150 度，故意不帶鎖骨——全部角度塞進盂肱關節，
    # 腋下的權重過渡帶被拉爆，撕裂粗網要能攔下它。
    axis, angle = aim_bone(rig, "r_uparm", "r_lowarm", target150)
    cases.append(("側舉 150 度（不帶鎖骨，反例）", {"r_uparm": (axis, angle)}))

    # 5 巴掌：肩前舉 + 肘彎，三段複合，測階層是否正確累積。
    slap = elevate(rig, "r", [0.55, 0.35, 0.75])
    axis, angle = aim_bone(rig, "r_lowarm", "r_wrist", [-0.85, 0.10, 0.50])
    slap["r_lowarm"] = (axis, angle)
    cases.append(("巴掌（肩前舉＋肘彎 ~80 度）", slap))

    # 6 極端：肩舉 + 肘全彎 + 上臂扭 60 度，用來找這具綁定真正的斷點。
    extreme = elevate(rig, "r", [0.15, 1.0, -0.2])
    axis, angle = aim_bone(rig, "r_lowarm", "r_wrist", [-0.3, -0.9, 0.3])
    extreme["r_lowarm"] = (axis, angle)
    extreme.update(distribute_twist(rig, "r_uparm", 60.0))
    cases.append(("極端：肩舉 + 肘全彎 + 上臂扭 60 度", extreme))

    results = []
    for label, spec in cases:
        posed = apply_pose(rig, rest, spec)
        ok = validate(rest, posed, faces, label=label, heights=heights,
                      check_sections=False)
        results.append((label, ok, posed, spec))

    print("── 自體貫穿（只對通過幾何驗收的姿勢做，昂貴）──")
    for label, ok, posed, _ in results:
        if not ok:
            print(f"  {label}: 幾何驗收未過，略過")
            continue
        hits = self_intersections(posed, faces)
        verdict = "無法檢查（候選對數超過上限）" if hits < 0 else (
            "無貫穿" if hits == 0 else f"{hits} 對三角形互相貫穿")
        print(f"  {label}: {verdict}")

    # 預期結果（2026-08-31 視覺校準後定案）。
    #   垂手（含斷面檢查）：預期不通過——引擎用原始權重，胸圍動 1.47 cm；
    #   產線的身份姿勢一律走 repose_arms_candidate6_dqs 的重映射版本。
    #   極端姿勢：預期不通過，它就是拿來標記包絡外的邊界探針。
    expected = {
        "前臂旋前 90 度（twist 骨分攤）": True,
        "前臂旋前 90 度（全灌最遠端一根，反例）": True,
        "側舉 150 度（含鎖骨 1/3，包絡上緣）": True,
        "側舉 150 度（不帶鎖骨，反例）": False,
        "巴掌（肩前舉＋肘彎 ~80 度）": True,
        "極端：肩舉 + 肘全彎 + 上臂扭 60 度": False,
    }
    print("\n── 總結（實際 vs 預期）──")
    failures = 0
    if base_ok:
        failures += 1
        print("  ★ 垂手＋斷面檢查竟然通過——引擎不該守得住斷面，檢查邏輯有異")
    for label, ok, _, _ in results:
        want = expected[label]
        match = ok == want
        failures += 0 if match else 1
        print(f"  {'✓' if match else '★ 不符預期'}  {label}："
              f"實際{'通過' if ok else '不通過'}／預期{'通過' if want else '不通過'}")
    for label, ok, posed, _ in results:
        if ok:
            tag = label.split("（")[0].replace(" ", "")
            np.save(LIMB / f"posetest-{tag}.npy", posed)
    if failures:
        print(f"POSE_ENGINE_TEST_FAILED mismatches={failures}")
        raise SystemExit(1)
    print("POSE_ENGINE_TEST_DONE")


if __name__ == "__main__":
    main()
