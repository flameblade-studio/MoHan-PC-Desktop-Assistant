# 執行期合成效能預算／运行时合成性能预算／Runtime compositing performance budget／実行時合成性能予算

## 繁體中文

### 量測範圍與方法

`tools/bench_composite.py` 在 `QT_QPA_PLATFORM=offscreen` 下直接量測 `LayeredFullBodyRenderer` 與 `LayeredParametricFaceRenderer`。正式基準為每輪 5 次、共 5 輪；每個場景回報中位數與以排序樣本線性插值計算的 p95，並回報輪間散布。量測使用 v5 二代 24×25 全身分層、7 個半身剪影，以及內建藍白漢服與原妝；不包含 UI event loop、adapter 發布或視窗排版。

### 實測基準表

| 場景 | 全部樣本中位數 | 全部樣本 p95 | 輪間中位數範圍／散布 | 輪間 p95 範圍／散布 |
| --- | ---: | ---: | --- | --- |
| `cold_full_body` | 1389.922 ms | 1468.653 ms | 1251.438–1409.878 ms／158.440 ms（11.399%） | 1326.069–1482.498 ms／156.429 ms（10.743%） |
| `hot_full_body_view_switch` | 2.485 ms | 3.157 ms | 2.416–2.599 ms／0.183 ms（7.400%） | 2.557–4.290 ms／1.733 ms（58.885%） |
| `hot_half_body_silhouette_switch` | 5.043 ms | 5.600 ms | 4.594–5.440 ms／0.846 ms（16.469%） | 4.842–5.761 ms／0.919 ms（17.107%） |

### 門檻取值

- `cold_full_body` 的擁有者目標是 300 ms；實測 aggregate p95 為 1468.653 ms，五輪最大輪 p95 為 1482.498 ms，因此 `tools/perf_budget.json` 設為 1482.498 ms 並標記 `over_target=true`。這是目前實測回歸上限，不代表達標，也不套用 1.5 倍放寬。
- 兩個熱切換的擁有者目標是 100 ms；依「實測 p95 × 1.5 與目標取較寬鬆者」分別得到 `max(3.157 × 1.5, 100)` 與 `max(5.600 × 1.5, 100)`，所以兩者門檻都是 100 ms，`over_target=false`。

### PNG 解碼稽核

`tools/bench_composite.py` 以 `QPixmap(path)` 與 `QImage.fromData` 的呼叫計數稽核，並只在稽核期間將 `QPixmapCache` 設為 0。第一次全身目標視角切換（`yaw+000-pitch+00` → `yaw+015-pitch+00`）發現 40 次 `QPixmap(path)` 呼叫、26 個唯一 PNG 路徑，其中 8 個路徑重複 2–3 次；另有 10 次 `QImage.fromData`、6 個唯一 payload，其中 3 個 payload 重複。半身第一次 `cheek-rest` → `front-crossed` 也發現 42／26、9 個重複路徑，以及 10／7、3 個重複 payload。兩端都完成載入後的熱切換新增解碼呼叫為 0。結論是第一次切換確實存在同一 PNG 的重複解碼呼叫，應列為後續優化待辦；本任務不改合成演算法。

### CI 閘門

`tests/test_perf_budget.py` 讀取 `tools/perf_budget.json`，在 CI 執行 `tools/bench_composite.py` 的 5 次×1 輪縮減版，並要求三個場景的實測 p95 小於或等於各自 `budget_ms`。冷啟仍以 `over_target=true` 如實呈現；閘門只阻擋相對目前基準的回歸。

### 結論與待辦

熱切換與半身切換目前低於 100 ms 目標；冷啟全身中位數與 p95 均遠超 300 ms，必須在另行授權的效能分支處理。重複 `QPixmap(path)`／`QImage.fromData` 已有量測證據，暫不在本分支修改 `infrastructure/active_outfit_overlay.py` 或 `presentation/companion_*.py`。

## 简体中文

### 测量范围与方法

`tools/bench_composite.py` 在 `QT_QPA_PLATFORM=offscreen` 下直接测量 `LayeredFullBodyRenderer` 与 `LayeredParametricFaceRenderer`。正式基准为每轮 5 次、共 5 轮；每个场景报告中位数与按排序样本线性插值计算的 p95，并报告轮间散布。测量使用 v5 二代 24×25 全身分层、7 个半身剪影，以及内置蓝白汉服与原妆；不包含 UI event loop、adapter 发布或窗口排版。

### 实测基准表

| 场景 | 全部样本中位数 | 全部样本 p95 | 轮间中位数范围／散布 | 轮间 p95 范围／散布 |
| --- | ---: | ---: | --- | --- |
| `cold_full_body` | 1389.922 ms | 1468.653 ms | 1251.438–1409.878 ms／158.440 ms（11.399%） | 1326.069–1482.498 ms／156.429 ms（10.743%） |
| `hot_full_body_view_switch` | 2.485 ms | 3.157 ms | 2.416–2.599 ms／0.183 ms（7.400%） | 2.557–4.290 ms／1.733 ms（58.885%） |
| `hot_half_body_silhouette_switch` | 5.043 ms | 5.600 ms | 4.594–5.440 ms／0.846 ms（16.469%） | 4.842–5.761 ms／0.919 ms（17.107%） |

