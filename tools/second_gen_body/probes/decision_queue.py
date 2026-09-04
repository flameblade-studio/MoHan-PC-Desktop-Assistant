"""裁決佇列：掃出真正卡在「等一個人類看一眼」的項目。

v1 的教訓：只讀 JSON 狀態欄位會產生大量偽陽性——權威結論寫在 REPORT.md
的「結論／Result」段（含 REJECTED_* 與 manual exit 4），而巢狀 JSON 裡
往往仍留著早期的 pending 欄位。抽驗 5 項全部早已裁決，偽陽性率 100%。

v2 改為：REPORT.md 的結論優先；只要該目錄已有正式裁決（REJECTED／
APPROVED／manual exit 非 0），一律排除，不論 JSON 怎麼寫。
"""
import os
import json
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")) / r"artifacts"
OUT = Path(__file__).with_name("decision-queue.tsv")
SKIP_TOP = {
    "instantmesh-b00-smoke", "worktree-quarantine",
    "third-party-downloads", "zenodo-doi-backfill-draft",
}
NOISE = {"selftest", "fixtures", "self-test"}
PENDING = re.compile(
    r"PENDING|NOT_TESTED|NEEDS_[A-Z_]*QA|NEEDS_[A-Z_]*REVIEW|QUARANTIN|"
    r"AWAIT|WAITING|MANUAL_[A-Z_]*(DECISION|CONFIRM)|DECISION_REQUIRED|"
    r"OWNER_[A-Z_]*(CONFIRM|REVIEW|APPROV)|REQUIRES_[A-Z_]*HUMAN",
    re.IGNORECASE,
)
# 已裁決的訊號——出現任一即整個目錄出局
DECIDED = re.compile(
    r"REJECTED|APPROVED|ACCEPTED|FAIL_CLOSED|PROMOTED|SUPERSEDED|"
    r"manual exit\s*[1-9]|人工閘門\s*exit\s*[1-9]",
    re.IGNORECASE,
)
STATUS_KEYS = {
    "status", "decision", "conclusion", "verdict", "result", "outcome",
    "identity_acceptance", "alpha_acceptance", "art_acceptance", "acceptance",
    "geometry_acceptance", "next_step", "blocking", "gate",
}
VIEWABLE = {".png", ".jpg", ".jpeg", ".webp"}


class DecisionQueueError(RuntimeError):
    """A decision-queue evidence file cannot be safely inspected."""


def decided_in_folder(folder: Path) -> str:
    """回傳該目錄已有的正式裁決字串；沒有則回空字串。"""
    for report in list(folder.glob("REPORT.md")) + list(folder.glob("*.md")):
        text = report.read_text(encoding="utf-8", errors="replace")[:4000]
        match = DECIDED.search(text)
        if match:
            line = next(
                (ln.strip() for ln in text.splitlines()
                 if match.group(0).lower() in ln.lower()), match.group(0)
            )
            return line[:110]
    for gate in folder.glob("*exit-code*.txt"):
        code = gate.read_text(encoding="utf-8", errors="replace").strip()
        if code.isdigit() and int(code) != 0 and "manual" in gate.name.lower():
            return f"{gate.name}={code}"
    return ""


def pending_hits(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise DecisionQueueError(f"cannot read JSON {path}: {error}") from error
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise DecisionQueueError(
            f"malformed JSON {path} at line {error.lineno}, column {error.colno}"
        ) from error
    hits: list[str] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                low = key.lower()
                if isinstance(value, str):
                    if (low in STATUS_KEYS or low.endswith(
                            ("_status", "_acceptance", "_decision"))) and \
                            PENDING.search(value) and not DECIDED.search(value):
                        hits.append(f"{key}={value.strip()[:80]}")
                elif isinstance(value, (dict, list)):
                    walk(value)
        elif isinstance(node, list):
            for item in node[:20]:
                walk(item)

    walk(data)
    return hits


def best_image(folder: Path) -> str:
    best = None
    for path in folder.rglob("*"):
        if path.suffix.lower() not in VIEWABLE or not path.is_file():
            continue
        score = path.stat().st_size
        if any(tag in path.name.lower()
               for tag in ("contact", "compare", "sheet", "candidate", "preview")):
            score *= 4
        if best is None or score > best[0]:
            best = (score, path)
    return str(best[1].relative_to(ROOT)).replace("\\", "/") if best else ""


def main() -> None:
    queue: dict[str, tuple[str, str]] = {}
    excluded = 0
    for top in sorted(ROOT.iterdir()):
        if not top.is_dir() or top.name in SKIP_TOP:
            continue
        for report in top.rglob("*.json"):
            parts = {part.lower() for part in report.parts}
            if parts & NOISE or "site-packages" in parts or "env" in parts:
                continue
            hits = pending_hits(report)
            if not hits:
                continue
            folder = report.parent
            key = str(folder.relative_to(ROOT)).replace("\\", "/")
            if key in queue:
                continue
            verdict = decided_in_folder(folder)
            if verdict:
                excluded += 1
                continue
            queue[key] = (best_image(folder), " | ".join(hits[:3]))

    rows = ["\t".join(("dir", "image", "status"))]
    for key in sorted(queue, key=lambda k: (not queue[k][0], k)):
        image, status = queue[key]
        rows.append("\t".join((key, image, status)))
    OUT.write_text("\n".join(rows), encoding="utf-8")
    viewable = sum(1 for value in queue.values() if value[0])
    print(f"QUEUE {len(queue)} truly pending, {viewable} viewable; "
          f"excluded {excluded} already-decided")


if __name__ == "__main__":
    try:
        main()
    except DecisionQueueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
