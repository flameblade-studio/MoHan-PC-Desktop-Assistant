"""產出可留存、可比較的 GitHub 流量月報／生成可留存、可比较的 GitHub 流量月报／
Produce archivable, comparable GitHub traffic reports／保存可能比較できる GitHub トラフィック月報。

The GitHub traffic API keeps only a rolling fourteen-day window.  This tool
validates every required response before writing the current snapshot and the
four-language Markdown report, so a failed or incomplete API call cannot leave
an apparently valid empty report behind.

用法：
    py -3.15 tools/traffic_report.py --month 2026-09
    py -3.15 tools/traffic_report.py --month 2026-09 --overwrite
"""
from __future__ import annotations

lazy import argparse
lazy import json
lazy import subprocess
lazy import sys
lazy from collections.abc import Callable
lazy from datetime import date, datetime, timedelta, timezone
lazy from pathlib import Path


REPOSITORY = "flameblade-studio/MoHan-PC-Desktop-Assistant"
ISSUE_NUMBER = 129
TRAFFIC_WINDOW_DAYS = 14
P0_BASELINE_DATE = "2026-08-30"
P0_BASELINE = {
    "views": 478,
    "unique_visitors": 21,
    "clones": 3934,
    "unique_cloners": 186,
    "release_downloads": 5,
    "stars": 2,
    "forks": 0,
    "watchers": 1,
    "google_uniques": 2,
    "ironman_uniques": 2,
}
METRIC_KEYS = (
    "views",
    "unique_visitors",
    "clones",
    "unique_cloners",
    "release_downloads",
    "stars",
    "forks",
    "watchers",
    "google_uniques",
    "ironman_uniques",
)
LANGUAGE_HEADINGS = ("繁體中文", "简体中文", "English", "日本語")
REPORT_H1 = (
    "# 墨寒每月流量月報／墨寒每月流量月报／"
    "MoHan monthly traffic report／墨寒月次トラフィックレポート"
)
MANUAL_KEYS = (
    "bot_share_estimate",
    "kofi_page_views",
    "kofi_members",
    "impact_notes",
)


