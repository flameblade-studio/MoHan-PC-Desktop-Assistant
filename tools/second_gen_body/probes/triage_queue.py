"""把 157 項待裁決分流成「已被架構決策取代」與「仍需擁有者過目」。

分流的依據不是逐張看圖，而是問一個更前面的問題：這一項當初在等的判準，
今天還成立嗎？兩個架構決策讓大部分判準失效——

  1. identity LoRA v2（3000 步）定案並選定權重 0.85，
     取代 identity 訓練 v1–v4、pure-face-mask v3、face-only 系列的全部候選比較。
  2. 幾何條件化（bundle shaded-render + img2img s0.95）取代「逐角度撈候選」，
     因為 24 個視角現在是從同一組控制圖確定性產生的，不再需要一角一角碰運氣。

被取代者不需要擁有者判斷——判準沒了，看圖也做不出決定。
仍然成立的判準只有三類：授權來源、DLC 結構、幾何控制契約。
"""
import re
import sys
from pathlib import Path

TSV = Path(__file__).with_name("decision-queue.tsv")
OUT = Path(__file__).with_name("queue-triage.tsv")

# 被取代的判準。每條都標明「被什麼取代」，不是憑感覺歸類。
SUPERSEDED = [
    (r"pure-face-mask|face-only-identity|face-core-hole|face-neck|face-only-refine",
     "SUPERSEDED_BY_LORA_V2", "臉部遮罩路線；identity 已改由 LoRA v2 承擔"),
    (r"identity-training|distinct-source|seven-source|authority-only|identity-refined"
     r"|identity-checkpoint|identity-step\d|identity-v3|identity28|diverse\d+|distinct\d+",
     "SUPERSEDED_BY_LORA_V2", "identity 訓練候選比較；LoRA v2 已定案且權重已選"),
    (r"candidate|imagegen|staging|attempt|baseline|ab-|smoke|fixture|screen|pre-review",
     "SUPERSEDED_BY_GEOMETRY_CONDITIONING", "逐角度撈候選；24 視角改為確定性產生"),
    (r"flux-v2|flux-nf4|flux-formal|flux2-klein|flux-schnell|flux-soft|flux-img2img",
     "SUPERSEDED_BY_CHROMA_PIPELINE", "Flux 系試驗；現行產線為 Chroma1-HD"),
    (r"qwen", "SUPERSEDED_BY_CHROMA_PIPELINE", "Qwen 系試驗；非現行產線"),
    (r"birefnet", "SUPERSEDED_BY_SILHOUETTE_MASK",
     "去背模型評估；bundle 自帶 silhouette，不再需要去背模型"),
]

# 判準仍然成立者。這些跟用哪個生圖模型無關，換產線也不會失效。
LIVE = [
    (r"ornament-source|license|third-party|source-audit",
     "LIVE_LICENSING", "素材來源授權；與生圖產線無關，白名單永遠適用"),
    (r"dlc|ownership|migration",
     "LIVE_DLC_STRUCTURE", "DLC 的解剖／服裝分離結構；套用到新的 24 視角仍需要"),
    (r"control-bundle|canonical24|renderer|shared-yaw-control|nongenerative-geometry"
     r"|segment-overlay|local-axis|mhr-neutral",
     "LIVE_GEOMETRY_CONTRACT", "幾何控制契約；正是現行產線的上游"),
]


def classify(folder: str) -> tuple[str, str]:
    for pattern, label, why in LIVE:
        if re.search(pattern, folder, re.I):
            return label, why
    for pattern, label, why in SUPERSEDED:
        if re.search(pattern, folder, re.I):
            return label, why
    return "UNCLASSIFIED", "自動分流無法歸類，需人工看一眼"


def main() -> None:
    rows = [l.split("\t") for l in TSV.read_text(encoding="utf-8").splitlines()[1:]]
    out = ["folder\tdisposition\trationale\timage"]
    tally: dict[str, int] = {}
    for row in rows:
        folder = row[0]
        image = row[1] if len(row) > 1 else ""
        label, why = classify(folder)
        tally[label] = tally.get(label, 0) + 1
        out.append(f"{folder}\t{label}\t{why}\t{image}")
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")

    for label, count in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"{count:4d}  {label}")
    live = sum(v for k, v in tally.items() if k.startswith("LIVE") or k == "UNCLASSIFIED")
    print(f"\n需擁有者過目：{live} 項（原 {len(rows)} 項）")
    print(f"寫入 {OUT}")

    print("\n── 需過目者逐項 ──")
    for line in out[1:]:
        folder, label, why, image = line.split("\t")
        if label.startswith("LIVE") or label == "UNCLASSIFIED":
            print(f"[{label}] {folder}\n    {why}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
