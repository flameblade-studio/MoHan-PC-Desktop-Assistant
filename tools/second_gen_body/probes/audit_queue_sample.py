"""抽驗裁決佇列的可信度——只比對裁決「值」，不比對鍵名或路徑。

v1 抽驗器的錯誤：對整份檔案做字串搜尋，於是 "promoted_qa": {、
"approved_output_sha256"、fail_closed_review.v1 這些鍵名與 schema 名稱
都被誤判成裁決，量出 58% 這個假數字。

v2 改為：JSON 必須解析後只看狀態類鍵的字串值；Markdown 只看「結論／
Result／Conclusion」段落之後的前幾行。路徑與鍵名一律不參與比對。
"""
import os
import json
import random
import re
from pathlib import Path

ROOT = Path(os.environ.get("MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")) / r"artifacts"
TSV = Path(__file__).with_name("decision-queue.tsv")
VERDICT = re.compile(
    r"^(REJECTED|APPROVED|ACCEPTED|FAIL_CLOSED|PROMOTED|SUPERSEDED|DENIED)[A-Z0-9_]*$"
)
# 結尾不可用 \b：REJECTED_ANGLE_TOWARD_MINUS135_... 這類含數字的裁決，
# [A-Z_]* 吃不下 135 而回溯，結尾 \b 又因下一字元是底線而失敗，整條漏抓。
VERDICT_IN_TEXT = re.compile(
    r"\b(REJECTED|APPROVED|ACCEPTED|FAIL_CLOSED|SUPERSEDED|DENIED)[A-Z0-9_]*"
)
STATUS_KEYS = {
    "status", "decision", "conclusion", "verdict", "result", "outcome",
    "identity_acceptance", "alpha_acceptance", "art_acceptance", "acceptance",
    "geometry_acceptance", "manual_status", "owner_status", "gate",
}
CONCLUSION_HEAD = re.compile(r"^#{1,3}\s*(結論|Result|Conclusion|裁決)", re.IGNORECASE)


def verdict_from_json(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return ""
    found = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                low = key.lower()
                if isinstance(value, str) and (
                    low in STATUS_KEYS or low.endswith(("_status", "_acceptance"))
                ):
                    if VERDICT.match(value.strip()):
                        found.append(f"{key}={value.strip()[:70]}")
                elif isinstance(value, (dict, list)):
                    walk(value)
        elif isinstance(node, list):
            for item in node[:30]:
                walk(item)

    walk(data)
    return found[0] if found else ""


def verdict_from_markdown(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[:60]
    except Exception:
        return ""
    inside = False
    for line in lines:
        if CONCLUSION_HEAD.match(line.strip()):
            inside = True
            continue
        if inside:
            if line.startswith("#"):
                break
            match = VERDICT_IN_TEXT.search(line)
            if match:
                return line.strip()[:88]
    return ""


def decided(folder: Path) -> tuple[str, str]:
    for path in sorted(folder.glob("*.md")):
        hit = verdict_from_markdown(path)
        if hit:
            return hit, path.name
    for path in sorted(folder.glob("*.json")):
        hit = verdict_from_json(path)
        if hit:
            return hit, path.name
    return "", ""


def main() -> None:
    rows = [line.split("\t") for line in TSV.read_text(encoding="utf-8").splitlines()[1:]]
    random.seed(20260831)
    sample = random.sample(rows, min(12, len(rows)))
    print(f"佇列 {len(rows)} 項，隨機抽驗 {len(sample)} 項\n")
    bad = 0
    for name, _image, status in sample:
        verdict, where = decided(ROOT / name)
        if verdict:
            bad += 1
            print(f"[偽陽性] {name}")
            print(f"    實際裁決({where}): {verdict}")
        else:
            print(f"[真 pending] {name}")
            print(f"    {status[:78]}")
        print()
    rate = bad / len(sample) * 100
    print(f"偽陽性 {bad}/{len(sample)} = {rate:.0f}%")
    print(f"推估真正待裁決 {round(len(rows) * (1 - bad / len(sample)))} 項")


if __name__ == "__main__":
    main()