### 门槛取值

- `cold_full_body` 的所有者目标是 300 ms；实测 aggregate p95 为 1468.653 ms，五轮最大轮 p95 为 1482.498 ms，因此 `tools/perf_budget.json` 设为 1482.498 ms 并标记 `over_target=true`。这是当前实测回归上限，不代表达标，也不套用 1.5 倍放宽。
- 两个热切换的所有者目标是 100 ms；按「实测 p95 × 1.5 与目标取较宽松者」分别得到 `max(3.157 × 1.5, 100)` 与 `max(5.600 × 1.5, 100)`，所以两者门槛都是 100 ms，`over_target=false`。

### PNG 解码稽核

`tools/bench_composite.py` 以 `QPixmap(path)` 与 `QImage.fromData` 的调用计数稽核，并只在稽核期间将 `QPixmapCache` 设为 0。第一次全身目标视角切换（`yaw+000-pitch+00` → `yaw+015-pitch+00`）发现 40 次 `QPixmap(path)` 调用、26 个唯一 PNG 路径，其中 8 个路径重复 2–3 次；另有 10 次 `QImage.fromData`、6 个唯一 payload，其中 3 个 payload 重复。半身第一次 `cheek-rest` → `front-crossed` 也发现 42／26、9 个重复路径，以及 10／7、3 个重复 payload。两端都完成加载后的热切换新增解码调用为 0。结论是第一次切换确实存在同一 PNG 的重复解码调用，应列为后续优化待办；本任务不改合成算法。

### CI 闸门

`tests/test_perf_budget.py` 读取 `tools/perf_budget.json`，在 CI 执行 `tools/bench_composite.py` 的 5 次×1 轮缩减版，并要求三个场景的实测 p95 小于或等于各自 `budget_ms`。冷启仍以 `over_target=true` 如实呈现；闸门只阻挡相对当前基准的回归。

### 结论与待办

热切换与半身切换目前低于 100 ms 目标；冷启全身中位数与 p95 均远超 300 ms，必须在另行授权的性能分支处理。重复 `QPixmap(path)`／`QImage.fromData` 已有测量证据，暂不在本分支修改 `infrastructure/active_outfit_overlay.py` 或 `presentation/companion_*.py`。

## English

### Scope and method

`tools/bench_composite.py` measures `LayeredFullBodyRenderer` and `LayeredParametricFaceRenderer` directly with `QT_QPA_PLATFORM=offscreen`. The formal baseline runs 5 samples per round for 5 rounds; each scenario reports the median, a linearly interpolated p95 over sorted samples, and round-to-round scatter. The workload uses the v5 second-generation 24×25 full-body layers, 7 half-body silhouettes, and the shipped blue-white Hanfu with classic makeup; it excludes the UI event loop, adapter publication, and window layout.

### Measured baseline table

| Scenario | All-sample median | All-sample p95 | Round median range／scatter | Round p95 range／scatter |
| --- | ---: | ---: | --- | --- |
| `cold_full_body` | 1389.922 ms | 1468.653 ms | 1251.438–1409.878 ms／158.440 ms (11.399%) | 1326.069–1482.498 ms／156.429 ms (10.743%) |
| `hot_full_body_view_switch` | 2.485 ms | 3.157 ms | 2.416–2.599 ms／0.183 ms (7.400%) | 2.557–4.290 ms／1.733 ms (58.885%) |
| `hot_half_body_silhouette_switch` | 5.043 ms | 5.600 ms | 4.594–5.440 ms／0.846 ms (16.469%) | 4.842–5.761 ms／0.919 ms (17.107%) |

### Budget selection

- The `cold_full_body` owner target is 300 ms; the measured aggregate p95 is 1468.653 ms and the maximum per-round p95 is 1482.498 ms, so `tools/perf_budget.json` uses 1482.498 ms and marks `over_target=true`. This is a measured regression ceiling, not a claim of target compliance, and it does not apply a 1.5 multiplier.
- The two hot switches have a 100 ms owner target; the required comparison gives `max(3.157 × 1.5, 100)` and `max(5.600 × 1.5, 100)`, so both budgets are 100 ms and `over_target=false`.

### PNG decode audit

`tools/bench_composite.py` audits `QPixmap(path)` and `QImage.fromData` call counts, setting `QPixmapCache` to 0 only during the audit. The first full-body target-view switch (`yaw+000-pitch+00` → `yaw+015-pitch+00`) made 40 `QPixmap(path)` calls across 26 unique PNG paths; 8 paths repeated 2–3 times. It also made 10 `QImage.fromData` calls across 6 unique payloads; 3 payloads repeated. The first half-body `cheek-rest` → `front-crossed` switch likewise made 42／26 calls／unique paths with 9 repeated paths, and 10／7 calls／unique payloads with 3 repeated payloads. After both endpoints were loaded, hot switches added 0 decode calls. The conclusion is that the first switch does make repeated decode calls for the same PNG, which is a follow-up optimization item; this task does not change the compositor algorithm.

