# 執行期合成效能預算／运行时合成性能预算／Runtime compositing performance budget／実行時合成パフォーマンス予算

## 繁體中文

`tools/bench_composite.py` 在 `QT_QPA_PLATFORM=offscreen` 下直接測量正式的全身與半身分層 renderer。每個執行結果的指標 p95 可用 `--record` 追加到 `tools/perf_budget.json`；一般閘門測試不會改寫版控資料。

每個「環境 × 指標」都保存 `samples_ms`、`sample_count` 與 `observed_spread`（min／median／p95）。樣本數少於 3 時，`gating=false`、必須有 `reason`，測試只記錄並印出「尚未擋門，因為樣本不足」；樣本數至少 3 時才擋門。

擋門門檻為：`max(max(observed p95) * 1.5, owner target)`。因此目前開發機三項都擋門：cold `2109.012 ms`、兩項 hot `100.0 ms`。CI 目前 cold `n=1`、兩項 hot `n=0`，三項都不擋門；它們的觀測仍會被保留，不能用 `gating=false` 關閉已達樣本數的指標。追加三次獨立 benchmark 執行後，`--record` 會自動重算散布與門檻。

目前資料摘要：

| 環境 × 指標 | n | min／median／p95 (ms) | 狀態／門檻 (ms) |
| --- | ---: | ---: | --- |
| developer × cold_full_body | 5 | 1288.591／1314.287／1391.630 | 擋門／2109.012 |
| developer × hot_full_body_view_switch | 5 | 2.624／2.804／4.944 | 擋門／100.000 |
| developer × hot_half_body_silhouette_switch | 5 | 4.496／4.825／5.826 | 擋門／100.000 |
| CI × cold_full_body | 1 | 1722.333／1722.333／1722.333 | 不擋門／樣本不足 |
| CI × hot_full_body_view_switch | 0 | —／—／— | 不擋門／樣本不足 |
| CI × hot_half_body_silhouette_switch | 0 | —／—／— | 不擋門／樣本不足 |

### 校準尺判斷

現行比值仍保留作為有足夠配對樣本時的輔助斷言，但固定 1×1 PNG 的 100000 次 `QImage.fromData` 解碼，不能完整代表已暖的半身切換：半身切換是在 1254×1254 畫布上繪製多個 RGBA 圖層，而且 decode audit 顯示暖切換沒有新的 PNG decode。故 `hot_half_body_silhouette_switch` 的 normalized ratio 不是充分的因果成本模型，可能因分母的 Qt 解碼速度或 CPU 雜訊變化而誤報。這一輪不改校準方式；後續建議新增同畫布、同圖層數、同 alpha 合成路徑的 matched compositor calibration，再與現行比值並行驗證。

## 简体中文

`tools/bench_composite.py` 在 `QT_QPA_PLATFORM=offscreen` 下直接测量正式的全身与半身分层 renderer。每次执行的指标 p95 可用 `--record` 追加到 `tools/perf_budget.json`；普通门禁测试不会改写版本库资料。

每个“环境 × 指标”都保存 `samples_ms`、`sample_count` 和 `observed_spread`（min／median／p95）。样本数少于 3 时，`gating=false` 且必须有 `reason`，测试只记录并打印“尚未挡门，因为样本不足”；样本数至少 3 时才挡门。

门槛为：`max(max(observed p95) * 1.5, owner target)`。当前开发机三项都挡门：cold `2109.012 ms`、两项 hot `100.0 ms`。CI 当前 cold `n=1`、两项 hot `n=0`，三项都不挡门；观测仍会保留，不能用 `gating=false` 关闭已达到样本数的指标。追加三次独立 benchmark 执行后，`--record` 会自动重算散布与门槛。

当前数据摘要：

| 环境 × 指标 | n | min／median／p95 (ms) | 状态／门槛 (ms) |
| --- | ---: | ---: | --- |
| developer × cold_full_body | 5 | 1288.591／1314.287／1391.630 | 挡门／2109.012 |
| developer × hot_full_body_view_switch | 5 | 2.624／2.804／4.944 | 挡门／100.000 |
| developer × hot_half_body_silhouette_switch | 5 | 4.496／4.825／5.826 | 挡门／100.000 |
| CI × cold_full_body | 1 | 1722.333／1722.333／1722.333 | 不挡门／样本不足 |
| CI × hot_full_body_view_switch | 0 | —／—／— | 不挡门／样本不足 |
| CI × hot_half_body_silhouette_switch | 0 | —／—／— | 不挡门／样本不足 |

### 校准尺判断

现行比值仍保留为有足够配对样本时的辅助断言，但固定 1×1 PNG 的 100000 次 `QImage.fromData` 解码，不能完整代表已暖的半身切换：半身切换是在 1254×1254 画布上绘制多个 RGBA 图层，而且 decode audit 显示暖切换没有新的 PNG decode。因此 `hot_half_body_silhouette_switch` 的 normalized ratio 不是充分的因果成本模型，可能因分母的 Qt 解码速度或 CPU 噪声变化而误报。本轮不改校准方式；后续建议加入同画布、同图层数、同 alpha 合成路径的 matched compositor calibration，再与现行比值并行验证。

