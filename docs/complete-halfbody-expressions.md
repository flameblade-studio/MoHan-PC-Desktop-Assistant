# 完整半身表情來源／完整半身表情来源／Complete half-body expression sources／完全な半身表情ソース

## 繁體中文

`complete_halfbody_expressions.py` 載入完整半身表情，`complete_halfbody_renderer.py` 保留目前畫面嘴型與眨眼的對應，`LayeredParametricFaceRenderer` 負責選擇新來源或既有路徑。衣裝、妝容與髮型仍由外觀合成器處理。此路徑正在 staging 驗證；目前沒有正式安裝的 manifest。原圖批准、接合批准、技術驗證及正式安裝必須分別記錄。

### 安裝契約

選填的 manifest 位於 `authority_dir/complete-expressions/manifest.json`，schema 為 `mohan.complete-halfbody-expressions.v1`。目錄不存在時沿用既有渲染；目錄存在但 manifest 缺失或無效時明確失敗。

- `poses` 可包含 `detachable_halfbody_assets.POSES` 中的七個名稱。
- 每個列入的姿勢都需要非空的 `source_lineage`、四個完整家族（`neutral`、`small`、`a`、`o`）與全部三個眼睛狀態（`rest`、`half`、`closed`）。
- 每個來源是相對可攜路徑加 SHA-256 紀錄，對應 1254 × 1254、8 位元 RGBA、同時含透明與可見像素的 PNG。路徑不能離開 manifest 目錄。來源位元組在載入時驗證並凍結。
- `expressions` 明確把既有表情名稱對應到姿勢與嘴型家族。每個已安裝姿勢都必須提供四個家族。未知表情名稱沿用既有路徑；任意情緒不會被默默對應到中性臉。
- 移除這個選填目錄後，重新建構渲染器即恢復既有路徑。不要就地編輯已載入的來源集合。

### 渲染與所有權

`render` 選擇完整的睜眼端點；嘴部開口為零時選用中性家族。既有半身動畫計時器透過 `render_overlay` 請求離散眨眼。Pixmap 快取鍵保留目前顯示端點的姿勢與嘴型家族，包含說話轉場產生的複本。內容快取保存兩組完整集合（七個姿勢 × 四個嘴型家族 × 三個眼睛狀態）；解碼後的來源影像另有 24 張的 LRU 上限。

外觀轉接器收到每個來源的複本與目前眼睛狀態。半閉與閉眼時抑制眼妝槽位。合併的 `apply` 與原子化的 `apply_animated` 契約都有專屬轉接器測試涵蓋。完整衣櫃選擇、舊核心身體還原、所有妝容外觀與每種外觀組合仍需各來源的整合證據；單靠這些測試不能宣稱涵蓋。

整頭接合必須取代舊頭部的完整 alpha 範圍，包含雙耳。只疊上新頭會在輪廓外露出舊五官。在已批准的 front-crossed 修復中，原生身體 alpha 在第 620 列以上為零，並在第 638 列前平滑恢復，早於第 640 列開始的標準頸部 alpha 漸變。這些座標只適用該已配準姿勢，不得套用到其他角度。已批准的臉部像素、接合處以下的頸部，以及獨立的衣裝／手部圖層分別檢查。

### 證據與限制

標準範圍與來源批准位於 `scratchpad/mohan-canonical-hairline-18/global-authority.json`；視角／動作涵蓋位於 `scratchpad/mohan-canonical-global-progress-32/coverage.json`。雙耳重複修復與其擁有者批准位於 `scratchpad/mohan-canonical-halfbody-ear-repair-50`。

目前的來源家族提供 SMALL、A 與 O。I／E／U 沿用既有別名，不是獨立製作的來源。正面 staging 渲染不代表完整的 24 視角／七動作／四妝容完成度或發行就緒。

## 简体中文

`complete_halfbody_expressions.py` 加载完整半身表情，`complete_halfbody_renderer.py` 保留当前画面嘴型与眨眼的对应，`LayeredParametricFaceRenderer` 负责选择新来源或既有路径。衣装、妆容与发型仍由外观合成器处理。此路径正在 staging 验证；目前没有正式安装的 manifest。原图批准、接合批准、技术验证及正式安装必须分别记录。

### 安装契约

可选的 manifest 位于 `authority_dir/complete-expressions/manifest.json`，schema 为 `mohan.complete-halfbody-expressions.v1`。目录不存在时沿用既有渲染；目录存在但 manifest 缺失或无效时明确失败。

