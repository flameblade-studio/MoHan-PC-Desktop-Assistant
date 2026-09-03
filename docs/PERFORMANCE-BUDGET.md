# 執行期合成效能預算／运行时合成性能预算／Runtime compositing performance budget／実行時合成性能予算

## 繁體中文

### 量測範圍與方法

`tools/bench_composite.py` 在 `QT_QPA_PLATFORM=offscreen` 下直接量測 `LayeredFullBodyRenderer` 與 `LayeredParametricFaceRenderer`，載入 `v5-base-layered`。正式開發機基準為每輪 5 次、共 5 輪；同一次執行也以固定的 68-byte 記憶體 PNG 執行 100000 次 `QImage.fromData` 解碼，校準指標為 `calibration.summary.p95_ms`。本次校準全樣本 p95 為 1014.439 ms，各輪 p95 為 967.026–1011.737 ms；縮減閘門驗證曾觀測到 833.677 ms 的校準下界。p95 使用排序樣本的線性插值；範圍只含 offscreen 合成，不含 UI event loop、adapter 發布與視窗配置。

### 實測基準表

| 指標 | 全樣本中位數 | 全樣本 p95 | 各輪 p95 範圍 | 各輪 p95 雜訊幅度 |
| --- | ---: | ---: | --- | ---: |
| `cold_full_body` | 1269.993 ms | 1337.497 ms | 1288.591–1406.008 ms | 117.417 ms |
| `hot_full_body_view_switch` | 2.690 ms | 4.861 ms | 2.624–5.015 ms | 2.391 ms |
| `hot_half_body_silhouette_switch` | 4.473 ms | 5.731 ms | 4.496–6.062 ms | 1.566 ms |

### 門檻取值

- `developer_known_hardware` 使用精確匹配的已知開發機環境；`absolute_budget_ms` 為 cold 1482.498 ms、兩個 hot 指標各 100.0 ms，保留既有已接受的絕對趨勢天花板。
- `ratio_budget` 以同輪合成 p95／校準 p95 的最大值為基礎；cold 的歷史 1482.498 ms 天花板再以已觀測的縮減閘門校準下界 833.677 ms 正規化，三個 CI 比值門檻依序為 1.778264、0.005186、0.006269。
- `ci_runner` 只把目前唯一的 1722.333 ms cold CI 觀測列為趨勢資料；獨立執行數為 1，未達 3 次，因此不建立絕對 CI 門檻。
- `cold_full_body` 保留 `over_target=true`；實測仍高於 300 ms 擁有者目標，這不是通過目標的宣告。

### PNG 解碼稽核

既有稽核顯示首次 full-body 與 half-body 切換仍會對相同 PNG 或 payload 重複解碼，兩端預熱後的 hot 切換則不再增加解碼呼叫。本次只新增固定記憶體 PNG 的 CPU／解碼校準尺，未改動合成器演算法；校準 payload 的 SHA-256 及每樣本 100000 次解碼規格記錄於 JSON。

### CI 閘門

`tests/test_perf_budget.py` 在 `ci_runner`（由 `GITHUB_ACTIONS=true` 或 `CI=true` 識別）讓合成執行 5 samples × 1 round，並在同次執行固定校準 5 rounds；將每個 `measurements.*.summary.p95_ms` 除以同一次執行的 `calibration.summary.p95_ms`，再與 `ratio_budget` 比較。`absolute_budget_ms` 在 CI 僅供記錄趨勢；校準或合成樣本少於 5、校準 p95 非正或非有限、或環境無法辨識時一律 fail-closed，並印出實測值與門檻。

### 結論與待辦

hot full-body 與 half-body 切換仍低於 100 ms 目標；cold full-body 仍遠高於 300 ms，需另案授權改善。CI 現在以同機校準比值主動擋回歸，同時保留絕對毫秒趨勢；後續累積至少 3 次獨立 CI 執行後，再評估是否能建立有統計依據的絕對 CI 趨勢線。

## 简体中文

### 量测范围与方法

`tools/bench_composite.py` 在 `QT_QPA_PLATFORM=offscreen` 下直接测量 `LayeredFullBodyRenderer` 与 `LayeredParametricFaceRenderer`，加载 `v5-base-layered`。正式开发机基准为每轮 5 次、共 5 轮；同一次执行也用固定的 68-byte 内存 PNG 执行 100000 次 `QImage.fromData` 解码，校准指标为 `calibration.summary.p95_ms`。本次校准全样本 p95 为 1014.439 ms，各轮 p95 为 967.026–1011.737 ms；缩减闸门验证曾观测到 833.677 ms 的校准下界。p95 使用排序样本的线性插值；范围只含 offscreen 合成，不含 UI event loop、adapter 发布与窗口布局。

### 实测基准表