### CI gate

`tests/test_perf_budget.py` reads `tools/perf_budget.json`, runs the reduced 5-sample×1-round `tools/bench_composite.py` measurement in CI, and requires every scenario's measured p95 to be at or below its `budget_ms`. The cold start remains honestly marked `over_target=true`; the gate only blocks regressions against the current baseline.

### Conclusion and follow-up

Hot full-body switching and half-body switching are currently below the 100 ms target; cold full-body median and p95 are far above 300 ms and require a separately authorized performance change. The repeated `QPixmap(path)`／`QImage.fromData` calls have measured evidence; this branch does not modify `infrastructure/active_outfit_overlay.py` or `presentation/companion_*.py`.

## 日本語

### 測定範囲と方法

`tools/bench_composite.py` は `QT_QPA_PLATFORM=offscreen` で `LayeredFullBodyRenderer` と `LayeredParametricFaceRenderer` を直接測定します。正式ベースラインは各ラウンド 5 回、合計 5 ラウンドです。各シナリオは中央値、ソート済みサンプルの線形補間 p95、ラウンド間のばらつきを報告します。v5 第二世代の全身 24×25 レイヤー、半身 7 シルエット、同梱の青白漢服と標準メイクを使用し、UI event loop、adapter 公開、ウィンドウ配置は含めません。

### 実測ベースライン表

| シナリオ | 全サンプル中央値 | 全サンプル p95 | ラウンド中央値の範囲／ばらつき | ラウンド p95 の範囲／ばらつき |
| --- | ---: | ---: | --- | --- |
| `cold_full_body` | 1389.922 ms | 1468.653 ms | 1251.438–1409.878 ms／158.440 ms（11.399%） | 1326.069–1482.498 ms／156.429 ms（10.743%） |
| `hot_full_body_view_switch` | 2.485 ms | 3.157 ms | 2.416–2.599 ms／0.183 ms（7.400%） | 2.557–4.290 ms／1.733 ms（58.885%） |
| `hot_half_body_silhouette_switch` | 5.043 ms | 5.600 ms | 4.594–5.440 ms／0.846 ms（16.469%） | 4.842–5.761 ms／0.919 ms（17.107%） |

### 閾値の選定

- `cold_full_body` の所有者目標は 300 ms です。実測 aggregate p95 は 1468.653 ms、5 ラウンド中の最大 p95 は 1482.498 ms なので、`tools/perf_budget.json` は 1482.498 ms とし、`over_target=true` を付けます。これは実測された回帰上限であり、目標達成の主張ではなく、1.5 倍の緩和も適用しません。
- 2 つのホット切替の所有者目標は 100 ms です。必要な比較は `max(3.157 × 1.5, 100)` と `max(5.600 × 1.5, 100)` となるため、どちらも 100 ms、`over_target=false` です。

### PNG デコード監査

`tools/bench_composite.py` は `QPixmap(path)` と `QImage.fromData` の呼び出し数を監査し、監査中だけ `QPixmapCache` を 0 に設定します。最初の全身ターゲット視点切替（`yaw+000-pitch+00` → `yaw+015-pitch+00`）では、26 個の一意な PNG パスに対して `QPixmap(path)` が 40 回呼ばれ、8 パスが 2–3 回重複しました。また `QImage.fromData` は 6 個の一意 payload に対して 10 回呼ばれ、3 payload が重複しました。半身の最初の `cheek-rest` → `front-crossed` 切替でも 42／26 回／一意パス、9 重複パス、10／7 回／一意 payload、3 重複 payload でした。両端を読み込み済みにしたホット切替の追加デコード呼び出しは 0 です。結論として、最初の切替では同じ PNG の重複デコード呼び出しが実際に発生しており、後続最適化の課題です。本タスクでは合成アルゴリズムを変更しません。

### CI ゲート

`tests/test_perf_budget.py` は `tools/perf_budget.json` を読み、CI で 5 回×1 ラウンドに縮小した `tools/bench_composite.py` を実行し、各シナリオの実測 p95 が対応する `budget_ms` 以下であることを要求します。冷起動は `over_target=true` として正直に残し、ゲートは現行ベースラインからの回帰だけを阻止します。

### 結論とフォローアップ

全身ホット切替と半身切替は現在 100 ms 目標以下です。全身冷起動の中央値と p95 は 300 ms を大きく超えており、別途承認された性能変更で対応する必要があります。重複 `QPixmap(path)`／`QImage.fromData` には実測証拠があり、本ブランチでは `infrastructure/active_outfit_overlay.py` と `presentation/companion_*.py` を変更しません。
