# 標準渲染基準／标准渲染基准／Golden render baseline／標準レンダー基準

## 繁體中文

`tools/golden_render.py` 使用正式的半身、全身與服裝疊加渲染路徑，在離線、`QT_QPA_PLATFORM=offscreen`、隔離且固定的 store／`LOCALAPPDATA` 下產生 352 張 RGBA PNG。版控只保存 `tests/golden/golden-manifest.json`；比對依解碼後的 RGBA 像素與尺寸計算 SHA-256，逐像素容忍為 0，不依賴 PNG 壓縮位元組。

執行 `python tools/golden_render.py` 重新渲染並比對。畫面變更符合預期時，由專案擁有者查看 `.quality-tmp/golden-diff/` 的 `original.png`、`new.png`、`difference.png`，建立含 `owner`、ISO `date`、`quote` 與完整 `cells`（或 `"*"`）的 `mohan.golden-render-approval.v1` JSON，再執行 `python tools/golden_render.py --update --approval <approval.json>`。缺少或未完整涵蓋矩陣的核准紀錄會拒絕更新。

矩陣為半身 25 表情 × 4 妝 × 3 眼態共 300 格，加上全身 13 角度 × 4 妝共 52 格；依妝容拆成 4 個測試模組，各 88 格，由 `tests/run_all.py --aggregate --shard-count 8 --shard-index <0..7>` 平均分配到分片。比對失敗時，Windows CI 會上傳差異圖供擁有者審閱。

## 简体中文

`tools/golden_render.py` 使用正式的半身、全身与服装叠加渲染路径，在离线、`QT_QPA_PLATFORM=offscreen`、隔离且固定的 store／`LOCALAPPDATA` 下生成 352 张 RGBA PNG。版本控制只保存 `tests/golden/golden-manifest.json`；比较按解码后的 RGBA 像素与尺寸计算 SHA-256，逐像素容忍为 0，不依赖 PNG 压缩字节。

运行 `python tools/golden_render.py` 重新渲染并比较。画面变化符合预期时，由项目所有者查看 `.quality-tmp/golden-diff/` 的 `original.png`、`new.png`、`difference.png`，创建包含 `owner`、ISO `date`、`quote` 与完整 `cells`（或 `"*"`）的 `mohan.golden-render-approval.v1` JSON，再运行 `python tools/golden_render.py --update --approval <approval.json>`。缺少或未完整覆盖矩阵的核准记录会拒绝更新。

矩阵为半身 25 表情 × 4 妆 × 3 眼态共 300 格，加上全身 13 角度 × 4 妆共 52 格；按妆容拆成 4 个测试模块，各 88 格，由 `tests/run_all.py --aggregate --shard-count 8 --shard-index <0..7>` 平均分配到分片。比较失败时，Windows CI 会上传差异图供所有者审阅。

## English

`tools/golden_render.py` uses the production half-body, full-body, and active-outfit composition paths to generate 352 RGBA PNGs offline with `QT_QPA_PLATFORM=offscreen` and isolated, fixed store and `LOCALAPPDATA` locations. Git stores only `tests/golden/golden-manifest.json`. Comparison hashes decoded RGBA pixels plus dimensions with zero per-pixel tolerance, independent of PNG compression bytes.

Run `python tools/golden_render.py` to render and compare. When a visual change is intentional, the project owner reviews `original.png`, `new.png`, and `difference.png` under `.quality-tmp/golden-diff/`, creates a `mohan.golden-render-approval.v1` JSON containing `owner`, ISO `date`, `quote`, and every changed `cells` ID (the entire matrix for an initial baseline, or `"*"`), then runs `python tools/golden_render.py --update --approval <approval.json>`. An absent or incomplete approval record cannot update the baseline.

The matrix holds 300 half-body cells (25 expressions × 4 makeup looks × 3 eye states) and 52 full-body cells (13 angles × 4 makeup looks). It is split by makeup into 4 test modules of 88 cells each, which `tests/run_all.py --aggregate --shard-count 8 --shard-index <0..7>` spreads across shards. When a comparison fails, Windows CI uploads the difference images for the owner to review.

## 日本語

`tools/golden_render.py` は正式な半身・全身・衣装合成経路を使用し、オフライン、`QT_QPA_PLATFORM=offscreen`、分離された固定 store／`LOCALAPPDATA` の条件で 352 枚の RGBA PNG を生成します。Git には `tests/golden/golden-manifest.json` のみを保存します。比較はデコード後の RGBA ピクセルと寸法の SHA-256 を使い、ピクセル許容値は 0 です。PNG 圧縮バイトには依存しません。

`python tools/golden_render.py` で再レンダーして比較します。意図した画面変更では、プロジェクト所有者が `.quality-tmp/golden-diff/` の `original.png`、`new.png`、`difference.png` を確認し、`owner`、ISO `date`、`quote`、対象となる全 `cells` ID（または `"*"`）を含む `mohan.golden-render-approval.v1` JSON を作成してから、`python tools/golden_render.py --update --approval <approval.json>` を実行します。承認記録がない場合、または対象が不足する場合、基準は更新されません。

マトリクスは半身 25 表情 × 4 メイク × 3 目の状態の 300 セルと、全身 13 角度 × 4 メイクの 52 セルです。メイクごとに 88 セルずつ 4 つのテストモジュールへ分割し、`tests/run_all.py --aggregate --shard-count 8 --shard-index <0..7>` がシャードへ均等に配分します。比較に失敗すると、Windows CI が差分画像をアップロードし、所有者が確認できます。