| 指标 | 全样本中位数 | 全样本 p95 | 各轮 p95 范围 | 各轮 p95 噪声幅度 |
| --- | ---: | ---: | --- | ---: |
| `cold_full_body` | 1269.993 ms | 1337.497 ms | 1288.591–1406.008 ms | 117.417 ms |
| `hot_full_body_view_switch` | 2.690 ms | 4.861 ms | 2.624–5.015 ms | 2.391 ms |
| `hot_half_body_silhouette_switch` | 4.473 ms | 5.731 ms | 4.496–6.062 ms | 1.566 ms |

### 门槛取值

- `developer_known_hardware` 使用精确匹配的已知开发机环境；`absolute_budget_ms` 为 cold 1482.498 ms、两个 hot 指标各 100.0 ms，保留既有已接受的绝对趋势上限。
- `ratio_budget` 以同轮合成 p95／校准 p95 的最大值为基础；cold 的历史 1482.498 ms 上限再用已观测的缩减闸门校准下界 833.677 ms 归一化，三个 CI 比值门槛依次为 1.778264、0.005186、0.006269。
- `ci_runner` 只把目前唯一的 1722.333 ms cold CI 观测列为趋势数据；独立执行数为 1，未达到 3 次，因此不建立绝对 CI 门槛。
- `cold_full_body` 保留 `over_target=true`；实测仍高于 300 ms 所有者目标，这不是达到目标的声明。

### PNG 解码稽核

既有稽核显示首次 full-body 与 half-body 切换仍会对相同 PNG 或 payload 重复解码，两端预热后的 hot 切换则不再增加解码调用。本次只新增固定内存 PNG 的 CPU／解码校准尺，未改动合成器算法；校准 payload 的 SHA-256 及每样本 100000 次解码规格记录在 JSON 中。

### CI 闸门

`tests/test_perf_budget.py` 在 `ci_runner`（由 `GITHUB_ACTIONS=true` 或 `CI=true` 识别）让合成执行 5 samples × 1 round，并在同次执行固定校准 5 rounds；将每个 `measurements.*.summary.p95_ms` 除以同一次执行的 `calibration.summary.p95_ms`，再与 `ratio_budget` 比较。`absolute_budget_ms` 在 CI 仅用于记录趋势；校准或合成样本少于 5、校准 p95 非正或非有限、或环境无法识别时一律 fail-closed，并打印实测值与门槛。

### 结论与待办

hot full-body 与 half-body 切换仍低于 100 ms 目标；cold full-body 仍远高于 300 ms，需要另案授权改进。CI 现在以同机校准比值主动阻挡回归，同时保留绝对毫秒趋势；后续累积至少 3 次独立 CI 执行后，再评估是否能建立有统计依据的绝对 CI 趋势线。

## English

### Scope and method

`tools/bench_composite.py` measures `LayeredFullBodyRenderer` and `LayeredParametricFaceRenderer` directly under `QT_QPA_PLATFORM=offscreen`, loading `v5-base-layered`. The formal developer baseline uses 5 samples per round for 5 rounds; the same execution also decodes a fixed 68-byte in-memory PNG 100000 times per sample with `QImage.fromData`, using `calibration.summary.p95_ms` as the calibration metric. This calibration capture has an all-sample p95 of 1014.439 ms and per-round p95 values from 967.026 to 1011.737 ms; reduced gate validation observed a calibration floor of 833.677 ms. p95 uses linear interpolation over sorted samples; the scope is offscreen compositing only and excludes the UI event loop, adapter publication, and window layout.

### Measured baseline table

| Metric | All-sample median | All-sample p95 | Per-round p95 range | Per-round p95 scatter |
| --- | ---: | ---: | --- | ---: |
| `cold_full_body` | 1269.993 ms | 1337.497 ms | 1288.591–1406.008 ms | 117.417 ms |
| `hot_full_body_view_switch` | 2.690 ms | 4.861 ms | 2.624–5.015 ms | 2.391 ms |
| `hot_half_body_silhouette_switch` | 4.473 ms | 5.731 ms | 4.496–6.062 ms | 1.566 ms |

### Budget selection

- `developer_known_hardware` uses an exact match for the recorded developer workstation; `absolute_budget_ms` is 1482.498 ms for cold and 100.0 ms for each hot metric, preserving the accepted absolute trend ceilings.
- `ratio_budget` starts with the maximum paired composition-p95/calibration-p95 ratio; the cold historical ceiling is normalized by the observed reduced-gate calibration floor of 833.677 ms, giving CI ratio thresholds of 1.778264, 0.005186, and 0.006269.
- `ci_runner` records the sole captured 1722.333 ms cold CI observation as trend data; independent_runs is 1, below 3, so no absolute CI threshold is established.
- `cold_full_body` retains `over_target=true`; the measured value remains above the 300 ms owner target, which is not a target-compliance claim.

### PNG decode audit

The existing audit shows that the first full-body and half-body switches still repeat decode calls for the same PNG or payload, while warmed hot switches add no further decode calls. This change adds only a fixed in-memory PNG CPU/decode calibration ruler and does not change the compositor algorithm; the calibration payload SHA-256 and 100000 decodes per sample are recorded in JSON.