- `poses` 可包含 `detachable_halfbody_assets.POSES` 中的七个名称。
- 每个列入的姿势都需要非空的 `source_lineage`、四个完整家族（`neutral`、`small`、`a`、`o`）与全部三个眼睛状态（`rest`、`half`、`closed`）。
- 每个来源是相对可携路径加 SHA-256 记录，对应 1254 × 1254、8 位 RGBA、同时含透明与可见像素的 PNG。路径不能离开 manifest 目录。来源字节在加载时验证并冻结。
- `expressions` 明确把既有表情名称对应到姿势与嘴型家族。每个已安装姿势都必须提供四个家族。未知表情名称沿用既有路径；任意情绪不会被默默对应到中性脸。
- 移除这个可选目录后，重新构建渲染器即恢复既有路径。不要就地编辑已加载的来源集合。

### 渲染与所有权

`render` 选择完整的睁眼端点；嘴部开口为零时选用中性家族。既有半身动画计时器通过 `render_overlay` 请求离散眨眼。Pixmap 缓存键保留当前显示端点的姿势与嘴型家族，包含说话转场产生的副本。内容缓存保存两组完整集合（七个姿势 × 四个嘴型家族 × 三个眼睛状态）；解码后的来源图像另有 24 张的 LRU 上限。

外观适配器收到每个来源的副本与当前眼睛状态。半闭与闭眼时抑制眼妆槽位。合并的 `apply` 与原子化的 `apply_animated` 契约都有专属适配器测试覆盖。完整衣柜选择、旧核心身体还原、所有妆容外观与每种外观组合仍需各来源的集成证据；单靠这些测试不能宣称覆盖。

整头接合必须取代旧头部的完整 alpha 范围，包含双耳。只叠上新头会在轮廓外露出旧五官。在已批准的 front-crossed 修复中，原生身体 alpha 在第 620 行以上为零，并在第 638 行前平滑恢复，早于第 640 行开始的标准颈部 alpha 渐变。这些坐标只适用该已配准姿势，不得套用到其他角度。已批准的脸部像素、接合处以下的颈部，以及独立的衣装／手部图层分别检查。

### 证据与限制

标准范围与来源批准位于 `scratchpad/mohan-canonical-hairline-18/global-authority.json`；视角／动作覆盖位于 `scratchpad/mohan-canonical-global-progress-32/coverage.json`。双耳重复修复与其所有者批准位于 `scratchpad/mohan-canonical-halfbody-ear-repair-50`。

目前的来源家族提供 SMALL、A 与 O。I／E／U 沿用既有别名，不是独立制作的来源。正面 staging 渲染不代表完整的 24 视角／七动作／四妆容完成度或发布就绪。

## English

`complete_halfbody_expressions.py` loads complete half-body expressions, `complete_halfbody_renderer.py` preserves the mapping between the displayed mouth and its blink, and `LayeredParametricFaceRenderer` chooses between the new sources and the existing route. Garments, makeup and hair are still composed by the appearance compositor. This route is being validated in staging; no production manifest is installed. Original-source acceptance, fitted-frame acceptance, runtime verification and formal installation are separate evidence states.

### Installation contract

The optional manifest is `authority_dir/complete-expressions/manifest.json` with schema `mohan.complete-halfbody-expressions.v1`. An absent directory preserves legacy rendering. An existing directory with a missing or invalid manifest fails explicitly.

- `poses` may include the seven names in `detachable_halfbody_assets.POSES`.
- Every included pose requires nonempty `source_lineage`, four complete families (`neutral`, `small`, `a`, `o`), and all three eye states (`rest`, `half`, `closed`).
- Each source is a relative portable path and SHA-256 record for a 1254 × 1254, 8-bit RGBA PNG containing both transparent and visible pixels. Paths cannot leave the manifest directory. Source bytes are validated and frozen at load time.
- `expressions` explicitly maps existing expression names to a pose and mouth family. Every installed pose must expose all four families. Unknown expression names keep the legacy route; arbitrary emotions are not silently mapped to a neutral face.
- Removing this optional directory restores the legacy route after constructing a new renderer. Do not edit a loaded source set in place.

### Rendering and ownership

`render` selects a complete open-eye endpoint; zero mouth aperture selects its neutral family. Existing half-body animation timers request discrete blinking through `render_overlay`. Pixmap cache keys retain the displayed endpoint's pose and mouth family, including copies made by speech transitions. The context cache holds two full sets of seven poses × four mouth families × three eye states; decoded source images have a separate 24-image LRU limit.

Appearance adapters receive a copy of each source and the current eye state. Eye makeup slots are suppressed during half/closed blinking. Both the combined `apply` and the atomic `apply_animated` contracts are covered by focused adapter tests. Full wardrobe-store selection, old core-body restoration, all makeup looks and every appearance combination still require source-specific integration evidence; those tests alone do not establish that coverage.

