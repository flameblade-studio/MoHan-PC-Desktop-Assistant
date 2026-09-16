# 執行期合成效能預算／运行时合成性能预算／Runtime compositing performance budget／実行時合成パフォーマンス予算

## 繁體中文

`tools/bench_composite.py` 在 `QT_QPA_PLATFORM=offscreen` 下直接測量正式的全身與半身分層 renderer。每個執行結果的指標 p95 可用 `--record` 追加到 `tools/perf_budget.json`；一般閘門測試維持版控資料原狀。

每個「環境 × 指標」都保存 `samples_ms`、`sample_count` 與 `observed_spread`（min／median／p95）。樣本數少於 3 時，`gating=false`、必須有 `reason`，測試記錄並印出既有狀態字串「尚未擋門，因為樣本不足」；樣本數達 3 後啟用門檻。

擋門門檻預先固定為：`max(max(observed p95) * 1.5, owner target)`；這裡的 observed p95 是每次獨立執行的 aggregate p95。樣本未達 3 筆時不建立有效門檻。目前六個環境 × 指標組合都只有 0–1 次獨立執行，因此全部只記錄、不擋門；這不是跳過測試，`gating=false` 受資料形狀與測試約束。每次 `--record` 只追加該次執行的 aggregate p95，個別組合達 n=3 後才自動重算散布並啟用閘門。

目前資料摘要：

| 環境 × 指標 | n | min／median／p95 (ms) | 狀態／門檻 (ms) |
| --- | ---: | ---: | --- |
| developer × cold_full_body | 1 | 1337.497／1337.497／1337.497 | 不擋門／樣本不足 |
| developer × hot_full_body_view_switch | 1 | 4.861／4.861／4.861 | 不擋門／樣本不足 |
| developer × hot_half_body_silhouette_switch | 1 | 5.731／5.731／5.731 | 不擋門／樣本不足 |
| CI × cold_full_body | 1 | 1722.333／1722.333／1722.333 | 不擋門／樣本不足 |
| CI × hot_full_body_view_switch | 0 | —／—／— | 不擋門／樣本不足 |
| CI × hot_half_body_silhouette_switch | 0 | —／—／— | 不擋門／樣本不足 |

### 校準尺判斷

現行比值仍保留作為有足夠配對樣本時的輔助斷言，但固定 1×1 PNG 的 100000 次 `QImage.fromData` 解碼，其代表範圍限於固定解碼基準，已暖半身切換另由合成路徑量測：半身切換是在 1254×1254 畫布上繪製多個 RGBA 圖層，而且 decode audit 顯示暖切換沒有新的 PNG decode。故 `hot_half_body_silhouette_switch` 的 normalized ratio 定位為輔助比值而非獨立因果成本模型，可能因分母的 Qt 解碼速度或 CPU 雜訊變化而誤報。這一輪維持既有校準方式；後續建議新增同畫布、同圖層數、同 alpha 合成路徑的 matched compositor calibration，再與現行比值並行驗證。

## 简体中文

`tools/bench_composite.py` 在 `QT_QPA_PLATFORM=offscreen` 下直接测量正式的全身与半身分层 renderer。每次执行的指标 p95 可用 `--record` 追加到 `tools/perf_budget.json`；普通门禁测试不会改写版本库资料。

每个“环境 × 指标”都保存 `samples_ms`、`sample_count` 和 `observed_spread`（min／median／p95）。样本数少于 3 时，`gating=false` 且必须有 `reason`，测试记录并打印现有状态字符串“尚未挡门，因为样本不足”；样本数达到 3 后启用关卡。

门槛预先固定为：`max(max(observed p95) * 1.5, owner target)`；这里的 observed p95 是每次独立执行的 aggregate p95。样本未达 3 笔时不建立有效门槛。目前六个环境 × 指标组合都只有 0–1 次独立执行，因此全部只记录、不挡门；这不是跳过测试，`gating=false` 受数据形状与测试约束。每次 `--record` 只追加该次执行的 aggregate p95，个别组合达到 n=3 后才自动重算散布并启用闸门。

当前数据摘要：

| 环境 × 指标 | n | min／median／p95 (ms) | 状态／门槛 (ms) |
| --- | ---: | ---: | --- |
| developer × cold_full_body | 1 | 1337.497／1337.497／1337.497 | 不挡门／样本不足 |
| developer × hot_full_body_view_switch | 1 | 4.861／4.861／4.861 | 不挡门／样本不足 |
| developer × hot_half_body_silhouette_switch | 1 | 5.731／5.731／5.731 | 不挡门／样本不足 |
| CI × cold_full_body | 1 | 1722.333／1722.333／1722.333 | 不挡门／样本不足 |
| CI × hot_full_body_view_switch | 0 | —／—／— | 不挡门／样本不足 |
| CI × hot_half_body_silhouette_switch | 0 | —／—／— | 不挡门／样本不足 |

### 校准尺判断

现行比值仍保留为有足够配对样本时的辅助断言，但固定 1×1 PNG 的 100000 次 `QImage.fromData` 解码，其代表范围限于固定解码基准，已暖半身切换另由合成路径测量：半身切换是在 1254×1254 画布上绘制多个 RGBA 图层，而且 decode audit 显示暖切换没有新的 PNG decode。因此 `hot_half_body_silhouette_switch` 的 normalized ratio 定位為輔助比值而非獨立因果成本模型，可能因分母的 Qt 解码速度或 CPU 噪声变化而误报。本轮保持现有校准方式；后续建议加入同画布、同图层数、同 alpha 合成路径的 matched compositor calibration，再与现行比值并行验证。