### CI gate

`tests/test_perf_budget.py` selects `ci_runner` when `GITHUB_ACTIONS=true` or `CI=true`, runs compositor measurements for 5 samples × 1 round, and fixes calibration at 5 rounds in that same execution. It divides each `measurements.*.summary.p95_ms` by the same execution's `calibration.summary.p95_ms` before comparing it with `ratio_budget`. `absolute_budget_ms` is record-only trend data in CI; fewer than 5 calibration or compositor samples, a non-positive or non-finite calibration p95, or an unidentifiable environment fails closed with the measured value and threshold.

### Conclusion and follow-up

Hot full-body and half-body switching remain below the 100 ms target; cold full-body remains far above 300 ms and requires a separately authorized improvement. CI now actively gates regressions with a same-machine calibration ratio while retaining absolute millisecond trends; after at least 3 independent CI runs, the project can reassess whether an evidence-based absolute CI trend line is justified.

## 日本語

### 測定範囲と方法

`tools/bench_composite.py` は `QT_QPA_PLATFORM=offscreen` 上で `LayeredFullBodyRenderer` と `LayeredParametricFaceRenderer` を直接測定し、`v5-base-layered` を読み込む。正式な開発機ベースラインは 1 ラウンド 5 サンプルを 5 ラウンド実行する。同じ実行内で固定 68-byte のメモリ内 PNG を `QImage.fromData` で各サンプル 100000 回デコードし、校正指標に `calibration.summary.p95_ms` を使う。今回の校正全サンプル p95 は 1014.439 ms、ラウンド別 p95 は 967.026–1011.737 ms であり、縮減ゲート検証では 833.677 ms の校正下限が観測された。p95 はソート済みサンプルの線形補間で求め、範囲は offscreen 合成だけとし、UI event loop、adapter 公開、ウィンドウ配置を除外する。

### 実測ベースライン表

| 指標 | 全サンプル中央値 | 全サンプル p95 | ラウンド別 p95 範囲 | ラウンド別 p95 ばらつき |
| --- | ---: | ---: | --- | ---: |
| `cold_full_body` | 1269.993 ms | 1337.497 ms | 1288.591–1406.008 ms | 117.417 ms |
| `hot_full_body_view_switch` | 2.690 ms | 4.861 ms | 2.624–5.015 ms | 2.391 ms |
| `hot_half_body_silhouette_switch` | 4.473 ms | 5.731 ms | 4.496–6.062 ms | 1.566 ms |

### 閾値の選定

- `developer_known_hardware` は記録済み開発機との完全一致を使う。`absolute_budget_ms` は cold が 1482.498 ms、各 hot 指標が 100.0 ms で、承認済みの絶対トレンド上限を保持する。
- `ratio_budget` は同一ラウンドの合成 p95／校正 p95 比の最大値を起点とし、cold の過去の 1482.498 ms 上限を観測済み縮減ゲート校正下限 833.677 ms で正規化する。3 つの CI 比率閾値は 1.778264、0.005186、0.006269 である。
- `ci_runner` は取得できた唯一の 1722.333 ms cold CI 観測をトレンドとして記録する。独立実行数は 1 で 3 未満のため、絶対 CI 閾値は設定しない。
- `cold_full_body` は `over_target=true` を維持する。実測値は 300 ms の所有者目標を上回っており、目標達成を意味しない。

### PNG デコード監査

既存監査では、full-body と half-body の初回切替で同じ PNG または payload のデコード呼び出しが繰り返され、両端をウォームアップした hot 切替では追加のデコードが発生しない。本変更は固定メモリ内 PNG の CPU／デコード校正尺だけを追加し、合成器アルゴリズムは変更しない。校正 payload の SHA-256 とサンプルごとの 100000 回デコード仕様は JSON に記録する。

### CI ゲート

`tests/test_perf_budget.py` は `GITHUB_ACTIONS=true` または `CI=true` のとき `ci_runner` を選び、合成測定を 5 samples × 1 round、同じ実行の校正を固定 5 rounds で行う。各 `measurements.*.summary.p95_ms` を同じ実行の `calibration.summary.p95_ms` で割り、`ratio_budget` と比較する。`absolute_budget_ms` は CI ではトレンド記録だけに使い、校正または合成サンプルが 5 未満、校正 p95 が正でないか有限でない、または環境を識別できない場合は実測値と閾値を示して fail-closed とする。

### 結論とフォローアップ

hot の full-body と half-body 切替は 100 ms 目標以内だが、cold full-body は 300 ms を大きく上回り、別途承認された改善が必要である。CI は同一マシン校正比で回帰を能動的にゲートしつつ絶対ミリ秒のトレンドを保持する。独立した CI 実行を少なくとも 3 回蓄積した後、根拠のある絶対 CI トレンド線を設定できるか再評価する。