REPORT_TEXT = {
    "繁體中文": {
        "title": "墨寒每月流量月報", "window_note": "GitHub 流量端點只提供最近 14 天；本月欄位代表本次擷取視窗，不宣稱完整曆月總量。", "collected": "擷取時間", "raw": "原始 JSON",
        "comparison": "本月與上月對比", "metric": "指標", "current": "本月", "previous": "上月", "change": "變化", "p0": "P0 基準",
        "pages": "最受歡迎的頁面", "page": "頁面", "page_title": "標題", "views": "瀏覽", "uniques": "不重複", "referrers": "最受歡迎的來源", "referrer": "來源",
        "releases": "Release 資產下載", "release": "Release", "assets": "資產數", "downloads": "累計下載", "manual": "這個月做了什麼可能影響數字的事",
        "manual_prompt": "請由擁有者在發布月報前補上以下欄位；沒有證據的數字請保留待填，不要猜測。", "bot_share": "機器人佔比推估", "kofi_views": "Ko-fi 頁面瀏覽", "kofi_members": "Ko-fi 會員數", "impact": "可能影響數字的工作", "placeholder": "待人工填寫", "no_data": "無資料",
        "clone_note": "clone 可能包含機器人與鏡像；這裡保留數字供追蹤，但不得直接當成成效。", "release_note": "Release API 的下載數是資產發布後累計值；變化欄是兩次快照的差額。", "issue_status": "Issue #129：可請擁有者結案；本工具不會自動關閉 issue。",
        "metrics": {"views": "瀏覽數", "unique_visitors": "不重複訪客", "clones": "clone 數（可能含機器人）", "unique_cloners": "不重複 clone", "release_downloads": "Release 資產下載（累計）", "stars": "星數", "forks": "Fork", "watchers": "Watchers／訂閱", "google_uniques": "Google 來源不重複訪客", "ironman_uniques": "鐵人賽來源不重複訪客"},
    },
    "简体中文": {
        "title": "墨寒每月流量月报", "window_note": "GitHub 流量接口只提供最近 14 天；本月栏位代表本次采集窗口，不宣称完整自然月总量。", "collected": "采集时间", "raw": "原始 JSON",
        "comparison": "本月与上月对比", "metric": "指标", "current": "本月", "previous": "上月", "change": "变化", "p0": "P0 基线",
        "pages": "最受欢迎的页面", "page": "页面", "page_title": "标题", "views": "浏览", "uniques": "不重复", "referrers": "最受欢迎的来源", "referrer": "来源",
        "releases": "Release 资产下载", "release": "Release", "assets": "资产数", "downloads": "累计下载", "manual": "这个月做了什么可能影响数字的事",
        "manual_prompt": "请由拥有者在发布月报前补充以下字段；没有证据的数字请保留待填写，不要猜测。", "bot_share": "机器人占比估计", "kofi_views": "Ko-fi 页面浏览", "kofi_members": "Ko-fi 会员数", "impact": "可能影响数字的工作", "placeholder": "待人工填写", "no_data": "无数据",
        "clone_note": "clone 可能包含机器人和镜像；这里保留数字供追踪，但不得直接当作成效。", "release_note": "Release API 的下载数是资产发布后的累计值；变化栏是两次快照的差额。", "issue_status": "Issue #129：可请拥有者结案；本工具不会自动关闭 issue。",
        "metrics": {"views": "浏览数", "unique_visitors": "不重复访客", "clones": "clone 数（可能含机器人）", "unique_cloners": "不重复 clone", "release_downloads": "Release 资产下载（累计）", "stars": "星数", "forks": "Fork", "watchers": "Watchers／订阅", "google_uniques": "Google 来源不重复访客", "ironman_uniques": "铁人赛来源不重复访客"},
    },
    "English": {
        "title": "MoHan monthly traffic report", "window_note": "The GitHub traffic API exposes only a rolling 14-day window; this month means the captured window, not a complete calendar month.", "collected": "Collected", "raw": "Raw JSON",
        "comparison": "This month versus last month", "metric": "Metric", "current": "This month", "previous": "Last month", "change": "Change", "p0": "P0 baseline",
        "pages": "Most popular pages", "page": "Page", "page_title": "Title", "views": "Views", "uniques": "Uniques", "referrers": "Most popular referrers", "referrer": "Referrer",
        "releases": "Release asset downloads", "release": "Release", "assets": "Assets", "downloads": "Cumulative downloads", "manual": "What we did this month that may affect the numbers",
        "manual_prompt": "The owner should fill in these fields before posting the report; leave unsupported numbers blank instead of guessing.", "bot_share": "Estimated bot share", "kofi_views": "Ko-fi page views", "kofi_members": "Ko-fi members", "impact": "Work that may affect the numbers", "placeholder": "Owner input required", "no_data": "No data",
        "clone_note": "Clones may include bots and mirrors; keep them for tracking, but never report them directly as impact.", "release_note": "Release API downloads are cumulative after publication; Change is the difference between snapshots.", "issue_status": "Issue #129: the owner may close it; this tool never closes the issue automatically.",
        "metrics": {"views": "Views", "unique_visitors": "Unique visitors", "clones": "Clones (may include bots)", "unique_cloners": "Unique cloners", "release_downloads": "Release asset downloads (cumulative)", "stars": "Stars", "forks": "Forks", "watchers": "Watchers", "google_uniques": "Unique visitors from Google", "ironman_uniques": "Unique visitors from Ironman"},
    },
    "日本語": {
        "title": "墨寒 月次トラフィック月報", "window_note": "GitHub トラフィック API が提供するのは直近 14 日の移動ウィンドウだけです。本月は取得ウィンドウを示し、完全な暦月の合計とは主張しません。", "collected": "取得時刻", "raw": "生 JSON",
        "comparison": "今月と先月の比較", "metric": "指標", "current": "今月", "previous": "先月", "change": "変化", "p0": "P0 基準",
        "pages": "人気のページ", "page": "ページ", "page_title": "タイトル", "views": "閲覧", "uniques": "ユニーク", "referrers": "人気の参照元", "referrer": "参照元",
        "releases": "Release アセットのダウンロード", "release": "Release", "assets": "アセット数", "downloads": "累計ダウンロード", "manual": "今月行った、数字に影響する可能性のあること",
        "manual_prompt": "月報を公開する前に所有者が次の欄を補完してください。根拠のない数字は推測せず、未記入のままにします。", "bot_share": "ボット比率の推定", "kofi_views": "Ko-fi ページ閲覧数", "kofi_members": "Ko-fi メンバー数", "impact": "数字に影響する可能性のある作業", "placeholder": "所有者の入力待ち", "no_data": "データなし",
        "clone_note": "clone にはボットやミラーが含まれる可能性があります。追跡用に残しますが、効果として直接報告しません。", "release_note": "Release API のダウンロード数は公開後の累計です。変化は二つのスナップショットの差分です。", "issue_status": "Issue #129：所有者がクローズできます。このツールは issue を自動でクローズしません。",
        "metrics": {"views": "閲覧数", "unique_visitors": "ユニーク訪問者", "clones": "clone 数（ボットを含む可能性）", "unique_cloners": "ユニーク clone", "release_downloads": "Release アセットのダウンロード（累計）", "stars": "スター", "forks": "Fork", "watchers": "Watchers", "google_uniques": "Google 経由のユニーク訪問者", "ironman_uniques": "Ironman 経由のユニーク訪問者"},
    },
}