## English

`tools/bench_composite.py` measures the shipped full-body and half-body layered renderers directly under `QT_QPA_PLATFORM=offscreen`. Each execution's metric p95 can be appended to `tools/perf_budget.json` with `--record`; the normal gate test leaves the tracked budget unchanged.

Every environment × metric stores `samples_ms`, `sample_count`, and `observed_spread` (min/median/p95). With fewer than 3 samples, `gating=false` requires a non-empty `reason`; the test records the observation and prints that the metric is not gated because samples are insufficient. A metric gates only at 3 or more samples.

The gate is fixed as `max(max(observed p95) * 1.5, owner target)`, where observed p95 is one aggregate p95 per independent execution. No effective threshold exists below three observations. All six environment × metric combinations currently have only 0–1 independent execution, so all are record-only; this is not a skipped test, and the data shape plus tests constrain `gating=false`. Each `--record` appends exactly one aggregate p95 for that execution; a combination becomes gated only after reaching n=3, when its spread and threshold are recomputed.

Current data:

| Environment × metric | n | min / median / p95 (ms) | Status / threshold (ms) |
| --- | ---: | ---: | --- |
| developer × cold_full_body | 1 | 1337.497 / 1337.497 / 1337.497 | not gated / insufficient samples |
| developer × hot_full_body_view_switch | 1 | 4.861 / 4.861 / 4.861 | not gated / insufficient samples |
| developer × hot_half_body_silhouette_switch | 1 | 5.731 / 5.731 / 5.731 | not gated / insufficient samples |
| CI × cold_full_body | 1 | 1722.333 / 1722.333 / 1722.333 | not gated / insufficient samples |
| CI × hot_full_body_view_switch | 0 | — / — / — | not gated / insufficient samples |
| CI × hot_half_body_silhouette_switch | 0 | — / — / — | not gated / insufficient samples |

### Calibration assessment

The existing normalized-ratio assertion remains available when enough paired samples exist, but 100000 decodes of a fixed 1×1 PNG with `QImage.fromData` represent the fixed decode baseline, while the compositor path measures a warmed half-body switch: that switch paints multiple RGBA layers on a 1254×1254 canvas, and the decode audit shows no new PNG decode on the warmed switch. Therefore the `hot_half_body_silhouette_switch` ratio serves as an auxiliary ratio rather than an independent causal cost model and can misreport when Qt decode speed or CPU noise changes in the denominator. This change deliberately keeps the existing ruler. A future improvement should add a matched compositor calibration with the same canvas, layer count, and alpha-compositing path, then compare it with the current ratio in parallel.

## 日本語

`tools/bench_composite.py` は `QT_QPA_PLATFORM=offscreen` で正式な全身・半身レイヤー renderer を直接測定します。各実行の指標 p95 は `--record` で `tools/perf_budget.json` に追記できます。通常のゲートテストは管理対象の予算ファイルを書き換えません。

環境 × 指標ごとに `samples_ms`、`sample_count`、`observed_spread`（min／median／p95）を保存します。3 未満のサンプルでは `gating=false` に空でない `reason` が必須で、観測だけを記録し「サンプル不足のためゲート待機」と表示します。3 以上になった指標だけをゲートします。

ゲートは `max(max(observed p95) * 1.5, owner target)` と定義し、observed p95 は独立実行ごとに 1 件の aggregate p95 とします。3 未満では有効な閾値を作りません。現在は 6 つの環境 × 指標組み合わせがすべて独立実行 0–1 回のため、すべて記録のみです。これはテストのスキップではなく、`gating=false` はデータ形状とテストで制約されます。`--record` は実行ごとに aggregate p95 を 1 件だけ追記し、各組み合わせが n=3 に達した時点で散布と閾値を再計算してゲートを有効化します。

現在のデータ：

| 環境 × 指標 | n | min／median／p95 (ms) | 状態／閾値 (ms) |
| --- | ---: | ---: | --- |
| developer × cold_full_body | 1 | 1337.497／1337.497／1337.497 | 非ゲート／サンプル不足 |
| developer × hot_full_body_view_switch | 1 | 4.861／4.861／4.861 | 非ゲート／サンプル不足 |
| developer × hot_half_body_silhouette_switch | 1 | 5.731／5.731／5.731 | 非ゲート／サンプル不足 |
| CI × cold_full_body | 1 | 1722.333／1722.333／1722.333 | 非ゲート／サンプル不足 |
| CI × hot_full_body_view_switch | 0 | —／—／— | 非ゲート／サンプル不足 |
| CI × hot_half_body_silhouette_switch | 0 | —／—／— | 非ゲート／サンプル不足 |

### 校正尺の判断

既存の正規化比率アサーションは、十分な対応サンプルがある場合に残します。ただし固定 1×1 PNG を `QImage.fromData` で 100000 回 decode する処理は、暖機済み半身切替を固定 decode 基準を表し、暖機済み半身切替は合成経路で個別に測定します。半身切替は 1254×1254 キャンバスで複数の RGBA レイヤーを描画し、decode audit でも暖機済み切替に新しい PNG decode はありません。そのため `hot_half_body_silhouette_switch` の比率は独立した因果コストモデルではなく補助比率として機能し、分母の Qt decode 速度や CPU ノイズの変動で誤判定し得ます。今回は既存の校正方式を維持します。将来は同じキャンバス、レイヤー数、alpha 合成経路を使う matched compositor calibration を追加し、現行比率と並行して検証することを推奨します。