## English

`tools/bench_composite.py` measures the shipped full-body and half-body layered renderers directly under `QT_QPA_PLATFORM=offscreen`. Each execution's metric p95 can be appended to `tools/perf_budget.json` with `--record`; the normal gate test never rewrites the tracked budget.

Every environment × metric stores `samples_ms`, `sample_count`, and `observed_spread` (min/median/p95). With fewer than 3 samples, `gating=false` requires a non-empty `reason`; the test records the observation and prints that the metric is not gated because samples are insufficient. A metric gates only at 3 or more samples.

The gate is `max(max(observed p95) * 1.5, owner target)`. The current developer history gates all three metrics: cold `2109.012 ms` and both hot metrics `100.0 ms`. CI currently has cold `n=1` and both hot metrics `n=0`, so none gates; observations remain recorded, and `gating=false` cannot disable a metric whose sample count has reached 3. After three independent benchmark executions, `--record` recomputes the spread and threshold.

Current data:

| Environment × metric | n | min / median / p95 (ms) | Status / threshold (ms) |
| --- | ---: | ---: | --- |
| developer × cold_full_body | 5 | 1288.591 / 1314.287 / 1391.630 | gated / 2109.012 |
| developer × hot_full_body_view_switch | 5 | 2.624 / 2.804 / 4.944 | gated / 100.000 |
| developer × hot_half_body_silhouette_switch | 5 | 4.496 / 4.825 / 5.826 | gated / 100.000 |
| CI × cold_full_body | 1 | 1722.333 / 1722.333 / 1722.333 | not gated / insufficient samples |
| CI × hot_full_body_view_switch | 0 | — / — / — | not gated / insufficient samples |
| CI × hot_half_body_silhouette_switch | 0 | — / — / — | not gated / insufficient samples |

### Calibration assessment

The existing normalized-ratio assertion remains available when enough paired samples exist, but 100000 decodes of a fixed 1×1 PNG with `QImage.fromData` do not fully represent a warmed half-body switch: that switch paints multiple RGBA layers on a 1254×1254 canvas, and the decode audit shows no new PNG decode on the warmed switch. Therefore the `hot_half_body_silhouette_switch` ratio is not a sufficient causal cost model and can misreport when Qt decode speed or CPU noise changes in the denominator. This change deliberately does not alter the ruler. A future improvement should add a matched compositor calibration with the same canvas, layer count, and alpha-compositing path, then compare it with the current ratio in parallel.

## 日本語

`tools/bench_composite.py` は `QT_QPA_PLATFORM=offscreen` で正式な全身・半身レイヤー renderer を直接測定します。各実行の指標 p95 は `--record` で `tools/perf_budget.json` に追記できます。通常のゲートテストは管理対象の予算ファイルを書き換えません。

環境 × 指標ごとに `samples_ms`、`sample_count`、`observed_spread`（min／median／p95）を保存します。3 未満のサンプルでは `gating=false` に空でない `reason` が必須で、観測だけを記録し「サンプル不足のためゲートしない」と表示します。3 以上になった指標だけをゲートします。

ゲートは `max(max(observed p95) * 1.5, owner target)` です。現在の開発機履歴は 3 指標すべてをゲートします：cold は `2109.012 ms`、hot 2 指標は `100.0 ms`。CI は cold `n=1`、hot 2 指標 `n=0` のため、現在はすべてゲートしません。観測は保持され、3 サンプルに達した指標を `gating=false` で無効化することはできません。独立 benchmark を 3 回追記すると、`--record` が散布と閾値を再計算します。

現在のデータ：

| 環境 × 指標 | n | min／median／p95 (ms) | 状態／閾値 (ms) |
| --- | ---: | ---: | --- |
| developer × cold_full_body | 5 | 1288.591／1314.287／1391.630 | ゲート／2109.012 |
| developer × hot_full_body_view_switch | 5 | 2.624／2.804／4.944 | ゲート／100.000 |
| developer × hot_half_body_silhouette_switch | 5 | 4.496／4.825／5.826 | ゲート／100.000 |
| CI × cold_full_body | 1 | 1722.333／1722.333／1722.333 | 非ゲート／サンプル不足 |
| CI × hot_full_body_view_switch | 0 | —／—／— | 非ゲート／サンプル不足 |
| CI × hot_half_body_silhouette_switch | 0 | —／—／— | 非ゲート／サンプル不足 |

### 校正尺の判断

既存の正規化比率アサーションは、十分な対応サンプルがある場合に残します。ただし固定 1×1 PNG を `QImage.fromData` で 100000 回 decode する処理は、暖機済み半身切替を完全には表しません。半身切替は 1254×1254 キャンバスで複数の RGBA レイヤーを描画し、decode audit でも暖機済み切替に新しい PNG decode はありません。そのため `hot_half_body_silhouette_switch` の比率は十分な因果コストモデルではなく、分母の Qt decode 速度や CPU ノイズの変動で誤判定し得ます。今回は校正方式を変更しません。将来は同じキャンバス、レイヤー数、alpha 合成経路を使う matched compositor calibration を追加し、現行比率と並行して検証することを推奨します。
