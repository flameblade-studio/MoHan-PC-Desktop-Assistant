"""能見度月報：一鍵抓齊 GitHub 流量並與 P0 基準對照（issue #129）。

為什麼存在：GitHub 流量數據只保留 14 天，不主動記錄就永久消失；而
clone 數已被證實幾乎全是機器人（基準：3,934 次 clone 對 21 個真人訪客），
所以每一項數字都必須標明可信度，不能直接當成效。

用法：
    py -3.15 tools/visibility_monthly_report.py            # 印出月報 markdown
    py -3.15 tools/visibility_monthly_report.py --post     # 直接留言到 issue #129

需要 gh CLI 已登入且對 repo 有 push 權限（traffic API 的最低要求）。
Ko-fi 無公開 API，該兩欄固定輸出待填佔位，由擁有者手動補。
"""
from __future__ import annotations

lazy import argparse
lazy import json
lazy import subprocess
lazy import sys
lazy from datetime import date

REPO = "flameblade-studio/MoHan-PC-Desktop-Assistant"
REPORT_ISSUE = 129
# P0 基準（issue #118，2026-08-30 量測）。之後每次月報都與這組數字對照。
BASELINE_DATE = "2026-08-30"
BASELINE_UNIQUE_VISITORS = 21
BASELINE_GOOGLE_UNIQUES = 2
BASELINE_ITHOME_UNIQUES = 2
BASELINE_STARS = 2
BASELINE_DOWNLOADS_TOTAL = 5


def api(path: str):
    endpoint = f"repos/{REPO}/{path}" if path else f"repos/{REPO}"
    result = subprocess.run(
        ["gh", "api", endpoint],
        check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(result.stdout)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--post", action="store_true",
                        help=f"留言到 issue #{REPORT_ISSUE}")
    args = parser.parse_args()

    views = api("traffic/views")
    clones = api("traffic/clones")
    referrers = api("traffic/popular/referrers")
    repo = api("")
    releases = api("releases?per_page=10")

    lines: list[str] = []
    today = date.today().isoformat()
    lines.append(f"## 能見度月報 {today}（14 天視窗）")
    lines.append("")
    lines.append(f"| 指標 | 本期 | 基準 {BASELINE_DATE} |")
    lines.append("|---|---:|---:|")
    lines.append(f"| 瀏覽 | {views['count']} | 478 |")
    lines.append(f"| **不重複訪客** | **{views['uniques']}** "
                 f"| **{BASELINE_UNIQUE_VISITORS}** |")
    lines.append(f"| clone（幾乎全為機器人，不得當成效） | {clones['count']} "
                 f"/ {clones['uniques']} 不重複 | 3934 / 186 |")
    lines.append(f"| 星數 / Fork / 訂閱 | {repo['stargazers_count']} / "
                 f"{repo['forks_count']} / {repo['subscribers_count']} "
                 f"| {BASELINE_STARS} / 0 / 1 |")

    total_downloads = 0
    per_release: list[str] = []
    for release in releases:
        subtotal = sum(asset["download_count"] for asset in release["assets"])
        total_downloads += subtotal
        if subtotal:
            per_release.append(f"{release['tag_name']} {subtotal}")
    lines.append(f"| 資產下載（歷史累計） | {total_downloads}"
                 f"（{'、'.join(per_release) if per_release else '無'}） "
                 f"| {BASELINE_DOWNLOADS_TOTAL}（v4.6.0，14 天視窗） |")
    lines.append("")

    lines.append("### 流量來源（判斷各通路成效的唯一依據）")
    lines.append("")
    lines.append("| 來源 | 瀏覽 | 不重複 |")
    lines.append("|---|---:|---:|")
    google = ithome = 0
    for ref in referrers:
        lines.append(f"| {ref['referrer']} | {ref['count']} | {ref['uniques']} |")
        if "google" in ref["referrer"].lower():
            google = ref["uniques"]
        if "ithome" in ref["referrer"].lower():
            ithome = ref["uniques"]
    lines.append("")
    lines.append(f"對照基準：Google {google}（基準 {BASELINE_GOOGLE_UNIQUES}）、"
                 f"鐵人賽 {ithome}（基準 {BASELINE_ITHOME_UNIQUES}）。")
    lines.append("")
    lines.append("### Ko-fi（無公開 API，擁有者手動補）")
    lines.append("")
    lines.append("- 頁面瀏覽：＿＿")
    lines.append("- 會員數：＿＿")
    lines.append("")
    lines.append("> 盲點聲明：GitHub 流量視窗僅 14 天，本表非整月總量；"
                 "clone 與瀏覽都含機器人，唯一可靠的真人訊號是不重複訪客"
                 "與來源分布的相對變化。")

    report = "\n".join(lines)
    print(report)

    if args.post:
        subprocess.run(
            ["gh", "issue", "comment", str(REPORT_ISSUE),
             "--repo", REPO, "--body", report],
            check=True, capture_output=True, text=True, encoding="utf-8")
        print(f"\n已留言至 issue #{REPORT_ISSUE}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
