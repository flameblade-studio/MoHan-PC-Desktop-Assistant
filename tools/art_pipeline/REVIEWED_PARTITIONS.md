# 分批分區接入／分批分区接入／Reviewed partition batches／確認済み領域のバッチ統合

## 繁體中文

進度查詢使用 `python -m tools.art_pipeline.partition_coverage MANIFEST EXPORT`，唯讀核對完成收據、證據及每張分區的原生像素後輸出 JSON。報告分列 yaw 來源識別碼、其他姿勢識別碼與待補的可見角色。識別碼只證明來源身分；實際拍攝角度、完整身體、600 層及正式換裝各自須有對應驗收證據。計數只納入收據完整且內容有效的批次。

彙整前也會重新計算各分區的尺寸、像素數、重疊與重建結果，交叉核對完成收據，並解碼每張輸出 PNG 比對原生 RGBA。驗證以原生像素及獨立證據為準，雜湊同步變更仍須通過內容核對；批次及分區目錄也須完整列出所有檔案。PNG 壓縮方式可以不同，但像素及證據必須一致。

跨批次彙整使用 `python -m tools.art_pipeline.consolidate_partitions --batch OLD_MANIFEST OLD_EXPORT --batch OTHER_MANIFEST OTHER_EXPORT --manifest NEW_MANIFEST --output NEW_EXPORT`。每個輸入須有與清單綁定的完成收據；逐檔核對輸出及原始來源、遮罩與明列雜湊的審閱證據。同視角須使用單一一致來源，各角色唯一且像素互斥。使用既有接入程式從原圖重建聯集分區及單一 `remaining_foreground`，以原圖重建結果取代舊批次剩餘區域的疊加。只有最後寫入完成收據的輸出表示成功；新清單本身是中間產物。此操作的成果範圍是彙整既有分區，正式換裝仍須通過其專屬驗收。

`review` 提供 `evidence_sha256` 或 `trace_sha256` 時，對應的 `evidence` 或 `trace` 必須是非空檔案路徑。接入前會核對雜湊並保留快照；輸出只採用編碼期間保持一致的位元組。相對路徑以清單位置為準。舊批次的描述文字仍可讀取，而已驗證證據檔案須提供雜湊。

`python -m tools.art_pipeline.reviewed_partitions batch.json new-output` 將已目視確認的可見髮型、上衣及短褲遮罩接到同一個產線入口。清單使用 `mohan.reviewed-visible-partitions.v1`；每筆 `entries` 提供唯一 `id`、含 `path` 與 `sha256` 的 RGBA `source`，以及 `parts`。各分區包含 `role`、同格式的二值 `mask`，以及 `review`：`decision=accept_visible_partition`、`reviewer`、`source_sha256`、`mask_sha256`。相對路徑以清單位置為準。

角色範圍是 `visible_core_hair`、`visible_upper_garment`、`visible_shorts`、`visible_left_hand`、`visible_right_hand`。整批先驗證來源、審閱綁定、原生尺寸及互斥歸屬，後建立全新輸出，且輸出路徑須為新目錄。保留每個 RGBA 像素，待分類區域明列為 `remaining_foreground`；身體角色須有獨立審閱證據。`receipt.json` 最後寫入，只有含此收據的目錄表示完成。此階段成果是可見分區產線接入；可換裝、可眨眼正式外觀包與 24 視角／600 層各自依專屬驗收決定完成狀態。

左右手使用角色本人的解剖學方向。腕部與前臂相連時，審閱證據須明列原生座標的關節分界；這項證據只確認可見像素歸屬；被遮住的手須另有補齊證據。待補角色表示該分區仍待建立，原圖是否露出雙手則由原生像素決定。

半身執行期手部遮罩放在 `assets/expressions/layered/{view_id}_visible_hand_{left|right}.png`。逐姿勢檔案優先於 `front`、`cheek`、`lean` 共用骨架檔；任一逐姿勢檔存在即要求完整有效的左右一對，並只載入通過完整性驗證的配對。完整透明的一對表示該姿勢的可見手部集合為空，並保持該姿勢的明確結果。來源分區仍須完成自身審閱；正式接入另須完成相應審閱與接入閘門。