Whole-head fitting must replace the old head's complete alpha footprint, including both ears. Merely overlaying a new head can expose old features outside its silhouette. In the approved front-crossed repair, native-body alpha is zero above row 620 and returns smoothly by row 638, before the canonical neck alpha fade begins at row 640. These coordinates are specific to that registered pose and must not be reused for other angles. The approved face pixels, the neck below the join, and the separate garment/hand layers are checked independently.

### Evidence and limitations

The canonical scope and source approvals are in `scratchpad/mohan-canonical-hairline-18/global-authority.json`; view/action coverage is in `scratchpad/mohan-canonical-global-progress-32/coverage.json`. The duplicate-ear repair and its owner approval are in `scratchpad/mohan-canonical-halfbody-ear-repair-50`.

The current source family provides SMALL, A and O. I/E/U use existing aliases and are not independently authored sources. No full 24-view / seven-action / four-makeup completeness or production readiness is implied by the frontal staging render.

## 日本語

`complete_halfbody_expressions.py` が完全な半身表情を読み込み、`complete_halfbody_renderer.py` が表示中の口形と瞬きの対応を保持し、`LayeredParametricFaceRenderer` が新ソースと既存経路を選択します。衣装・化粧・髪型は引き続き外観コンポジタが合成します。この経路は staging で検証中で、正式な manifest は未導入です。原画承認、接合承認、技術検証、正式導入は別々の証拠状態として記録します。

### 導入契約

任意の manifest は `authority_dir/complete-expressions/manifest.json` にあり、schema は `mohan.complete-halfbody-expressions.v1` です。ディレクトリが無ければ既存の描画を維持し、ディレクトリがあるのに manifest が欠落または無効なら明示的に失敗します。

- `poses` には `detachable_halfbody_assets.POSES` の七つの名前を含められます。
- 含めた各ポーズには空でない `source_lineage`、四つの完全なファミリー（`neutral`、`small`、`a`、`o`）、三つの目の状態（`rest`、`half`、`closed`）すべてが必要です。
- 各ソースは相対的な可搬パスと SHA-256 記録で、透明画素と可視画素を両方含む 1254 × 1254 の 8 ビット RGBA PNG を指します。パスは manifest ディレクトリの外に出られません。ソースのバイト列は読み込み時に検証して凍結します。
- `expressions` は既存の表情名をポーズと口形ファミリーへ明示的に対応付けます。導入済みの各ポーズは四つのファミリーすべてを公開する必要があります。未知の表情名は既存経路を維持し、任意の感情が黙って中立顔へ対応付けられることはありません。
- この任意ディレクトリを削除すると、レンダラーを再構築した時点で既存経路に戻ります。読み込み済みのソース集合をその場で編集しないでください。

### 描画と所有権

`render` は完全な開眼エンドポイントを選び、口の開きがゼロなら中立ファミリーを選びます。既存の半身アニメーションタイマーは `render_overlay` を通じて離散的な瞬きを要求します。Pixmap のキャッシュキーは、発話遷移で作られた複製を含め、表示中エンドポイントのポーズと口形ファミリーを保持します。コンテキストキャッシュは七ポーズ × 四口形ファミリー × 三目状態の完全な集合を二組保持し、デコード済みソース画像には別途 24 枚の LRU 上限があります。

外観アダプタは各ソースの複製と現在の目の状態を受け取ります。半閉・閉眼の瞬き中は目のメイクスロットを抑制します。結合された `apply` と原子的な `apply_animated` の両契約は専用のアダプタテストで検証済みです。完全なワードローブ選択、旧コアボディの復元、すべてのメイク外観、あらゆる外観の組み合わせには引き続きソースごとの統合証拠が必要で、これらのテストだけで網羅を主張することはできません。

頭部全体の接合は両耳を含む旧頭部の完全な alpha 範囲を置き換える必要があります。新しい頭部を重ねるだけでは輪郭の外に旧特徴が露出します。承認済みの front-crossed 修復では、ネイティブボディの alpha は 620 行より上でゼロになり、638 行までに滑らかに戻り、640 行から始まる標準の首 alpha フェードより手前です。これらの座標はその登録済みポーズ固有のもので、他の角度に再利用してはいけません。承認済みの顔画素、接合部より下の首、独立した衣装／手レイヤーはそれぞれ独立に検査します。

### 証拠と制限

標準範囲とソース承認は `scratchpad/mohan-canonical-hairline-18/global-authority.json` に、視点／動作の網羅は `scratchpad/mohan-canonical-global-progress-32/coverage.json` にあります。両耳重複の修復とその所有者承認は `scratchpad/mohan-canonical-halfbody-ear-repair-50` にあります。

現在のソースファミリーは SMALL、A、O を提供します。I／E／U は既存の別名を使い、独立に制作されたソースではありません。正面の staging 描画は 24 視点／七動作／四メイクの完全性や製品準備完了を意味しません。
