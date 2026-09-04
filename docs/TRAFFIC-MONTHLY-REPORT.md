# 每月流量月報操作說明／每月流量月报操作说明／Monthly traffic report runbook／月次トラフィック月報の実行手順

## 繁體中文

### 目的

本工具把 GitHub 流量端點、熱門頁面、來源、repo 互動數與各 Release 資產下載保存成可重跑的月報。GitHub 流量只保留 14 天，因此原始 JSON 與 Markdown 都要納入每月交接。

### 每月固定日

請擁有者選定固定日期（例如每月第一個工作日），確認 `gh auth status` 可用且帳號對 repo 有讀取 traffic 的權限後執行：

```text
py -3.15 tools/traffic_report.py --month 2026-09
```

首次執行若找不到上月 JSON，報表會以 `—` 標示上月不可比較，不會猜測成長率。若同月份需要重新擷取，必須明確加上 `--overwrite`。

### 輸出檔案

- Markdown 月報寫入 `docs/reports/traffic-YYYY-MM.md`。
- 原始 API 快照寫入 `docs/reports/traffic-YYYY-MM.json`，供下一個月比較並永久留存。
- 報表列出本月與上月、P0（訪客 21、Google 2、鐵人賽 2）基準、熱門頁面、熱門來源、Release 下載、stars、forks 與 watchers。
- Ko-fi 指標、機器人佔比推估，以及「這個月做了什麼可能影響數字的事」保留在報表的人工填寫區塊。
- 執行後將 Markdown 內容貼到 Issue #129 留言作為固定日期的記錄；工具不會自動關閉 issue。

### 資料邊界

GitHub API 的瀏覽與 clone 數是最近 14 天視窗；Release 下載是發布後累計值；clone 可能包含機器人與鏡像，不能直接當成成效。無網路、未登入、權限不足或回應缺欄位時，程式會明確報錯並以 exit 1 結束，不會產生空報表。Issue #129 不由工具自動關閉，可請擁有者在證據核對後結案。

## 简体中文

### 目的

本工具把 GitHub 流量接口、热门页面、来源、仓库互动数和各 Release 资产下载保存为可重复运行的月报。GitHub 流量只保留 14 天，因此原始 JSON 和 Markdown 都要纳入每月交接。

### 每月固定日

请拥有者选定固定日期（例如每月第一个工作日），确认 `gh auth status` 可用且账号对仓库有读取 traffic 的权限后运行：

```text
py -3.15 tools/traffic_report.py --month 2026-09
```

首次运行如果找不到上月 JSON，报表会用 `—` 标示上月不可比较，不会猜测增长率。如果同月份需要重新采集，必须明确加上 `--overwrite`。

### 输出文件

- Markdown 月报写入 `docs/reports/traffic-YYYY-MM.md`。
- 原始 API 快照写入 `docs/reports/traffic-YYYY-MM.json`，供下个月比较并永久保存。
- 报表列出本月与上月、P0（访客 21、Google 2、铁人赛 2）基线、热门页面、热门来源、Release 下载、stars、forks 和 watchers。
- Ko-fi 指标、机器人占比估计，以及“这个月做了什么可能影响数字的事”保留在报表的人工填写区域。
- 运行后将 Markdown 内容贴到 Issue #129 留言，作为固定日期的记录；工具不会自动关闭 issue。

### 数据边界

GitHub API 的浏览和 clone 数是最近 14 天窗口；Release 下载是发布后的累计值；clone 可能包含机器人和镜像，不能直接当作成效。无网络、未登录、权限不足或响应缺少字段时，程序会明确报错并以 exit 1 结束，不会生成空报表。Issue #129 不由工具自动关闭，可请拥有者在核对证据后结案。

## English

### Purpose

This tool stores GitHub traffic endpoints, popular pages, referrers, repository engagement, and every Release asset download in a repeatable monthly report. GitHub keeps traffic for only 14 days, so both the raw JSON and Markdown must be retained during the monthly handoff.

### Fixed monthly day

The owner should choose a fixed date, such as the first working day of each month, confirm that `gh auth status` works and that the account can read traffic for the repository, then run:

```text
py -3.15 tools/traffic_report.py --month 2026-09
```

On the first run, if last month’s JSON is absent, the report marks last month as `—` and does not guess a growth rate. To recapture the same month, pass `--overwrite` explicitly.

### Output files

- The Markdown report is written to `docs/reports/traffic-YYYY-MM.md`.
- The raw API snapshot is written to `docs/reports/traffic-YYYY-MM.json` for next month’s comparison and permanent retention.
- The report lists this month versus last month, the P0 baseline (21 visitors, Google 2, Ironman 2), popular pages, popular referrers, Release downloads, stars, forks, and watchers.
- Ko-fi metrics, an estimated bot share, and “what we did this month that may affect the numbers” remain in the report’s owner-input section.
- After running it, paste the Markdown into an Issue #129 comment as the fixed-day record; the tool never closes the issue automatically.

### Data boundaries

GitHub API views and clones cover a rolling 14-day window; Release downloads are cumulative after publication; clones may include bots and mirrors and must not be treated directly as impact. If the network is unavailable, the CLI is not logged in, permission is insufficient, or a response is missing fields, the program reports the error and exits 1 without creating an empty report. The tool never closes Issue #129; the owner may close it after checking the evidence.

## 日本語

### 目的

このツールは GitHub のトラフィック API、人気ページ、参照元、リポジトリの反応数、各 Release アセットのダウンロード数を、再実行可能な月報として保存します。GitHub のトラフィックは 14 日間しか保持されないため、生 JSON と Markdown の両方を毎月の引き継ぎで保存します。

### 毎月の固定日

所有者が毎月の固定日（例：最初の営業日）を決め、`gh auth status` が利用でき、リポジトリの traffic を読む権限があることを確認してから実行します。

```text
py -3.15 tools/traffic_report.py --month 2026-09
```

初回実行で先月の JSON がない場合、月報は先月を `—` と表示し、成長率を推測しません。同じ月を再取得する場合は `--overwrite` を明示します。

### 出力ファイル

- Markdown 月報は `docs/reports/traffic-YYYY-MM.md` に書き込みます。
- 生 API スナップショットは `docs/reports/traffic-YYYY-MM.json` に保存し、翌月の比較と恒久保存に使います。
- 月報には今月と先月、P0 基準（訪問者 21、Google 2、Ironman 2）、人気ページ、人気の参照元、Release ダウンロード、stars、forks、watchers を記載します。
- Ko-fi 指標、ボット比率の推定、「今月行った、数字に影響する可能性のあること」は月報の所有者入力欄に残します。
- 実行後は Markdown を Issue #129 のコメントへ貼り、固定日の記録にします。ツールは issue を自動でクローズしません。

### データの境界

GitHub API の閲覧数と clone 数は直近 14 日の移動ウィンドウです。Release ダウンロードは公開後の累計であり、clone にはボットやミラーが含まれる可能性があるため、効果として直接扱いません。ネットワーク不可、未ログイン、権限不足、応答の必須欄欠落時は明確にエラーを報告して exit 1 で終了し、空の月報を作りません。ツールは Issue #129 を自動で閉じず、証拠確認後に所有者がクローズできます。