## 简体中文

进度查询使用 `python -m tools.art_pipeline.partition_coverage MANIFEST EXPORT`，只读核对完成收据、证据及每张分区的原始像素后输出 JSON。报告分别列出 yaw 来源标识、其他姿势标识与待补的可见角色。标识只证明来源身份；实际拍摄角度、完整身体、600 层及正式换装各自须有对应验收证据。计数只纳入收据完整且内容有效的批次。

汇总前也会重新计算各分区的尺寸、像素数、重叠与重建结果，交叉核对完成收据，并解码每张输出 PNG 比对原生 RGBA。验证以原生像素和独立证据为准，哈希同步变更仍须通过内容核对；批次及分区目录也须完整列出所有文件。PNG 压缩方式可以不同，但像素及证据必须一致。

跨批次汇总使用 `python -m tools.art_pipeline.consolidate_partitions --batch OLD_MANIFEST OLD_EXPORT --batch OTHER_MANIFEST OTHER_EXPORT --manifest NEW_MANIFEST --output NEW_EXPORT`。每个输入须有与清单绑定的完成收据；逐文件核对输出及原始来源、遮罩和明确哈希的审阅证据。同视角须使用单一一致来源，各角色唯一且像素互斥。通过既有接入程序从原图重建并集分区和单一 `remaining_foreground`，以原图重建结果取代旧批次剩余区域的叠加。只有最后写入完成收据的输出表示成功；新清单本身是中间产物。此操作的成果范围是汇总现有分区，正式换装仍须通过其专属验收。

`review` 提供 `evidence_sha256` 或 `trace_sha256` 时，对应的 `evidence` 或 `trace` 必须是非空文件路径。接入前校验哈希并保留快照；输出只采用编码期间保持一致的字节。相对路径以清单位置为准。旧批次的描述文字仍可读取，而已验证证据文件须提供哈希。

`python -m tools.art_pipeline.reviewed_partitions batch.json new-output` 将已目视确认的可见头发、上衣及短裤遮罩接入统一产线。清单使用 `mohan.reviewed-visible-partitions.v1`；`entries` 中每项包含唯一 `id`、带 `path` 和 `sha256` 的 RGBA `source`，以及 `parts`。分区包含 `role`、同格式的二值 `mask` 和 `review`：`decision=accept_visible_partition`、`reviewer`、`source_sha256`、`mask_sha256`。相对路径基于清单目录。

角色限于 `visible_core_hair`、`visible_upper_garment`、`visible_shorts`、`visible_left_hand`、`visible_right_hand`。整批验证来源、审阅绑定、原始尺寸和互斥归属后才创建新输出，且输出路径须为新目录。所有 RGBA 像素保持不变；`remaining_foreground` 是待分类余项，身体角色须有独立审阅证据。最后写入 `receipt.json`，只有含此收据的目录表示完成。这一阶段成果是可见分区产线接入；正式换装、眨眼包与 24 视角／600 层各自依据专属验收决定完成状态。

左右手使用角色本人的解剖学方向。手腕与前臂相连时，审阅证据须记录原始坐标的关节分界；这项证据只确认可见像素归属；被遮住的手须另有补齐证据。待补角色表示该分区仍待建立，原图是否露出双手则由原生像素决定。

半身运行时手部遮罩放在 `assets/expressions/layered/{view_id}_visible_hand_{left|right}.png`。逐姿势文件优先于 `front`、`cheek`、`lean` 共用骨架文件；任一逐姿势文件存在即要求完整有效的左右一对，并只载入通过完整性验证的配对。完整透明的一对表示该姿势的可见手部集合为空，并保持该姿势的明确结果。来源分区仍须完成自身审阅；正式接入还须完成相应审阅与接入关卡。