class TrafficReportError(RuntimeError):
    """Raised when a trustworthy report cannot be collected or written."""


def _mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TrafficReportError(f"資料格式錯誤：{context} 必須是 JSON 物件。")
    return value


def _required(value: dict[str, object], key: str, context: str) -> object:
    if key not in value:
        raise TrafficReportError(f"資料不完整：{context} 缺少 {key}。")
    return value[key]


def _required_text(value: dict[str, object], key: str, context: str) -> str:
    item = _required(value, key, context)
    if not isinstance(item, str) or not item:
        raise TrafficReportError(f"資料格式錯誤：{context}.{key} 必須是非空字串。")
    return item


def _required_count(value: dict[str, object], key: str, context: str) -> int:
    item = _required(value, key, context)
    if isinstance(item, bool) or not isinstance(item, int) or item < 0:
        raise TrafficReportError(f"資料格式錯誤：{context}.{key} 必須是非負整數。")
    return item


def _required_list(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        raise TrafficReportError(f"資料格式錯誤：{context} 必須是 JSON 陣列。")
    return value


def _normalise_month(value: str) -> str:
    try:
        parsed = date.fromisoformat(f"{value}-01")
    except ValueError as exc:
        raise TrafficReportError(
            f"月份格式錯誤：{value!r}，請使用 YYYY-MM。"
        ) from exc
    normalised = parsed.strftime("%Y-%m")
    if normalised != value:
        raise TrafficReportError(f"月份格式錯誤：{value!r}，請使用 YYYY-MM。")
    return normalised


def previous_month(month: str) -> str:
    first_day = date.fromisoformat(f"{_normalise_month(month)}-01")
    return (first_day - timedelta(days=1)).strftime("%Y-%m")


def _traffic_metric(payload: object, context: str, daily_key: str) -> dict[str, int]:
    record = _mapping(payload, context)
    count = _required_count(record, "count", context)
    uniques = _required_count(record, "uniques", context)
    daily = _required_list(_required(record, daily_key, context), f"{context}.{daily_key}")
    for index, item in enumerate(daily):
        day = _mapping(item, f"{context}.{daily_key}[{index}]")
        _required_text(day, "timestamp", f"{context}.{daily_key}[{index}]")
        _required_count(day, "count", f"{context}.{daily_key}[{index}]")
        _required_count(day, "uniques", f"{context}.{daily_key}[{index}]")
    return {"count": count, "uniques": uniques}


def _popular_rows(
    payload: object,
    context: str,
    name_key: str,
) -> list[dict[str, object]]:
    entries = _required_list(payload, context)
    rows: list[dict[str, object]] = []
    for index, item in enumerate(entries):
        entry = _mapping(item, f"{context}[{index}]")
        name = _required_text(entry, name_key, f"{context}[{index}]")
        title = entry.get("title", "")
        if not isinstance(title, str):
            raise TrafficReportError(
                f"資料格式錯誤：{context}[{index}].title 必須是字串。"
            )
        rows.append(
            {
                "name": name,
                "title": title,
                "count": _required_count(entry, "count", f"{context}[{index}]"),
                "uniques": _required_count(
                    entry,
                    "uniques",
                    f"{context}[{index}]",
                ),
            }
        )
    return rows


def _repository_metrics(payload: object) -> dict[str, int]:
    record = _mapping(payload, "repository")
    return {
        "stars": _required_count(record, "stargazers_count", "repository"),
        "forks": _required_count(record, "forks_count", "repository"),
        "watchers": _required_count(record, "subscribers_count", "repository"),
    }


def _release_items(payload: object) -> list[object]:
    raw = _required_list(payload, "releases")
    if not raw:
        return []
    nested = all(isinstance(page, list) for page in raw)
    if nested:
        items: list[object] = []
        for page_index, page in enumerate(raw):
            items.extend(
                _required_list(page, f"releases page {page_index}")
            )
        return items
    if any(isinstance(page, list) for page in raw):
        raise TrafficReportError("資料格式錯誤：releases 分頁格式混用。")
    return raw


def _release_rows(payload: object) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index, item in enumerate(_release_items(payload)):
        release = _mapping(item, f"releases[{index}]")
        tag = _required_text(release, "tag_name", f"releases[{index}]")
        assets = _required_list(
            _required(release, "assets", f"releases[{index}]"),
            f"releases[{index}].assets",
        )
        downloads = 0
        for asset_index, asset_item in enumerate(assets):
            asset = _mapping(asset_item, f"releases[{index}].assets[{asset_index}]")
            _required_text(
                asset,
                "name",
                f"releases[{index}].assets[{asset_index}]",
            )
            downloads += _required_count(
                asset,
                "download_count",
                f"releases[{index}].assets[{asset_index}]",
            )
        published = release.get("published_at", "")
        if published is None:
            published = ""
        if not isinstance(published, str):
            raise TrafficReportError(
                f"資料格式錯誤：releases[{index}].published_at 必須是字串。"
            )
        rows.append(
            {
                "tag": tag,
                "published": published[:10],
                "asset_count": len(assets),
                "downloads": downloads,
            }
        )
    return rows


def _source_uniques(
    rows: list[dict[str, object]], tokens: tuple[str, ...]
) -> int:
    total = 0
    for row in rows:
        name = row["name"]
        if not isinstance(name, str):
            raise TrafficReportError("資料格式錯誤：來源名稱必須是字串。")
        if any(token in name.lower() for token in tokens):
            uniques = row["uniques"]
            if not isinstance(uniques, int):
                raise TrafficReportError("資料格式錯誤：來源不重複數必須是整數。")
            total += uniques
    return total


def _api_endpoints(repo: str) -> dict[str, str]:
    prefix = f"repos/{repo}"
    return {
        "repository": prefix,
        "views": f"{prefix}/traffic/views",
        "clones": f"{prefix}/traffic/clones",
        "popular_paths": f"{prefix}/traffic/popular/paths",
        "popular_referrers": f"{prefix}/traffic/popular/referrers",
        "releases": f"{prefix}/releases?per_page=100",
    }


def gh_api(endpoint: str, *, paginate: bool = False) -> object:
    """Call gh api and convert network/auth failures into a clear report error."""
    command = ["gh", "api"]
    if paginate:
        command.extend(["--paginate", "--slurp"])
    command.append(endpoint)
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as exc:
        raise TrafficReportError(
            "無法執行 gh api：請確認 gh CLI 已安裝、網路可用，且已完成登入。"
        ) from exc
    if result.returncode:
        detail = " ".join(result.stderr.split())[:500]
        if not detail:
            detail = "沒有錯誤細節"
        raise TrafficReportError(
            f"GitHub API 取得失敗（{endpoint}，exit {result.returncode}）：{detail}。"
            "請確認網路、gh auth 狀態，以及對該 repo 的流量讀取權限。"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise TrafficReportError(
            f"GitHub API 回應不是有效 JSON（{endpoint}）；未產生報表。"
        ) from exc


def collect_snapshot(
    api_call: Callable[..., object],
    *,
    repo: str = REPOSITORY,
    month: str | None = None,
    collected_at: str | None = None,
) -> dict[str, object]:
    """Fetch and validate one snapshot; the callable is injectable for tests."""
    selected_month = _normalise_month(
        month or date.today().strftime("%Y-%m")
    )
    captured_at = collected_at or datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    if not isinstance(captured_at, str) or not captured_at:
        raise TrafficReportError("擷取時間必須是非空字串。")
    endpoints = _api_endpoints(repo)
    raw = {
        "repository": api_call(endpoints["repository"]),
        "views": api_call(endpoints["views"]),
        "clones": api_call(endpoints["clones"]),
        "popular_paths": api_call(endpoints["popular_paths"]),
        "popular_referrers": api_call(endpoints["popular_referrers"]),
        "releases": api_call(endpoints["releases"], paginate=True),
    }
    views = _traffic_metric(raw["views"], "traffic.views", "views")
    clones = _traffic_metric(raw["clones"], "traffic.clones", "clones")
    popular_paths = _popular_rows(
        raw["popular_paths"],
        "traffic.popular.paths",
        "path",
    )
    popular_referrers = _popular_rows(
        raw["popular_referrers"],
        "traffic.popular.referrers",
        "referrer",
    )
    repository = _repository_metrics(raw["repository"])
    releases = _release_rows(raw["releases"])
    release_downloads = sum(row["downloads"] for row in releases)
    if not isinstance(release_downloads, int):
        raise TrafficReportError("資料格式錯誤：Release 下載總數必須是整數。")
    summary = {
        "views": views["count"],
        "unique_visitors": views["uniques"],
        "clones": clones["count"],
        "unique_cloners": clones["uniques"],
        "release_downloads": release_downloads,
        "stars": repository["stars"],
        "forks": repository["forks"],
        "watchers": repository["watchers"],
        "google_uniques": _source_uniques(popular_referrers, ("google",)),
        "ironman_uniques": _source_uniques(
            popular_referrers,
            ("ithome", "ironman", "鐵人", "铁人"),
        ),
    }
    manual = {key: "" for key in MANUAL_KEYS}
    return {
        "schema_version": 1,
        "repository": repo,
        "month": selected_month,
        "collected_at": captured_at,
        "source_window_days": TRAFFIC_WINDOW_DAYS,
        "p0_baseline_date": P0_BASELINE_DATE,
        "p0_baseline": dict(P0_BASELINE),
        "raw": raw,
        "metrics": {
            "summary": summary,
            "views": views,
            "clones": clones,
            "popular_paths": popular_paths,
            "popular_referrers": popular_referrers,
            "repository": repository,
            "releases": releases,
            "release_downloads_total": release_downloads,
            "manual": manual,
        },
    }


def _normalised_rows(
    metrics: dict[str, object],
    key: str,
    context: str,
) -> list[dict[str, object]]:
    rows = _required_list(_required(metrics, key, "metrics"), context)
    result: list[dict[str, object]] = []
    for index, item in enumerate(rows):
        row = _mapping(item, f"{context}[{index}]")
        _required_text(row, "name", f"{context}[{index}]")
        _required_count(row, "count", f"{context}[{index}]")
        _required_count(row, "uniques", f"{context}[{index}]")
        result.append(row)
    return result


def _saved_release_rows(
    metrics: dict[str, object],
    context: str,
) -> list[dict[str, object]]:
    rows = _required_list(_required(metrics, "releases", "metrics"), context)
    result: list[dict[str, object]] = []
    for index, item in enumerate(rows):
        row = _mapping(item, f"{context}[{index}]")
        _required_text(row, "tag", f"{context}[{index}]")
        _required_count(row, "asset_count", f"{context}[{index}]")
        _required_count(row, "downloads", f"{context}[{index}]")
        result.append(row)
    return result


def _validate_saved_snapshot(snapshot: object) -> dict[str, object]:
    record = _mapping(snapshot, "snapshot")
    _required_text(record, "month", "snapshot")
    metrics = _mapping(_required(record, "metrics", "snapshot"), "metrics")
    summary = _mapping(_required(metrics, "summary", "metrics"), "metrics.summary")
    for key in METRIC_KEYS:
        _required_count(summary, key, "metrics.summary")
    _normalised_rows(metrics, "popular_paths", "metrics.popular_paths")
    _normalised_rows(metrics, "popular_referrers", "metrics.popular_referrers")
    repository = _mapping(
        _required(metrics, "repository", "metrics"),
        "metrics.repository",
    )
    for key in ("stars", "forks", "watchers"):
        _required_count(repository, key, "metrics.repository")
    _saved_release_rows(metrics, "metrics.releases")
    _required_count(metrics, "release_downloads_total", "metrics")
    return record


def load_snapshot(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise TrafficReportError(f"無法讀取上月 JSON：{path}。") from exc
    except json.JSONDecodeError as exc:
        raise TrafficReportError(f"上月 JSON 損壞：{path}。") from exc
    return _validate_saved_snapshot(payload)


def _metrics(snapshot: dict[str, object]) -> dict[str, object]:
    return _mapping(_required(snapshot, "metrics", "snapshot"), "snapshot.metrics")


def _summary(snapshot: dict[str, object]) -> dict[str, object]:
    return _mapping(_required(_metrics(snapshot), "summary", "metrics"), "summary")


def _number(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TrafficReportError("資料格式錯誤：報表數字必須是整數。")
    return value


def _number_cell(value: object) -> str:
    return f"{_number(value):,}"


def _delta_cell(current: object, previous: object | None) -> str:
    if current is None or previous is None:
        return "—"
    delta = _number(current) - _number(previous)
    if delta > 0:
        return f"+{delta:,}"
    return f"{delta:,}"


def _release_comparison_rows(
    current: list[dict[str, object]],
    previous: list[dict[str, object]] | None,
) -> list[tuple[str, dict[str, object] | None, dict[str, object] | None]]:
    current_by_tag: dict[str, dict[str, object]] = {}
    previous_by_tag: dict[str, dict[str, object]] = {}
    order: list[str] = []
    for row in current:
        tag = _required_text(row, "tag", "metrics.releases")
        current_by_tag[tag] = row
        order.append(tag)
    for row in previous or []:
        tag = _required_text(row, "tag", "previous.metrics.releases")
        previous_by_tag[tag] = row
        if tag not in current_by_tag:
            order.append(tag)
    return [
        (tag, current_by_tag.get(tag), previous_by_tag.get(tag))
        for tag in order
    ]


def _render_language(
    language: str,
    current_snapshot: dict[str, object],
    previous_snapshot: dict[str, object] | None,
    report_filename: str,
    raw_filename: str,
) -> list[str]:
    text = REPORT_TEXT[language]
    current_metrics = _metrics(current_snapshot)
    previous_metrics = _metrics(previous_snapshot) if previous_snapshot else None
    current_summary = _summary(current_snapshot)
    previous_summary = _summary(previous_snapshot) if previous_snapshot else None
    month = _required_text(current_snapshot, "month", "snapshot")
    collected_at = _required_text(current_snapshot, "collected_at", "snapshot")
    lines = [
        f"## {language}",
        "",
        f"### {text['title']} — {month}",
        "",
        text["window_note"],
        f"**{text['collected']}**: {collected_at}",
        f"**{text['raw']}**: `{raw_filename}`",
        f"**Report**: `{report_filename}`",
        "",
        f"### {text['comparison']}",
        "",
        f"| {text['metric']} | {text['current']} | {text['previous']} | {text['change']} | {text['p0']} |",
        "|---|---:|---:|---:|---:|",
    ]
    for key in METRIC_KEYS:
        current = _required(current_summary, key, "metrics.summary")
        previous = (
            _required(previous_summary, key, "previous.metrics.summary")
            if previous_summary
            else None
        )
        lines.append(
            f"| {text['metrics'][key]} | {_number_cell(current)} | "
            f"{_number_cell(previous) if previous is not None else '—'} | "
            f"{_delta_cell(current, previous)} | {_number_cell(P0_BASELINE[key])} |"
        )
    lines.extend(
        [
            "",
            f"> {text['clone_note']}",
            "",
            f"### {text['pages']}",
            "",
            f"| {text['page']} | {text['page_title']} | {text['views']} | {text['uniques']} |",
            "|---|---|---:|---:|",
        ]
    )
    paths = _normalised_rows(current_metrics, "popular_paths", "metrics.popular_paths")
    if paths:
        for row in paths:
            lines.append(
                f"| {row['name']} | {row['title'] or '—'} | "
                f"{_number_cell(row['count'])} | {_number_cell(row['uniques'])} |"
            )
    else:
        lines.append(f"| {text['no_data']} | {text['no_data']} | — | — |")
    lines.extend(
        [
            "",
            f"### {text['referrers']}",
            "",
            f"| {text['referrer']} | {text['views']} | {text['uniques']} |",
            "|---|---:|---:|",
        ]
    )
    referrers = _normalised_rows(
        current_metrics,
        "popular_referrers",
        "metrics.popular_referrers",
    )
    if referrers:
        for row in referrers:
            lines.append(
                f"| {row['name']} | {_number_cell(row['count'])} | "
                f"{_number_cell(row['uniques'])} |"
            )
    else:
        lines.append(f"| {text['no_data']} | — | — |")
    lines.extend(
        [
            "",
            f"### {text['releases']}",
            "",
            f"| {text['release']} | {text['assets']} | {text['current']} | {text['previous']} | {text['change']} |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    current_releases = _saved_release_rows(
        current_metrics,
        "metrics.releases",
    )
    previous_releases = (
        _saved_release_rows(previous_metrics, "previous.metrics.releases")
        if previous_metrics
        else None
    )
    release_rows = _release_comparison_rows(current_releases, previous_releases)
    if release_rows:
        for tag, current, previous in release_rows:
            current_downloads = current.get("downloads") if current else None
            previous_downloads = previous.get("downloads") if previous else None
            asset_source = current or previous
            asset_count = asset_source.get("asset_count") if asset_source else None
            lines.append(
                f"| {tag} | {_number_cell(asset_count) if asset_count is not None else '—'} | "
                f"{_number_cell(current_downloads) if current_downloads is not None else '—'} | "
                f"{_number_cell(previous_downloads) if previous_downloads is not None else '—'} | "
                f"{_delta_cell(current_downloads, previous_downloads)} |"
            )
    else:
        lines.append(f"| {text['no_data']} | — | — | — | — |")
    lines.extend(
        [
            "",
            f"> {text['release_note']}",
            "",
            f"### {text['manual']}",
            "",
            text["manual_prompt"],
            "",
            f"- **{text['bot_share']}**：{text['placeholder']}",
            f"- **{text['kofi_views']}**：{text['placeholder']}",
            f"- **{text['kofi_members']}**：{text['placeholder']}",
            f"- **{text['impact']}**：{text['placeholder']}",
            "",
            f"> {text['issue_status']}",
        ]
    )
    return lines


def render_report(
    current_snapshot: dict[str, object],
    previous_snapshot: dict[str, object] | None = None,
    *,
    report_filename: str | None = None,
    raw_filename: str | None = None,
) -> str:
    """Render the validated snapshot as four parallel language sections."""
    current = _validate_saved_snapshot(current_snapshot)
    previous = (
        _validate_saved_snapshot(previous_snapshot)
        if previous_snapshot is not None
        else None
    )
    month = _required_text(current, "month", "snapshot")
    report_name = report_filename or f"traffic-{month}.md"
    raw_name = raw_filename or f"traffic-{month}.json"
    lines = [REPORT_H1, ""]
    for language in LANGUAGE_HEADINGS:
        lines.extend(
            _render_language(language, current, previous, report_name, raw_name)
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(
    current_snapshot: dict[str, object],
    previous_snapshot: dict[str, object] | None,
    output_dir: Path,
    *,
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Write the raw snapshot and report only after all data is validated."""
    current = _validate_saved_snapshot(current_snapshot)
    output_dir = Path(output_dir)
    month = _required_text(current, "month", "snapshot")
    report_path = output_dir / f"traffic-{month}.md"
    raw_path = output_dir / f"traffic-{month}.json"
    if not overwrite and (report_path.exists() or raw_path.exists()):
        raise TrafficReportError(
            f"輸出已存在：{report_path} 或 {raw_path}；如要重跑同月份，請明確使用 --overwrite。"
        )
    report = render_report(
        current,
        previous_snapshot,
        report_filename=report_path.name,
        raw_filename=raw_path.name,
    )
    raw = json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        raw_path.write_text(raw, encoding="utf-8")
        report_path.write_text(report, encoding="utf-8")
    except OSError as exc:
        raise TrafficReportError(
            f"無法寫入月報輸出：{output_dir}；未完成本次保存。"
        ) from exc
    return report_path, raw_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--month",
        help="報表月份（YYYY-MM）；預設為今天所在月份。",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/reports"),
        help="輸出目錄，預設為 docs/reports。",
    )
    parser.add_argument(
        "--previous-json",
        type=Path,
        help="指定上月留存 JSON；未指定時尋找輸出目錄中的上一月份檔案。",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="明確允許覆寫同月份的既有月報與原始 JSON。",
    )
    args = parser.parse_args(argv)
    try:
        month = _normalise_month(args.month or date.today().strftime("%Y-%m"))
        snapshot = collect_snapshot(gh_api, month=month)
        default_previous = args.output_dir / f"traffic-{previous_month(month)}.json"
        previous_path = args.previous_json or default_previous
        if args.previous_json is not None and not previous_path.is_file():
            raise TrafficReportError(f"指定的上月 JSON 不存在：{previous_path}。")
        previous = load_snapshot(previous_path) if previous_path.is_file() else None
        report_path, raw_path = write_outputs(
            snapshot,
            previous,
            args.output_dir,
            overwrite=args.overwrite,
        )
    except TrafficReportError as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 1
    print(f"已產出月報：{report_path}")
    print(f"已保存原始 JSON：{raw_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
