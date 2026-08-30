"""量測墨寒的能見度指標，供每月月報使用（issue #129）。

GitHub 的流量資料只保留十四天——不主動記錄就永久消失。本工具一鍵產出
月報所需的全部數字，並與 2026-08-30 的基準對照，讓「改動有沒有用」
可被驗證而非憑感覺。

用法：
    python tools/measure_visibility.py              # 人類可讀
    python tools/measure_visibility.py --json       # 機器可讀，供存檔

需要已登入的 gh CLI（流量端點需要推送權限）。
"""
from __future__ import annotations

lazy import argparse
lazy import json
lazy import subprocess
lazy import sys

REPOSITORY = "flameblade-studio/MoHan-PC-Desktop-Assistant"

# 2026-08-30 基準（issue #118）。每次量測都與此對照。
BASELINE = {
    "views": 478,
    "unique_visitors": 21,
    "clones": 3934,
    "unique_cloners": 186,
    "stars": 2,
    "forks": 0,
    "watchers": 1,
    "google_visitors": 2,
    "ironman_visitors": 2,
    "latest_release_downloads": 5,
}


def _gh_json(path: str) -> dict | list | None:
    """呼叫 gh api 並解析 JSON；端點不可用時回傳 None 而非中斷。"""
    result = subprocess.run(
        ["gh", "api", path],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def collect() -> dict:
    repo = _gh_json(f"repos/{REPOSITORY}") or {}
    views = _gh_json(f"repos/{REPOSITORY}/traffic/views") or {}
    clones = _gh_json(f"repos/{REPOSITORY}/traffic/clones") or {}
    referrers = _gh_json(f"repos/{REPOSITORY}/traffic/popular/referrers") or []
    releases = _gh_json(f"repos/{REPOSITORY}/releases?per_page=10") or []

    by_referrer = {entry["referrer"]: entry["uniques"] for entry in referrers}
    release_rows = []
    for release in releases:
        downloads = sum(asset["download_count"] for asset in release.get("assets", []))
        release_rows.append(
            {
                "tag": release.get("tag_name", "?"),
                "published": (release.get("published_at") or "")[:10],
                "assets": len(release.get("assets", [])),
                "downloads": downloads,
            }
        )

    return {
        "repository": REPOSITORY,
        "views": views.get("count", 0),
        "unique_visitors": views.get("uniques", 0),
        "clones": clones.get("count", 0),
        "unique_cloners": clones.get("uniques", 0),
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "watchers": repo.get("subscribers_count", 0),
        "open_issues": repo.get("open_issues_count", 0),
        "referrers": by_referrer,
        "google_visitors": by_referrer.get("Google", 0),
        "ironman_visitors": by_referrer.get("ithelp.ithome.com.tw", 0),
        "releases": release_rows,
        "latest_release_downloads": release_rows[0]["downloads"] if release_rows else 0,
    }


def _delta(current: int, baseline: int) -> str:
    if baseline == 0:
        return f"{current:>7,}  （基準 0）"
    ratio = current / baseline
    return f"{current:>7,}  （基準 {baseline:,}，{ratio:.1f}×）"


def render(data: dict) -> str:
    lines = [
        f"墨寒能見度量測 — {data['repository']}",
        "GitHub 流量僅涵蓋最近十四天。",
        "",
        "指標                    本次        對照 2026-08-30 基準",
        "-" * 58,
    ]
    rows = (
        ("瀏覽數", "views"),
        ("不重複訪客", "unique_visitors"),
        ("星數", "stars"),
        ("Fork", "forks"),
        ("訂閱", "watchers"),
        ("Google 來源訪客", "google_visitors"),
        ("鐵人賽來源訪客", "ironman_visitors"),
        ("最新版下載", "latest_release_downloads"),
    )
    for label, key in rows:
        lines.append(f"{label:<18}{_delta(data[key], BASELINE[key])}")

    lines += [
        "",
        f"clone {data['clones']:,} 次 / {data['unique_cloners']:,} 不重複",
        "  ！clone 數絕大多數來自機器人與鏡像，不得作為成效回報。",
        f"  基準當時 {BASELINE['clones']:,} 次 clone 只對應 "
        f"{BASELINE['unique_visitors']} 個真人訪客。",
        "",
        "流量來源（不重複訪客）：",
    ]
    for referrer, uniques in sorted(
        data["referrers"].items(), key=lambda item: -item[1]
    ):
        lines.append(f"  {referrer:<30}{uniques:>5}")
    if not data["referrers"]:
        lines.append("  （無資料）")

    lines += ["", "各版本資產下載："]
    for row in data["releases"][:6]:
        lines.append(
            f"  {row['tag']:<12}{row['published']}  資產 {row['assets']:>2} 個  "
            f"下載 {row['downloads']:>4}"
        )
        if row["assets"] == 0:
            lines.append("    ！此版本沒有任何可下載資產（見 issue #120）")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="輸出 JSON，供月報存檔比對"
    )
    arguments = parser.parse_args()
    data = collect()
    if not data["views"] and not data["stars"]:
        print(
            "無法取得資料：請確認 gh CLI 已登入且對本儲存庫有推送權限。",
            file=sys.stderr,
        )
        return 1
    if arguments.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