## English

Run `python -m tools.art_pipeline.partition_coverage MANIFEST EXPORT` to read and verify completion receipts, evidence and native partition pixels before emitting JSON. The report separates yaw source identifiers, other pose identifiers, and visible roles awaiting completion. Labels establish source identity only; camera angle, complete body, 600-layer status, and production wardrobe acceptance each require their own evidence. Counts include only batches with complete receipts and valid contents.

Before consolidation, partition dimensions, pixel counts, overlap and reconstruction results are recomputed and checked against the completion receipt. Every output PNG is decoded and compared with native RGBA. Validation follows native pixels and independent evidence, so synchronized hash changes still undergo content checks; batch and entry directories must also list every file. PNG compression may differ, but pixels and evidence must agree.

Use `python -m tools.art_pipeline.consolidate_partitions --batch OLD_MANIFEST OLD_EXPORT --batch OTHER_MANIFEST OTHER_EXPORT --manifest NEW_MANIFEST --output NEW_EXPORT` to consolidate completed batches. Each input requires a completed receipt bound to its manifest; output files, native sources, masks and explicitly hashed review evidence are verified. Each view uses one consistent source, each role is unique, and pixel ownership is disjoint. The existing integrator rebuilds the union and one `remaining_foreground` from native sources, using that reconstruction in place of accumulated old complements. Only the final export receipt denotes success; a new manifest by itself is an intermediate artifact. Consolidation covers existing partitions, while production wardrobe readiness follows its dedicated acceptance process.

When `review` supplies `evidence_sha256` or `trace_sha256`, the corresponding `evidence` or `trace` must be a nonempty file path. Its hash is checked and bytes are snapshotted; output creation uses only bytes that remain stable during encoding. Relative paths resolve from the manifest. Legacy unhashed prose remains supported as descriptive text, while verified file evidence includes a hash.

`python -m tools.art_pipeline.reviewed_partitions batch.json new-output` integrates visually reviewed hair, top and shorts masks through one tooling entry point. The manifest schema is `mohan.reviewed-visible-partitions.v1`. Each `entries` item has a unique `id`, an RGBA `source` with `path` and `sha256`, and `parts`. Each part includes `role`, a binary `mask` with the same path/hash format, and `review`: `decision=accept_visible_partition`, `reviewer`, `source_sha256`, `mask_sha256`. Relative paths resolve from the manifest directory.

The role set is `visible_core_hair`, `visible_upper_garment`, `visible_shorts`, `visible_left_hand`, and `visible_right_hand`. The whole batch validates source identity, review binding, native dimensions and disjoint ownership before creating a new output; the output path must be new. Every RGBA pixel is preserved. `remaining_foreground` is a complement awaiting classification; a body role requires separate review evidence. The final `receipt.json` marks completion, so only a directory containing that receipt is complete. This stage integrates visible partitions into tooling; production wardrobe/blink acceptance and 24-view/600-layer completion follow their dedicated criteria.

Hand sides are anatomical. Where wrist and forearm remain connected, review evidence records the native joint boundary as visible pixel ownership. Hidden hand surfaces require separate completion evidence. A role awaiting completion means its partition is pending, while native pixels determine whether each source shows both hands.

Half-body runtime hand masks use `assets/expressions/layered/{view_id}_visible_hand_{left|right}.png`. Pose-specific pairs take precedence over shared `front`, `cheek`, or `lean` rig files. Either pose file requires a complete valid pair; only pairs that pass integrity validation are loaded. An explicitly transparent pair defines an empty visible-hand set for that pose and preserves that explicit pose result. Source partitions still require their own review; formal integration separately requires the corresponding review and integration gates.

## 日本語

`python -m tools.art_pipeline.partition_coverage MANIFEST EXPORT` は完了記録、証拠、各領域の原寸画素を読み取り検証して JSON を出力します。yaw の原画識別子、その他の姿勢識別子、完了待ちの可視役割を分けて表示します。識別子は原画の同一性だけを証明します。実際の撮影角度、身体全体、600 層、正式な着せ替えは、それぞれ専用の合格証拠を必要とします。集計には完了記録と内容検証が揃ったバッチだけを含めます。

統合前に各領域の寸法、画素数、重複、再構築結果を再計算して完了受領記録と照合し、各出力 PNG を復号して原寸 RGBA と比較します。検証は原寸画素と独立証拠を基準とするため、ハッシュを同時変更した場合も内容照合を行います。バッチと領域ディレクトリは全ファイルを記載する必要があります。PNG 圧縮方式は異なっても、画素と証拠は一致する必要があります。

`python -m tools.art_pipeline.consolidate_partitions --batch OLD_MANIFEST OLD_EXPORT --batch OTHER_MANIFEST OTHER_EXPORT --manifest NEW_MANIFEST --output NEW_EXPORT` で完了バッチを統合します。各入力にはマニフェストに関連付けた完了受領記録が必要で、出力、原画、マスク、ハッシュ付き確認証拠を検証します。同一視点は一つの整合した原画を使い、各役割を一意にして画素所有を排他的にします。既存の統合処理で原画から領域の和集合と単一の `remaining_foreground` を再構築し、原画からの再構築結果を旧バッチ残部の累積に代えて使用します。最後の出力受領記録だけが成功を示し、新マニフェスト単体は中間成果物です。この操作の範囲は既存領域の統合で、正式な着せ替え対応は専用の受入手順で決定します。

`review` に `evidence_sha256` または `trace_sha256` がある場合、対応する `evidence` または `trace` は空でないファイルパスである必要があります。ハッシュとバイト列のスナップショットを検証し、出力作成にはエンコード中も一貫したバイト列だけを使用します。相対パスはマニフェストを基準に解決します。ハッシュのない旧形式の説明文も引き続き読めます。検証済み証拠ファイルにはハッシュが必要です。

`python -m tools.art_pipeline.reviewed_partitions batch.json new-output` は目視確認済みの髪、上着、ショートパンツのマスクを共通の制作入口へ統合します。スキーマは `mohan.reviewed-visible-partitions.v1`。`entries` の各項目には固有の `id`、`path` と `sha256` を持つ RGBA `source`、`parts` を指定します。各領域には `role`、同じ形式の二値 `mask`、`review`（`decision=accept_visible_partition`、`reviewer`、`source_sha256`、`mask_sha256`）が必要です。相対パスの基準はマニフェストのディレクトリです。

役割は `visible_core_hair`、`visible_upper_garment`、`visible_shorts`、`visible_left_hand`、`visible_right_hand` に限定します。全件の原画、確認記録、原寸、排他的所有を検証してから新規出力を作成し、出力先には新規ディレクトリを使用します。全 RGBA 画素を保持し、`remaining_foreground` は分類待ちの残部で、身体役割には別途確認証拠が必要です。最後に `receipt.json` を書き込み、この記録を含むディレクトリだけを完了済みと扱います。この段階の成果は可視領域の制作工程への統合です。正式な着せ替え・瞬きパックや 24 視点／600 層の完成は、それぞれ専用の受入条件で決定します。

左右は人物の解剖学的な方向です。手首と前腕が連続する場合、確認記録に原寸座標の関節境界を示します。これは可視画素の所有を示します。隠れた手には別途補完証拠が必要です。完了待ちの役割は該当領域の登録待ちを示し、両手の可視状態は各原画の原寸画素で決定します。

半身の実行時手マスクは `assets/expressions/layered/{view_id}_visible_hand_{left|right}.png` を使用します。姿勢別の組を共通の `front`、`cheek`、`lean` より優先し、片方でも存在すれば有効な左右両方を要求します。完全性検証を通過した組だけを読み込み、明示的に透明な組はその姿勢の可視手集合を空として保持します。原画領域には引き続き個別の確認が必要です。正式統合には、対応する確認と統合の関門を別途通過する必要があります。
